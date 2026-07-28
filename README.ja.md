<!-- i18n: language-switcher -->
[English](README.md) | [日本語](README.ja.md)

# YouTubeツール

小さなYouTubeユーティリティアプリを一つの学習およびメンテナンスリポジトリにまとめています。

最終確認日: 2026-06-21

## アプリ

| アプリ | パス | 目的 | 実行環境 |
| --- | --- | --- | --- |
| バイリンガル字幕ジェネレーター | `apps/bilingual-subtitle` | 英語のYouTube字幕をダウンロードし、バイリンガルの英語/日本語TSV、SRT、Markdownファイルを生成 | Python + uv |
| YTフェッチャーウェブ | `apps/yt-fetcher-web` | バッチ字幕、MP3、MP4ダウンロード用のFastAPIウェブUI | Python + uv + FastAPI |
| YTフェッチャーCLI | `apps/yt-fetcher-cli` | 字幕、MP3、MP4ダウンロード用のスタンドアロンCLI | Python + uv + PyInstaller |
| シンプルYouTubeダウンローダー | `apps/simple-youtube-downloader` | 参照と近代化のために保持されている古いStreamlitダウンローダー実験 | Python + Streamlit |

これらのアプリは一つのプログラムになる必要はありません。このリポジトリは、同じ問題領域、メンテナンスの懸念、および安全に関する注意事項を共有しているため、グループ化されています。

## リポジトリのレイアウト

```text
apps/
  bilingual-subtitle/
  simple-youtube-downloader/
  yt-fetcher-web/
  yt-fetcher-cli/
docs/
  consolidation.md
```

各アプリは独自の `pyproject.toml`、`uv.lock`、README、およびコマンドを保持しています。ルートレベルのタスクが別に指示しない限り、アプリディレクトリから作業してください。

コードリーディングの実践的な作業を始めるには、これらのパッケージガイドを参照してください：

| パッケージ | ガイド |
| --- | --- |
| バイリンガル字幕内部 | [`apps/bilingual-subtitle/gen_subtitle/README.md`](apps/bilingual-subtitle/gen_subtitle/README.md) |
| CLIフェッチャー内部 | [`apps/yt-fetcher-cli/yt_fetcher/README.md`](apps/yt-fetcher-cli/yt_fetcher/README.md) |
| ウェブフェッチャー内部 | [`apps/yt-fetcher-web/yt_fetcher/README.md`](apps/yt-fetcher-web/yt_fetcher/README.md) |

## クイックスタート

インタラクティブCLIフローは、コマンドラインアプリを使用するためのデフォルトの方法です。

リポジトリのルートから：

```bash
python3 launcher.py
```

番号でツールを選択すると、利用可能な場合はガイド付きフローが開始されます。

```bash
cd apps/bilingual-subtitle
uv sync
uv run python main.py
```

```bash
cd apps/yt-fetcher-web
uv sync
uv run python main.py
```

```bash
cd apps/yt-fetcher-cli
uv sync
uv run python cli.py
```

```bash
cd apps/simple-youtube-downloader
pip install -r requirements.txt
streamlit run src/main.py
```

## 安全性と範囲

- アクセスおよび処理が許可されているコンテンツのみにこれらのツールを使用してください。
- YouTubeの利用規約、著作権、レート制限、およびクリエイターの許可を尊重してください。
- ダウンロードしたメディア、字幕、APIキー、クッキー、またはブラウザプロファイルをコミットしないでください。
- MP3/MP4の抽出は `ffmpeg` に依存します。
- DeepL翻訳を使用する場合、DeepL翻訳者パスで `DEEPL_AUTH_KEY` が必要です。

## メンテナンスノート

- コードを共有する前に、各アプリが単独で実行可能であることを確認してください。
- 共通コードが意味を持つようになった場合、テストがある後に `packages/` に移動してください。
- 巧妙なルートオーケストレーターよりも、小さな文書化されたコマンドを優先してください。
- コマンドの動作が変更された場合は、アプリのREADMEを更新してください。
- `apps/simple-youtube-downloader` をメンテナンスされたアプリとして扱う前に近代化してください。

## ライセンス

0BSD。ほぼすべての目的でこのプロジェクトを使用、コピー、変更、配布できます。