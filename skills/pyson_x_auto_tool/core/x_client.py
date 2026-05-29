"""
Project Prometheus - X API Client Module v4.0
=============================================
X (Twitter) API v2 クライアント
Basicプラン完全対応版 - いいね機能を根本から再設計
"""

import tweepy
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import time

from .config import get_config
from .logger import get_logger

logger = get_logger("x_client")

@dataclass
class Tweet:
    """ツイートデータクラス"""
    id: str
    text: str
    author_id: str
    author_username: Optional[str] = None
    created_at: Optional[datetime] = None
    like_count: int = 0
    retweet_count: int = 0
    reply_count: int = 0
    has_media: bool = False
    is_retweet: bool = False
    is_reply: bool = False
    
    @classmethod
    def from_tweepy(cls, tweet: tweepy.Tweet, includes: Optional[Dict] = None) -> "Tweet":
        """tweepyのTweetオブジェクトから変換"""
        author_username = None
        if includes and "users" in includes:
            for user in includes["users"]:
                if user.id == tweet.author_id:
                    author_username = user.username
                    break
        
        has_media = False
        if hasattr(tweet, "attachments") and tweet.attachments:
            has_media = "media_keys" in tweet.attachments
        
        is_retweet = tweet.text.startswith("RT @")
        
        is_reply = False
        if hasattr(tweet, "in_reply_to_user_id") and tweet.in_reply_to_user_id:
            is_reply = True
        
        like_count = 0
        retweet_count = 0
        reply_count = 0
        if hasattr(tweet, "public_metrics") and tweet.public_metrics:
            like_count = tweet.public_metrics.get("like_count", 0)
            retweet_count = tweet.public_metrics.get("retweet_count", 0)
            reply_count = tweet.public_metrics.get("reply_count", 0)
        
        return cls(
            id=str(tweet.id),
            text=tweet.text,
            author_id=str(tweet.author_id),
            author_username=author_username,
            created_at=tweet.created_at if hasattr(tweet, "created_at") else None,
            like_count=like_count,
            retweet_count=retweet_count,
            reply_count=reply_count,
            has_media=has_media,
            is_retweet=is_retweet,
            is_reply=is_reply
        )


class XClient:
    """
    X API v2 クライアント v4.0
    
    Basicプランの厳しい制限に完全対応:
    - いいね: 15分あたり5回
    - 429エラー時は即座に停止し、リセット時刻まで待機
    """
    
    def __init__(self):
        config = get_config()
        
        if not all([config.x_api_key, config.x_api_secret, 
                    config.x_access_token, config.x_access_token_secret]):
            raise ValueError("X API認証情報が設定されていません")
        
        self.client = tweepy.Client(
            consumer_key=config.x_api_key,
            consumer_secret=config.x_api_secret,
            access_token=config.x_access_token,
            access_token_secret=config.x_access_token_secret,
            wait_on_rate_limit=False  # 自分で制御
        )
        
        self._me: Optional[tweepy.User] = None
        
        # レート制限追跡（v4.0 新設計）
        self._rate_limit_reset: Optional[int] = None  # UNIXタイムスタンプ
        self._rate_limit_remaining: int = 5  # 残り回数
        self._last_like_time: Optional[datetime] = None
    
    def verify_credentials(self) -> Dict[str, Any]:
        """認証情報の検証"""
        try:
            me = self.client.get_me(user_fields=["public_metrics"])
            if me.data:
                self._me = me.data
                return {
                    "success": True,
                    "user_id": str(me.data.id),
                    "username": me.data.username,
                    "name": me.data.name
                }
            return {"success": False, "error": "ユーザー情報を取得できません"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @property
    def me(self) -> Optional[tweepy.User]:
        """認証ユーザー情報"""
        if self._me is None:
            self.verify_credentials()
        return self._me
    
    def get_me(self):
        """認証ユーザー情報を取得"""
        try:
            response = self.client.get_me()
            if response.data:
                return response.data
            return None
        except Exception as e:
            logger.error(f"ユーザー情報取得エラー: {e}")
            return None
    
    def get_home_timeline(self, max_results: int = 100) -> List[Tweet]:
        """ホームタイムラインを取得"""
        try:
            response = self.client.get_home_timeline(
                max_results=min(max_results, 100),
                tweet_fields=["created_at", "public_metrics", "attachments", "in_reply_to_user_id"],
                expansions=["author_id", "attachments.media_keys"],
                user_fields=["username"]
            )
            
            if not response.data:
                return []
            
            includes = {}
            if response.includes:
                includes = response.includes
            
            tweets = [Tweet.from_tweepy(t, includes) for t in response.data]
            logger.info(f"タイムラインから{len(tweets)}件取得")
            return tweets
            
        except tweepy.TooManyRequests:
            logger.warning("タイムライン取得: レート制限")
            return []
        except Exception as e:
            logger.error(f"タイムライン取得エラー: {e}")
            return []
    
    def _check_rate_limit_wait(self) -> Tuple[bool, int]:
        """
        レート制限の待機が必要かチェック
        
        Returns:
            Tuple[bool, int]: (待機必要か, 待機秒数)
        """
        if self._rate_limit_reset:
            now = int(time.time())
            if now < self._rate_limit_reset:
                wait_seconds = self._rate_limit_reset - now + 5  # 5秒余裕
                return True, wait_seconds
            else:
                # リセット時刻を過ぎた
                self._rate_limit_reset = None
                self._rate_limit_remaining = 5
        
        return False, 0
    
    def _update_rate_limit_from_response(self, response):
        """レスポンスヘッダーからレート制限情報を更新"""
        if hasattr(response, 'headers'):
            headers = response.headers
            
            reset = headers.get('x-rate-limit-reset')
            remaining = headers.get('x-rate-limit-remaining')
            limit = headers.get('x-rate-limit-limit')
            
            if reset:
                self._rate_limit_reset = int(reset)
            if remaining:
                self._rate_limit_remaining = int(remaining)
            
            logger.debug(f"Rate Limit更新: {remaining}/{limit}, Reset: {reset}")
    
    def like_tweet(self, tweet_id: str) -> Tuple[bool, Optional[Dict]]:
        """
        ツイートにいいねする（v4.0 完全再設計版）
        
        Returns:
            Tuple[bool, Optional[Dict]]: (成功したか, エラー情報)
            エラー情報: {"rate_limit": True, "reset_time": int, "remaining": int}
        """
        # まず待機が必要かチェック
        need_wait, wait_seconds = self._check_rate_limit_wait()
        if need_wait:
            logger.warning(f"レート制限中: あと{wait_seconds}秒待機が必要")
            return False, {
                "rate_limit": True,
                "reset_time": self._rate_limit_reset,
                "remaining": 0,
                "wait_seconds": wait_seconds
            }
        
        try:
            response = self.client.like(tweet_id)
            
            # 成功
            self._last_like_time = datetime.now()
            self._rate_limit_remaining = max(0, self._rate_limit_remaining - 1)
            
            logger.info(f"✅ いいね成功: {tweet_id} (残り: {self._rate_limit_remaining}回)")
            return True, None
            
        except tweepy.TooManyRequests as e:
            # レート制限エラー
            error_info = {
                "rate_limit": True,
                "reset_time": None,
                "remaining": 0
            }
            
            if hasattr(e, 'response') and e.response is not None:
                headers = e.response.headers
                
                reset_time = headers.get('x-rate-limit-reset')
                remaining = headers.get('x-rate-limit-remaining', '0')
                limit = headers.get('x-rate-limit-limit', '5')
                
                if reset_time:
                    self._rate_limit_reset = int(reset_time)
                    error_info["reset_time"] = int(reset_time)
                    
                    # リセットまでの秒数を計算
                    wait_seconds = int(reset_time) - int(time.time())
                    error_info["wait_seconds"] = max(0, wait_seconds) + 5
                    
                    reset_dt = datetime.fromtimestamp(int(reset_time))
                    logger.warning(f"❌ レート制限 (429)")
                    logger.warning(f"   残り: {remaining}/{limit}")
                    logger.warning(f"   リセット: {reset_dt.strftime('%H:%M:%S')} (あと{wait_seconds}秒)")
                else:
                    # リセット時刻不明の場合は15分待機
                    error_info["wait_seconds"] = 900
                    self._rate_limit_reset = int(time.time()) + 900
                    logger.warning(f"❌ レート制限 (429) - リセット時刻不明、15分待機")
                
                error_info["remaining"] = int(remaining)
            else:
                # ヘッダーが取得できない場合
                error_info["wait_seconds"] = 900
                self._rate_limit_reset = int(time.time()) + 900
                logger.warning(f"❌ レート制限 (429) - 詳細不明、15分待機")
            
            return False, error_info
            
        except tweepy.Forbidden as e:
            error_str = str(e).lower()
            if "already liked" in error_str:
                logger.debug(f"既にいいね済み: {tweet_id}")
                return True, None  # 成功扱い
            elif "not allowed" in error_str or "not permitted" in error_str:
                logger.error(f"❌ 権限エラー: APIキーの権限を確認してください")
                return False, {"permission_error": True}
            else:
                logger.warning(f"❌ いいね禁止: {e}")
                return False, {"forbidden": True}
                
        except tweepy.Unauthorized as e:
            logger.error(f"❌ 認証エラー: {e}")
            return False, {"auth_error": True}
            
        except Exception as e:
            logger.error(f"❌ 予期せぬエラー: {type(e).__name__}: {e}")
            return False, {"unknown_error": str(e)}
    
    def get_rate_limit_status(self) -> Dict:
        """現在のレート制限状態を取得"""
        need_wait, wait_seconds = self._check_rate_limit_wait()
        
        return {
            "rate_limited": need_wait,
            "wait_seconds": wait_seconds,
            "remaining": self._rate_limit_remaining,
            "reset_time": self._rate_limit_reset,
            "reset_datetime": datetime.fromtimestamp(self._rate_limit_reset).isoformat() if self._rate_limit_reset else None
        }
    
    def is_rate_limited(self) -> bool:
        """レート制限中かどうか"""
        need_wait, _ = self._check_rate_limit_wait()
        return need_wait
    
    def post_tweet(self, text: str, reply_to: Optional[str] = None) -> Optional[str]:
        """ツイートを投稿"""
        try:
            params = {"text": text}
            if reply_to:
                params["in_reply_to_tweet_id"] = reply_to
            
            response = self.client.create_tweet(**params)
            
            if response.data:
                tweet_id = str(response.data["id"])
                logger.info(f"✅ ツイート投稿成功: {tweet_id}")
                return tweet_id
            return None
            
        except tweepy.TooManyRequests:
            logger.warning("投稿レート制限")
            return None
        except Exception as e:
            logger.error(f"投稿エラー: {e}")
            return None
    
    # ===== VIP機能用メソッド =====
    
    def get_owned_lists(self) -> List[Dict]:
        """自分が所有するリスト一覧を取得"""
        try:
            me = self.me
            if not me:
                return []
            
            response = self.client.get_owned_lists(
                id=me.id,
                list_fields=["member_count", "description", "created_at"]
            )
            
            if not response.data:
                return []
            
            lists = []
            for lst in response.data:
                lists.append({
                    "id": str(lst.id),
                    "name": lst.name,
                    "description": getattr(lst, "description", ""),
                    "member_count": getattr(lst, "member_count", 0)
                })
            
            return lists
            
        except Exception as e:
            logger.error(f"リスト取得エラー: {e}")
            return []
    
    def get_list(self, list_id: str) -> Optional[Dict]:
        """リスト情報を取得"""
        try:
            response = self.client.get_list(
                id=list_id,
                list_fields=["member_count", "description", "created_at"]
            )
            
            if not response.data:
                return None
            
            lst = response.data
            return {
                "id": str(lst.id),
                "name": lst.name,
                "description": getattr(lst, "description", ""),
                "member_count": getattr(lst, "member_count", 0)
            }
            
        except Exception as e:
            logger.error(f"リスト情報取得エラー: {e}")
            return None
    
    def get_list_members(self, list_id: str, max_results: int = 100) -> List[Dict]:
        """リストのメンバーを取得"""
        try:
            response = self.client.get_list_members(
                id=list_id,
                max_results=min(max_results, 100),
                user_fields=["username", "name", "public_metrics", "description"]
            )
            
            if not response.data:
                return []
            
            members = []
            for user in response.data:
                members.append({
                    "id": str(user.id),
                    "username": user.username,
                    "name": user.name,
                    "description": getattr(user, "description", ""),
                    "followers_count": user.public_metrics.get("followers_count", 0) if hasattr(user, "public_metrics") and user.public_metrics else 0
                })
            
            return members
            
        except Exception as e:
            logger.error(f"リストメンバー取得エラー: {e}")
            return []
    
    def get_user_tweets(self, user_id: str, max_results: int = 10) -> List[Tweet]:
        """特定ユーザーの最新ツイートを取得"""
        try:
            response = self.client.get_users_tweets(
                id=user_id,
                max_results=min(max_results, 100),
                tweet_fields=["created_at", "public_metrics"],
                exclude=["retweets", "replies"]
            )
            
            if not response.data:
                return []
            
            tweets = [Tweet.from_tweepy(t) for t in response.data]
            return tweets
            
        except Exception as e:
            logger.error(f"ユーザーツイート取得エラー: {e}")
            return []


# シングルトンインスタンス
_client: Optional[XClient] = None

def get_x_client() -> XClient:
    """XClientのシングルトンインスタンスを取得"""
    global _client
    if _client is None:
        _client = XClient()
    return _client
