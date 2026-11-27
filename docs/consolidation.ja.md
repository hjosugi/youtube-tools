<!-- i18n: language-switcher -->
[English](consolidation.md) | [日本語](consolidation.ja.md)

# 統合ノート

日付: 2026-06-20

このリポジトリは以下を統合します：

- `hjosugi/youtube-bilingual-subtitle`
- `hjosugi/yt-fetcher`
- `hjosugi/yt-fetcher-cli`
- `hjosugi/simple-youtube-downloader`

元のプログラムは意図的に別々のアプリとして保持されます：

- `youtube-bilingual-subtitle` は `apps/bilingual-subtitle` になります
- `yt-fetcher` は `apps/yt-fetcher-web` になります
- `yt-fetcher-cli` は `apps/yt-fetcher-cli` になります
- `simple-youtube-downloader` は `apps/simple-youtube-downloader` になります

## 理由

- すべてのプロジェクトはYouTubeユーティリティプロジェクトです
- すべてのプロジェクトはPython/uvプロジェクトです
- それらは安全性、著作権、ffmpeg、yt-dlp、および出力ファイルに関する懸念を共有しています
- 3つの公開リポジトリを保持すると、GitHubプロファイルがトピックに見合わないほど騒がしくなります

## 非目標

- まだ1つのCLIまたは1つのパッケージ名を強制しない
- テストが存在するまで `yt_fetcher` モジュールの重複を排除しない
- ウェブデプロイメント設定とCLIリリース設定を混合しない

## フォローアップ

1. 各アプリのスモークテストを追加する。
2. DeepLがサポートされ続ける場合、翻訳プロバイダー用の `.env.example` を追加する。
3. アプリごとに依存関係のベースラインをレビューする。
4. コマンドが安定した後にGitHub Actionsを追加する。

---

# 1つのツールへの統合

日付: 2026-09-04

4つのアプリを1つのコマンドにまとめました。`apps/yt`、コマンド名は `yt` です。

## 置き換え対応表

| 旧アプリ | 置き換え先 |
| --- | --- |
| `apps/yt-fetcher-cli` | `yt` — 役割は同じ。言語・形式の選択、画質/音質の指定、既定値の保存を追加 |
| `apps/bilingual-subtitle` | `yt -m s -l en,ja` — 翻訳エンジンではなく YouTube 自身の字幕トラックを取得 |
| `apps/yt-fetcher-web` | `yt --gui` — FastAPI サーバーではなくデスクトップウィンドウ |
| `apps/simple-youtube-downloader` | `yt` — Streamlit の実験はメンテナンス対象外 |

`launcher.py` は廃止しました。引数なしの `yt` が対話モードを開始し、`yt --gui` がウィンドウを開きます。

## 削除したもの

- **翻訳機能**。`DeepLTranslator` と `ArgosTranslator`、`DEEPL_AUTH_KEY`、対訳の TSV/SRT/Markdown
  ライターを削除しました。`-l en,ja` は YouTube が公開している字幕トラックを取得するだけなので、
  API キーもモデルのダウンロードも翻訳コストも不要です。
- **Web サーバー**。FastAPI、Dockerfile、`render.yaml` / `fly.toml` / `Procfile` を削除しました。
  1人で使うダウンロードツールにデプロイ先は不要でした。
- **3つに複製されていた `yt_fetcher`**。テスト付きの `ytcli` パッケージ1つにまとめました。

## 挙動の変更点

- `--subtitles/--mp3/--mp4` は `-m` と `a` / `v` / `s` の文字指定に変わりました。
- 字幕の言語は、その動画に実際に存在するトラックへ解決してから要求します。旧来の `en.*` という
  パターンは YouTube の機械翻訳トラック（`en-de`、`en-fr` など）にも一致し、HTTP 429 を招いていました。
- 字幕は `srt` / `vtt` / `tsv` / `txt` / `md` で出力できます。旧 CLI は `tsv` のみでした。
- 動画と音声は一時ディレクトリへ別々に取得します。更新時刻から推測せず、置き場所で結果を特定します。
- TLS 証明書は `certifi` で検証します。配布バイナリで検証を無効化するのはやめました。
  `--insecure` は明示指定した場合のみです。
- ダウンロード先を含む既定値は設定ファイルに保存します（`yt --config-path`）。

## 前回のフォローアップの結果

1. ~~各アプリのスモークテストを追加する。~~ 完了: `apps/yt/tests` に83件。
2. ~~DeepL をサポートし続ける場合、翻訳プロバイダー用の `.env.example` を追加する。~~ 翻訳機能ごと廃止。
3. ~~アプリごとに依存関係のベースラインをレビューする。~~ プロジェクトは1つになり、`yt-dlp`・`certifi`・`pytest`・`ruff`・`pyinstaller` を最新化。
4. ~~コマンドが安定した後に GitHub Actions を追加する。~~ 完了: リポジトリ直下に `ci.yml` と `release.yml`。
   旧ワークフローは `apps/yt-fetcher-cli/.github/workflows/` にあり、GitHub からは実行されていませんでした。

---

# コマンドの代わりに Web UI

日付: 2026-11-27

ツールは動いていましたが、使うには `-m a` を覚え、先に ffmpeg を入れ、ウィンドウを開くには Tk 付きの Python が
必要でした。今回はこの3つの障害を取り除きました。

## 変更点

| 以前 | 現在 |
| --- | --- |
| `yt --gui` で Tk のウィンドウを開く | 引数なしの `yt` で、`127.0.0.1` で動く画面がブラウザに開く |
| `yt URL -m a` | `yt mp3 URL`（`mp4`・`sub`・`all` も同様）。`-m` も引き続き使える |
| ターミナルで引数なしの `yt` は質問形式の対話モードを開始 | 対話モードは `yt -i` |
| MP3 / MP4 の前に ffmpeg のインストールが必要 | 無ければ、固定した静的ビルドを初回に自動ダウンロード |
| バイナリをダウンロードし、`chmod +x` して `PATH` に移動 | `curl ... install.sh \| sh` または `irm ... install.ps1 \| iex` |
| 依存関係は手作業で更新 | Dependabot が更新し、CI がマージし、自動でリリース |

## ブラウザの画面にした理由

- Tk は多くの Python ビルドに含まれていません。NixOS や uv の Python もそうで、このツールを開発している
  マシンでウィンドウが開きませんでした。ブラウザはどの環境にもあります。
- 画面に必要なのは標準ライブラリの `http.server` だけです。GUI ツールキットを足すどころか、
  バイナリから Tcl/Tk を外せました。
- `duckdb -ui` と同じ形です。プログラムは1つで、UI はそれを呼び出すもう1つの方法にすぎません。
  画面は各ダウンロードの下に、同じことをするコマンドを表示します。

## 挙動の細かな変更

- MP4 は 1080p まで H.264 を優先し、どのプレイヤーでも再生できるようにしました。
  以前は YouTube が AV1 を提供していれば AV1 を選んでいました。
- `&list=...` が付いた動画 URL は、その動画1本だけをダウンロードします。プレイリストの URL は中の動画に展開し、
  プレイリストでも字幕が取得できるようになりました。
- yt-dlp を `default` と `curl-cffi` の extras 付きで導入し、Deno だけでなく `PATH` にあるすべての
  JavaScript ランタイムを使うようにしました。「formats may be missing」と「no impersonate target」の警告が出なくなります。
- リリースバイナリに Linux arm64 を追加し、`SHA256SUMS` を同梱しました。
- `[tool.bumpversion]` を `scripts/bump-version.py` に置き換えました。追加のインストールが不要で、`uv.lock` も更新します。

## 削除したもの

- Tk のウィンドウ（`ytcli/ui/gui`）。すべてのプラットフォームで Web UI が代わりになります。
- `apps/yt/install.sh`。ローカルでビルドしたバイナリを `sudo` で入れるものでした。
  リポジトリ直下のインストーラーはリリースをダウンロードし、root 権限を必要としません。
