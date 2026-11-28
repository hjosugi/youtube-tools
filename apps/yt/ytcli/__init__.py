"""yt - one cross-platform tool for YouTube audio, video and subtitles."""

__version__ = "1.1.1"
__all__ = ["__version__", "main"]


def main() -> int:
    """Entry point kept here so `import ytcli` stays cheap."""
    from .ui.cli import main as _main

    return _main()
