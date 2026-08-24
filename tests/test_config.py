import json
from pathlib import Path

from localscribe import config
from localscribe.config import AppConfig, ConfigStore
from localscribe.domain import CleanupMode


def test_config_round_trip(tmp_path) -> None:
    store = ConfigStore(tmp_path / "config.json")
    expected = AppConfig(mode=CleanupMode.BUSINESS, custom_words=["Kubernetes", "OpenAI"])
    store.save(expected)
    assert store.load() == expected


def test_corrupt_config_falls_back_to_defaults(tmp_path) -> None:
    path = tmp_path / "config.json"
    path.write_text("not json", encoding="utf-8")
    assert ConfigStore(path).load() == AppConfig()


def test_unknown_keys_are_ignored(tmp_path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"mode": "casual", "future_option": True}), encoding="utf-8")
    assert ConfigStore(path).load().mode is CleanupMode.CASUAL


def test_legacy_storage_is_migrated_to_renamed_app_directory(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("LOCALSCRIBE_DATA_DIR", raising=False)
    monkeypatch.setattr(config, "user_config_dir", lambda name: str(tmp_path / name))
    monkeypatch.setattr(config, "user_data_dir", lambda name: str(tmp_path / name))
    legacy = tmp_path / "LocalScribe Flow"
    legacy.mkdir()
    (legacy / "config.json").write_text(json.dumps({"mode": "business"}), encoding="utf-8")
    (legacy / "downloaded-model.bin").write_bytes(b"existing model")

    store = ConfigStore()

    assert store.path == tmp_path / "LocalScribe" / "config.json"
    assert store.load().mode is CleanupMode.BUSINESS
    assert (config.data_directory() / "downloaded-model.bin").read_bytes() == b"existing model"
    assert not legacy.exists()
