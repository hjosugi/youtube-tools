<!-- i18n: language-switcher -->
[English](README.md) | [日本語](README.ja.md)

# yt

YouTube の **字幕**・**MP3**・**MP4** を、ブラウザの画面か短いコマンド1つで取得します。

```bash
yt                 # ローカルの Web UI を開く: URL を貼ってボタンを押すだけ
yt mp3 URL         # 1行で済ませる場合
```

`yt` は Python 製で、Linux / macOS / Windows 用の単体バイナリとして配布しています。

## インストール

### 単体バイナリ（Python 不要）

```bash
# Linux / macOS
curl -fsSL https://raw.githubusercontent.com/hjosugi/youtube-tools/main/install.sh | sh
```

```powershell
# Windows
irm https://raw.githubusercontent.com/hjosugi/youtube-tools/main/install.ps1 | iex
```

インストーラーは `yt` を `~/.local/bin`（Windows は `%LOCALAPPDATA%\Programs\yt`）に置き、
リリースの `SHA256SUMS` でダウンロードを検証します。Linux と Windows ではアプリ一覧に **yt** を追加し、
インストール済みのシェル用の補完も配置します。もう一度実行すると更新です。
`YT_INSTALL_DIR` と `YT_VERSION`（例: `v1.1.0`）で置き場所と版を変えられます。

[Releases](https://github.com/hjosugi/youtube-tools/releases) から自分でダウンロードすることもできます。

| プラットフォーム | ファイル |
| --- | --- |
| Linux x86_64 | `yt-linux-x86_64` |
| Linux arm64 | `yt-linux-arm64` |
| macOS Apple Silicon | `yt-macos-arm64` |
| macOS Intel | `yt-macos-x86_64` |
| Windows x86_64 | `yt-windows-x86_64.exe` |

macOS でブラウザからダウンロードしたバイナリは、署名していないため Gatekeeper に隔離されます。
`xattr -d com.apple.quarantine ./yt-macos-arm64` で解除してください。上のインストーラーならこの問題は起きません。

### ソースから

```bash
cd apps/yt
uv sync
uv run yt
```

### 実行時に必要なもの

- **ffmpeg**。MP3 への変換と MP4 の結合に使います。`PATH` に ffmpeg があればそれを使います。
  無ければ、音声か動画を最初に要求したときに `yt` が静的ビルドをダウンロードし、SHA-256 を検証して
  キャッシュディレクトリ（Linux は `~/.cache/yt`、macOS は `~/Library/Caches/yt`、
  Windows は `%LOCALAPPDATA%\yt\Cache`。`YT_CACHE_DIR` で変更可）に保存します。字幕には ffmpeg は不要です。
- **JavaScript ランタイム**は任意ですが推奨です。Deno・Node.js 22 以上・Bun・QuickJS のどれかが `PATH` にあると、
  yt-dlp が YouTube の JavaScript チャレンジを解けるようになり、すべての形式を取得できます。

## Web UI

```bash
yt            # yt ui、yt --gui でも同じ
```

引数なしの `yt` は `127.0.0.1` で小さなサーバーを起動し、ブラウザで開きます。

1. YouTube の URL を貼り付けます。動画のタイトルと字幕の言語が表示されます。
2. **字幕**・**MP3**・**MP4**・**ぜんぶ** のどれかを押します。
3. ファイルが「ダウンロード」に並び、フォルダを開くリンクが付きます。

知っておくと便利なこと:

- **Enter** は最後に押したボタンと同じ動作です。ページのどこで Ctrl+V を押しても URL 欄に貼り付けられ、
  ほかのタブからリンクをドラッグしても入ります。
- 複数の URL は改行で区切ります。プレイリストの URL は動画1本ごとのダウンロードになります。
  `&list=...` が付いているだけの動画 URL は、その動画1本だけを取得します。
- **設定** には保存先、字幕の言語と形式、動画と音声の品質、ファイルの種類があります。
  変更はすぐに保存され、コマンドラインが読むのと同じ設定ファイルに書かれます。
- 各ダウンロードの **詳細** には、同じことをするコマンドとログが表示されます。
- 画面はブラウザの言語（日本語か英語）に合わせて表示され、切り替えボタンもあります。

動き方:

- ターミナルから起動した場合、Ctrl+C か **終了** ボタンを押すまでサーバーは動き続けます。
  ターミナルなしで起動した場合（アプリ一覧から）は、最後のタブを閉じて数分後に自動で終了します。
- すでに動いているときに `yt` を起動すると、2つ目のサーバーは作らず、既存の画面を開きます。
- `--port N` でポートを指定できます（既定は 4816、使用中なら空いている番号）。`--no-open` はブラウザを開きません。

誰が操作できるか: サーバーは `127.0.0.1` でのみ待ち受けます。リクエストは `Host` ヘッダーでそのアドレスを指し、
起動時の URL に含まれる秘密の値と引き換えに発行されるセッション Cookie を持ち、変更を伴う場合は
同一オリジンの JSON でなければなりません。同じブラウザで開いているほかの Web ページからは操作できません。

## コマンドライン

```bash
yt [a|v|s|av|mp3|mp4|sub|all] URL... [オプション]
```

### 何をダウンロードするか

```bash
yt mp3 URL         # 音声
yt mp4 URL         # 動画
yt sub URL         # 字幕
yt all URL         # 3つとも
yt mp3 sub URL     # 言葉は組み合わせられる
yt URL             # 保存済みの既定値（初期状態は字幕）
```

音声は `yt a URL`、動画は `yt v URL`、字幕は `yt s URL` で取得できます。`av`、`as`、`vs`、`avs` と組み合わせても、`-m` に続けて指定しても使えます。言葉・URL・オプションの順番は自由です。ターミナルで `yt mp3` だけを入力すると、URL を尋ねます。

### 字幕

指定がなければ英語をダウンロードします。

```bash
yt sub URL                  # en
yt sub URL -l en,ja         # 英語と日本語
yt sub URL -l all           # その動画にある全言語
yt URL --list-subs          # 選ぶ前に利用できる言語を確認
yt sub URL --no-auto-subs   # 自動生成字幕を除き、人が書いた字幕だけ
```

言語ごとに別ファイルへ書き出します（例: `Some Title.en.srt` と `Some Title.ja.srt`）。
動画にない言語は、その旨を表示して飛ばします。

出力形式は `-f` で選べます。既定は `srt,tsv` です。

| 形式 | 内容 |
| --- | --- |
| `srt` | SubRip。動画プレイヤーでそのまま使えます |
| `vtt` | WebVTT |
| `tsv` | `no` / `start` / `end` / `text` の4列。表計算向け |
| `txt` | 本文のみ。1行1字幕 |
| `md` | 通し番号とタイムスタンプ付きの Markdown |

```bash
yt sub URL -f srt,tsv,md
```

`<i>` などの装飾タグは取り除き、YouTube の自動字幕がスクロール表示のために繰り返す行は1つにまとめます。

### 画質・音質

```bash
yt mp4 URL --vq 1080              # 高さ 1080px までに制限
yt mp4 URL --vq best --video-format mkv
yt mp3 URL --aq 192               # 192 kbps
yt URL -m a --aq best --audio-format flac
```

| オプション | 選択肢 | 既定 |
| --- | --- | --- |
| `--vq`, `--video-quality` | `best`, `2160`, `1440`, `1080`, `720`, `480`, `360`, `worst` | `best` |
| `--video-format` | `mp4`, `mkv`, `webm` | `mp4` |
| `--aq`, `--audio-quality` | `best`, `320`, `256`, `192`, `128`, `96`, `64`（kbps） | `best` |
| `--audio-format` | `mp3`, `m4a`, `opus`, `flac`, `wav` | `mp3` |

MP4 は、どの環境でも再生できるように H.264 の映像を優先します。YouTube には 1080p を超える H.264 がないため、
`--vq 1440` と `--vq 2160` はその解像度を持つコーデックをそのまま取得します。

### 既定値

毎回指定するオプションは保存できます。保存先も含みます。Web UI も同じファイルに保存します。

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
保存先の既定は、コマンドラインではカレントディレクトリ、Web UI ではダウンロードフォルダです。

### 対話モード（ターミナル）

```bash
yt -i
```

各オプションを順に質問し、実行前に内容を表示します。

### オプション一覧

| オプション | 説明 |
| --- | --- |
| `mp3`, `mp4`, `sub`, `all` | 何をダウンロードするかを言葉で指定 |
| `ui` | Web UI を開く（引数なしの `yt` と同じ） |
| `-m`, `--mode` | 言葉と同じ内容を `a` / `v` / `s` の組み合わせ、または `all` で指定 |
| `-l`, `--lang` | 字幕の言語。カンマ区切り、または `all` |
| `-f`, `--sub-format` | 字幕の出力形式: `srt`, `vtt`, `tsv`, `txt`, `md` |
| `--no-auto-subs` | 自動生成字幕を使わない |
| `--vq`, `--video-quality` | 動画の最大の高さ |
| `--video-format` | 動画コンテナ |
| `--aq`, `--audio-quality` | 音声ビットレート（kbps） |
| `--audio-format` | 音声コーデック |
| `-o`, `--output` | 保存先ディレクトリ |
| `-g`, `--gui`, `--ui` | Web UI を開く |
| `--port` | Web UI のポート |
| `--no-open` | ブラウザのタブを開かずに Web UI を起動 |
| `-i`, `--interactive` | ターミナルの対話モード |
| `--list-subs` | 利用できる字幕の言語を表示 |
| `--save-config` | 現在のオプションを既定値として保存 |
| `--show-config` | 有効な既定値を表示 |
| `--config-path` | 設定ファイルの場所を表示 |
| `-c`, `--completion SHELL` | `bash`・`zsh`・`fish`・`pwsh`・`powershell` の補完スクリプトを表示 |
| `--insecure` | TLS 証明書の検証を省略（最終手段） |
| `--version` | バージョンを表示 |

## シェル補完

`yt ` の後で Tab を押すと操作の候補が、`yt v --vq ` の後なら画質の候補が出ます。単体バイナリにも Python 版にも4シェル分の補完が入っています。今のターミナルで有効にするには、使っているシェルの行を実行します。

| シェル | 今すぐ有効にする方法 |
| --- | --- |
| Bash | `source <(yt -c bash)` |
| Zsh | `autoload -Uz compinit && compinit` の後で `source <(yt -c zsh)` |
| fish | `yt -c fish \| source` |
| PowerShell | `yt -c pwsh \| Out-String \| Invoke-Expression` |

Linux・macOS のインストーラーは、Bash・fish があれば各シェルのユーザー用補完ディレクトリに配置します。Zsh は `~/.zshrc` の `compinit` より前に `fpath=("${XDG_DATA_HOME:-$HOME/.local/share}/zsh/site-functions" $fpath)` を追加してください。Windows ではインストールした PowerShell ですぐに補完が有効になり、次回も使うために `$PROFILE` に追加する1行が表示されます。

## 開発

```bash
uv sync
uv run yt --help
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run python build.py                      # dist/ に単体バイナリを作成
uv run python smoke.py dist/yt-linux-x86_64 # ビルドしたバイナリの UI を起動して確認
```

コードは `ytcli/` にあります。

| パス | 内容 |
| --- | --- |
| `download/` | yt-dlp とやり取りする部分。字幕・音声・動画の各ステージ |
| `subtitles/` | 字幕ファイルの解析と書き出し、言語の選択 |
| `settings/` | オプションと設定ファイル |
| `ffmpeg.py` | ffmpeg の検出と、固定したビルドの取得 |
| `ui/cli.py`, `ui/args.py` | コマンドライン |
| `ui/web/` | Web UI。サーバー、ダウンロードキュー、`static/` の画面 |

### リリース

`build.py` は実行中のプラットフォーム向けに PyInstaller を走らせます。リリースワークフローは `v*` タグごとに
5つのプラットフォームで実行し、各バイナリの UI を起動して確認したうえで、`SHA256SUMS` と一緒に公開します。
公開後は、新しいリリースに対してインストーラーも実行して確認します。

```bash
python ../../scripts/bump-version.py minor   # patch、major、1.4.2 も可
git commit -am "Release 1.2.0" && git tag v1.2.0 && git push origin main v1.2.0
```

依存関係の更新にこの作業は不要です。Dependabot がプルリクエストを作り、CI が通れば自動でマージされ、
バイナリに含まれるものが変わった場合はパッチリリースが続きます。Dependabot から見えない唯一の固定値は、
`ytcli/ffmpeg.py` にある ffmpeg のビルドです。

## 注意

- ダウンロードが許可されているコンテンツにのみ使ってください。YouTube の利用規約・著作権・レート制限を守ってください。
- 翻訳機能はありません。`-l en,ja` は YouTube が公開している字幕トラックを取得するだけです。
- ダウンロードした動画・音声・字幕・Cookie は git に入れないでください。
