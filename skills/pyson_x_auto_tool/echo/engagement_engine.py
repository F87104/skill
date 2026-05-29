"""
Project Prometheus - Echo Engagement Engine v4.0
================================================
Basicプラン完全対応版 - 15分5回制限に最適化
"""

import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import random

from ..core.x_client import XClient, Tweet, get_x_client
from ..core.config import get_config
from ..core.logger import get_logger

logger = get_logger("echo.engine")


class EngagementEngine:
    """
    エンゲージメントエンジン v4.0
    
    X API Basicプランの厳しい制限に完全対応:
    - 15分あたり5回のいいね制限
    - 429エラー時は自動でリセット時刻まで待機
    - 無駄なAPIコールを完全に排除
    """
    
    def __init__(self, keywords: List[str]):
        self.client = get_x_client()
        self.config = get_config().echo
        self.keywords = keywords
        
        # 統計
        self.likes_today = 0
        self.likes_this_cycle = 0
        self.last_reset_date = datetime.now().date()
        
        # いいね済みツイートID（重複防止）
        self.liked_tweet_ids: set = set()
        
        logger.info(f"キーワード設定: {keywords}")
    
    def _reset_daily_counter(self):
        """日付が変わったらカウンターをリセット"""
        today = datetime.now().date()
        if today != self.last_reset_date:
            logger.info(f"日付変更: カウンターリセット ({self.likes_today}件 → 0件)")
            self.likes_today = 0
            self.last_reset_date = today
    
    def _score_tweet(self, tweet: Tweet) -> int:
        """ツイートのスコアを計算"""
        score = 0
        
        # RTとリプライは除外
        if tweet.is_retweet or tweet.is_reply:
            return 0
        
        # 既にいいね済みは除外
        if tweet.id in self.liked_tweet_ids:
            return 0
        
        text_lower = tweet.text.lower()
        
        # キーワードマッチ
        for keyword in self.keywords:
            if keyword.lower() in text_lower:
                score += 10
        
        # エンゲージメント指標
        if tweet.like_count > 100:
            score += 5
        elif tweet.like_count > 10:
            score += 2
        
        if tweet.retweet_count > 50:
            score += 5
        elif tweet.retweet_count > 5:
            score += 2
        
        # メディア付きはボーナス
        if tweet.has_media:
            score += 3
        
        return score
    
    def run_cycle(self) -> Dict:
        """
        1サイクル実行（v4.0 完全再設計版）
        
        Returns:
            Dict: サイクル結果
        """
        logger.info("=" * 50)
        logger.info("[PHASE] Echo - エンゲージメントサイクル開始")
        logger.info("=" * 50)
        
        self._reset_daily_counter()
        self.likes_this_cycle = 0
        
        result = {
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "rate_limited": False,
            "wait_seconds": 0
        }
        
        # Step 1: まずレート制限状態をチェック
        if self.client.is_rate_limited():
            status = self.client.get_rate_limit_status()
            wait_seconds = status.get("wait_seconds", 900)
            logger.warning(f"⏳ レート制限中: あと{wait_seconds}秒待機が必要")
            result["rate_limited"] = True
            result["wait_seconds"] = wait_seconds
            return result
        
        # Step 2: タイムライン取得
        tweets = self.client.get_home_timeline(max_results=100)
        if not tweets:
            logger.warning("タイムラインが空です")
            return result
        
        # Step 3: スコアリング
        scored_tweets: List[Tuple[Tweet, int]] = []
        for tweet in tweets:
            score = self._score_tweet(tweet)
            if score > 0:
                scored_tweets.append((tweet, score))
        
        # スコア順にソート
        scored_tweets.sort(key=lambda x: x[1], reverse=True)
        logger.info(f"スコアリング完了: {len(scored_tweets)}件が対象")
        
        if not scored_tweets:
            logger.info("いいね対象のツイートがありません")
            return result
        
        # Step 4: いいね実行（最大5件、1件ずつ慎重に）
        max_likes = min(5, len(scored_tweets))  # Basicプランは15分5回
        
        for i, (tweet, score) in enumerate(scored_tweets[:max_likes]):
            # 各いいね前にレート制限チェック
            if self.client.is_rate_limited():
                status = self.client.get_rate_limit_status()
                wait_seconds = status.get("wait_seconds", 900)
                logger.warning(f"⏳ レート制限検出: あと{wait_seconds}秒待機が必要")
                result["rate_limited"] = True
                result["wait_seconds"] = wait_seconds
                break
            
            # いいね実行
            author = tweet.author_username or tweet.author_id
            logger.info(f"[{i+1}/{max_likes}] @{author}: {tweet.text[:50]}...")
            
            success, error_info = self.client.like_tweet(tweet.id)
            
            if success:
                result["success"] += 1
                self.likes_today += 1
                self.likes_this_cycle += 1
                self.liked_tweet_ids.add(tweet.id)
                
                # 成功後は3分待機（15分で5回 = 3分間隔）
                if i < max_likes - 1:  # 最後の1件は待機不要
                    wait_time = random.randint(180, 200)  # 3分〜3分20秒
                    logger.info(f"   → 次のいいねまで {wait_time}秒 待機...")
                    time.sleep(wait_time)
            else:
                result["failed"] += 1
                
                if error_info and error_info.get("rate_limit"):
                    wait_seconds = error_info.get("wait_seconds", 900)
                    result["rate_limited"] = True
                    result["wait_seconds"] = wait_seconds
                    logger.warning(f"⏳ レート制限: {wait_seconds}秒後に再開可能")
                    break
                elif error_info and error_info.get("permission_error"):
                    logger.error("❌ 権限エラー: APIキーの設定を確認してください")
                    break
        
        logger.info(f"サイクル完了: {result['success']}/{max_likes}件成功")
        return result
    
    def get_status(self) -> Dict:
        """現在の状態を取得"""
        rate_status = self.client.get_rate_limit_status()
        
        return {
            "likes_today": self.likes_today,
            "likes_remaining_today": max(0, 80 - self.likes_today),
            "rate_limited": rate_status.get("rate_limited", False),
            "wait_seconds": rate_status.get("wait_seconds", 0),
            "reset_time": rate_status.get("reset_datetime"),
            "keywords": self.keywords
        }
