"use strict";

// ---- words -------------------------------------------------------------------------

const TEXT = {
  en: {
    otherLanguage: "日本語",
    quit: "Quit",
    urlLabel: "YouTube URL",
    urlPlaceholder: "Paste a YouTube URL",
    paste: "Paste",
    subs: "Subtitles",
    all: "All three",
    allDetail: "subtitles + audio + video",
    audioDetail: "audio",
    videoDetail: "video",
    best: "best",
    worst: "smallest",
    upTo: "up to {q}p",
    enterHint: "Enter = {action}",
    saveTo: "Save to",
    change: "Change",
    open: "Open",
    settings: "Settings",
    sLangs: "Subtitle languages",
    sLangsHelp: "Comma separated, or all. A language the video lacks is skipped.",
    sFormats: "Subtitle files",
    autoSubs: "Use auto-generated captions when there are no written ones",
    vQuality: "Video",
    vFormat: "Video file type",
    aQuality: "Audio",
    aFormat: "Audio file type",
    kbps: "{q} kbps",
    autoSaved: "Changes are saved as you make them.",
    downloads: "Downloads",
    clear: "Clear finished",
    stop: "Stop",
    showFolder: "Show folder",
    details: "Details",
    command: "The same thing as a command:",
    queued: "Waiting",
    starting: "Starting…",
    stageSubtitle: "Getting subtitles",
    stageAudio: "Downloading audio",
    stageVideo: "Downloading video",
    stageFfmpeg: "Getting ffmpeg (first time only)",
    stagePlaylist: "Reading the playlist",
    processing: "Converting…",
    done: "Done",
    failed: "Failed",
    cancelled: "Stopped",
    stopping: "Stopping…",
    checking: "Looking the video up…",
    noUrl: "Paste a YouTube URL first.",
    notUrl: "That does not look like a URL.",
    manyUrls: "{n} URLs",
    playlist: "Playlist with {n} videos: each one is downloaded.",
    tracks: "Subtitles: {list}",
    tracksAuto: "Auto captions only: {list}",
    noTracks: "No subtitles on this video",
    clipboardBlocked: "The browser blocked the clipboard. Press Ctrl+V in the box instead.",
    ffmpegDownload: "MP3 and MP4 need ffmpeg. It is downloaded automatically the first time.",
    ffmpegMissing: "MP3 and MP4 need ffmpeg, and there is no automatic download for this computer. Install ffmpeg first.",
    chooseFolder: "Choose where to save",
    useThis: "Save here",
    cancel: "Cancel",
    parent: "↑ Up",
    noFolders: "No folders inside.",
    quitDone: "yt has stopped. You can close this tab.",
    gone: "Lost the connection to yt. Start yt again to continue.",
  },
  ja: {
    otherLanguage: "English",
    quit: "終了",
    urlLabel: "YouTube の URL",
    urlPlaceholder: "YouTube の URL を貼り付け",
    paste: "貼り付け",
    subs: "字幕",
    all: "ぜんぶ",
    allDetail: "字幕 + 音声 + 動画",
    audioDetail: "音声",
    videoDetail: "動画",
    best: "最高",
    worst: "最小",
    upTo: "{q}p まで",
    enterHint: "Enter で「{action}」",
    saveTo: "保存先",
    change: "変更",
    open: "開く",
    settings: "設定",
    sLangs: "字幕の言語",
    sLangsHelp: "カンマ区切り。all で全部。動画にない言語は飛ばします。",
    sFormats: "字幕ファイル",
    autoSubs: "人が書いた字幕がなければ自動生成の字幕を使う",
    vQuality: "動画",
    vFormat: "動画ファイルの種類",
    aQuality: "音声",
    aFormat: "音声ファイルの種類",
    kbps: "{q} kbps",
    autoSaved: "変更はその場で保存されます。",
    downloads: "ダウンロード",
    clear: "完了分を消す",
    stop: "中止",
    showFolder: "フォルダを開く",
    details: "詳細",
    command: "同じことをするコマンド:",
    queued: "待機中",
    starting: "開始中…",
    stageSubtitle: "字幕を取得中",
    stageAudio: "音声をダウンロード中",
    stageVideo: "動画をダウンロード中",
    stageFfmpeg: "ffmpeg を準備中(初回のみ)",
    stagePlaylist: "プレイリストを確認中",
    processing: "変換中…",
    done: "完了",
    failed: "失敗",
    cancelled: "中止しました",
    stopping: "中止しています…",
    checking: "動画を確認中…",
    noUrl: "先に YouTube の URL を貼り付けてください。",
    notUrl: "URL ではないようです。",
    manyUrls: "{n} 件の URL",
    playlist: "プレイリスト({n} 本)。1本ずつダウンロードします。",
    tracks: "字幕: {list}",
    tracksAuto: "自動生成の字幕のみ: {list}",
    noTracks: "この動画に字幕はありません",
    clipboardBlocked: "ブラウザがクリップボードを許可しませんでした。入力欄で Ctrl+V を押してください。",
    ffmpegDownload: "MP3 / MP4 には ffmpeg が必要です。初回だけ自動でダウンロードします。",
    ffmpegMissing: "MP3 / MP4 には ffmpeg が必要ですが、このパソコン向けの自動ダウンロードがありません。先に ffmpeg を入れてください。",
    chooseFolder: "保存先を選ぶ",
    useThis: "ここに保存",
    cancel: "キャンセル",
    parent: "↑ 上へ",
    noFolders: "中にフォルダはありません。",
    quitDone: "yt を終了しました。このタブは閉じて大丈夫です。",
    gone: "yt との接続が切れました。続けるにはもう一度 yt を起動してください。",
  },
};

const STAGE_KEYS = {
  subtitle: "stageSubtitle",
  audio: "stageAudio",
  video: "stageVideo",
  ffmpeg: "stageFfmpeg",
  playlist: "stagePlaylist",
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

let language = remembered("yt.language") || ((navigator.language || "en").toLowerCase().startsWith("ja") ? "ja" : "en");
let state = null; // the server's settings, as last reported
let info = null; // what we know about the single URL in the box
let jobs = [];
let quitting = false;

function t(key, values = {}) {
  const text = (TEXT[language] || TEXT.en)[key] ?? TEXT.en[key] ?? key;
  return text.replace(/\{(\w+)\}/g, (_match, name) => values[name] ?? "");
}

function remembered(key) {
  try { return localStorage.getItem(key); } catch { return null; }
}

function remember(key, value) {
  try { localStorage.setItem(key, value); } catch { /* private mode: not worth an error */ }
}

async function api(path, body) {
  const request = body === undefined
    ? {}
    : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
  const response = await fetch(path, request);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || response.statusText);
  return data;
}

// ---- the URL box -------------------------------------------------------------------

function typedUrls() {
  return [...new Set($("#urls").value.split(/\s+/).filter((part) => /^https?:\/\/\S+/i.test(part)))];
}

function hint(text, bad = false) {
  const element = $("#hint");
  element.textContent = text;
  element.classList.toggle("bad", bad);
}

function fitUrlBox() {
  const box = $("#urls");
  box.style.height = "auto";
  box.style.height = `${box.scrollHeight + 4}px`;
}

function setUrls(text) {
  $("#urls").value = text.trim();
  urlsChanged();
}

let lookupTimer = 0;
let lookupTicket = 0;

function urlsChanged() {
  fitUrlBox();
  clearTimeout(lookupTimer);
  const urls = typedUrls();
  const typed = $("#urls").value.trim();
  if (urls.length !== 1 || (info && info.url !== urls[0])) showInfo(null);
  if (!typed) return hint("");
  if (!urls.length) return hint(t("notUrl"), true);
  if (urls.length > 1) return hint(t("manyUrls", { n: urls.length }));
  if (info && info.url === urls[0]) return;
  hint(t("checking"));
  lookupTimer = setTimeout(() => lookUp(urls[0]), 350);
}

async function lookUp(url) {
  const ticket = ++lookupTicket;
  try {
    const found = await api("/api/info", { url });
    if (ticket !== lookupTicket || typedUrls()[0] !== url) return;
    showInfo(found);
    hint(found.playlist ? t("playlist", { n: found.playlist }) : "");
  } catch (error) {
    if (ticket === lookupTicket) hint(error.message, true);
  }
}

function showInfo(found) {
  info = found;
  const preview = $("#preview");
  preview.hidden = !found || !found.title;
  if (found && found.title) {
    $("#title").textContent = found.title;
    $("#meta").textContent = [found.uploader, clock(found.duration)].filter(Boolean).join(" · ");
    $("#tracks").textContent = found.playlist ? "" : trackSummary(found);
    setThumbnail($("#thumb"), found.id);
  }
  drawLanguageChips();
}

function trackSummary(found) {
  if (found.manual.length) return t("tracks", { list: shortList(found.manual) });
  if (found.automatic.length) return t("tracksAuto", { list: shortList(found.automatic) });
  return t("noTracks");
}

function shortList(codes, limit = 12) {
  return codes.length > limit ? `${codes.slice(0, limit).join(", ")} … (+${codes.length - limit})` : codes.join(", ");
}

function setThumbnail(image, id) {
  const usable = /^[\w-]{11}$/.test(id || "");
  // Offline or blocked: remember it, so a redraw does not bring the broken-image icon back.
  image.onerror = () => { image.dataset.failed = id; image.hidden = true; };
  image.hidden = !usable || image.dataset.failed === id;
  const source = usable ? `https://i.ytimg.com/vi/${id}/mqdefault.jpg` : "";
  if (image.getAttribute("src") !== source) {
    if (source) image.src = source; else image.removeAttribute("src");
  }
}

function clock(seconds) {
  if (!seconds) return "";
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const rest = String(seconds % 60).padStart(2, "0");
  return hours ? `${hours}:${String(minutes).padStart(2, "0")}:${rest}` : `${minutes}:${rest}`;
}

async function pasteFromClipboard() {
  try {
    setUrls(await navigator.clipboard.readText());
    $("#urls").focus();
  } catch {
    hint(t("clipboardBlocked"), true);
    $("#urls").focus();
  }
}

// ---- the four buttons --------------------------------------------------------------

async function go(mode) {
  const urls = typedUrls();
  if (!urls.length) {
    hint(t("noUrl"), true);
    return $("#urls").focus();
  }
  const buttons = $$(".action");
  buttons.forEach((button) => { button.disabled = true; });
  try {
    await api("/api/jobs", { urls, mode });
    state.options.mode = mode;
    setUrls("");
    hint("");
    drawActions();
  } catch (error) {
    hint(error.message, true);
  } finally {
    buttons.forEach((button) => { button.disabled = false; });
    $("#urls").focus();
  }
}

function drawActions() {
  const options = state.options;
  $("#label-a").textContent = options.audio_format.toUpperCase();
  $("#label-v").textContent = options.video_format.toUpperCase();
  $("#detail-s").textContent = `${options.sub_langs} · ${options.sub_formats}`.replaceAll(",", ", ");
  $("#detail-a").textContent = `${t("audioDetail")} · ${qualityName(options.audio_quality, "kbps")}`;
  $("#detail-v").textContent = `${t("videoDetail")} · ${qualityName(options.video_quality, "upTo")}`;

  let label = "";
  for (const button of $$(".action")) {
    const isDefault = button.dataset.mode === options.mode;
    button.classList.toggle("default", isDefault);
    if (isDefault) label = $(".big", button).textContent;
  }
  $("#enterHint").textContent = label ? t("enterHint", { action: label }) : "";
}

function qualityName(value, numberKey) {
  if (value === "best" || value === "worst") return t(value);
  return t(numberKey, { q: value });
}

// ---- settings ----------------------------------------------------------------------

function drawSettings() {
  const options = state.options;
  $("#set-langs").value = options.sub_langs;
  $("#set-auto").checked = options.auto_subs;
  fillSelect($("#set-vq"), state.choices.video_quality, options.video_quality, (value) => qualityName(value, "upTo"));
  fillSelect($("#set-vf"), state.choices.video_format, options.video_format, (value) => value.toUpperCase());
  fillSelect($("#set-aq"), state.choices.audio_quality, options.audio_quality, (value) => qualityName(value, "kbps"));
  fillSelect($("#set-af"), state.choices.audio_format, options.audio_format, (value) => value.toUpperCase());

  const chosen = options.sub_formats.split(",");
  const formats = $("#set-formats");
  formats.replaceChildren(...state.choices.sub_formats.map((name) => {
    const label = document.createElement("label");
    label.className = "check";
    const box = document.createElement("input");
    box.type = "checkbox";
    box.value = name;
    box.checked = chosen.includes(name);
    label.append(box, name);
    return label;
  }));

  $("#folder").textContent = state.folder_label;
  const note = $("#ffmpegNote");
  note.hidden = state.ffmpeg === "system" || state.ffmpeg === "cached";
  note.textContent = state.ffmpeg === "missing" ? t("ffmpegMissing") : t("ffmpegDownload");
  drawLanguageChips();
}

function fillSelect(select, values, current, name) {
  select.replaceChildren(...values.map((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = name(value);
    option.selected = value === current;
    return option;
  }));
}

// The languages of the video in the box, as buttons that add or remove them from the list.
function drawLanguageChips() {
  const holder = $("#langChips");
  if (!state || !info || info.playlist) return holder.replaceChildren();
  const wanted = listOf($("#set-langs").value);
  const codes = [...new Set([...info.manual, ...info.automatic])].slice(0, 40);
  holder.replaceChildren(...codes.map((code) => {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "chip";
    chip.classList.toggle("on", wanted.includes(code));
    chip.classList.toggle("auto", !info.manual.includes(code));
    chip.textContent = code;
    chip.addEventListener("click", () => {
      const next = wanted.includes(code) ? wanted.filter((item) => item !== code) : [...wanted, code];
      $("#set-langs").value = next.join(",");
      saveSettings();
    });
    return chip;
  }));
}

function listOf(text) {
  return text.split(/[,\s]+/).filter(Boolean);
}

let saveTimer = 0;

function saveSettingsSoon() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(saveSettings, 500);
}

async function saveSettings(extra = {}) {
  clearTimeout(saveTimer);
  const formats = $$("#set-formats input:checked").map((box) => box.value);
  const changes = {
    sub_langs: listOf($("#set-langs").value).join(",") || state.options.sub_langs,
    sub_formats: formats.length ? formats.join(",") : state.options.sub_formats,
    auto_subs: $("#set-auto").checked,
    video_quality: $("#set-vq").value,
    video_format: $("#set-vf").value,
    audio_quality: $("#set-aq").value,
    audio_format: $("#set-af").value,
    ...extra,
  };
  try {
    state = await api("/api/settings", changes);
    drawSettings();
    drawActions();
  } catch (error) {
    hint(error.message, true);
  }
}

// ---- choosing the folder -----------------------------------------------------------

async function showFolder(path) {
  $("#folderError").textContent = "";
  let listing;
  try {
    listing = await api(`/api/folders?path=${encodeURIComponent(path)}`);
  } catch (error) {
    $("#folderError").textContent = error.message;
    return;
  }
  $("#folderPath").value = listing.path;

  $("#folderShortcuts").replaceChildren(...listing.shortcuts.map((place) => {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "chip";
    chip.textContent = place.name;
    chip.addEventListener("click", () => showFolder(place.path));
    return chip;
  }));

  const rows = [];
  if (listing.parent) rows.push(folderRow(t("parent"), listing.parent));
  rows.push(...listing.folders.map((folder) => folderRow(folder.name, folder.path)));
  if (!listing.folders.length) {
    const empty = document.createElement("li");
    empty.className = "empty";
    empty.textContent = t("noFolders");
    rows.push(empty);
  }
  $("#folderList").replaceChildren(...rows);
}

function folderRow(name, path) {
  const item = document.createElement("li");
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = name;
  button.addEventListener("click", () => showFolder(path));
  item.append(button);
  return item;
}

function chooseFolder() {
  $("#folderDialog").returnValue = ""; // Escape must not repeat the previous "Save here"
  $("#folderDialog").showModal();
  showFolder(state.folder);
}

// ---- downloads ---------------------------------------------------------------------

function drawJobs() {
  const list = $("#jobs");
  const known = new Map($$(".job", list).map((element) => [element.dataset.id, element]));
  $("#downloads").hidden = !jobs.length;

  for (const job of jobs) {
    let element = known.get(job.id);
    if (!element) {
      element = $("#jobTemplate").content.firstElementChild.cloneNode(true);
      element.dataset.id = job.id;
      translate(element);
      wireJob(element);
      list.prepend(element); // newest on top
    }
    known.delete(job.id);
    drawJob(element, job);
  }
  for (const gone of known.values()) gone.remove();

  const busy = jobs.filter((job) => job.status === "queued" || job.status === "running").length;
  document.title = busy ? `(${busy}) yt` : "yt";
  $("#clear").hidden = !jobs.some((job) => !["queued", "running"].includes(job.status));
}

function wireJob(element) {
  const id = element.dataset.id;
  $(".cancel", element).addEventListener("click", () => api(`/api/jobs/${id}/cancel`, {}).catch(() => {}));
  $(".show", element).addEventListener("click", () => openPath({ job: id }));
  $(".jmore", element).addEventListener("toggle", () => {
    element.dataset.logCount = "";
    refreshLog(element, jobs.find((job) => job.id === id));
  });
}

function drawJob(element, job) {
  element.className = `job ${job.status}`;
  $(".jtitle", element).textContent = job.title || job.url;
  setThumbnail($(".jthumb", element), job.video_id);

  const names = { s: t("subs"), a: job.audio_format.toUpperCase(), v: job.video_format.toUpperCase() };
  $(".badges", element).replaceChildren(...[..."sav"].filter((letter) => job.modes.includes(letter)).map((letter) => {
    const badge = document.createElement("span");
    badge.className = "badge";
    badge.textContent = names[letter];
    return badge;
  }));

  const bar = $("progress", element);
  if (job.percent === null || job.processing) bar.removeAttribute("value"); else bar.value = job.percent;
  $(".jtext", element).textContent = statusText(job);

  const files = $(".jfiles", element);
  if (files.childElementCount !== job.files.length) {
    files.replaceChildren(...job.files.map((file, index) => {
      const item = document.createElement("li");
      const link = document.createElement("button");
      link.type = "button";
      link.className = "link";
      link.textContent = file.name;
      link.addEventListener("click", () => openPath({ job: job.id, file: index }));
      const size = document.createElement("span");
      size.className = "size";
      size.textContent = megabytes(file.size);
      item.append(link, size);
      return item;
    }));
  }

  $(".jnote", element).textContent = [job.error, ...(job.status === "failed" ? [] : job.warnings)].filter(Boolean).join("\n");
  $(".cmd", element).textContent = job.command;
  $(".cancel", element).hidden = !["queued", "running"].includes(job.status);
  $(".show", element).hidden = !job.files.length;
  refreshLog(element, job);
}

function statusText(job) {
  if (job.status === "running") {
    if (job.processing) return t("processing");
    const stage = t(STAGE_KEYS[job.stage] || "starting");
    return job.percent === null ? stage : `${stage} ${Math.round(job.percent)}%`;
  }
  return t(job.status);
}

function megabytes(bytes) {
  if (!bytes) return "";
  return bytes < 1048576 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / 1048576).toFixed(1)} MB`;
}

async function refreshLog(element, job) {
  if (!job || !$(".jmore", element).open) return;
  if (element.dataset.logCount === String(job.log_count)) return;
  element.dataset.logCount = String(job.log_count);
  try {
    const { lines } = await api(`/api/jobs/${job.id}/log`);
    const log = $(".log", element);
    const pinned = log.scrollTop + log.clientHeight >= log.scrollHeight - 8;
    log.textContent = lines.join("\n");
    if (pinned) log.scrollTop = log.scrollHeight;
  } catch { /* the job was cleared meanwhile */ }
}

function openPath(target) {
  api("/api/open", target).catch((error) => hint(error.message, true));
}

// ---- staying in touch with the server ----------------------------------------------

function listen() {
  const source = new EventSource("/api/events");
  let failures = 0;
  source.addEventListener("jobs", (event) => {
    failures = 0;
    showGone("");
    jobs = JSON.parse(event.data).jobs;
    drawJobs();
  });
  source.addEventListener("open", () => { failures = 0; showGone(""); });
  source.addEventListener("error", () => {
    failures += 1;
    if (quitting) return source.close();
    if (failures >= 3) showGone(t("gone")); // the browser keeps retrying by itself
  });
}

function showGone(text) {
  $("#gone").hidden = !text;
  $("#goneText").textContent = text;
}

async function quit() {
  quitting = true;
  try { await api("/api/quit", {}); } catch { /* it is going away either way */ }
  showGone(t("quitDone"));
}

// ---- language ----------------------------------------------------------------------

function translate(root = document) {
  for (const element of $$("[data-t]", root)) element.textContent = t(element.dataset.t);
  for (const element of $$("[data-t-placeholder]", root)) element.placeholder = t(element.dataset.tPlaceholder);
  for (const element of $$("[data-t-title]", root)) element.title = t(element.dataset.tTitle);
  for (const element of $$("[data-t-label]", root)) element.setAttribute("aria-label", t(element.dataset.tLabel));
}

function drawEverything() {
  document.documentElement.lang = language;
  translate();
  $("#lang").textContent = t("otherLanguage");
  $("#version").textContent = `v${state.version}`;
  drawSettings();
  drawActions();
  for (const element of $$(".job")) element.remove(); // rebuilt in the new language
  drawJobs();
  if (info) showInfo(info);
}

// On the very first run, ask for subtitles in the reader's own language as well as English.
async function firstRunDefaults() {
  const own = (navigator.language || "en").split("-")[0].toLowerCase();
  if (own === "en" || !/^[a-z]{2,3}$/.test(own)) return;
  try {
    state = await api("/api/settings", { sub_langs: `${own},en` });
  } catch { /* keep the built-in default */ }
}

// ---- start -------------------------------------------------------------------------

async function start() {
  history.replaceState(null, "", "/"); // the secret in the address has done its job
  state = await api("/api/state");
  if (state.first_run) await firstRunDefaults();
  jobs = state.jobs;
  drawEverything();
  listen();

  const box = $("#urls");
  box.addEventListener("input", urlsChanged);
  box.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      go(state.options.mode);
    }
  });
  $("#paste").addEventListener("click", pasteFromClipboard);
  for (const button of $$(".action")) button.addEventListener("click", () => go(button.dataset.mode));

  // Ctrl+V anywhere on the page lands in the URL box.
  document.addEventListener("paste", (event) => {
    if (event.target.closest("input, textarea")) return;
    const text = event.clipboardData.getData("text");
    if (text) { event.preventDefault(); setUrls(text); box.focus(); }
  });
  // So does a link dragged in from another tab.
  document.addEventListener("dragover", (event) => event.preventDefault());
  document.addEventListener("drop", (event) => {
    event.preventDefault();
    const text = event.dataTransfer.getData("text/uri-list") || event.dataTransfer.getData("text");
    if (text) setUrls(text);
  });

  $("#set-langs").addEventListener("input", saveSettingsSoon);
  $("#settings").addEventListener("change", () => saveSettings());

  $("#folder").addEventListener("click", chooseFolder);
  $("#changeFolder").addEventListener("click", chooseFolder);
  $("#openFolder").addEventListener("click", () => openPath({}));
  $("#folderPath").addEventListener("keydown", (event) => {
    if (event.key === "Enter") { event.preventDefault(); showFolder(event.target.value); }
  });
  $("#folderDialog").addEventListener("close", (event) => {
    if (event.target.returnValue === "use") saveSettings({ output: $("#folderPath").value });
  });

  $("#clear").addEventListener("click", () => api("/api/jobs/clear", {}).catch(() => {}));
  $("#quit").addEventListener("click", quit);
  $("#lang").addEventListener("click", () => {
    language = language === "ja" ? "en" : "ja";
    remember("yt.language", language);
    drawEverything();
  });
}

start().catch((error) => showGone(error.message));
