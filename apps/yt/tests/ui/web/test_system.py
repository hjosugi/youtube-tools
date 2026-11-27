"""The desktop helpers: Downloads, the file manager, the folder list."""

from pathlib import Path

import pytest

from ytcli.models import AppError
from ytcli.ui.web import system

# Taken before the autouse `desktop` fixture swaps them for recorders.
real_open_path = system.open_path
real_open_browser = system.open_browser


@pytest.fixture
def home(tmp_path, monkeypatch) -> Path:
    monkeypatch.setattr(system.Path, "home", lambda: tmp_path)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    return tmp_path


class TestDownloadsDir:
    def test_the_usual_folder(self, home, monkeypatch):
        monkeypatch.setattr(system.sys, "platform", "darwin")
        (home / "Downloads").mkdir()
        assert system.downloads_dir() == home / "Downloads"

    def test_home_when_there_is_none(self, home, monkeypatch):
        monkeypatch.setattr(system.sys, "platform", "win32")
        assert system.downloads_dir() == home

    def test_linux_uses_the_localised_name(self, home, monkeypatch):
        monkeypatch.setattr(system.sys, "platform", "linux")
        (home / "ダウンロード").mkdir()
        (home / ".config").mkdir()
        (home / ".config" / "user-dirs.dirs").write_text(
            'XDG_DESKTOP_DIR="$HOME/デスクトップ"\nXDG_DOWNLOAD_DIR="$HOME/ダウンロード"\n', encoding="utf-8"
        )
        assert system.downloads_dir() == home / "ダウンロード"

    def test_a_disabled_xdg_entry_is_ignored(self, home, monkeypatch):
        # XDG spells "no such folder" as the home directory itself.
        monkeypatch.setattr(system.sys, "platform", "linux")
        (home / "Downloads").mkdir()
        (home / ".config").mkdir()
        (home / ".config" / "user-dirs.dirs").write_text('XDG_DOWNLOAD_DIR="$HOME/"\n', encoding="utf-8")
        assert system.downloads_dir() == home / "Downloads"


def test_paths_under_home_are_shortened(home):
    assert system.short_path(home / "Music" / "yt") == str(Path("~") / "Music" / "yt")
    assert system.short_path(home.parent) == str(home.parent)


class TestFolders:
    def test_lists_visible_folders_in_order(self, home):
        for name in ("beta", "Alpha", ".cache"):
            (home / name).mkdir()
        (home / "notes.txt").write_text("x")
        listing = system.list_folders(str(home))
        assert [folder["name"] for folder in listing["folders"]] == ["Alpha", "beta"]
        assert listing["folders"][0]["path"] == str(home.resolve() / "Alpha")
        assert listing["parent"] == str(home.resolve().parent)

    def test_starts_in_downloads(self, home, monkeypatch):
        monkeypatch.setattr(system.sys, "platform", "darwin")
        (home / "Downloads").mkdir()
        assert system.list_folders("")["path"] == str((home / "Downloads").resolve())

    def test_shortcuts_only_name_folders_that_exist(self, home, monkeypatch):
        monkeypatch.setattr(system.sys, "platform", "darwin")
        (home / "Music").mkdir()
        names = [place["path"] for place in system.list_folders(str(home))["shortcuts"]]
        assert names == [str(home), str(home / "Music")]

    def test_the_top_of_the_tree_has_no_parent(self):
        root = Path(Path.cwd().anchor)
        assert system.list_folders(str(root))["parent"] == ""

    def test_a_file_or_a_missing_path_is_an_error(self, home):
        (home / "notes.txt").write_text("x")
        with pytest.raises(AppError, match="Not a folder"):
            system.list_folders(str(home / "notes.txt"))
        with pytest.raises(AppError):
            system.list_folders(str(home / "nope"))


class TestOpenPath:
    @pytest.fixture
    def started(self, monkeypatch):
        commands: list[list[str]] = []
        monkeypatch.setattr(system.subprocess, "Popen", lambda command, **kwargs: commands.append(command))
        return commands

    def test_linux_opens_the_folder_of_a_file(self, tmp_path, monkeypatch, started):
        monkeypatch.setattr(system.sys, "platform", "linux")
        target = tmp_path / "a.mp3"
        target.write_text("x")
        real_open_path(target)
        real_open_path(tmp_path)
        assert started == [["xdg-open", str(tmp_path)], ["xdg-open", str(tmp_path)]]

    def test_macos_reveals_the_file(self, tmp_path, monkeypatch, started):
        monkeypatch.setattr(system.sys, "platform", "darwin")
        target = tmp_path / "a.mp3"
        target.write_text("x")
        real_open_path(target)
        real_open_path(tmp_path)
        assert started == [["open", "-R", str(target)], ["open", str(tmp_path)]]

    def test_windows_selects_the_file(self, tmp_path, monkeypatch, started):
        monkeypatch.setattr(system.sys, "platform", "win32")
        target = tmp_path / "a.mp3"
        target.write_text("x")
        real_open_path(target)
        assert started == [["explorer", f"/select,{target}"]]

    def test_a_missing_path_is_reported(self, tmp_path):
        with pytest.raises(AppError, match="Not found"):
            real_open_path(tmp_path / "gone")

    def test_a_missing_file_manager_is_reported(self, tmp_path, monkeypatch):
        def missing(command, **kwargs):
            raise FileNotFoundError("xdg-open")

        monkeypatch.setattr(system.sys, "platform", "linux")
        monkeypatch.setattr(system.subprocess, "Popen", missing)
        with pytest.raises(AppError, match="Could not open"):
            real_open_path(tmp_path)


class TestBrowser:
    def test_reports_whether_a_tab_was_opened(self, monkeypatch):
        monkeypatch.setattr(system.webbrowser, "open", lambda url: url.endswith("ok"))
        assert real_open_browser("http://127.0.0.1/ok") is True
        assert real_open_browser("http://127.0.0.1/no") is False

    def test_no_browser_at_all_is_not_a_crash(self, monkeypatch):
        def boom(url):
            raise system.webbrowser.Error("no runnable browser")

        monkeypatch.setattr(system.webbrowser, "open", boom)
        assert real_open_browser("http://127.0.0.1/") is False


class TestLibraryPath:
    """A frozen build must not leak its bundled libraries into the browser it starts."""

    def test_the_original_value_is_put_back(self, monkeypatch):
        monkeypatch.setattr(system.sys, "frozen", True, raising=False)
        monkeypatch.setenv("LD_LIBRARY_PATH", "/tmp/_MEI123")
        monkeypatch.setenv("LD_LIBRARY_PATH_ORIG", "/usr/lib")
        system.restore_library_path()
        assert system.os.environ["LD_LIBRARY_PATH"] == "/usr/lib"

    def test_without_an_original_it_is_removed(self, monkeypatch):
        monkeypatch.setattr(system.sys, "frozen", True, raising=False)
        monkeypatch.setenv("LD_LIBRARY_PATH", "/tmp/_MEI123")
        monkeypatch.delenv("LD_LIBRARY_PATH_ORIG", raising=False)
        system.restore_library_path()
        assert "LD_LIBRARY_PATH" not in system.os.environ

    def test_a_normal_python_is_left_alone(self, monkeypatch):
        monkeypatch.delattr(system.sys, "frozen", raising=False)
        monkeypatch.setenv("LD_LIBRARY_PATH", "/opt/lib")
        system.restore_library_path()
        assert system.os.environ["LD_LIBRARY_PATH"] == "/opt/lib"
