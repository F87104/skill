# Project Prometheus v4.0 インストール手順

## 概要

X API Basicプランの厳しいレート制限（15分5回）に完全対応した新バージョンです。

## 更新内容

1. **auto_like_v4.py** - 新しい自動いいねスクリプト（シンプル＆確実）
2. **core/x_client.py** - APIクライアントの完全再設計
3. **echo/engagement_engine.py** - エンゲージメントエンジンの再設計
4. **自動いいね開始_v4.command** - 新しいデスクトップショートカット

## インストール手順

### 1. ZIPファイルを展開

ダウンロードした `prometheus_v4_update.zip` を展開します。

### 2. ファイルをコピー

展開したファイルを、既存の `~/prometheus` フォルダにコピーします。

```bash
# ターミナルで実行
cd ~/Downloads
unzip prometheus_v4_update.zip -d ~/prometheus_v4_temp
cp ~/prometheus_v4_temp/auto_like_v4.py ~/prometheus/
cp ~/prometheus_v4_temp/core/x_client.py ~/prometheus/core/
cp ~/prometheus_v4_temp/echo/engagement_engine.py ~/prometheus/echo/
cp ~/prometheus_v4_temp/echo/__init__.py ~/prometheus/echo/
```

### 3. ショートカットをデスクトップにコピー

```bash
cp ~/prometheus_v4_temp/自動いいね開始_v4.command ~/Desktop/
chmod +x ~/Desktop/自動いいね開始_v4.command
```

### 4. 動作確認

```bash
cd ~/prometheus
python3 auto_like_v4.py
```

成功すると以下のように表示されます：
- `[SUCCESS] 認証成功: @Fuj_100mili`
- `[SUCCESS] ✅ いいね成功`

## 使い方

### 方法1: デスクトップショートカット

デスクトップの「自動いいね開始_v4.command」をダブルクリック

### 方法2: ターミナルから実行

```bash
cd ~/prometheus
python3 auto_like_v4.py --loop  # 継続実行
python3 auto_like_v4.py         # 1回だけ実行
```

## トラブルシューティング

### 「レート制限」が表示される

正常な動作です。Xのルール（15分5回）に従って自動で待機します。

### いいねが1件も成功しない

1. `.env` ファイルのAPI認証情報を確認
2. X Developer Portalでアプリの権限を確認（Read and Write必須）

## 技術的な変更点

- いいね成功後は3分間隔で次のいいね（15分÷5回=3分）
- 429エラー時はレスポンスヘッダーからリセット時刻を取得
- レート制限中は自動で待機時間を計算
