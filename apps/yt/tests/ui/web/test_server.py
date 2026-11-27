"""The HTTP side: who is let in, and what each endpoint does."""

import http.client
import json
from urllib.parse import quote

import pytest

from ytcli.settings import load_config
from ytcli.ui.web import server as server_module

from .conftest import PLAYLIST, wait_until

URL = "https://y/watch?v=one"


class TestDoor:
    """Only the tab that `yt` opened may talk to the server."""

    def test_the_start_link_hands_out_the_cookie(self, ui):
        response, body = ui.request("GET", f"/?k={ui.server.app.token}", cookie=False)
        assert response.status == 200
        assert b"<title>yt</title>" in body
        cookie = response.headers["Set-Cookie"]
        assert cookie.startswith(ui.cookie)
        assert "HttpOnly" in cookie and "SameSite=Strict" in cookie

    def test_the_cookie_alone_is_enough_afterwards(self, ui):
        assert ui.request("GET", "/")[0].status == 200
        assert ui.get("/api/ping") == (200, {"app": "yt", "version": server_module.__version__})

    @pytest.mark.parametrize("path", ["/", "/?k=wrong", "/api/state", "/assets/app.js", "/api/events"])
    def test_nothing_is_served_without_it(self, ui, path):
        response, body = ui.request("GET", path, cookie=False)
        assert response.status == 403
        assert b"yt" in body  # the page says how to get back in

    def test_a_wrong_cookie_is_refused(self, ui):
        assert ui.get("/api/state", cookie=f"{ui.server.cookie_name}=guess")[0] == 403

    def test_the_secret_in_the_link_does_not_unlock_the_api(self, ui):
        assert ui.get(f"/api/state?k={ui.server.app.token}", cookie=False)[0] == 403

    def test_another_host_name_is_refused(self, ui):
        # DNS rebinding: a hostile page whose name resolves to 127.0.0.1.
        assert ui.get("/api/state", headers={"Host": f"evil.example:{ui.port}"})[0] == 403
        assert ui.get("/api/state", headers={"Host": f"localhost:{ui.port}"})[0] == 200

    def test_a_post_from_another_site_is_refused(self, ui):
        assert ui.post("/api/jobs/clear", headers={"Origin": "https://evil.example"})[0] == 403
        assert ui.post("/api/jobs/clear", headers={"Origin": f"http://127.0.0.1:{ui.port}"})[0] == 200

    def test_a_form_post_is_refused(self, ui):
        # A plain HTML form cannot send JSON, so cross-site forms never get through.
        status, _body = ui.post(
            "/api/jobs/clear", headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert status == 403

    def test_pages_forbid_being_framed_or_loading_foreign_scripts(self, ui):
        response, _body = ui.request("GET", "/")
        policy = response.headers["Content-Security-Policy"]
        assert "default-src 'self'" in policy and "frame-ancestors 'none'" in policy
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["Cache-Control"] == "no-store"


class TestAssets:
    @pytest.mark.parametrize(
        ("name", "kind"),
        [("app.js", "text/javascript"), ("style.css", "text/css"), ("icon.svg", "image/svg+xml")],
    )
    def test_the_page_files_are_served(self, ui, name, kind):
        response, body = ui.request("GET", f"/assets/{name}")
        assert response.status == 200
        assert response.headers["Content-Type"].startswith(kind)
        assert int(response.headers["Content-Length"]) == len(body) > 0

    @pytest.mark.parametrize("path", ["/assets/server.py", "/assets/..", "/assets/../server.py", "/nope"])
    def test_nothing_else_is(self, ui, path):
        assert ui.get(path)[0] == 404

    def test_the_page_only_uses_files_that_exist(self, ui):
        _response, page = ui.request("GET", "/")
        for name in server_module.ASSETS:
            assert f"/assets/{name}".encode() in page


class TestState:
    def test_it_holds_everything_the_page_draws(self, ui, out_dir):
        status, state = ui.get("/api/state")
        assert status == 200
        assert state["options"]["output"] == str(out_dir)
        assert state["folder"] == str(out_dir)
        assert state["choices"]["sub_formats"] == ["srt", "vtt", "tsv", "txt", "md"]
        assert state["choices"]["audio_format"][0] == "mp3"
        assert state["ffmpeg"] in ("system", "cached", "downloadable", "missing")
        assert state["first_run"] is True
        assert state["jobs"] == []

    def test_settings_are_saved_as_they_change(self, ui):
        status, state = ui.post(
            "/api/settings", {"sub_langs": "ja, en", "video_quality": "1080", "auto_subs": False}
        )
        assert status == 200
        assert state["options"]["sub_langs"] == "ja,en"
        assert state["first_run"] is False
        stored = load_config({"sub_langs": "", "video_quality": "", "auto_subs": True})
        assert stored == {"sub_langs": "ja,en", "video_quality": "1080", "auto_subs": False}

    def test_lists_are_accepted_too(self, ui):
        _status, state = ui.post("/api/settings", {"sub_formats": ["srt", "md"]})
        assert state["options"]["sub_formats"] == "srt,md"

    @pytest.mark.parametrize(
        "changes",
        [
            {"video_quality": "4320"},
            {"sub_formats": "docx"},
            {"auto_subs": "yes"},
            {"audio_format": 3},
            {"output": " "},
        ],
    )
    def test_values_the_tool_cannot_use_are_refused(self, ui, changes):
        status, answer = ui.post("/api/settings", changes)
        assert status == 400 and answer["error"]
        assert ui.get("/api/state")[1]["first_run"] is True  # nothing was written

    def test_unknown_settings_are_ignored(self, ui):
        _status, state = ui.post("/api/settings", {"insecure": True, "urls": ["x"]})
        assert "insecure" not in state["options"]

    def test_the_folder_can_be_changed(self, ui, tmp_path):
        _status, state = ui.post("/api/settings", {"output": str(tmp_path / "music")})
        assert state["folder"] == str(tmp_path / "music")


class TestFolderDefault:
    """Downloads is only the UI's stand-in for "not set": the CLI keeps its own default."""

    @pytest.fixture
    def app(self, ui):
        ui.server.app.folder_is_default = True
        return ui.server.app

    def test_using_the_ui_does_not_move_the_command_line_default(self, ui, app, manager):
        ui.post("/api/jobs", {"urls": [URL], "mode": "a"})
        ui.post("/api/settings", {"video_quality": "720"})
        assert load_config({"output": "", "mode": "", "video_quality": ""}) == {
            "output": ".",
            "mode": "a",
            "video_quality": "720",
        }

    def test_choosing_a_folder_in_the_page_is_remembered(self, ui, app, tmp_path):
        ui.post("/api/settings", {"output": str(tmp_path / "music")})
        ui.post("/api/settings", {"video_quality": "720"})
        assert load_config({"output": ""}) == {"output": str(tmp_path / "music")}


class TestDownloading:
    def test_looking_a_url_up(self, ui):
        assert ui.post("/api/info", {"url": f" {URL} "}) == (
            200,
            {
                "url": URL,
                "id": "abcdefghijk",
                "title": "Title of one",
                "uploader": "Someone",
                "duration": 75,
                "manual": ["en"],
                "automatic": ["en", "ja"],
                "playlist": 0,
            },
        )
        assert ui.post("/api/info", {"url": PLAYLIST})[1]["playlist"] == 2

    def test_a_lookup_failure_is_an_error_message(self, ui):
        assert ui.post("/api/info", {"url": "https://y/watch?v=unknown"}) == (
            400,
            {"error": "Could not read video info: gone"},
        )

    def test_one_click_downloads(self, ui, manager, out_dir):
        status, answer = ui.post("/api/jobs", {"urls": [URL, URL, "  "], "mode": "mp3"})
        assert (status, answer) == (200, {"jobs": ["1"]})  # the duplicate and the blank are dropped
        wait_until(lambda: not manager.active())
        job = ui.get("/api/state")[1]["jobs"][0]
        assert (job["status"], job["modes"], job["files"][0]["name"]) == ("done", "a", "one.mp3")
        assert (out_dir / "one.mp3").is_file()
        assert ui.get("/api/jobs/1/log") == (200, {"lines": [f"starting {URL}"]})

    def test_the_button_pressed_becomes_the_default(self, ui, manager):
        ui.post("/api/jobs", {"urls": [URL], "mode": "v"})
        assert ui.get("/api/state")[1]["options"]["mode"] == "v"
        assert load_config({"mode": ""}) == {"mode": "v"}

    def test_without_a_mode_the_default_is_used(self, ui, manager):
        ui.post("/api/jobs", {"urls": [URL]})
        wait_until(lambda: not manager.active())
        assert ui.get("/api/state")[1]["jobs"][0]["modes"] == "s"

    @pytest.mark.parametrize(
        "body",
        [
            {"urls": []},
            {"urls": "https://y/watch?v=one"},
            {"urls": ["file:///etc/passwd"]},
            {"urls": ["ytsearch:cats"]},
            {"urls": ["-o/tmp/x"]},
            {"urls": [URL], "mode": "x"},
            {"urls": [f"{URL}{number}" for number in range(201)]},
        ],
    )
    def test_only_web_links_and_real_modes_are_accepted(self, ui, manager, body):
        status, answer = ui.post("/api/jobs", body)
        assert status == 400 and answer["error"]
        assert manager.snapshot()[1] == []

    def test_stopping_and_clearing(self, ui, manager, downloads):
        downloads.hold.clear()
        ui.post("/api/jobs", {"urls": [URL], "mode": "a"})
        assert downloads.started.wait(5)
        assert ui.post("/api/jobs/1/cancel") == (200, {"ok": True})
        wait_until(lambda: not manager.active())
        assert ui.post("/api/jobs/1/cancel") == (200, {"ok": False})
        assert ui.post("/api/jobs/clear") == (200, {"ok": True})
        assert ui.get("/api/state")[1]["jobs"] == []
        assert ui.get("/api/jobs/1/log")[0] == 404

    def test_the_event_stream_pushes_the_job_list(self, ui, manager):
        connection = http.client.HTTPConnection("127.0.0.1", ui.port, timeout=5)
        connection.request("GET", "/api/events", headers={"Cookie": ui.cookie})
        response = connection.getresponse()
        assert response.status == 200
        assert response.headers["Content-Type"].startswith("text/event-stream")

        def next_event() -> dict:
            assert response.readline() == b"event: jobs\n"
            data = response.readline()
            assert response.readline() == b"\n"
            return json.loads(data.removeprefix(b"data: "))

        assert next_event() == {"jobs": []}
        wait_until(lambda: ui.server.app._clients == 1)

        ui.post("/api/jobs", {"urls": [URL], "mode": "a"})
        seen = next_event()["jobs"]
        while seen[0]["status"] != "done":
            seen = next_event()["jobs"]
        assert seen[0]["files"][0]["name"] == "one.mp3"

        connection.close()
        ui.server.app.stop.set()  # ends the stream loop, as closing the tab does on its next write
        wait_until(lambda: ui.server.app._clients == 0)


class TestDesktop:
    def test_opening_the_output_folder_creates_it_first(self, ui, desktop, out_dir):
        assert ui.post("/api/open") == (200, {"ok": True})
        assert desktop["paths"] == [out_dir]
        assert out_dir.is_dir()

    def test_showing_a_finished_file_or_its_folder(self, ui, manager, desktop, out_dir):
        ui.post("/api/jobs", {"urls": [URL], "mode": "a"})
        wait_until(lambda: not manager.active())
        ui.post("/api/open", {"job": "1", "file": 0})
        ui.post("/api/open", {"job": "1"})
        assert desktop["paths"] == [out_dir / "one.mp3", out_dir]

    @pytest.mark.parametrize("body", [{"job": "9"}, {"job": "1", "file": 5}, {"job": "1", "file": "../x"}])
    def test_only_paths_the_server_knows_can_be_opened(self, ui, manager, desktop, body):
        ui.post("/api/jobs", {"urls": [URL], "mode": "a"})
        wait_until(lambda: not manager.active())
        assert ui.post("/api/open", body)[0] == 400
        assert desktop["paths"] == []

    def test_browsing_for_a_folder(self, ui, tmp_path):
        (tmp_path / "music").mkdir()
        (tmp_path / ".hidden").mkdir()
        (tmp_path / "file.txt").write_text("x")
        status, listing = ui.get(f"/api/folders?path={quote(str(tmp_path))}")
        assert status == 200
        assert listing["path"] == str(tmp_path.resolve())
        assert listing["parent"] == str(tmp_path.resolve().parent)
        assert [folder["name"] for folder in listing["folders"]] == ["music"]
        assert ui.get(f"/api/folders?path={quote(str(tmp_path / 'nope'))}")[0] == 400

    def test_quitting_stops_the_app(self, ui):
        assert ui.post("/api/quit") == (200, {"ok": True})
        wait_until(ui.server.app.stop.is_set)  # set right after the answer went out


class TestBadRequests:
    def test_broken_json(self, ui):
        connection = http.client.HTTPConnection("127.0.0.1", ui.port, timeout=5)
        headers = {"Cookie": ui.cookie, "Content-Type": "application/json"}
        connection.request("POST", "/api/info", body="{not json", headers=headers)
        response = connection.getresponse()
        assert (response.status, json.loads(response.read())) == (
            400,
            {"error": "Request is not valid JSON."},
        )

    def test_json_that_is_not_an_object(self, ui):
        assert ui.post("/api/info", ["x"]) == (400, {"error": "Request must be a JSON object."})

    def test_an_oversized_body(self, ui):
        status, answer = ui.post("/api/info", {"url": "x" * (server_module.MAX_BODY + 1)})
        assert (status, answer) == (400, {"error": "Request too large."})

    def test_a_handler_bug_does_not_kill_the_server(self, ui, monkeypatch):
        def boom(_path):
            raise RuntimeError("bug")

        monkeypatch.setattr(server_module.system, "list_folders", boom)
        assert ui.get("/api/folders") == (500, {"error": "unexpected error: bug"})
        assert ui.get("/api/ping")[0] == 200
