import json

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
