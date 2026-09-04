import pytest

from ytcli.download import batch
from ytcli.models import AppError, DownloadResult, SubtitleTracks
from ytcli.settings import Options, load_config
from ytcli.ui import cli


@pytest.fixture
def fake_download(monkeypatch):
    """Replace the real download with a recorder that reports two saved files."""
    calls: list[tuple[Options, str]] = []

    def fake(options, url, *args, **kwargs):
        calls.append((options, url))
        return DownloadResult(url=url, files=[options.out_dir / "a.srt"], warnings=["heads up"])

    monkeypatch.setattr(batch, "download", fake)
    return calls


def test_config_path_command(capsys):
    assert cli.main(["--config-path"]) == 0
    assert "config.toml" in capsys.readouterr().out


def test_show_config_command(capsys):
    assert cli.main(["--show-config"]) == 0
    out = capsys.readouterr().out
    assert 'mode          = "s"' in out
    assert "auto_subs     = true" in out


def test_save_config_without_a_url_exits_cleanly(capsys):
    assert cli.main(["--save-config", "-o", "/tmp/dl", "-m", "av"]) == 0
    stored = load_config({"output": "", "mode": ""})
    assert stored["output"] == "/tmp/dl"
    assert stored["mode"] == "av"
    assert "Saved defaults" in capsys.readouterr().out


def test_save_config_then_downloads_when_a_url_is_given(fake_download):
    assert cli.main(["--save-config", "URL"]) == 0
    assert len(fake_download) == 1


def test_downloads_every_url(fake_download, capsys):
    assert cli.main(["one", "two", "-m", "s"]) == 0
    assert [url for _options, url in fake_download] == ["one", "two"]
    out = capsys.readouterr().out
    assert "Done. 2 file(s)" in out
    assert "note: heads up" in out


def test_a_failing_url_sets_the_exit_code(monkeypatch, capsys):
    def boom(options, url, *args, **kwargs):
        raise AppError("nope")

    monkeypatch.setattr(batch, "download", boom)
    assert cli.main(["URL"]) == 1
    assert "error (URL): nope" in capsys.readouterr().err


def test_an_unexpected_error_does_not_escape(monkeypatch, capsys):
    def boom(options, url, *args, **kwargs):
        raise ValueError("weird")

    monkeypatch.setattr(batch, "download", boom)
    assert cli.main(["URL"]) == 1
    assert "unexpected error" in capsys.readouterr().err


def test_no_url_without_a_terminal_is_an_error(monkeypatch, capsys):
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: False)
    assert cli.main([]) == 1
    assert "no URL given" in capsys.readouterr().err


def test_a_bad_mode_reports_an_error_without_a_traceback(capsys):
    assert cli.main(["URL", "-m", "x"]) == 1
    assert "error:" in capsys.readouterr().err


def test_list_subs_prints_both_track_kinds(monkeypatch, capsys):
    monkeypatch.setattr(cli, "list_subtitles", lambda url, **kw: SubtitleTracks(("en",), ("de",)))
    assert cli.main(["URL", "--list-subs"]) == 0
    out = capsys.readouterr().out
    assert "manual   : en" in out
    assert "automatic: de" in out


def test_list_subs_without_a_url_is_an_error(capsys):
    assert cli.main(["--list-subs"]) == 1
    assert "needs a URL" in capsys.readouterr().err


def test_list_subs_reports_a_failure(monkeypatch, capsys):
    def boom(url, **kwargs):
        raise AppError("no info")

    monkeypatch.setattr(cli, "list_subtitles", boom)
    assert cli.main(["URL", "--list-subs"]) == 1
    assert "no info" in capsys.readouterr().err


def test_interrupting_returns_the_shell_convention(monkeypatch):
    def boom(options, url, *args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(batch, "download", boom)
    assert cli.main(["URL"]) == 130


def test_the_saved_defaults_are_used_for_a_later_run(fake_download):
    assert cli.main(["--save-config", "-m", "av", "--vq", "720"]) == 0
    assert cli.main(["URL"]) == 0
    options, _url = fake_download[0]
    assert options.modes == "av"
    assert options.video_quality == "720"


def test_interactive_flag_runs_the_wizard(monkeypatch, fake_download):
    answers = iter(["URL", "s", "", "", "", ""])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    assert cli.main(["-i"]) == 0
    assert fake_download[0][1] == "URL"


def test_cancelling_the_wizard_stops_the_run(monkeypatch, capsys):
    answers = iter(["URL", "s", "", "", "", "n"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    assert cli.main(["-i"]) == 1
    assert "Cancelled." in capsys.readouterr().out
