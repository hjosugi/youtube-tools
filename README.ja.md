<!-- i18n: language-switcher -->
[English](README.md) | [日本語](README.ja.md)

# YouTube Tools

YouTube の音声・動画・字幕を1つで扱うクロスプラットフォームツールです。

最終確認日: 2026-09-04

## ツール

| アプリ | パス | 用途 | 実行環境 |
| --- | --- | --- | --- |
| `yt` | `apps/yt` | 音声・動画・字幕をダウンロードする CLI とデスクトップ GUI | Python + uv、または単体バイナリ |

機能は1つのコマンドにまとまっています。詳細は `apps/yt/README.ja.md` を参照してください。

## クイックスタート

[Releases](https://github.com/hjosugi/youtube-tools/releases) から使用中の環境向けバイナリを取得すれば Python は不要です。ソースから動かす場合は次のとおりです。

```bash
cd apps/yt
uv sync
uv run yt --help
```

```bash
yt URL                     # 英語字幕を .srt と .tsv で
yt URL -m avs              # 音声・動画・字幕を1回で
yt URL -m s -l en,ja       # 英語と日本語の字幕
yt URL -m v --vq 1080      # 動画を 1080p までに制限
yt URL -m a --aq 192       # 音声を 192 kbps で
yt --gui                   # GUI を開く
yt -i                      # ターミナルの対話モード
yt -o ~/Downloads --save-config   # 保存先を既定値として記憶
```

音声の抽出と、映像・音声ストリームの結合には `ffmpeg` が必要です。`PATH` に入れておいてください。

## リポジトリ構成

```text
apps/
  yt/            本体: CLI・GUI・テスト・ビルドスクリプト・シェル補完
docs/
  consolidation.ja.md
.github/workflows/
  ci.yml         Linux / macOS / Windows で lint とテスト
  release.yml    v* タグで各プラットフォーム向けの単体バイナリを作成
```

## これまでの経緯

もとは4つの別々の YouTube ユーティリティでした。現在は1つのツールに統合しています。
統合の内容と削除したものは [`docs/consolidation.ja.md`](docs/consolidation.ja.md) を参照してください。

## 安全性と利用範囲

- アクセスと処理が許可されているコンテンツにのみ使用してください。
- YouTube の利用規約・著作権・レート制限・投稿者の許諾を尊重してください。
- ダウンロードしたメディア・字幕・API キー・Cookie・ブラウザプロファイルはコミットしないでください。
- MP3 / MP4 の抽出には `ffmpeg` が必要です。

## ライセンス

0BSD。ほぼ任意の目的で利用・複製・改変・配布できます。
