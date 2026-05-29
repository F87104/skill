#!/usr/bin/env python3
"""
=====================================================
Project Prometheus v11.2 [Complete Edition]
v11の全機能 + v11.1の効率改善を統合した完全版

【対応コマンド】
--loop        : 24時間自動運用（いいね＆フォロー＆アンフォロー）
--timeline    : おすすめTLにいいね＆フォロー（1サイクル）
--following   : フォロー中TLにいいね（1サイクル）
--likeback    : 通知欄のいいね・RTに返す（1サイクル）
--follow-only : フォローのみ実行（1サイクル）
--unfollow-only : アンフォローのみ実行（1サイクル）

【v11.2の改善点】
1. 待機時間をconfig.iniから取得（5〜10分 → 1〜3分）
2. POWERFUL_MODEを反映（キーワードなしで全ツイート対象）
3. いいね履歴を24時間で自動削除
=====================================================
"""

import time
import random
import sys
import json
import configparser
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import os

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
except ImportError:
    print("Error: Playwrightがインストールされていません。")
    print("解決策: pip3 install playwright && playwright install")
    sys.exit(1)

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    RESET = '\033[0m'

def log_info(msg):
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(Colors.BLUE + "[" + timestamp + "][INFO]" + Colors.RESET + " " + str(msg))

def log_success(msg):
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(Colors.GREEN + "[" + timestamp + "][SUCCESS]" + Colors.RESET + " " + str(msg))

def log_error(msg):
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(Colors.RED + "[" + timestamp + "][ERROR]" + Colors.RESET + " " + str(msg))

def log_debug(msg):
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(Colors.YELLOW + "[" + timestamp + "][DEBUG]" + Colors.RESET + " " + str(msg))

def log_follow(msg):
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(Colors.MAGENTA + "[" + timestamp + "][FOLLOW]" + Colors.RESET + " " + str(msg))

def log_unfollow(msg):
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(Colors.CYAN + "[" + timestamp + "][UNFOLLOW]" + Colors.RESET + " " + str(msg))

class Config:
    def __init__(self, config_path=None):
        self.config = configparser.ConfigParser()
        config_path = config_path or os.path.expanduser('~/prometheus/config.ini')
        if not os.path.exists(config_path):
            log_error("config.iniが見つかりません: " + str(config_path))
            sys.exit(1)
        self.config.read(config_path, encoding='utf-8')
        log_info("設定読み込み完了: " + str(config_path))

    def get(self, section, option, default=None):
        return self.config.get(section, option, fallback=default)

    def getint(self, section, option, default=None):
        try: return self.config.getint(section, option)
        except: return default

    def getboolean(self, section, option, default=False):
        try: return self.config.getboolean(section, option)
        except: return default

    def getlist(self, section, option, default=None):
        value = self.config.get(section, option, fallback='')
        return [item.strip() for item in value.split(',')] if value else (default or [])

class PrometheusV11_2:
    def __init__(self, config_path=None):
        self.config = Config(config_path)
        self.user_data_dir = os.path.expanduser('~/.prometheus_v11_session')
        self.liked_users_file = Path(self.user_data_dir) / 'liked_users.json'
        self.followed_users_file = Path(self.user_data_dir) / 'followed_users.json'
        # v11.2改善: 24時間以上前の履歴を自動削除
        self.liked_users = self._load_json_with_expiry(self.liked_users_file, "いいね履歴")
        self.followed_users = self._load_json(self.followed_users_file, "フォロー履歴")

    def _load_json(self, file_path, log_name):
        try:
            if file_path.exists():
                with file_path.open('r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            log_debug(log_name + "の読み込みに失敗: " + str(e))
        return {}

    def _load_json_with_expiry(self, file_path, log_name):
        """v11.2改善: 24時間以上前の履歴を自動削除"""
        try:
            if file_path.exists():
                with file_path.open('r', encoding='utf-8') as f:
                    data = json.load(f)
                    one_day_ago = datetime.now() - timedelta(days=1)
                    filtered = {}
                    for k, v in data.items():
                        try:
                            if datetime.fromisoformat(v) > one_day_ago:
                                filtered[k] = v
                        except:
                            pass
                    removed_count = len(data) - len(filtered)
                    if removed_count > 0:
                        log_info(f"24時間以上前の{log_name}を{removed_count}件削除しました。")
                    return filtered
        except Exception as e:
            log_debug(log_name + "の読み込みに失敗: " + str(e))
        return {}

    def _save_json(self, data, file_path, log_name):
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with file_path.open('w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log_error(log_name + "の保存に失敗: " + str(e))

    def run(self, mode='loop'):
        log_info("--- Project Prometheus v11.2 [Complete Edition] ---")
        log_info(f"実行モード: {mode}")
        
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=False,
                args=['--disable-blink-features=AutomationControlled', '--no-sandbox'],
                ignore_default_args=['--enable-automation'],
                viewport={'width': 800, 'height': 600}
            )
            page = context.pages[0] if context.pages else context.new_page()
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")

            self.check_and_perform_login(page)
            log_success("自動化処理を開始します。ウィンドウは最小化して構いません。")

            try:
                if mode == 'loop':
                    self._run_loop_mode(page)
                elif mode == 'timeline':
                    self._run_timeline_mode(page)
                elif mode == 'following':
                    self._run_following_mode(page)
                elif mode == 'likeback':
                    self._run_likeback_mode(page)
                elif mode == 'follow-only':
                    self._run_follow_only_mode(page)
                elif mode == 'unfollow-only':
                    self._run_unfollow_only_mode(page)
                else:
                    log_error(f"不明なモード: {mode}")
            except KeyboardInterrupt:
                log_info("プログラムを停止します。")
            finally:
                log_info("ブラウザを閉じます。")
                context.close()

    def _run_loop_mode(self, page):
        """24時間自動運用モード"""
        cycle_counter = 0
        while True:
            cycle_counter += 1
            log_info("--- Cycle " + str(cycle_counter) + " ---")
            
            # 3サイクルに1回、アンフォロー処理を実行
            if self.config.getboolean('Growth', 'ENABLE_UNFOLLOW', False) and cycle_counter % 3 == 0:
                self.run_unfollow_cycle(page)
            else:
                self.run_like_and_follow_cycle(page, "https://x.com/home")
            
            # v11.2改善: 待機時間をconfig.iniから取得
            min_wait = self.config.getint('Behavior', 'MIN_ACTION_WAIT', 60)
            max_wait = self.config.getint('Behavior', 'MAX_ACTION_WAIT', 180)
            wait = random.randint(min_wait, max_wait)
            log_info(f"次のサイクルまで待機: {wait}秒...")
            time.sleep(wait)

    def _run_timeline_mode(self, page):
        """おすすめTLにいいね＆フォロー（1サイクル）"""
        log_info("タイムラインモードを実行します...")
        self.run_like_and_follow_cycle(page, "https://x.com/home")
        log_success("タイムラインモード完了！")

    def _run_following_mode(self, page):
        """フォロー中TLにいいね（1サイクル）"""
        log_info("フォロー中モードを実行します...")
        self.run_like_and_follow_cycle(page, "https://x.com/home/following")
        log_success("フォロー中モード完了！")

    def _run_likeback_mode(self, page):
        """通知欄のいいね・RTに返す（1サイクル）"""
        log_info("いいね返しモードを実行します...")
        self.run_likeback_cycle(page)
        log_success("いいね返しモード完了！")

    def _run_follow_only_mode(self, page):
        """フォローのみ実行（1サイクル）"""
        log_info("フォローのみモードを実行します...")
        self.run_follow_only_cycle(page)
        log_success("フォローのみモード完了！")

    def _run_unfollow_only_mode(self, page):
        """アンフォローのみ実行（1サイクル）"""
        log_info("アンフォローのみモードを実行します...")
        self.run_unfollow_cycle(page)
        log_success("アンフォローのみモード完了！")

    def check_and_perform_login(self, page):
        try:
            page.goto("https://x.com/home", wait_until='domcontentloaded', timeout=30000)
            time.sleep(5)
            if "login" in page.url:
                log_info("=" * 50)
                log_info("ログインが必要です。")
                log_info("表示されているブラウザでXにログインしてください。")
                log_info("ログイン完了後、このターミナルでEnterキーを押してください。")
                log_info("=" * 50)
                input()
                log_success("ログイン情報を保存しました！")
            else:
                log_success("ログイン済みです。")
        except PlaywrightTimeoutError:
            log_error("ログインページの読み込みに失敗しました。ネットワークを確認してください。")
            sys.exit(1)

    def run_like_and_follow_cycle(self, page, url):
        log_info("いいね＆フォローサイクルを開始します...")
        try:
            page.goto(url, wait_until='domcontentloaded', timeout=30000)
            time.sleep(random.uniform(3, 5))

            for i in range(3):
                page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                time.sleep(random.uniform(2, 4))

            tweets = page.locator("article[data-testid='tweet']").all()
            log_info(str(len(tweets)) + "件のツイートを検出しました。")

            # 設定読み込み
            powerful_mode = self.config.getboolean('Behavior', 'POWERFUL_MODE', False)
            enable_follow = self.config.getboolean('Growth', 'ENABLE_FOLLOW', False)
            likes_target = self.config.getint('Limits', 'LIKES_PER_CYCLE_TARGET', 10)
            follows_target = self.config.getint('Growth', 'FOLLOWS_PER_CYCLE', 2)
            like_prob = self.config.getint('Behavior', 'LIKE_PROBABILITY', 90)
            follow_prob = self.config.getint('Growth', 'FOLLOW_PROBABILITY', 20)
            target_keywords = self.config.getlist('Keywords', 'TARGET_KEYWORDS')
            exclude_keywords = self.config.getlist('Keywords', 'EXCLUDE_KEYWORDS')

            liked_count = 0
            followed_count = 0

            for tweet in tweets:
                if liked_count >= likes_target and followed_count >= follows_target:
                    break
                try:
                    user_locator = tweet.locator("[data-testid='User-Name'] a[role='link']").first
                    if user_locator.count() == 0:
                        continue
                    href = user_locator.get_attribute('href')
                    user = '@' + href.split('/')[-1] if href else None
                    if not user:
                        continue

                    text_locator = tweet.locator("[data-testid='tweetText']")
                    text = text_locator.inner_text() if text_locator.count() > 0 else ""

                    # v11.2改善: POWERFUL_MODEを反映
                    is_target = powerful_mode or (
                        any(k in text for k in target_keywords) and 
                        not any(k in text for k in exclude_keywords)
                    )

                    # いいね処理
                    if liked_count < likes_target and is_target and random.randint(1, 100) <= like_prob:
                        if user.lower() not in self.liked_users:
                            btn = tweet.locator("[data-testid='like']")
                            if btn.count() > 0:
                                btn.first.click()
                                preview = text[:30].replace('\n', ' ') if text else "(テキストなし)"
                                log_success(f"いいね成功: {user} -> 「{preview}...」")
                                self.liked_users[user.lower()] = datetime.now().isoformat()
                                self._save_json(self.liked_users, self.liked_users_file, "いいね履歴")
                                liked_count += 1
                                time.sleep(random.uniform(5, 10))

                    # フォロー処理
                    if enable_follow and followed_count < follows_target and is_target and random.randint(1, 100) <= follow_prob:
                        if user.lower() not in self.followed_users:
                            follow_btn = tweet.locator("[data-testid='placementTracking']")
                            if follow_btn.count() > 0:
                                follow_btn.first.click()
                                log_follow(f"フォロー成功: {user}")
                                self.followed_users[user.lower()] = {
                                    'followed_at': datetime.now().isoformat(),
                                    'status': 'pending'
                                }
                                self._save_json(self.followed_users, self.followed_users_file, "フォロー履歴")
                                followed_count += 1
                                time.sleep(random.uniform(5, 10))

                except Exception as e:
                    log_debug(f"ツイート処理中にエラー: {e}")
                    continue
            
            log_info(f"サイクル完了: {liked_count}件のいいね, {followed_count}件のフォローを実行しました。")
        except Exception as e:
            log_error(f"サイクル実行中に致命的なエラーが発生しました: {e}")

    def run_likeback_cycle(self, page):
        """通知欄からいいね返しを実行"""
        log_info("通知欄からいいね返しを開始します...")
        try:
            page.goto("https://x.com/notifications", wait_until='domcontentloaded', timeout=30000)
            time.sleep(random.uniform(3, 5))

            # スクロールして通知を読み込む
            for i in range(2):
                page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                time.sleep(random.uniform(1.5, 2.5))

            # 通知からユーザーを取得
            notifications = page.locator("article").all()
            log_info(f"{len(notifications)}件の通知を検出しました。")

            likes_target = self.config.getint('Limits', 'LIKES_PER_CYCLE_TARGET', 10)
            liked_count = 0
            users_to_like = set()

            for notif in notifications:
                try:
                    # 通知からユーザー名を取得
                    user_links = notif.locator("a[role='link'][href^='/']").all()
                    for link in user_links:
                        href = link.get_attribute('href')
                        if href and not href.startswith('/i/') and not href.startswith('/notifications'):
                            user = '@' + href.split('/')[-1]
                            if user.lower() not in self.liked_users:
                                users_to_like.add(user)
                except:
                    continue

            log_info(f"{len(users_to_like)}件のユーザーにいいね返しを実行します...")

            for user in list(users_to_like)[:likes_target]:
                try:
                    user_profile_url = "https://x.com/" + user.lstrip('@')
                    page.goto(user_profile_url, wait_until='domcontentloaded', timeout=30000)
                    time.sleep(random.uniform(2, 4))

                    # 最新ツイートにいいね
                    tweets = page.locator("article[data-testid='tweet']").all()
                    if tweets:
                        like_btn = tweets[0].locator("[data-testid='like']")
                        if like_btn.count() > 0:
                            like_btn.first.click()
                            log_success(f"いいね返し成功: {user}")
                            self.liked_users[user.lower()] = datetime.now().isoformat()
                            self._save_json(self.liked_users, self.liked_users_file, "いいね履歴")
                            liked_count += 1
                            time.sleep(random.uniform(5, 10))
                        else:
                            log_debug(f"{user} の最新ツイートは既にいいね済みか、ボタンが見つかりません。")
                    else:
                        log_debug(f"{user} には表示できるツイートがありません。")

                except Exception as e:
                    log_debug(f"いいね返し処理中にエラー ({user}): {e}")
                    continue

            log_info(f"いいね返しサイクル完了: {liked_count}件のいいねを実行しました。")
        except Exception as e:
            log_error(f"いいね返しサイクル実行中にエラー: {e}")

    def run_follow_only_cycle(self, page):
        """フォローのみ実行"""
        log_info("フォローのみサイクルを開始します...")
        try:
            page.goto("https://x.com/home", wait_until='domcontentloaded', timeout=30000)
            time.sleep(random.uniform(3, 5))

            for i in range(3):
                page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                time.sleep(random.uniform(2, 4))

            tweets = page.locator("article[data-testid='tweet']").all()
            log_info(f"{len(tweets)}件のツイートを検出しました。")

            follows_target = self.config.getint('Growth', 'FOLLOWS_PER_CYCLE', 5)
            follow_prob = self.config.getint('Growth', 'FOLLOW_PROBABILITY', 50)
            followed_count = 0

            for tweet in tweets:
                if followed_count >= follows_target:
                    break
                try:
                    user_locator = tweet.locator("[data-testid='User-Name'] a[role='link']").first
                    if user_locator.count() == 0:
                        continue
                    href = user_locator.get_attribute('href')
                    user = '@' + href.split('/')[-1] if href else None
                    if not user:
                        continue

                    if random.randint(1, 100) <= follow_prob:
                        if user.lower() not in self.followed_users:
                            follow_btn = tweet.locator("[data-testid='placementTracking']")
                            if follow_btn.count() > 0:
                                follow_btn.first.click()
                                log_follow(f"フォロー成功: {user}")
                                self.followed_users[user.lower()] = {
                                    'followed_at': datetime.now().isoformat(),
                                    'status': 'pending'
                                }
                                self._save_json(self.followed_users, self.followed_users_file, "フォロー履歴")
                                followed_count += 1
                                time.sleep(random.uniform(5, 10))

                except Exception as e:
                    log_debug(f"フォロー処理中にエラー: {e}")
                    continue

            log_info(f"フォローのみサイクル完了: {followed_count}件のフォローを実行しました。")
        except Exception as e:
            log_error(f"フォローのみサイクル実行中にエラー: {e}")

    def run_unfollow_cycle(self, page):
        """アンフォローサイクル"""
        log_info("アンフォローサイクルを開始します...")
        unfollow_after_days = self.config.getint('Growth', 'UNFOLLOW_AFTER_DAYS', 7)
        unfollows_target = self.config.getint('Growth', 'UNFOLLOWS_PER_CYCLE', 5)
        
        users_to_unfollow = []
        now = datetime.now()

        for user, data in self.followed_users.items():
            if isinstance(data, dict) and data.get('status') == 'pending':
                try:
                    followed_at = datetime.fromisoformat(data['followed_at'])
                    if now - followed_at > timedelta(days=unfollow_after_days):
                        users_to_unfollow.append(user)
                except:
                    pass

        if not users_to_unfollow:
            log_info("アンフォロー対象のユーザーはいません。")
            return

        log_info(f"{len(users_to_unfollow)}件のアンフォロー候補を検出しました。")
        unfollowed_count = 0

        for user in users_to_unfollow:
            if unfollowed_count >= unfollows_target:
                break
            try:
                user_profile_url = "https://x.com/" + user.lstrip('@')
                page.goto(user_profile_url, wait_until='domcontentloaded', timeout=30000)
                time.sleep(random.uniform(2, 4))
                
                unfollow_button = page.locator("[data-testid$='-unfollow']")
                if unfollow_button.count() > 0:
                    unfollow_button.first.click()
                    time.sleep(0.5)
                    confirm_btn = page.locator("[data-testid='confirmationSheetConfirm']")
                    if confirm_btn.count() > 0:
                        confirm_btn.click()
                    log_unfollow(f"アンフォロー成功: {user}")
                    self.followed_users[user]['status'] = 'unfollowed'
                    unfollowed_count += 1
                    time.sleep(random.uniform(10, 20))
                else:
                    self.followed_users[user]['status'] = 'not_following'
                    log_debug(f"{user}は既にアンフォロー済み、またはフォローしていませんでした。")

            except Exception as e:
                log_error(f"アンフォロー処理中にエラー ({user}): {e}")
                continue
        
        self._save_json(self.followed_users, self.followed_users_file, "フォロー履歴")
        log_info(f"アンフォローサイクル完了: {unfollowed_count}件のアンフォローを実行しました。")

def main():
    parser = argparse.ArgumentParser(
        description='Project Prometheus v11.2 [Complete Edition]',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python3 auto_like_v11.2_complete.py --loop          # 24時間自動運用
  python3 auto_like_v11.2_complete.py --timeline      # おすすめTLにいいね
  python3 auto_like_v11.2_complete.py --following     # フォロー中TLにいいね
  python3 auto_like_v11.2_complete.py --likeback      # 通知いいね返し
  python3 auto_like_v11.2_complete.py --follow-only   # フォローのみ
  python3 auto_like_v11.2_complete.py --unfollow-only # アンフォローのみ
        """
    )
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--loop', action='store_true', help='24時間自動運用（いいね＆フォロー＆アンフォロー）')
    group.add_argument('--timeline', action='store_true', help='おすすめTLにいいね＆フォロー（1サイクル）')
    group.add_argument('--following', action='store_true', help='フォロー中TLにいいね（1サイクル）')
    group.add_argument('--likeback', action='store_true', help='通知欄のいいね・RTに返す（1サイクル）')
    group.add_argument('--follow-only', action='store_true', help='フォローのみ実行（1サイクル）')
    group.add_argument('--unfollow-only', action='store_true', help='アンフォローのみ実行（1サイクル）')
    
    args = parser.parse_args()
    
    # モードを決定
    if args.loop:
        mode = 'loop'
    elif args.timeline:
        mode = 'timeline'
    elif args.following:
        mode = 'following'
    elif args.likeback:
        mode = 'likeback'
    elif args.follow_only:
        mode = 'follow-only'
    elif args.unfollow_only:
        mode = 'unfollow-only'
    else:
        # デフォルトはtimeline
        mode = 'timeline'
        log_info("モードが指定されていないため、--timeline モードで実行します。")
    
    app = PrometheusV11_2()
    app.run(mode)

if __name__ == "__main__":
    main()
