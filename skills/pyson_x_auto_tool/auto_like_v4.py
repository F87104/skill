#!/usr/bin/env python3
"""
Project Prometheus - 自動いいね v4.0
====================================
X API Basicプラン完全対応版

特徴:
- 15分あたり5回のいいね制限に完全対応
- 429エラー時は自動でリセット時刻まで待機
- いいね成功後は3分間隔で次のいいね
- シンプルで確実な動作

使い方:
    python3 auto_like_v4.py           # 1サイクル実行（最大5件）
    python3 auto_like_v4.py --loop    # 継続実行（Ctrl+Cで停止）
"""

import os
import sys
import time
import random
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import tweepy

# ===== 設定 =====
KEYWORDS = ["FX", "為替", "ドル円", "株式", "日経平均", "投資", "経済", "マーケット"]
MAX_LIKES_PER_CYCLE = 5  # 15分あたり5回
WAIT_BETWEEN_LIKES = 180  # 3分（15分÷5回）
WAIT_AFTER_RATE_LIMIT = 900  # 15分

# ===== カラー出力 =====
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def log_info(msg):
    print(f"{Colors.BLUE}[INFO]{Colors.RESET} {msg}")

def log_success(msg):
    print(f"{Colors.GREEN}[SUCCESS]{Colors.RESET} {msg}")

def log_warning(msg):
    print(f"{Colors.YELLOW}[WARNING]{Colors.RESET} {msg}")

def log_error(msg):
    print(f"{Colors.RED}[ERROR]{Colors.RESET} {msg}")

def log_phase(msg):
    print(f"\n{Colors.CYAN}{Colors.BOLD}{msg}{Colors.RESET}")

# ===== バナー =====
BANNER = f"""
{Colors.CYAN}╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   ██████╗ ██████╗  ██████╗ ███╗   ███╗███████╗████████╗  ║
║   ██╔══██╗██╔══██╗██╔═══██╗████╗ ████║██╔════╝╚══██╔══╝  ║
║   ██████╔╝██████╔╝██║   ██║██╔████╔██║█████╗     ██║     ║
║   ██╔═══╝ ██╔══██╗██║   ██║██║╚██╔╝██║██╔══╝     ██║     ║
║   ██║     ██║  ██║╚██████╔╝██║ ╚═╝ ██║███████╗   ██║     ║
║   ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝   ╚═╝     ║
║                                                           ║
║   自動いいね v4.0 - Basicプラン完全対応版                 ║
║   15分5回制限に最適化                                     ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝{Colors.RESET}
"""

class AutoLikeEngine:
    """自動いいねエンジン v4.0"""
    
    def __init__(self):
        # API認証情報を取得
        api_key = os.getenv("X_API_KEY")
        api_secret = os.getenv("X_API_SECRET")
        access_token = os.getenv("X_ACCESS_TOKEN")
        access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")
        
        if not all([api_key, api_secret, access_token, access_token_secret]):
            log_error("API認証情報が設定されていません")
            log_error(".envファイルを確認してください")
            sys.exit(1)
        
        # Tweepyクライアント初期化
        self.client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret,
            wait_on_rate_limit=False
        )
        
        # 状態管理
        self.liked_ids = set()
        self.rate_limit_reset = None
        self.likes_today = 0
        
        log_info("APIクライアント初期化完了")
    
    def verify_credentials(self):
        """認証確認"""
        try:
            me = self.client.get_me()
            if me.data:
                log_success(f"認証成功: @{me.data.username}")
                return True
        except Exception as e:
            log_error(f"認証エラー: {e}")
        return False
    
    def get_timeline(self, max_results=100):
        """タイムライン取得"""
        try:
            response = self.client.get_home_timeline(
                max_results=max_results,
                tweet_fields=["created_at", "public_metrics"],
                expansions=["author_id"],
                user_fields=["username"]
            )
            
            if not response.data:
                return []
            
            # ユーザー情報をマッピング
            users = {}
            if response.includes and "users" in response.includes:
                for user in response.includes["users"]:
                    users[user.id] = user.username
            
            tweets = []
            for tweet in response.data:
                tweets.append({
                    "id": str(tweet.id),
                    "text": tweet.text,
                    "author_id": str(tweet.author_id),
                    "author_username": users.get(tweet.author_id, "unknown"),
                    "like_count": tweet.public_metrics.get("like_count", 0) if tweet.public_metrics else 0,
                    "is_retweet": tweet.text.startswith("RT @")
                })
            
            return tweets
            
        except tweepy.TooManyRequests:
            log_warning("タイムライン取得: レート制限")
            return []
        except Exception as e:
            log_error(f"タイムライン取得エラー: {e}")
            return []
    
    def score_tweet(self, tweet):
        """ツイートスコアリング"""
        # RTは除外
        if tweet["is_retweet"]:
            return 0
        
        # 既にいいね済みは除外
        if tweet["id"] in self.liked_ids:
            return 0
        
        score = 0
        text_lower = tweet["text"].lower()
        
        # キーワードマッチ
        for keyword in KEYWORDS:
            if keyword.lower() in text_lower:
                score += 10
        
        # エンゲージメント
        if tweet["like_count"] > 100:
            score += 5
        elif tweet["like_count"] > 10:
            score += 2
        
        return score
    
    def like_tweet(self, tweet_id):
        """いいね実行"""
        # レート制限チェック
        if self.rate_limit_reset:
            now = int(time.time())
            if now < self.rate_limit_reset:
                wait = self.rate_limit_reset - now + 5
                return False, {"rate_limit": True, "wait_seconds": wait}
            else:
                self.rate_limit_reset = None
        
        try:
            self.client.like(tweet_id)
            self.liked_ids.add(tweet_id)
            self.likes_today += 1
            return True, None
            
        except tweepy.TooManyRequests as e:
            # レート制限エラー
            wait_seconds = WAIT_AFTER_RATE_LIMIT
            
            if hasattr(e, 'response') and e.response is not None:
                headers = e.response.headers
                reset_time = headers.get('x-rate-limit-reset')
                remaining = headers.get('x-rate-limit-remaining', '0')
                limit = headers.get('x-rate-limit-limit', '5')
                
                if reset_time:
                    self.rate_limit_reset = int(reset_time)
                    wait_seconds = int(reset_time) - int(time.time()) + 5
                    reset_dt = datetime.fromtimestamp(int(reset_time))
                    log_warning(f"レート制限 (429): {remaining}/{limit}")
                    log_warning(f"リセット時刻: {reset_dt.strftime('%H:%M:%S')} (あと{wait_seconds}秒)")
                else:
                    self.rate_limit_reset = int(time.time()) + WAIT_AFTER_RATE_LIMIT
                    log_warning(f"レート制限 (429): リセット時刻不明、{WAIT_AFTER_RATE_LIMIT}秒待機")
            else:
                self.rate_limit_reset = int(time.time()) + WAIT_AFTER_RATE_LIMIT
                log_warning(f"レート制限 (429): 詳細不明、{WAIT_AFTER_RATE_LIMIT}秒待機")
            
            return False, {"rate_limit": True, "wait_seconds": wait_seconds}
            
        except tweepy.Forbidden as e:
            error_str = str(e).lower()
            if "already liked" in error_str:
                self.liked_ids.add(tweet_id)
                return True, None  # 既にいいね済みは成功扱い
            log_warning(f"いいね禁止: {e}")
            return False, {"forbidden": True}
            
        except Exception as e:
            log_error(f"いいねエラー: {e}")
            return False, {"error": str(e)}
    
    def run_cycle(self):
        """1サイクル実行"""
        log_phase("=" * 50)
        log_phase("自動いいねサイクル開始")
        log_phase("=" * 50)
        
        result = {
            "success": 0,
            "failed": 0,
            "rate_limited": False,
            "wait_seconds": 0
        }
        
        # レート制限チェック
        if self.rate_limit_reset:
            now = int(time.time())
            if now < self.rate_limit_reset:
                wait = self.rate_limit_reset - now + 5
                log_warning(f"レート制限中: あと{wait}秒待機が必要")
                result["rate_limited"] = True
                result["wait_seconds"] = wait
                return result
        
        # タイムライン取得
        log_info("タイムライン取得中...")
        tweets = self.get_timeline(max_results=100)
        
        if not tweets:
            log_warning("タイムラインが空です")
            return result
        
        log_info(f"取得: {len(tweets)}件")
        
        # スコアリング
        scored = []
        for tweet in tweets:
            score = self.score_tweet(tweet)
            if score > 0:
                scored.append((tweet, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        log_info(f"スコアリング対象: {len(scored)}件")
        
        if not scored:
            log_info("いいね対象のツイートがありません")
            return result
        
        # いいね実行
        max_likes = min(MAX_LIKES_PER_CYCLE, len(scored))
        log_info(f"いいね実行: 最大{max_likes}件")
        
        for i, (tweet, score) in enumerate(scored[:max_likes]):
            author = tweet["author_username"]
            text_preview = tweet["text"][:40].replace("\n", " ")
            
            log_info(f"[{i+1}/{max_likes}] @{author}: {text_preview}...")
            
            success, error_info = self.like_tweet(tweet["id"])
            
            if success:
                result["success"] += 1
                log_success(f"✅ いいね成功 (本日: {self.likes_today}件)")
                
                # 次のいいねまで待機
                if i < max_likes - 1:
                    wait = random.randint(WAIT_BETWEEN_LIKES, WAIT_BETWEEN_LIKES + 20)
                    log_info(f"次のいいねまで {wait}秒 待機...")
                    time.sleep(wait)
            else:
                result["failed"] += 1
                
                if error_info and error_info.get("rate_limit"):
                    result["rate_limited"] = True
                    result["wait_seconds"] = error_info.get("wait_seconds", WAIT_AFTER_RATE_LIMIT)
                    break
        
        log_phase(f"サイクル完了: {result['success']}/{max_likes}件成功")
        return result


def main():
    parser = argparse.ArgumentParser(description="自動いいね v4.0")
    parser.add_argument("--loop", action="store_true", help="継続実行モード")
    args = parser.parse_args()
    
    print(BANNER)
    
    # エンジン初期化
    engine = AutoLikeEngine()
    
    # 認証確認
    if not engine.verify_credentials():
        sys.exit(1)
    
    print()
    log_info(f"キーワード: {', '.join(KEYWORDS)}")
    log_info(f"15分あたり最大: {MAX_LIKES_PER_CYCLE}件")
    log_info(f"いいね間隔: {WAIT_BETWEEN_LIKES}秒")
    
    if args.loop:
        log_info("継続モードで実行します（Ctrl+C で停止）")
        
        cycle = 1
        try:
            while True:
                print()
                log_phase(f"===== サイクル {cycle} =====")
                
                result = engine.run_cycle()
                
                if result["rate_limited"]:
                    wait = result["wait_seconds"]
                    log_warning(f"レート制限: {wait}秒待機します...")
                    time.sleep(wait)
                else:
                    # 次のサイクルまで待機
                    log_info("次のサイクルまで15分待機...")
                    time.sleep(WAIT_AFTER_RATE_LIMIT)
                
                cycle += 1
                
        except KeyboardInterrupt:
            print()
            log_info("停止しました")
            log_info(f"本日のいいね合計: {engine.likes_today}件")
    else:
        # 1回実行
        result = engine.run_cycle()
        
        print()
        log_phase("【実行結果】")
        print(f"成功: {result['success']}件")
        print(f"失敗: {result['failed']}件")
        print(f"本日合計: {engine.likes_today}件")
        
        if result["rate_limited"]:
            wait = result["wait_seconds"]
            log_warning(f"レート制限中: 次回実行は{wait}秒後")


if __name__ == "__main__":
    main()
