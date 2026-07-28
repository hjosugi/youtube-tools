<!-- i18n: language-switcher -->
[English](README.md) | [日本語](README.ja.md)

# gen-subtitle

YouTubeから英語の字幕をダウンロードし、バイリンガル（英語-日本語）のTSV、SRT、およびMarkdownファイルを生成するスクリプトです。

## 前提条件

- Python 3.11以上
- [uv](https://docs.astral.sh/uv/) がインストールされていること
- 内部で `yt-dlp` を使用

## セットアップ

このスクリプトは依存関係を管理するために `uv` を使用します。

```bash
# 依存関係を同期
uv sync
```

### 環境変数

翻訳にDeepLを使用したい場合は、`.env.template`を`.env`にコピーし、DeepL APIキーを設定してください。

```bash
cp .env.template .env
```
`.env` の内容:
```
DEEPL_AUTH_KEY=your_deepl_auth_key_here
```

## 使用方法

引数なしで実行すると、ガイド付きセットアップが開始されます。最初に `-h` を読むことなく使用できます。

```bash
uv run python main.py
```

プロンプトでは以下を尋ねられます：

1. YouTube URL
2. 翻訳モード：Argos、英語のみ、またはDeepL
3. 出力ディレクトリ
4. 出力ベース名
5. バッチサイズ
6. 最終確認

スクリプトを使用する際には、すべてを直接渡すこともできます：

```bash
uv run python main.py <YouTube_URL> --translator argos
```

### コマンドラインオプション

```
usage: main.py [-h] [--translator {argos,deepl}]
               [--deepl-auth-key DEEPL_AUTH_KEY] [--out-dir OUT_DIR]
               [-n OUTPUT_NAME] [--en-only] [--batch-size BATCH_SIZE]
               [-i]
               [url]

位置引数:
  url                   YouTube URL

オプション:
  -h, --help            このヘルプメッセージを表示して終了
  --translator {argos,deepl}
                        日本語テキストを生成する翻訳エンジン。デフォルトはargos
  --deepl-auth-key DEEPL_AUTH_KEY
                        DeepL APIキー。指定しない場合は、.envファイルまたはDEEPL_AUTH_KEY環境変数を使用します。
  --out-dir OUT_DIR     出力ディレクトリ。デフォルト: out
  -n, --output-name OUTPUT_NAME
                        出力ファイルのベース名。指定しない場合は、動画IDから自動的に決定されます。
  --en-only             翻訳をスキップして英語のみ出力します。
  --batch-size BATCH_SIZE
                        一緒にバッチ処理する翻訳の数。デフォルト: 100
  -i, --interactive     オプションを対話的に尋ねる
```

### 実行例

デフォルトでは、スクリプトは提供されたYouTube URLの英語字幕をダウンロードし、無料の[Argos Translate](https://github.com/argosopentech/argos-translate)モデルを使用して日本語翻訳を生成し、`out`ディレクトリに以下のファイルを出力します：

1. **`.tsv`**: 翻訳結果を含むタブ区切りデータ。
2. **`.srt`**: 動画プレーヤー用のバイリンガル字幕（SRT）形式。
3. **`.md`**: 言語学習のための並列翻訳を含むフォーマットされたMarkdownファイル。

（成功裏に完了すると、`yt-dlp`によってダウンロードされた元の字幕ファイルは自動的に削除されます。）

### 開発チェック

```bash
uv run python test_interactive.py
```