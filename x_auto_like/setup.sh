#!/bin/bash
# ============================================================
# X 自動いいねシステム セットアップスクリプト
# さくらVPS (Ubuntu 22.04 / 24.04) 向け
# ============================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================================"
echo " X 自動いいねシステム セットアップ"
echo "============================================================"

# --- Python3 / pip3 の確認 ---
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] python3 が見つかりません。インストールしてください。"
    exit 1
fi

echo "[1/4] Python バージョン確認..."
python3 --version

# --- 依存パッケージのインストール ---
echo "[2/4] 依存パッケージをインストール中..."
pip3 install --upgrade pip -q
pip3 install -r requirements.txt -q
echo "  完了: tweepy, PyYAML"

# --- ログディレクトリの作成 ---
echo "[3/4] ログディレクトリを作成中..."
mkdir -p logs
echo "  完了: logs/"

# --- cron ジョブの設定 ---
echo "[4/4] cron ジョブを設定中..."
CRON_CMD="*/15 * * * * cd $SCRIPT_DIR && /usr/bin/python3 $SCRIPT_DIR/auto_like.py >> $SCRIPT_DIR/logs/cron.log 2>&1"

# 既存のcronに同じジョブがなければ追加
if crontab -l 2>/dev/null | grep -qF "auto_like.py"; then
    echo "  cron ジョブはすでに設定済みです。スキップします。"
else
    (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
    echo "  完了: 15分ごとに自動実行するcronジョブを追加しました。"
fi

echo ""
echo "============================================================"
echo " セットアップ完了！"
echo "============================================================"
echo ""
echo "次のステップ:"
echo "  1. config.yaml を開いて API キーと対象アカウントを設定してください"
echo "     nano config.yaml"
echo ""
echo "  2. 初回認証を実行してアクセストークンを取得してください"
echo "     python3 auth_setup.py"
echo ""
echo "  3. 動作確認のため、手動で1回実行してください"
echo "     python3 auto_like.py"
echo ""
echo "  4. ログを確認してください"
echo "     tail -f logs/auto_like.log"
echo ""
echo "  5. cron の設定を確認してください"
echo "     crontab -l"
echo "============================================================"
