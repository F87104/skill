# X 自動いいねシステム 導入・運用マニュアル

## 概要
指定した最大300アカウントの新規投稿を15分ごとに検知し、自動でいいね（Like）するシステムです。
さくらVPS上で常時稼働させることを想定しており、X（Twitter）のAPI凍結リスクを最小限に抑えるための工夫が施されています。

---

## 1. 事前準備（X Developer アカウントの取得）

X API を利用するために、Developer アカウントと API キーを取得します。

1. **Developer Portal にアクセス**
   - [X Developer Portal](https://developer.x.com/) にアクセスし、自動いいねを行いたいアカウントでログインします。
   - 「Sign up for Free Account」または「Subscribe to a tier」を選択します。

2. **料金プランの選択**
   - 現在、新規開発者は **Pay-per-use（従量課金制）** プランを選択する必要があります。
   - ※2025年8月以降、Free tier では「いいね」の書き込みができません [1]。
   - クレジットカードを登録し、Pay-per-use プランを有効化してください。

3. **プロジェクトとアプリの作成**
   - Developer Portal のダッシュボードで「Projects & Apps」から新しいアプリを作成します。
   - アプリの権限（App permissions）を **「Read and write」** に設定します。
   - 以下の3つのキーをコピーして控えておきます。
     - **Client ID** (OAuth 2.0 Client ID)
     - **Client Secret**
     - **Bearer Token**

---

## 2. さくらVPSへの導入手順

作成したシステムをVPSに転送し、セットアップを行います。

### 2.1. ファイルの配置
納品した `x_auto_like` フォルダを、さくらVPSの任意の場所（例: `/home/ubuntu/x_auto_like`）に配置します。

### 2.2. 設定ファイルの編集
`config.yaml` をテキストエディタで開き、APIキーと対象アカウントを設定します。

```bash
cd x_auto_like
nano config.yaml
```

**編集箇所:**
- `client_id`: 取得した Client ID
- `client_secret`: 取得した Client Secret
- `bearer_token`: 取得した Bearer Token
- `target_accounts`: いいね対象のアカウントの `@` を除いたユーザー名を列挙（最大300件）

### 2.3. セットアップスクリプトの実行
依存パッケージのインストールと、定期実行（cron）の設定を行います。

```bash
bash setup.sh
```

### 2.4. 初回認証（アクセストークンの取得）
Xアカウントへのアクセス権限（アクセストークン）を取得します。

```bash
python3 auth_setup.py
```

1. 画面に表示されるURLをブラウザで開きます。
2. Xアカウントでログインし、アプリを連携（Authorize）します。
3. 画面に表示される **PINコード** をコピーし、ターミナルに貼り付けてEnterを押します。
4. ターミナルに表示された `access_token` と `access_token_secret` をコピーし、`config.yaml` に追記します。

### 2.5. 動作確認
手動でスクリプトを実行し、エラーが出ないか確認します。

```bash
python3 auto_like.py
```

---

## 3. 凍結対策と安全な運用について

このシステムは凍結リスクを最小化するために以下の対策を実装しています。

1. **レートリミットの厳守**:
   X API のいいね上限（50回/15分）に対し、1回の実行上限をデフォルトで **30回** に制限しています [2]。
2. **ランダムな待機時間**:
   機械的な動作と判定されないよう、いいねといいねの間に2〜5秒のランダムな待機時間を設けています。
3. **重複いいねの防止**:
   SQLiteデータベースを使用して、過去にいいねしたツイートIDを記憶し、同じツイートへの無駄なAPI呼び出しを防ぎます。
4. **エラー時の指数バックオフ**:
   APIの一時的なエラー時には、待機時間を倍々に増やしながらリトライします。

### 運用上の注意点
- **対象アカウント数と頻度**:
  300アカウントすべてが同時に投稿した場合、15分で30いいねの上限に達するため、残りは次の15分サイクルで処理されます。
- **コスト管理**:
  Pay-per-useプランでは、投稿の読み取り（$0.005/件）といいね（$0.015/件）に費用がかかります。APIの利用状況は Developer Portal で定期的に確認してください [3]。

---

## 4. ログの確認とトラブルシューティング

システムは自動的にバックグラウンドで動作し、ログを記録します。
動作状況を確認するには以下のコマンドを使用します。

```bash
# リアルタイムでログを確認
tail -f logs/auto_like.log

# エラーログだけを確認
grep "ERROR" logs/auto_like.log
```

## References
[1] [Update to X API Free Tier: Removal of Like and Follow Endpoints - X Developer Community](https://devcommunity.x.com/t/update-to-x-api-free-tier-removal-of-like-and-follow-endpoints/247646)
[2] [X API Rate Limits - X Developer Platform](https://docs.x.com/x-api/fundamentals/rate-limits)
[3] [X API pay-per-usage pricing and credits - X Developer Platform](https://docs.x.com/x-api/getting-started/pricing)
