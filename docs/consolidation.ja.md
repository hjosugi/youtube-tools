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
