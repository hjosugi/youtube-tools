<!-- i18n: language-switcher -->
[English](README.md) | [日本語](README.ja.md)

# yt-fetch-cli

`yt-fetch-cli`は、YouTubeの字幕、高品質オーディオ（MP3）、およびビデオ（MP4）をシームレスにダウンロードするための、非常に高速で、厳密にネイティブな、ゼロ環境のスタンドアロンCLIツールです。

これは、内部で素晴らしい`yt-dlp`エンジンを`PyInstaller`を介してバンドルしているため、**このコマンドを実行するためにPythonや`yt-dlp`をインストールする必要はありません**。

## インストール

[GitHub Releases](https://github.com/hjosugi/youtube-tools/releases)ページに移動し、Linux用の`yt-fetch-cli`をダウンロードします。

実行可能にして、PATHに移動します：
```bash
chmod +x yt-fetch-cli
sudo mv yt-fetch-cli /usr/local/bin/
```
> **注意**：Pythonは必要ありませんが、MP3オーディオフォーマットを抽出するために、システムに`ffmpeg`がインストールされている必要があります（例：`sudo apt install ffmpeg`）。これは標準の`yt-dlp`の後処理動作です。

## 機能と使用法

引数なしで`yt-fetch-cli`を実行すると、ガイド付きセットアップが行われます。最初に`-h`を読むことなく使用できます。

```bash
yt-fetch-cli
```

プロンプトでは以下を尋ねられます：

1. YouTube URL
2. 字幕 / MP3 / MP4
3. 必要に応じたMP4解像度
4. 出力ディレクトリ
5. 最終確認

スクリプトで直接すべてを渡すこともできます：

```bash
# 例：1080pで字幕、MP3、MP4をダウンロード
yt-fetch-cli "https://www.youtube.com/watch?v=..." --subtitles --mp3 --mp4 --resolution 1080
```

### インタラクティブモード

**引数なし**または`--interactive`で実行すると、オプションをガイドされます：

```bash
$ yt-fetch-cli
YouTube Fetcherインタラクティブセットアップ
YouTube URL（スペースで区切る）：https://www.youtube.com/watch?v=...
字幕をTSVとして [Y/n]：
MP3オーディオ [y/N]：y
MP4ビデオ [y/N]：
出力ディレクトリ [.]: downloads
ダウンロードを開始 [Y/n]：
```

プロンプトで複数のスペース区切りのURLを貼り付けることができます。

### オプション

| フラグ | 説明 |
| ---- | ----------- |
| `--subtitles` | 自動および手動の英語字幕をダウンロードし、明示的に`.tsv`に出力します。 |
| `--mp3` | 世界中で最高品質のオーディオをダウンロードし、MP3に抽出します。 |
| `--mp4` | ビデオをダウンロードし、最高品質のオーディオとインラインでマージします。 |
| `--resolution` | 最大高さを制限します。選択肢：`best, 1080, 720, 480, 360`（デフォルト：`best`） |
| `-o`, `--output` | 目的地ディレクトリ。（デフォルト：`./` 現在のディレクトリ） |

---
### 自動補完

リポジトリ内の`completions/`フォルダに、`bash`と`fish`用の手動で非常にスナッピーな静的自動補完フックを提供しています。これらをシェルプロファイル（`~/.bashrc` / `~/.config/fish/config.fish`）にソースするだけで、`[Tab]`自動補完が利用可能になります。

## 開発

このツールを修正する場合は、[`uv`](https://docs.astral.sh/uv/)をインストールし、次のコマンドを実行します：
```bash
# 依存関係をインストール
uv sync

# CLIラッパーを通常通り実行
uv run python cli.py

# ダウンロードせずにインタラクティブプロンプトフローをテスト
uv run python test_interactive.py

# バージョンを自動的に更新（Gitクリーンツリーが必要）
# 例：パッケージロジック文字列を更新し、クリーンにコミットし、ネイティブにタグロジックを設定
uvx bump-my-version bump patch # （またはminor、major）

# PyInstallerを介してローカルにビルド
./build.sh
```