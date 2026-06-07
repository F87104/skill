# Substack 自動いいねツール（Selenium版）

Substackのホームフィードを巡回し、投稿に自動でいいねするツールです。
**Selenium + Chrome** で動作し、専用プロフィールにログイン状態を保存します。

## 前提条件

```bash
pip3 install selenium webdriver-manager
```

- Google Chrome がインストールされていること
- **実行前に通常の Chrome を完全終了すること**（Mac: `Command + Q`）

## 初回セットアップ

1. 通常の Chrome を終了する
2. スクリプトを実行する

```bash
python3 skills/substack_auto_tool/substack_auto_like.py
```

3. 起動した Chrome で Substack にログインする（初回のみ）
4. ログイン状態は `~/.substack_prometheus` に保存され、次回以降は自動ログイン

## 使い方

```bash
python3 skills/substack_auto_tool/substack_auto_like.py
```

- ホームフィード（`https://substack.com/home`）を開き、いいねボタンを巡回
- 1回の実行で最大 **20件** いいね（`MAX_LIKES`）
- いいね間隔は **8〜20秒** のランダム待機（`MIN_WAIT` / `MAX_WAIT`）
- `Ctrl + C` で中断可能

## 設定のカスタマイズ

`substack_auto_like.py` 上部の定数を編集します。

| 定数 | デフォルト | 説明 |
|------|-----------|------|
| `MIN_WAIT` | 8 | いいね間の最小待機秒数 |
| `MAX_WAIT` | 20 | いいね間の最大待機秒数 |
| `MAX_LIKES` | 20 | 1回の実行でのいいね上限 |

## ファイル構成

```
skills/substack_auto_tool/
├── SKILL.md                 この指示書
└── substack_auto_like.py    Selenium自動いいねスクリプト
```

## トラブルシューティング

### Chromeが起動しない

通常の Chrome が開いたままの可能性があります。完全終了してから再実行してください。

### ログインが確認できない

ブラウザで Substack に手動ログイン後、再度実行してください。
プロフィールをリセットする場合:

```bash
rm -rf ~/.substack_prometheus
```

## 注意事項

- 自動操作ツールです。Substack の利用規約に従ってご使用ください。
- 過度な利用はアカウント制限の原因になる可能性があります。
- Substack の UI 変更により、セレクタが動かなくなる場合があります。
