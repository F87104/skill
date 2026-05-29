# Project Prometheus ブラウザ自動いいね v5.0 - インストール手順

## 概要

X APIの厳しい制限（15分5回）を回避するため、ブラウザ自動化（Playwright）を使用した新しいバージョンです。

**メリット:**
- API制限なし（15分5回の制限を受けない）
- 自然なペースでいいね（5〜15秒間隔）
- ログイン状態を保存（2回目以降は自動ログイン）

## インストール手順

### 1. Playwrightをインストール

ターミナルを開いて、以下のコマンドを実行してください：

```bash
# Playwrightライブラリをインストール
pip3 install playwright

# ブラウザ（Chromium）をインストール
playwright install chromium
```

### 2. スクリプトをコピー

ダウンロードした `auto_like_browser.py` を `~/prometheus/` フォルダにコピーします。

### 3. 初回セットアップ（ログイン）

初回は手動でXにログインする必要があります：

```bash
cd ~/prometheus
python3 auto_like_browser.py --setup
```

ブラウザが開くので、Xにログインしてください。ログイン後、ターミナルでEnterキーを押すと完了です。

**ログイン情報は保存されるので、次回以降は自動でログインされます。**

### 4. 動作確認

```bash
cd ~/prometheus
python3 auto_like_browser.py
```

## 使い方

### 1回だけ実行（10件いいね）

```bash
cd ~/prometheus
python3 auto_like_browser.py
```

### 継続実行（Ctrl+Cで停止）

```bash
cd ~/prometheus
python3 auto_like_browser.py --loop
```

### ブラウザを表示して実行（動作確認用）

```bash
cd ~/prometheus
python3 auto_like_browser.py --visible
```

## デスクトップショートカットの作成

ターミナルで以下を実行：

```bash
cat > ~/Desktop/自動いいね_ブラウザ版.command << 'EOF'
#!/bin/bash
cd ~/prometheus
python3 auto_like_browser.py --loop
EOF

chmod +x ~/Desktop/自動いいね_ブラウザ版.command
```

## 設定のカスタマイズ

`auto_like_browser.py` の上部にある設定を変更できます：

```python
KEYWORDS = ["FX", "為替", "ドル円", ...]  # いいね対象のキーワード
LIKES_PER_CYCLE = 10  # 1サイクルあたりのいいね数
MIN_WAIT = 5  # いいね間の最小待機秒数
MAX_WAIT = 15  # いいね間の最大待機秒数
```

## トラブルシューティング

### 「Playwrightがインストールされていません」

```bash
pip3 install playwright
playwright install chromium
```

### ログインが保存されない

`~/.prometheus_browser` フォルダを削除して、再度 `--setup` を実行：

```bash
rm -rf ~/.prometheus_browser
python3 auto_like_browser.py --setup
```

### ブラウザが起動しない

Chromiumを再インストール：

```bash
playwright install chromium --force
```

## 注意事項

- このツールは自動化ツールです。Xの利用規約に従ってご使用ください。
- 過度な使用はアカウント制限の原因になる可能性があります。
- 適度な間隔（5〜15秒）を設定しています。
