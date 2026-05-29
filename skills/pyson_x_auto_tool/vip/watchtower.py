"""
The Watchtower - VIPリスト監視エンジン
=====================================
VIPリストのタイムラインを監視し、戦略的にいいねを実行
"""

import time
import random
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Optional, Dict, Set

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import get_config, get_logger, get_x_client
from .list_manager import ListManager, VIPMember, VIPTier

logger = get_logger("vip.watchtower")


@dataclass
class VIPTweet:
    """VIPのツイート"""
    tweet_id: str
    user_id: str
    username: str
    display_name: str
    content: str
    tier: str
    created_at: str
    like_count: int = 0
    retweet_count: int = 0
    reply_count: int = 0
    priority_score: float = 0.0


class Watchtower:
    """VIPリスト監視エンジン"""
    
    # 階層別の優先度重み
    TIER_WEIGHTS = {
        "titans": 3.0,
        "influencers": 2.0,
        "practitioners": 1.5,
        "media": 1.0
    }
    
    # 1日のVIPいいね上限
    DAILY_VIP_LIKE_LIMIT = 100
    
    # 同一ユーザーへの最小間隔（時間）
    MIN_HOURS_BETWEEN_SAME_USER = 12
    
    def __init__(self):
        self.config = get_config()
        self.x_client = get_x_client()
        self.list_manager = ListManager()
        
        # エンゲージメント履歴
        self.engaged_tweets: Set[str] = set()
        self.user_last_engaged: Dict[str, datetime] = {}
        self.today_vip_likes = 0
        self.last_reset_date = datetime.now().date()
    
    def _reset_daily_counters(self):
        """日次カウンターをリセット"""
        today = datetime.now().date()
        if today > self.last_reset_date:
            self.today_vip_likes = 0
            self.last_reset_date = today
            logger.info("日次カウンターをリセットしました")
    
    def _can_engage_user(self, user_id: str) -> bool:
        """ユーザーにエンゲージ可能か確認"""
        if user_id not in self.user_last_engaged:
            return True
        
        last_engaged = self.user_last_engaged[user_id]
        hours_since = (datetime.now() - last_engaged).total_seconds() / 3600
        
        return hours_since >= self.MIN_HOURS_BETWEEN_SAME_USER
    
    def _calculate_priority(self, tweet: dict, member: VIPMember) -> float:
        """ツイートの優先度スコアを計算"""
        score = 0.0
        
        # 階層による重み
        tier_weight = self.TIER_WEIGHTS.get(member.tier, 1.0)
        score += tier_weight * 10
        
        # 新鮮さ（24時間以内のツイートを優先）
        created_at = tweet.get("created_at", "")
        if created_at:
            try:
                tweet_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                hours_old = (datetime.now(tweet_time.tzinfo) - tweet_time).total_seconds() / 3600
                if hours_old < 1:
                    score += 20  # 1時間以内
                elif hours_old < 6:
                    score += 15  # 6時間以内
                elif hours_old < 24:
                    score += 10  # 24時間以内
            except:
                pass
        
        # エンゲージメント数による調整
        metrics = tweet.get("public_metrics", {})
        like_count = metrics.get("like_count", 0)
        retweet_count = metrics.get("retweet_count", 0)
        
        # 適度なエンゲージメントがあるツイートを優先
        if 10 <= like_count <= 1000:
            score += 5
        if 5 <= retweet_count <= 500:
            score += 3
        
        # フォロワー数による調整（影響力）
        if member.followers_count > 100000:
            score += 5
        elif member.followers_count > 10000:
            score += 3
        
        # 過去のエンゲージメント頻度による調整
        if member.engagement_count > 10:
            score += 2  # 関係構築中
        
        return score
    
    def fetch_vip_timeline(self, tier: Optional[str] = None, limit: int = 50) -> List[VIPTweet]:
        """VIPのタイムラインを取得"""
        self._reset_daily_counters()
        
        vip_tweets = []
        
        # 対象メンバーを取得
        if tier:
            members = self.list_manager.get_members_by_tier(tier)
        else:
            members = self.list_manager.get_all_vip_members()
        
        if not members:
            logger.warning("VIPメンバーが登録されていません")
            return []
        
        logger.info(f"VIPメンバー {len(members)}名のタイムラインを取得中...")
        
        # 各メンバーの最新ツイートを取得
        for member in members:
            if not self._can_engage_user(member.user_id):
                continue
            
            try:
                tweets = self.x_client.get_user_tweets(
                    user_id=member.user_id,
                    max_results=5  # 各ユーザーから最新5件
                )
                
                for tweet in tweets:
                    if tweet["id"] in self.engaged_tweets:
                        continue
                    
                    priority = self._calculate_priority(tweet, member)
                    
                    vip_tweet = VIPTweet(
                        tweet_id=tweet["id"],
                        user_id=member.user_id,
                        username=member.username,
                        display_name=member.display_name,
                        content=tweet.get("text", ""),
                        tier=member.tier,
                        created_at=tweet.get("created_at", ""),
                        like_count=tweet.get("public_metrics", {}).get("like_count", 0),
                        retweet_count=tweet.get("public_metrics", {}).get("retweet_count", 0),
                        reply_count=tweet.get("public_metrics", {}).get("reply_count", 0),
                        priority_score=priority
                    )
                    vip_tweets.append(vip_tweet)
                
                # レート制限対策
                time.sleep(0.5)
                
            except Exception as e:
                logger.warning(f"@{member.username} のツイート取得エラー: {e}")
                continue
        
        # 優先度でソート
        vip_tweets.sort(key=lambda x: x.priority_score, reverse=True)
        
        logger.info(f"VIPツイート {len(vip_tweets)}件を取得（上位{limit}件を処理）")
        
        return vip_tweets[:limit]
    
    def run_vip_engagement(self, max_likes: int = 20, tier: Optional[str] = None) -> dict:
        """VIPエンゲージメントサイクルを実行"""
        logger.phase("Watchtower - VIPエンゲージメントサイクル開始")
        
        results = {
            "tweets_fetched": 0,
            "likes_attempted": 0,
            "likes_success": 0,
            "likes_failed": 0,
            "rate_limited": False,
            "engaged_users": []
        }
        
        # 日次上限チェック
        if self.today_vip_likes >= self.DAILY_VIP_LIKE_LIMIT:
            logger.warning("本日のVIPいいね上限に達しています")
            results["rate_limited"] = True
            return results
        
        # 残り可能ないいね数
        remaining = min(max_likes, self.DAILY_VIP_LIKE_LIMIT - self.today_vip_likes)
        
        # VIPタイムラインを取得
        vip_tweets = self.fetch_vip_timeline(tier=tier, limit=remaining * 2)
        results["tweets_fetched"] = len(vip_tweets)
        
        if not vip_tweets:
            logger.info("対象ツイートがありません")
            return results
        
        # いいね実行
        likes_done = 0
        for tweet in vip_tweets:
            if likes_done >= remaining:
                break
            
            # 同一ユーザーチェック
            if not self._can_engage_user(tweet.user_id):
                continue
            
            try:
                # いいね実行
                success = self.x_client.like_tweet(tweet.tweet_id)
                results["likes_attempted"] += 1
                
                if success:
                    results["likes_success"] += 1
                    likes_done += 1
                    self.today_vip_likes += 1
                    
                    # 記録更新
                    self.engaged_tweets.add(tweet.tweet_id)
                    self.user_last_engaged[tweet.user_id] = datetime.now()
                    self.list_manager.update_engagement(tweet.user_id)
                    
                    results["engaged_users"].append({
                        "username": tweet.username,
                        "tier": tweet.tier,
                        "tweet_preview": tweet.content[:50] + "..."
                    })
                    
                    logger.info(f"✓ @{tweet.username} ({tweet.tier}): {tweet.content[:40]}...")
                    
                    # 自然な間隔を空ける
                    delay = random.uniform(15, 30)
                    logger.info(f"  次のいいねまで {delay:.1f}秒 待機...")
                    time.sleep(delay)
                else:
                    results["likes_failed"] += 1
                    
            except Exception as e:
                error_msg = str(e)
                if "rate" in error_msg.lower() or "limit" in error_msg.lower():
                    logger.warning("レート制限に達しました")
                    results["rate_limited"] = True
                    break
                else:
                    logger.warning(f"いいねエラー: {e}")
                    results["likes_failed"] += 1
        
        logger.info(f"サイクル完了: {results['likes_success']}/{results['likes_attempted']}件成功")
        
        return results
    
    def run_continuous(self, interval_minutes: int = 30, tier: Optional[str] = None):
        """継続モードで実行"""
        logger.info(f"継続モードで実行します（{interval_minutes}分間隔、Ctrl+C で停止）")
        
        cycle = 1
        try:
            while True:
                print(f"\n{'='*60}")
                print(f"【VIPエンゲージメント サイクル {cycle}】")
                print(f"{'='*60}")
                
                results = self.run_vip_engagement(max_likes=10, tier=tier)
                
                # 結果表示
                print(f"\n取得ツイート: {results['tweets_fetched']}件")
                print(f"いいね成功: {results['likes_success']}/{results['likes_attempted']}件")
                print(f"本日累計: {self.today_vip_likes}/{self.DAILY_VIP_LIKE_LIMIT}件")
                
                if results["engaged_users"]:
                    print("\n【エンゲージしたVIP】")
                    for user in results["engaged_users"]:
                        print(f"  @{user['username']} ({user['tier']})")
                
                if results["rate_limited"]:
                    logger.warning("レート制限のため30分待機します...")
                    time.sleep(1800)
                else:
                    logger.info(f"次のサイクルまで{interval_minutes}分待機...")
                    time.sleep(interval_minutes * 60)
                
                cycle += 1
                
        except KeyboardInterrupt:
            logger.info("\n停止しました")
    
    def get_stats(self) -> dict:
        """統計情報を取得"""
        self._reset_daily_counters()
        
        summary = self.list_manager.get_lists_summary()
        
        return {
            "total_lists": summary["total_lists"],
            "total_vip_members": summary["total_members"],
            "by_tier": summary["by_tier"],
            "today_vip_likes": self.today_vip_likes,
            "today_remaining": self.DAILY_VIP_LIKE_LIMIT - self.today_vip_likes,
            "engaged_tweets_count": len(self.engaged_tweets)
        }
