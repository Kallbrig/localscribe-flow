from __future__ import annotations

import hashlib
import json
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse

RELEASE_API = "https://api.github.com/repos/Kallbrig/localscribe-flow/releases/latest"


class UpdateError(RuntimeError):
    pass


@dataclass(frozen=True)
class AvailableUpdate:
    version: str
    installer_url: str
    installer_name: str
    sha256: str
    release_url: str


@dataclass(frozen=True)
class DownloadedUpdate:
    version: str
    installer_path: Path
    release_url: str


def _version_tuple(value: str) -> tuple[int, ...]:
    core = value.strip().lower().removeprefix("v").split("-", 1)[0]
    try:
        return tuple(int(part) for part in core.split("."))
    except ValueError as exc:
        raise UpdateError(f"Invalid release version: {value}") from exc


def _request(url: str) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "LocalScribe-Flow-Updater",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    return urllib.request.urlopen(request, timeout=30)  # noqa: S310


def find_update(current_version: str) -> AvailableUpdate | None:
    with _request(RELEASE_API) as response:
        release = cast(dict[str, Any], json.load(response))
    tag = str(release.get("tag_name", ""))
    if not tag or _version_tuple(tag) <= _version_tuple(current_version):
        return None
    for raw_asset in release.get("assets", []):
        asset = cast(dict[str, Any], raw_asset)
        name = str(asset.get("name", ""))
        if not name.lower().endswith("-setup.exe"):
            continue
        digest = str(asset.get("digest", ""))
        checksum = digest.removeprefix("sha256:").lower()
        if (
            not digest.startswith("sha256:")
            or len(checksum) != 64
            or any(character not in "0123456789abcdef" for character in checksum)
        ):
            raise UpdateError("The update is missing its SHA-256 integrity digest")
        installer_url = str(asset["browser_download_url"])
        parsed_url = urlparse(installer_url)
        if parsed_url.scheme != "https" or parsed_url.hostname != "github.com":
            raise UpdateError("The update installer is not hosted securely by GitHub")
        return AvailableUpdate(
            version=tag.removeprefix("v"),
            installer_url=installer_url,
            installer_name=name,
            sha256=checksum,
            release_url=str(release.get("html_url", "")),
        )
    raise UpdateError("The latest release does not contain a Windows installer")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_update(
    update: AvailableUpdate,
    destination_dir: Path,
    progress: Callable[[int, int], None] | None = None,
) -> DownloadedUpdate:
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / update.installer_name
    if destination.is_file() and _file_sha256(destination) == update.sha256:
        return DownloadedUpdate(update.version, destination, update.release_url)
    partial = destination.with_suffix(destination.suffix + ".part")
    partial.unlink(missing_ok=True)
    try:
        with _request(update.installer_url) as response, partial.open("wb") as output:
            total = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
                downloaded += len(chunk)
                if progress:
                    progress(downloaded, total)
        if _file_sha256(partial) != update.sha256:
            raise UpdateError("The downloaded update failed SHA-256 verification")
        partial.replace(destination)
    except Exception:
        partial.unlink(missing_ok=True)
        raise
    return DownloadedUpdate(update.version, destination, update.release_url)
