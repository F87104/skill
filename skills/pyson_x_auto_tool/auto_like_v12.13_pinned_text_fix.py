#!/usr/bin/env python3
"""
Project Prometheus v12.13 [Pinned Text Fix Edition]
「固定」というテキストを直接検出して固定ツイートを確実にスキップする
"""

import time
import random
import sys
import json
import configparser
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

class Config:
    def __init__(self, config_path=None):
        self.config = configparser.ConfigParser()
        self.config_path = config_path or os.path.expanduser('~/prometheus/config.ini')
        if not os.path.exists(self.config_path):
            log_error(f"config.iniが見つかりません: {self.config_path}")
            sys.exit(1)
        self.config.read(self.config_path, encoding='utf-8')
        log_info(f"設定読み込み完了: {self.config_path}")

    def get(self, section, option, default=None):
        return self.config.get(section, option, fallback=default)

    def getint(self, section, option, default=None):
        try: return self.config.getint(section, option)
        except: return default

class PrometheusV12_13:
    def __init__(self, config_path=None):
        self.config = Config(config_path)
        self.user_data_dir = os.path.expanduser('~/.prometheus_v12_session')
        self.liked_users_file = Path(self.user_data_dir) / 'liked_users.json'
        self.liked_users = self._load_json(self.liked_users_file, "いいね履歴")
        self.my_username = self.config.get('General', 'MY_USERNAME')
        if not self.my_username or self.my_username == 'your_x_username_here':
            log_error("config.iniにMY_USERNAMEが設定されていません。")
            sys.exit(1)

    def _load_json(self, file_path, log_name):
        try:
            if file_path.exists():
                with file_path.open('r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            log_debug(f"{log_name}の読み込みに失敗: {e}")
        return {}

    def _save_json(self, data, file_path, log_name):
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with file_path.open('w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log_error(f"{log_name}の保存に失敗: {e}")

    def run(self):
        log_info("--- Project Prometheus v12.13 [Pinned Text Fix Edition] ---")
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

            if not self.check_and_perform_login(page):
                log_error("ログインに失敗したため、処理を終了します。")
                context.close()
                return
            
            log_success("自動化処理を開始します。")

            try:
                self.run_full_likeback_cycle(page)
            except KeyboardInterrupt:
                log_info("プログラムを停止します。")
            finally:
                log_info("ブラウザを閉じます。")
                context.close()

    def check_and_perform_login(self, page):
        try:
            log_info("ログイン状態を確認します...")
            page.goto("https://x.com/home", wait_until='domcontentloaded', timeout=30000)
            
            try:
                page.wait_for_selector("article[data-testid='tweet']", timeout=10000)
                log_success("ログイン済みです。")
                return True
            except PlaywrightTimeoutError:
                log_info("=" * 50)
                log_info("ログインが必要です。")
                log_info("表示されているブラウザでXにログインしてください。")
                log_info("ログイン完了後、このターミナルでEnterキーを押してください。")
                log_info("=" * 50)
                input()
                
                log_info("ログイン完了を確認しています...")
                try:
                    page.goto("https://x.com/home", wait_until='domcontentloaded', timeout=30000)
                    page.wait_for_selector("article[data-testid='tweet']", timeout=60000)
                    log_success("ログインを確認しました！セッション情報を保存します。")
                    return True
                except PlaywrightTimeoutError:
                    log_error("ログインが確認できませんでした。タイムアウトしました。")
                    return False

        except Exception as e:
            log_error(f"ログイン確認中に予期せぬエラーが発生しました: {e}")
            return False

    def run_full_likeback_cycle(self, page):
        log_info("フルいいね返しサイクルを開始します...")
        try:
            profile_url = f"https://x.com/{self.my_username}"
            log_info(f"プロフィールページに移動: {profile_url}")
            page.goto(profile_url, wait_until='domcontentloaded', timeout=30000)
            time.sleep(random.uniform(3, 5))

            processed_tweets = set()
            total_liked_back_count = 0

            for _ in range(self.config.getint('Likeback', 'MAX_TWEET_SCROLLS', 5)):
                tweets = page.locator("article[data-testid='tweet']").all()
                if not tweets:
                    log_info("プロフィールページにツイートが見つかりません。")
                    break

                tweets_with_time = []
                for tweet in tweets:
                    # --- v12.13 修正点: 「固定」テキストで固定ツイートを検出 --- #
                    pinned_text_locator = tweet.locator("div[data-testid='socialContext']:has-text('固定')")
                    if pinned_text_locator.count() > 0:
                        log_info("固定ツイートを検出しました。スキップします。")
                        continue

                    time_locator = tweet.locator("time").first
                    tweet_url_locator = tweet.locator("a[href*='/status/']").first

                    if time_locator.count() > 0 and tweet_url_locator.count() > 0:
                        datetime_str = time_locator.get_attribute('datetime')
                        tweet_url = tweet_url_locator.get_attribute('href')
                        
                        if tweet_url not in processed_tweets:
                            tweets_with_time.append((datetime_str, tweet_url))
                
                if not tweets_with_time:
                    log_info("このページの新しいツイートは全て処理済みです。")
                    page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    time.sleep(random.uniform(3, 5))
                    continue

                tweets_with_time.sort(key=lambda x: x[0], reverse=True)
                log_info(f"収集したツイートをタイムスタンプ順にソートしました。")

                for datetime_str, tweet_url in tweets_with_time:
                    processed_tweets.add(tweet_url)
                    full_tweet_url = f"https://x.com{tweet_url}"
                    log_info(f"ツイートを処理: {full_tweet_url} ({datetime_str})")

                    try:
                        likes_page_url = f"{full_tweet_url}/likes"
                        log_info(f"いいね一覧ページに直接移動: {likes_page_url}")
                        page.goto(likes_page_url, wait_until='domcontentloaded', timeout=30000)
                        time.sleep(random.uniform(2, 4))

                        try:
                            page.wait_for_selector("[data-testid='UserCell']", timeout=10000)
                            log_info("いいねしたユーザー一覧を開きました。")
                        except PlaywrightTimeoutError:
                            log_info("このツイートにはいいねがないか、一覧を取得できませんでした。")
                            continue

                        liker_handles = self.scroll_and_get_all_likers(page)
                        log_info(f"{len(liker_handles)}件のいいねを検出しました。")

                        if not liker_handles:
                            continue

                        for user_handle in liker_handles:
                            if user_handle.lower() in self.liked_users:
                                log_debug(f"{user_handle} には既にいいね返し済みです。")
                                continue

                            user_profile_url = f"https://x.com/{user_handle.lstrip('@')}"
                            log_info(f"{user_handle} のプロフィールに移動します...")
                            page.goto(user_profile_url, wait_until='domcontentloaded', timeout=20000)
                            time.sleep(random.uniform(2, 4))

                            latest_tweet = page.locator("article[data-testid='tweet']").first
                            if latest_tweet.count() == 0:
                                log_info(f"{user_handle} には表示できるツイートがありません。")
                                continue

                            like_button = latest_tweet.locator("[data-testid='like']")
                            if like_button.count() > 0:
                                like_button.click()
                                log_success(f"{user_handle} の最新ツイートにいいねしました！")
                                self.liked_users[user_handle.lower()] = datetime.now().isoformat()
                                self._save_json(self.liked_users, self.liked_users_file, "いいね履歴")
                                total_liked_back_count += 1
                                time.sleep(random.uniform(10, 20))
                            else:
                                log_info(f"{user_handle} の最新ツイートには既にいいね済みか、ボタンが見つかりません。")
                        
                        log_info("プロフィールページに戻ります。")
                        page.goto(profile_url, wait_until='domcontentloaded', timeout=30000)
                        time.sleep(random.uniform(2, 3))

                    except Exception as e:
                        log_error(f"ツイート処理中にエラー: {e}")
                        page.goto(profile_url, wait_until='domcontentloaded', timeout=30000)
                        continue
                
                log_info("次のツイートを読み込むためにスクロールします。")
                page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                time.sleep(random.uniform(3, 5))

            log_success(f"フルいいね返しサイクル完了: 合計 {total_liked_back_count} 件のいいね返しを実行しました。")

        except Exception as e:
            log_error(f"フルいいね返しサイクル実行中に致命的なエラーが発生しました: {e}")

    def scroll_and_get_all_likers(self, page):
        all_handles = set()
        scroll_attempts = 0
        max_scrolls = self.config.getint('Likeback', 'MAX_LIKER_SCROLLS', 10)
        
        while scroll_attempts < max_scrolls:
            liker_cells = page.locator("[data-testid='UserCell']").all()
            current_handles_on_page = set()
            for cell in liker_cells:
                user_link_locator = cell.locator("a[href^='/'][role='link']").first
                if user_link_locator.count() > 0:
                    href = user_link_locator.get_attribute('href')
                    if href and href.startswith('/') and len(href) > 1:
                        handle = '@' + href[1:]
                        current_handles_on_page.add(handle)
            
            if not current_handles_on_page.difference(all_handles):
                log_info("いいね一覧の最後まで到達したか、新しいユーザーが見つかりませんでした。")
                break

            all_handles.update(current_handles_on_page)
            page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            time.sleep(random.uniform(1.5, 2.5))
            scroll_attempts += 1
        
        if scroll_attempts >= max_scrolls:
            log_info(f"いいね一覧のスクロールが最大回数({max_scrolls})に達しました。")

        return list(all_handles)

def main():
    app = PrometheusV12_13()
    app.run()

if __name__ == "__main__":
    main()
