#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
X 自動いいねシステム
====================
指定したアカウントの新規投稿を検知し、自動でいいねします。
さくらVPS上でcronにより15分ごとに実行されることを想定しています。

凍結対策:
  - レートリミット厳守（50回/15分の上限に対し30回/実行で余裕を確保）
  - いいね間にランダムスリープ（2〜5秒）
  - SQLiteによる重複いいね完全防止
  - エラー時の指数バックオフ
  - 詳細ログによる異常検知
"""

import os
import sys
import time
import random
import sqlite3
import logging
import logging.handlers
import yaml
import tweepy
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ============================================================
# スクリプトのディレクトリを基準にパスを解決
# ============================================================
SCRIPT_DIR = Path(__file__).parent.resolve()


def load_config(config_path: Path) -> dict:
    """設定ファイルを読み込む"""
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def setup_logging(log_file: str) -> logging.Logger:
    """ロギングを設定する"""
    log_path = SCRIPT_DIR / log_file
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("auto_like")
    logger.setLevel(logging.INFO)

    # ログローテーション（1MB × 5世代）
    handler = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=1_048_576, backupCount=5, encoding="utf-8"
    )
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # コンソールにも出力
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    logger.addHandler(console)

    return logger


def init_db(db_file: str) -> sqlite3.Connection:
    """SQLiteデータベースを初期化する"""
    db_path = SCRIPT_DIR / db_file
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS liked_tweets (
            tweet_id TEXT PRIMARY KEY,
            liked_at  TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_liked_at ON liked_tweets (liked_at)
    """)
    conn.commit()
    return conn


def cleanup_old_records(conn: sqlite3.Connection, cleanup_days: int, logger: logging.Logger):
    """古いいいね済みレコードを削除してDBサイズを管理する"""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=cleanup_days)).isoformat()
    cursor = conn.execute(
        "DELETE FROM liked_tweets WHERE liked_at < ?", (cutoff,)
    )
    conn.commit()
    if cursor.rowcount > 0:
        logger.info(f"古いレコードを {cursor.rowcount} 件削除しました（{cleanup_days}日以前）")


def is_already_liked(conn: sqlite3.Connection, tweet_id: str) -> bool:
    """すでにいいね済みかチェックする"""
    row = conn.execute(
        "SELECT 1 FROM liked_tweets WHERE tweet_id = ?", (tweet_id,)
    ).fetchone()
    return row is not None


def record_like(conn: sqlite3.Connection, tweet_id: str):
    """いいね済みとして記録する"""
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT OR IGNORE INTO liked_tweets (tweet_id, liked_at) VALUES (?, ?)",
        (tweet_id, now)
    )
    conn.commit()


def get_user_id(client: tweepy.Client, username: str, logger: logging.Logger) -> str | None:
    """ユーザー名からユーザーIDを取得する"""
    try:
        response = client.get_user(username=username)
        if response.data:
            return str(response.data.id)
        else:
            logger.warning(f"ユーザーが見つかりません: @{username}")
            return None
    except tweepy.TweepyException as e:
        logger.error(f"ユーザーID取得エラー (@{username}): {e}")
        return None


def get_recent_tweets(
    client: tweepy.Client,
    user_id: str,
    username: str,
    max_results: int,
    logger: logging.Logger
) -> list:
    """指定ユーザーの最新ツイートを取得する"""
    try:
        # 過去15分以内の投稿のみ取得（15分ごとの実行に合わせる）
        start_time = datetime.now(timezone.utc) - timedelta(minutes=16)
        response = client.get_users_tweets(
            id=user_id,
            max_results=max_results,
            start_time=start_time,
            tweet_fields=["created_at", "author_id"],
            exclude=["retweets", "replies"]  # RTと返信は除外（任意）
        )
        if response.data:
            return response.data
        return []
    except tweepy.TooManyRequests as e:
        logger.warning(f"レートリミット到達 (@{username}): {e}")
        # レートリミットリセットまで待機
        reset_time = int(e.response.headers.get("x-rate-limit-reset", time.time() + 900))
        wait_sec = max(reset_time - int(time.time()), 0) + 10
        logger.info(f"レートリミットリセット待機: {wait_sec}秒")
        time.sleep(wait_sec)
        return []
    except tweepy.TweepyException as e:
        logger.error(f"ツイート取得エラー (@{username}): {e}")
        return []


def like_tweet_with_retry(
    client: tweepy.Client,
    my_user_id: str,
    tweet_id: str,
    username: str,
    logger: logging.Logger,
    max_retries: int = 3
) -> bool:
    """いいねを実行する（エラー時は指数バックオフでリトライ）"""
    for attempt in range(max_retries):
        try:
            client.like(tweet_id=tweet_id)
            return True
        except tweepy.TooManyRequests as e:
            reset_time = int(e.response.headers.get("x-rate-limit-reset", time.time() + 900))
            wait_sec = max(reset_time - int(time.time()), 0) + 10
            logger.warning(
                f"いいねレートリミット到達 (@{username}, tweet:{tweet_id}): "
                f"{wait_sec}秒待機後リトライ"
            )
            time.sleep(wait_sec)
        except tweepy.Forbidden as e:
            # すでにいいね済みの場合など
            logger.info(f"いいねスキップ（Forbidden） (@{username}, tweet:{tweet_id}): {e}")
            return True  # 重複いいねとして扱い、記録はする
        except tweepy.TweepyException as e:
            wait_sec = (2 ** attempt) * 5  # 指数バックオフ: 5, 10, 20秒
            logger.error(
                f"いいねエラー (@{username}, tweet:{tweet_id}): {e} "
                f"({attempt + 1}/{max_retries}) {wait_sec}秒後リトライ"
            )
            if attempt < max_retries - 1:
                time.sleep(wait_sec)
    logger.error(f"いいね失敗（リトライ上限） (@{username}, tweet:{tweet_id})")
    return False


def main():
    # --- 設定読み込み ---
    config_path = SCRIPT_DIR / "config.yaml"
    if not config_path.exists():
        print(f"設定ファイルが見つかりません: {config_path}", file=sys.stderr)
        sys.exit(1)

    config = load_config(config_path)
    settings = config["settings"]
    api_conf = config["api"]
    target_accounts = config.get("target_accounts", [])

    # --- ロギング設定 ---
    logger = setup_logging(settings["log_file"])
    logger.info("=" * 60)
    logger.info("X 自動いいねシステム 起動")
    logger.info(f"対象アカウント数: {len(target_accounts)}")

    if not target_accounts:
        logger.warning("対象アカウントが設定されていません。config.yaml を確認してください。")
        sys.exit(0)

    # --- DB初期化 ---
    conn = init_db(settings["db_file"])
    cleanup_old_records(conn, settings["cleanup_days"], logger)

    # --- Tweepy クライアント初期化 ---
    try:
        client = tweepy.Client(
            bearer_token=api_conf["bearer_token"],
            consumer_key=api_conf["client_id"],
            consumer_secret=api_conf["client_secret"],
            access_token=api_conf["access_token"],
            access_token_secret=api_conf["access_token_secret"],
            wait_on_rate_limit=False  # 自前でレートリミット管理
        )
        # 自分のユーザーIDを取得
        me = client.get_me()
        if not me.data:
            logger.error("認証情報が無効です。API キーを確認してください。")
            sys.exit(1)
        my_user_id = str(me.data.id)
        logger.info(f"認証済みユーザー: @{me.data.username} (ID: {my_user_id})")
    except tweepy.TweepyException as e:
        logger.error(f"Tweepy クライアント初期化エラー: {e}")
        sys.exit(1)

    # --- メイン処理 ---
    total_liked = 0
    max_likes = settings["max_likes_per_run"]

    for username in target_accounts:
        if total_liked >= max_likes:
            logger.info(f"1回の実行上限 ({max_likes}いいね) に達しました。残りは次回実行時に処理します。")
            break

        # ユーザーIDを取得
        user_id = get_user_id(client, username, logger)
        if not user_id:
            continue

        # 最新ツイートを取得
        tweets = get_recent_tweets(
            client, user_id, username,
            settings["max_results_per_user"], logger
        )

        if not tweets:
            continue

        logger.info(f"@{username}: {len(tweets)} 件の新規投稿を検出")

        for tweet in tweets:
            if total_liked >= max_likes:
                break

            tweet_id = str(tweet.id)

            # 重複チェック
            if is_already_liked(conn, tweet_id):
                logger.debug(f"スキップ（いいね済み）: tweet_id={tweet_id}")
                continue

            # いいね実行
            success = like_tweet_with_retry(
                client, my_user_id, tweet_id, username, logger
            )

            if success:
                record_like(conn, tweet_id)
                total_liked += 1
                logger.info(
                    f"いいね完了: @{username} tweet_id={tweet_id} "
                    f"({total_liked}/{max_likes})"
                )

                # ランダムスリープ（凍結対策）
                if total_liked < max_likes:
                    sleep_sec = random.uniform(
                        settings["sleep_min"],
                        settings["sleep_max"]
                    )
                    time.sleep(sleep_sec)

        # アカウント間にも短い待機を入れる
        time.sleep(random.uniform(0.5, 1.5))

    # --- 終了 ---
    conn.close()
    logger.info(f"実行完了: 今回のいいね数 = {total_liked} 件")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
