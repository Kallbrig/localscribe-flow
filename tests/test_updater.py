import hashlib
import io
import json
from pathlib import Path
from typing import Any

import pytest

from localscribe import updater
from localscribe.updater import AvailableUpdate, UpdateError, download_update, find_update


class Response(io.BytesIO):
    def __init__(self, content: bytes, headers: dict[str, str] | None = None) -> None:
        super().__init__(content)
        self.headers = headers or {}

    def __enter__(self) -> "Response":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def release(version: str, digest: str) -> bytes:
    payload: dict[str, Any] = {
        "tag_name": f"v{version}",
        "html_url": f"https://github.com/example/releases/tag/v{version}",
        "assets": [
            {
                "name": f"LocalScribe-{version}-Setup.exe",
                "digest": f"sha256:{digest}",
                "browser_download_url": "https://github.com/example/installer.exe",
            }
        ],
    }
    return json.dumps(payload).encode()


def test_find_update_selects_new_verified_installer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(updater, "_request", lambda url: Response(release("1.2.0", "a" * 64)))

    result = find_update("1.1.9")

    assert result is not None
    assert result.version == "1.2.0"
    assert result.sha256 == "a" * 64


def test_find_update_rejects_asset_without_digest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(updater, "_request", lambda url: Response(release("2.0.0", "")))

    with pytest.raises(UpdateError, match="integrity digest"):
        find_update("1.0.0")


def test_download_update_verifies_sha256(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    content = b"verified installer"
    digest = hashlib.sha256(content).hexdigest()
    available = AvailableUpdate(
        "1.2.0",
        "https://github.com/example/installer.exe",
        "LocalScribe-1.2.0-Setup.exe",
        digest,
        "https://github.com/example/releases/tag/v1.2.0",
    )
    monkeypatch.setattr(
        updater,
        "_request",
        lambda url: Response(content, {"Content-Length": str(len(content))}),
    )

    result = download_update(available, tmp_path)

    assert result.installer_path.read_bytes() == content
    assert not result.installer_path.with_suffix(".exe.part").exists()


def test_download_update_removes_tampered_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    available = AvailableUpdate(
        "1.2.0",
        "https://github.com/example/installer.exe",
        "update-Setup.exe",
        "0" * 64,
        "https://github.com/example/releases/tag/v1.2.0",
    )
    monkeypatch.setattr(updater, "_request", lambda url: Response(b"tampered"))

    with pytest.raises(UpdateError, match="verification"):
        download_update(available, tmp_path)

    assert not (tmp_path / "update-Setup.exe.part").exists()
