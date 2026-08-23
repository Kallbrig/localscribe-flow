from localscribe.cli import build_parser


def test_cli_parses_cleanup_mode() -> None:
    args = build_parser().parse_args(["voice.wav", "--mode", "business"])
    assert args.mode == "business"
    assert args.audio.name == "voice.wav"
