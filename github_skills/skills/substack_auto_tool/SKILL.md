# Substack 自動いいね＆フォローツール（安全版 v2）

人間らしい動作パターンでアカウント凍結を防止する自動いいね＆フォローツールです。
**Seleniumは不要**で、純粋なHTTP APIベースで動作します。

## 安全機能

| 機能 | 内容 |
|---|---|
| 日次いいね上限 | 50件/日（カウンターで厳密管理） |
| 日次フォロー上限 | 5件/日 |
| いいね間の待機 | 5〜25秒（正規分布ランダム） |
| モード間の休憩 | 30〜120秒 |
| フォロー間の待機 | 30〜90秒 |
| 連続いいね制限 | 3件連続で長い休憩 |
| ランダムスキップ | 25%の確率で意図的にスキップ |
| レート制限検出 | 2回で3時間自動停止 |
| エラー検出 | 3回で6時間自動停止 |
| 実行間隔ランダム化 | ±30分のジッター |
| User-Agentローテーション | 3種類をランダム使用 |

## 旧版との比較

| 項目 | 旧版 | 安全版 v2 |
|---|---|---|
| 1回のいいね数 | 34件×3モード=102件 | 8件×3モード=24件 |
| 1日のいいね数 | 306件（制限なし） | 最大50件（厳密管理） |
| 1日のフォロー数 | 15件 | 最大5件 |
| いいね間の待機 | 固定2秒 | 5〜25秒（ランダム） |
| モード間の休憩 | 5秒 | 30〜120秒 |
| レート制限対応 | 60秒待機 | 3時間自動停止 |
| エラー対応 | なし | 3回で6時間停止 |
| 実行間隔 | 固定5時間 | 8時間±30分 |

---

## セットアップ

```bash
pip install requests
```

## クッキーの設定

1. ブラウザでSubstackにログイン
2. F12（DevTools）を開く
3. Application > Cookies > substack.com
4. `substack.sid` の値をコピー
5. `config.json` の `"cookie"` に貼り付け

---

## 使い方

### 接続テスト

```bash
python3 main.py --test
```

### 全モード実行（推奨）

```bash
cd "/Users/asamifujita/Library/CloudStorage/GoogleDrive-fujita.waraku@gmail.com/マイドライブ/AI_images/substack-auto-like 3"
python3 main.py --config config.json --mode all
```

### ドライラン（実行せず確認）

```bash
python3 main.py --config config.json --mode all --dry-run
```

### 本日の残り件数を確認

```bash
python3 main.py --status
```

### 統計情報

```bash
python3 main.py --stats
```

### 個別モード

```bash
# いいねのみ
python3 main.py --config config.json --mode likes-all

# フォローのみ
python3 main.py --config config.json --mode follow

# フォローバックのみ
python3 main.py --config config.json --mode followback
```

---

## config.json の設定

```json
{
  "cookie": "YOUR_COOKIE_HERE",
  "max_likes_per_mode": 8,
  "max_follows": 3,
  "daily_like_limit": 50,
  "daily_follow_limit": 5,
  "schedule_interval_minutes": 480,
  "quiet_hours_start": 0,
  "quiet_hours_end": 8
}
```

| 設定項目 | デフォルト | 説明 |
|---|---|---|
| max_likes_per_mode | 8 | 1回あたりの各モードの最大いいね数 |
| max_follows | 3 | 1回あたりの最大フォロー数 |
| daily_like_limit | 50 | 1日のいいね上限（厳密管理） |
| daily_follow_limit | 5 | 1日のフォロー上限（厳密管理） |
| schedule_interval_minutes | 480 | スケジューラーの実行間隔（分） |
| quiet_hours_start | 0 | 静粛時間の開始（時） |
| quiet_hours_end | 8 | 静粛時間の終了（時） |

---

## ファイル構成

```
substack-auto-like/
├── main.py              メインCLI
├── substack_client.py   API通信（安全機能内蔵）
├── auto_liker.py        自動いいね（3モード）
├── auto_follow.py       自動フォロー（APIベース）
├── scheduler.py         定期実行
├── config.json          設定ファイル
├── daily_limits.json    日次制限カウンター（自動生成）
├── like_state.json      いいね状態（自動生成）
├── follow_state.json    フォロー状態（自動生成）
├── get_cookie.py        クッキー取得ヘルパー
├── run_auto.sh          cron用スクリプト
├── setup_cron.sh        crontabセットアップ
└── requirements.txt     依存パッケージ（requestsのみ）
```

---

## 使用APIエンドポイント

| エンドポイント | メソッド | 用途 |
|---|---|---|
| `/api/v1/reader/feed` | GET | ホームフィード取得 |
| `/api/v1/activity-feed-web` | GET | アクティビティ取得 |
| `/api/v1/feed/following` | GET | フォロー中リスト取得 |
| `/api/v1/post/{id}/reaction` | POST | 投稿にいいね |
| `/api/v1/comment/{id}/reaction` | POST | コメント/ノートにいいね |
| `/api/v1/feed/{user_id}/follow` | POST | ユーザーフォロー |
| `/api/v1/reader/signup/pub` | POST | Publication購読 |

---

## 注意事項

- 非公式APIを使用しているため、Substack側の仕様変更で動作しなくなる可能性があります
- クッキーには有効期限があります。期限切れの場合は再取得が必要です
- クッキーの値は機密情報です。GitHubなどに公開しないでください
- アカウント凍結が解除されたら、まず `--dry-run` で動作確認してから実行してください
