# pysonX 自動運用ツール スキルマニュアル

## 1. スキル名
pysonX 自動運用ツール (pysonX Automation Tools)

## 2. 概要
本スキルは、X（旧Twitter）における自動いいね、自動フォロー、自動いいね返し、および投稿生成を統合的に行う「pysonX (Prometheus)」システムの運用方法を定義する。

## 3. 主要ファイル構成
リポジトリ内の `skills/pyson_x_auto_tool/` には以下の主要ファイルが含まれる。

### A. 自動いいね・フォロー（安定版）
- `auto_like_v11.2.1_hotfix.py`: 24時間自動運用（投資関連のみ）＆フォロー＆アンフォローの推奨版。
- `auto_like_v11.3_smart_follow.py`: 条件付きフォロー（フォロワー500人以上、詐欺排除）に対応した最新版。

### B. 自動いいね返し
- `auto_like_v12.13_pinned_text_fix.py`: 自分のツイートにいいねしてくれた人に返す安定版。固定ツイートスキップ対応。

### C. 投稿生成（Trend Oracle）
- `trend_oracle_v2.8.0_pro_news_triple_choice.py`: 話題のニュースから投資家Fスタイルの投稿文を3案自動生成する最新版。

### D. 設定・プロンプト
- `config.ini`: 動作待機時間、キーワード、フォロー確率などの基本設定ファイル。
- `post_prompt.txt`: 投稿生成時に使用されるベースプロンプト。

## 4. 基本的な使い方（Macターミナル）

### 24時間自動運用（おすすめ）
```bash
python3 ~/prometheus/auto_like_v11.2.1_hotfix.py --loop
```

### 通知欄へのいいね返し
```bash
python3 ~/prometheus/auto_like_v11.2.1_hotfix.py --likeback
```

### ニュースから投稿生成
```bash
python3 ~/prometheus/trend_oracle_v2.8.0_pro_news_triple_choice.py
```

## 5. 運用上の注意
- **初回実行時**: ブラウザが開くので、手動でXにログインしてください。ログイン後、ターミナルでEnterキーを押すと自動運用が開始されます。
- **エラー対応**: ログイン切れやYahooニュースのURL変更などは、最新バージョン（v11.2.1以降 / v2.8.0）で修正済みです。
- **APIキー**: `trend_oracle` の実行には OpenAI APIキーの設定が必要です。

---
**詳細な設定**: `config.ini` を編集することで、ターゲットキーワードや除外キーワード、フォローの有効/無効を細かく調整できます。
