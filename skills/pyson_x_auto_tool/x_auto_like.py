#!/usr/bin/env python3
import os
import sys
import json
import time
import random
import logging
from datetime import datetime, timedelta
from pathlib import Path

try:
    import tweepy
except ImportError:
    print("tweepyがインストールされていません。")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    print("python-dotenvがインストールされていません。")
    sys.exit(1)

log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"x_auto_like_{datetime.now().strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class OptimizedAutoLiker:
    def __init__(self):
        env_path = Path(__file__).parent / ".env"
        load_dotenv(env_path)
        self.api_key = os.getenv('X_API_KEY')
        self.api_secret = os.getenv('X_API_SECRET')
        self.access_token = os.getenv('X_ACCESS_TOKEN')
        self.access_token_secret = os.getenv('X_ACCESS_TOKEN_SECRET')
        if not all([self.api_key, self.api_secret, self.access_token, self.access_token_secret]):
            logger.error("APIキーが設定されていません。")
            sys.exit(1)
        self.config = {
            'max_likes_per_session': int(os.getenv('MAX_LIKES_PER_SESSION', 80)),
            'max_likes_per_day': int(os.getenv('MAX_LIKES_PER_DAY', 480)),
            'following_likes_per_run': int(os.getenv('FOLLOWING_LIKES_PER_RUN', 80)),
            'min_delay': int(os.getenv('MIN_DELAY', 15)),
            'max_delay': int(os.getenv('MAX_DELAY', 25)),
            'likes_per_15min': int(os.getenv('LIKES_PER_15MIN', 48)),
        }
        data_dir = Path(__file__).parent / "data"
        data_dir.mkdir(exist_ok=True)
        self.history_file = data_dir / "like_history.json"
        self.daily_count_file = data_dir / "daily_count.json"
        self.likeback_history_file = data_dir / "likeback_history.json"
        self.liked_tweets = self._load_json_set(self.history_file)
        self.daily_count = self._load_daily_count()
        self.likeback_history = self._load_json_set(self.likeback_history_file)
        self.like_timestamps = []
        self.client = None
        self.my_user_id = None
        self._init_client()
        self.session_count = 0

    def _load_json_set(self, file_path):
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return set(data)
            except:
                pass
        return set()

    def _save_json_set(self, file_path, data_set):
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(list(data_set), f, ensure_ascii=False)

    def _load_daily_count(self):
        today = datetime.now().strftime('%Y-%m-%d')
        if self.daily_count_file.exists():
            try:
                with open(self.daily_count_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get('date') == today:
                        return data
            except:
                pass
        return {'date': today, 'count': 0}

    def _save_daily_count(self):
        with open(self.daily_count_file, 'w', encoding='utf-8') as f:
            json.dump(self.daily_count, f, ensure_ascii=False)

    def _init_client(self):
        try:
            self.client = tweepy.Client(
                consumer_key=self.api_key,
                consumer_secret=self.api_secret,
                access_token=self.access_token,
                access_token_secret=self.access_token_secret,
                wait_on_rate_limit=False
            )
            me = self.client.get_me()
            if me.data:
                self.my_user_id = me.data.id
                logger.info(f"認証成功: @{me.data.username}")
            else:
                logger.error("認証に失敗しました。")
                sys.exit(1)
        except Exception as e:
            logger.error(f"API初期化エラー: {e}")
            sys.exit(1)

    def _check_like_rate_limit(self):
        now = datetime.now()
        cutoff = now - timedelta(minutes=15)
        self.like_timestamps = [ts for ts in self.like_timestamps if ts > cutoff]
        if len(self.like_timestamps) >= self.config['likes_per_15min']:
            oldest = min(self.like_timestamps)
            wait_until = oldest + timedelta(minutes=15)
            wait_seconds = (wait_until - now).total_seconds()
            if wait_seconds > 0:
                logger.info(f"レート制限管理: {wait_seconds:.0f}秒待機...")
                time.sleep(wait_seconds + 5)
                self.like_timestamps = []
        return True

    def _check_daily_limit(self):
        today = datetime.now().strftime('%Y-%m-%d')
        if self.daily_count['date'] != today:
            self.daily_count = {'date': today, 'count': 0}
        if self.daily_count['count'] >= self.config['max_likes_per_day']:
            logger.warning(f"本日のいいね上限に達しました。")
            return False
        return True

    def _check_session_limit(self):
        if self.session_count >= self.config['max_likes_per_session']:
            logger.info(f"セッション上限に達しました。")
            return False
        return True

    def _smart_delay(self):
        base_delay = random.uniform(self.config['min_delay'], self.config['max_delay'])
        if random.random() < 0.1:
            base_delay += random.uniform(20, 40)
        logger.info(f"次のいいねまで {base_delay:.0f}秒 待機...")
        time.sleep(base_delay)

    def like_tweet(self, tweet_id):
        tweet_id_str = str(tweet_id)
        if tweet_id_str in self.liked_tweets:
            return False
        if not self._check_daily_limit():
            return False
        if not self._check_session_limit():
            return False
        self._check_like_rate_limit()
        try:
            self.client.like(tweet_id)
            self.liked_tweets.add(tweet_id_str)
            self._save_json_set(self.history_file, self.liked_tweets)
            self.daily_count['count'] += 1
            self._save_daily_count()
            self.session_count += 1
            self.like_timestamps.append(datetime.now())
            logger.info(f"いいね成功: {tweet_id} (本日: {self.daily_count['count']}件)")
            return True
        except tweepy.TooManyRequests:
            logger.warning("APIレート制限。60秒待機...")
            time.sleep(60)
            return False
        except tweepy.Forbidden:
            self.liked_tweets.add(tweet_id_str)
            self._save_json_set(self.history_file, self.liked_tweets)
            return False
        except Exception as e:
            logger.error(f"いいねエラー: {e}")
            return False

    def get_timeline_tweets(self, count=100):
        logger.info("タイムライン取得中...")
        try:
            tweets = self.client.get_home_timeline(max_results=min(count, 100), exclude=['retweets', 'replies'])
            if tweets.data:
                logger.info(f"タイムラインから{len(tweets.data)}件取得")
                return [tweet.id for tweet in tweets.data]
            return []
        except tweepy.TooManyRequests:
            logger.warning("タイムライン取得レート制限。60秒待機...")
            time.sleep(60)
            return []
        except Exception as e:
            logger.error(f"タイムライン取得エラー: {e}")
            return []

    def get_following_tweets(self, max_users=30, tweets_per_user=3):
        logger.info("フォロー中のユーザーのツイート取得中...")
        tweet_ids = []
        try:
            following = self.client.get_users_following(self.my_user_id, max_results=min(max_users * 2, 1000))
            if not following.data:
                return []
            users = list(following.data)
            random.shuffle(users)
            for user in users[:max_users]:
                try:
                    tweets = self.client.get_users_tweets(user.id, max_results=tweets_per_user, exclude=['retweets', 'replies'])
                    if tweets.data:
                        tweet_ids.extend([t.id for t in tweets.data])
                    time.sleep(0.3)
                except:
                    continue
            logger.info(f"フォロー中から{len(tweet_ids)}件取得")
            return tweet_ids
        except tweepy.TooManyRequests:
            logger.warning("フォロー取得レート制限。60秒待機...")
            time.sleep(60)
            return []
        except Exception as e:
            logger.error(f"フォロー取得エラー: {e}")
            return []

    def get_my_tweets(self, count=10):
        logger.info("自分のツイート取得中...")
        try:
            tweets = self.client.get_users_tweets(self.my_user_id, max_results=min(count, 100), exclude=['retweets'])
            if tweets.data:
                return [tweet.id for tweet in tweets.data]
            return []
        except Exception as e:
            logger.error(f"自分のツイート取得エラー: {e}")
            return []

    def get_liking_users(self, tweet_id):
        try:
            liking_users = self.client.get_liking_users(tweet_id)
            if liking_users.data:
                return [(user.id, user.username) for user in liking_users.data]
            return []
        except:
            return []

    def get_user_recent_tweet(self, user_id):
        try:
            tweets = self.client.get_users_tweets(user_id, max_results=5, exclude=['retweets', 'replies'])
            if tweets.data:
                return tweets.data[0].id
            return None
        except:
            return None

    def run_timeline_likes(self):
        logger.info("=" * 50)
        logger.info("モード: タイムラインいいね")
        logger.info("=" * 50)
        tweet_ids = self.get_timeline_tweets(100)
        if not tweet_ids:
            return 0
        new_tweets = [tid for tid in tweet_ids if str(tid) not in self.liked_tweets]
        random.shuffle(new_tweets)
        logger.info(f"いいね対象: {len(new_tweets)}件")
        liked_count = 0
        for tweet_id in new_tweets:
            if not self._check_session_limit() or not self._check_daily_limit():
                break
            if self.like_tweet(tweet_id):
                liked_count += 1
                self._smart_delay()
        logger.info(f"完了: {liked_count}件")
        return liked_count

    def run_following_likes(self):
        logger.info("=" * 50)
        logger.info("モード: フォロー中の人へのいいね")
        logger.info("=" * 50)
        tweet_ids = self.get_following_tweets(max_users=30, tweets_per_user=3)
        if not tweet_ids:
            return 0
        new_tweets = [tid for tid in tweet_ids if str(tid) not in self.liked_tweets]
        random.shuffle(new_tweets)
        logger.info(f"いいね対象: {len(new_tweets)}件")
        liked_count = 0
        max_likes = self.config['following_likes_per_run']
        for tweet_id in new_tweets:
            if liked_count >= max_likes or not self._check_session_limit() or not self._check_daily_limit():
                break
            if self.like_tweet(tweet_id):
                liked_count += 1
                self._smart_delay()
        logger.info(f"完了: {liked_count}件")
        return liked_count

    def run_likeback(self):
        logger.info("=" * 50)
        logger.info("モード: いいね返し")
        logger.info("=" * 50)
        my_tweets = self.get_my_tweets(10)
        if not my_tweets:
            return 0
        users_to_likeback = []
        today = datetime.now().strftime('%Y-%m-%d')
        for tweet_id in my_tweets:
            liking_users = self.get_liking_users(tweet_id)
            for user_id, username in liking_users:
                if user_id == self.my_user_id:
                    continue
                likeback_key = f"{user_id}_{today}"
                if likeback_key in self.likeback_history:
                    continue
                users_to_likeback.append((user_id, username))
            time.sleep(0.3)
        users_to_likeback = list(set(users_to_likeback))
        random.shuffle(users_to_likeback)
        logger.info(f"いいね返し対象: {len(users_to_likeback)}人")
        liked_count = 0
        for user_id, username in users_to_likeback:
            if not self._check_session_limit() or not self._check_daily_limit():
                break
            tweet_id = self.get_user_recent_tweet(user_id)
            if not tweet_id:
                continue
            if self.like_tweet(tweet_id):
                liked_count += 1
                likeback_key = f"{user_id}_{today}"
                self.likeback_history.add(likeback_key)
                self._save_json_set(self.likeback_history_file, self.likeback_history)
                logger.info(f"@{username} にいいね返し")
                self._smart_delay()
        logger.info(f"完了: {liked_count}件")
        return liked_count

    def run_all(self):
        logger.info("全モード実行開始")
        total = 0
        total += self.run_following_likes()
        if self._check_daily_limit():
            time.sleep(30)
        self.session_count = 0
        total += self.run_likeback()
        if self._check_daily_limit():
            time.sleep(30)
        self.session_count = 0
        total += self.run_timeline_likes()
        logger.info(f"全モード完了: 合計{total}件")
        return total

    def show_status(self):
        today = datetime.now().strftime('%Y-%m-%d')
        if self.daily_count['date'] != today:
            self.daily_count = {'date': today, 'count': 0}
        logger.info("=" * 50)
        logger.info(f"本日のいいね数: {self.daily_count['count']}件")
        logger.info(f"残り: {self.config['max_likes_per_day'] - self.daily_count['count']}件")
        logger.info("=" * 50)

def main():
    import argparse
    parser = argparse.ArgumentParser(description='X自動いいねスクリプト v3.0')
    parser.add_argument('--mode', choices=['timeline', 'following', 'likeback', 'all'], default='timeline')
    parser.add_argument('--test', action='store_true')
    parser.add_argument('--status', action='store_true')
    args = parser.parse_args()
    logger.info("X自動いいねスクリプト v3.0")
    liker = OptimizedAutoLiker()
    if args.test:
        logger.info("テストモード: 認証成功")
        return
    if args.status:
        liker.show_status()
        return
    if args.mode == 'timeline':
        liker.run_timeline_likes()
    elif args.mode == 'following':
        liker.run_following_likes()
    elif args.mode == 'likeback':
        liker.run_likeback()
    elif args.mode == 'all':
        liker.run_all()

if __name__ == '__main__':
    main()