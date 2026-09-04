<!-- i18n: language-switcher -->
[English](README.md) | [日本語](README.ja.md)

# yt

YouTube の **音声 (a)** ・ **動画 (v)** ・ **字幕 (s)** を1つで扱うクロスプラットフォームツールです。

Python 製の CLI で、Linux / macOS / Windows 用の単体バイナリとしても配布します。
GUI モードもあります。

```bash
yt "https://www.youtube.com/watch?v=..." -m avs
```

## インストール

### 単体バイナリ（Python 不要）

[Releases](https://github.com/hjosugi/youtube-tools/releases) から使用中の環境向けをダウンロードしてください。

| プラットフォーム | ファイル |
| --- | --- |
| Linux x86_64 | `yt-linux-x86_64` |
| macOS Apple Silicon | `yt-macos-arm64` |
| macOS Intel | `yt-macos-x86_64` |
| Windows x86_64 | `yt-windows-x86_64.exe` |

```bash
chmod +x yt-linux-x86_64
sudo mv yt-linux-x86_64 /usr/local/bin/yt
```

macOS では署名していないため初回は Gatekeeper に止められます。
`xattr -d com.apple.quarantine ./yt-macos-arm64` で解除してください。

### ソースから

```bash
cd apps/yt
uv sync
uv run yt --help
```

音声の抽出と、映像・音声ストリームの結合に `ffmpeg` が必要です。`PATH` に入れておいてください。

## 使い方

```bash
yt [URL ...] [-m AVS] [-l 言語] [-f 形式] [--vq 画質] [--aq 音質] [-o 保存先]
```

### 何をダウンロードするか

`-m` には `a`（音声）・`v`（動画）・`s`（字幕）を自由に組み合わせて渡します。

```bash
yt URL -m s        # 字幕のみ（デフォルト）
yt URL -m av       # 音声と動画
yt URL -m avs      # 3つとも1回で
yt URL -m all      # -m avs と同じ
```

`-m audio,video` や `-m a+v` でも動きます。`-m` を省略すると字幕をダウンロードします。
`yt -m av --save-config` で既定値を変更できます。

### 字幕

指定がなければ英語だけをダウンロードします。

```bash
yt URL -m s                 # en
yt URL -m s -l en,ja        # 英語と日本語
yt URL -m s -l all          # その動画にある全言語
yt URL --list-subs          # 選ぶ前に利用できる言語を確認
yt URL -m s --no-auto-subs  # 自動生成字幕を除き、人手の字幕だけ
```

言語ごとに別ファイルへ書き出します（例: `Some Title.en.srt` と `Some Title.ja.srt`）。

出力形式は `-f` で選べます。デフォルトは `srt,tsv` です。

| 形式 | 内容 |
| --- | --- |
| `srt` | SubRip。動画プレイヤーでそのまま使えます |
| `vtt` | WebVTT |
| `tsv` | `no` / `start` / `end` / `text` の4列。表計算向け |
| `txt` | 本文のみ。1行1字幕 |
| `md` | 通し番号とタイムスタンプ付きの Markdown |

```bash
yt URL -m s -f srt,tsv,md
```

`<i>` などの装飾タグは取り除き、YouTube の自動字幕がスクロール表示のために繰り返す行は
1つにまとめます。

### 画質・音質

```bash
yt URL -m v --vq 1080              # 高さ 1080px までに制限
yt URL -m v --vq best --video-format mkv
yt URL -m a --aq 192               # 192 kbps
yt URL -m a --aq best --audio-format flac
```

| オプション | 選択肢 | デフォルト |
| --- | --- | --- |
| `--vq`, `--video-quality` | `best`, `2160`, `1440`, `1080`, `720`, `480`, `360`, `worst` | `best` |
| `--video-format` | `mp4`, `mkv`, `webm` | `mp4` |
| `--aq`, `--audio-quality` | `best`, `320`, `256`, `192`, `128`, `96`, `64`（kbps） | `best` |
| `--audio-format` | `mp3`, `m4a`, `opus`, `flac`, `wav` | `mp3` |

### デフォルト設定

毎回打ち込むオプションは保存できます。ダウンロード先も含みます。

```bash
yt -o ~/Downloads/yt -m avs --vq 1080 --save-config
yt --show-config
yt --config-path
```

| プラットフォーム | 設定ファイル |
| --- | --- |
| Linux | `~/.config/yt/config.toml`（`XDG_CONFIG_HOME` を参照） |
| macOS | `~/Library/Application Support/yt/config.toml` |
| Windows | `%APPDATA%\yt\config.toml` |

`YT_CONFIG_FILE` で別の場所を指定できます。コマンドラインの指定は常に設定ファイルより優先されます。

### GUI モード

```bash
yt --gui
```

CLI と同じ項目を Tk のウィンドウで操作できます。URL 入力欄、音声・動画・字幕のチェックボックス、
字幕の言語と形式、画質・音質、保存先、実行ログ、そして「Save as defaults」ボタンがあります。
ダウンロードはバックグラウンドで走るのでウィンドウは固まらず、「Stop」で中断できます。

配布バイナリには Tk を同梱しています。Tk なしでビルドされたシステム Python から実行する場合は
`python3-tk`（Debian/Ubuntu）、`python3-tkinter`（Fedora）、`tk`（Arch）を入れるか、`yt -i` を使ってください。

### 対話モード（ターミナル）

```bash
yt -i
```

各オプションを順に質問し、実行前に内容を表示します。ターミナルで引数なしの `yt` も同じ動きです。

### オプション一覧

| オプション | 説明 |
| --- | --- |
| `-m`, `--mode` | `a` / `v` / `s` の組み合わせ、または `all` |
| `-l`, `--lang` | 字幕の言語。カンマ区切り、または `all` |
| `-f`, `--sub-format` | 字幕の出力形式: `srt`, `vtt`, `tsv`, `txt`, `md` |
| `--no-auto-subs` | 自動生成字幕を使わない |
| `--vq`, `--video-quality` | 動画の最大の高さ |
| `--video-format` | 動画コンテナ |
| `--aq`, `--audio-quality` | 音声ビットレート（kbps） |
| `--audio-format` | 音声コーデック |
| `-o`, `--output` | 保存先ディレクトリ |
| `-i`, `--interactive` | ターミナルの対話モード |
| `-g`, `--gui` | GUI を開く |
| `--list-subs` | 利用できる字幕の言語を表示 |
| `--save-config` | 現在のオプションを既定値として保存 |
| `--show-config` | 有効な既定値を表示 |
| `--config-path` | 設定ファイルの場所を表示 |
| `--insecure` | TLS 証明書の検証を省略（最終手段） |
| `--version` | バージョンを表示 |

## シェル補完

各シェル向けの補完定義を `completions/` に置いています。

```bash
# bash
sudo cp completions/yt.bash /usr/share/bash-completion/completions/yt

# zsh （$fpath 上の任意のディレクトリ）
sudo cp completions/yt.zsh /usr/local/share/zsh/site-functions/_yt

# fish
cp completions/yt.fish ~/.config/fish/completions/yt.fish

# PowerShell
Add-Content $PROFILE ". path\to\completions\yt.ps1"
```

Linux / macOS では `./install.sh` がバイナリと bash / zsh / fish の補完をまとめて配置します。

## 開発

```bash
uv sync
uv run yt --help
uv run pytest
uv run ruff check .
uv run python build.py        # dist/ に単体バイナリを作成
```

`build.py` は実行中のプラットフォーム向けに PyInstaller を走らせます。
リリースワークフローでは Linux / macOS / Windows で実行します。

## 注意

- ダウンロードが許可されているコンテンツにのみ使ってください。YouTube の利用規約・著作権・レート制限を守ってください。
- 翻訳機能はありません。`-l en,ja` は YouTube が公開している字幕トラックを取得するだけです。
- ダウンロードした動画・音声・字幕・Cookie は git に入れないでください。
