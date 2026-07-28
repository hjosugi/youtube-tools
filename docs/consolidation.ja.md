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