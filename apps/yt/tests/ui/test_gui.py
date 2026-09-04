"""The GUI needs a display, so these are skipped on headless machines."""

import pytest

from ytcli.models import AppError
from ytcli.settings import Options

tk = pytest.importorskip("tkinter")


@pytest.fixture
def window():
    try:
        root = tk.Tk()
    except tk.TclError as error:  # no display
        pytest.skip(f"no display: {error}")
    root.withdraw()
    yield root
    root.destroy()


@pytest.fixture
def app(window):
    from ytcli.ui.gui.app import App

    return App(window, Options(modes="avs", sub_langs=("en", "ja"), sub_formats=("srt", "md")))


def test_the_form_starts_from_the_given_options(app):
    collected = app.form.collect()
    assert collected.modes == "avs"
    assert collected.sub_langs == ("en", "ja")
    assert collected.sub_formats == ("srt", "md")


def test_urls_are_read_one_per_line(app):
    app.form.urls.insert("1.0", "https://youtu.be/a\n\n  https://youtu.be/b  \n")
    assert app.form.collect().urls == ["https://youtu.be/a", "https://youtu.be/b"]


def test_no_mode_selected_is_refused(app):
    for var in app.form.modes.values():
        var.set(False)
    with pytest.raises(AppError, match="at least one of Audio"):
        app.form.collect()


def test_no_subtitle_format_selected_is_refused(app):
    for var in app.form.sub_formats.values():
        var.set(False)
    with pytest.raises(AppError, match="at least one subtitle format"):
        app.form.collect()


def test_an_empty_output_falls_back_to_the_current_directory(app):
    app.form.output.set("   ")
    assert app.form.collect().output == "."


def test_the_log_pane_stays_read_only(app):
    app.write("hello")
    assert "hello" in app.log.get("1.0", "end")
    assert str(app.log.cget("state")) == "disabled"


def test_saving_defaults_writes_the_config(app, isolated_config):
    app.save_defaults()
    assert isolated_config.is_file()
    assert "avs" in isolated_config.read_text()
