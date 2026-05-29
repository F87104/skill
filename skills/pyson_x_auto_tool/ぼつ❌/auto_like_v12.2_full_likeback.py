#!/usr/bin/env python3
"""
Project Prometheus v12.2 [Full Likeback Edition]
100人以上のいいねにも対応し、全員にいいね返しを行う
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

# (v12.1から変更なし)
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

class PrometheusV12_2:
    def __init__(self, config_path=None):
        self.config = Config(config_path)
        self.user_data_dir = os.path.expanduser('~/.prometheus_v12_session')
        self.liked_users_file = Path(self.user_data_dir) / 'liked_users.json'
        self.liked_users = self._load_json(self.liked_users_file, "いいね履歴")
        self.my_username = self.config.get('General', 'MY_USERNAME')
        if not self.my_username:
            log_error("config.iniにMY_USERNAMEが設定されていません。")
            sys.exit(1)

    def _load_json(self, file_path, log_name):
        try:
            if file_path.exists():
                with file_path.open('r', encoding='utf-8') as f:
                    return json.load(f)
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

    def run(self):
        log_info("--- Project Prometheus v12.2 [Full Likeback Edition] ---")
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
            log_success("自動化処理を開始します。")

            try:
                self.run_full_likeback_cycle(page)
            except KeyboardInterrupt:
                log_info("プログラムを停止します。")
            finally:
                log_info("ブラウザを閉じます。")
                context.close()

    def check_and_perform_login(self, page):
        # (v12.1から変更なし)
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
        except Exception as e:
            log_error("ログインページの読み込みに失敗しました: " + str(e))
            sys.exit(1)

    def run_full_likeback_cycle(self, page):
        log_info("フルいいね返しサイクルを開始します...")
        try:
            profile_url = f"https://x.com/{self.my_username}"
            log_info(f"プロフィールページに移動: {profile_url}")
            page.goto(profile_url, wait_until='domcontentloaded', timeout=30000)
            time.sleep(random.uniform(3, 5))

            processed_tweets = set()
            total_liked_back_count = 0

            # 過去のツイートを遡るループ
            for _ in range(self.config.getint('Likeback', 'MAX_TWEET_SCROLLS', 5)):
                tweets = page.locator("article[data-testid='tweet']").all()
                new_tweets_found = False

                for tweet in tweets:
                    tweet_url_locator = tweet.locator("a[href*='/status/']").first
                    if tweet_url_locator.count() == 0: continue
                    tweet_id = tweet_url_locator.get_attribute('href')

                    if tweet_id in processed_tweets: continue
                    
                    new_tweets_found = True
                    processed_tweets.add(tweet_id)
                    log_info(f"ツイートを処理: {tweet_id}")

                    try:
                        likes_link = tweet.locator("a[href$='/likes']")
                        if likes_link.count() == 0:
                            log_info("このツイートにはいいねがありません。")
                            continue
                        
                        likes_link.first.click()
                        log_info("いいねしたユーザー一覧を開きました。")
                        page.wait_for_selector("[data-testid='primaryColumn']", timeout=10000)
                        time.sleep(random.uniform(2, 4))

                        # いいね一覧を最後までスクロールして全員取得
                        liker_handles = self.scroll_and_get_all_likers(page)
                        log_info(f"{len(liker_handles)}件のいいねを検出しました。")

                        for user_handle in liker_handles:
                            if user_handle.lower() in self.liked_users:
                                log_debug(f"{user_handle} には既にいいね返し済みです。")
                                continue

                            user_profile_url = f"https://x.com/{user_handle.lstrip('@')}"
                            log_info(f"{user_handle} のプロフィールに移動します...")
                            page.goto(user_profile_url, wait_until='domcontentloaded', timeout=20000)
                            time.sleep(random.uniform(2, 4))

                            latest_tweet = page.locator("article[data-testid='tweet']").first
                            like_button = latest_tweet.locator("[data-testid='like']")

                            if like_button.count() > 0:
                                like_button.click()
                                log_success(f"{user_handle} の最新ツイートにいいねしました！")
                                self.liked_users[user_handle.lower()] = datetime.now().isoformat()
                                self._save_json(self.liked_users, self.liked_users_file, "いいね履歴")
                                total_liked_back_count += 1
                                time.sleep(random.uniform(10, 20)) # API制限対策
                            else:
                                log_info(f"{user_handle} の最新ツイートには既にいいね済みか、ボタンが見つかりません。")

                        page.go_back() # プロフィールページに戻る
                        time.sleep(random.uniform(2, 3))

                    except Exception as e:
                        log_error(f"ツイート処理中にエラー: {e}")
                        page.goto(profile_url, wait_until='domcontentloaded', timeout=30000)
                        continue

                # ページをスクロール
                page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                time.sleep(random.uniform(3, 5))

                if not new_tweets_found:
                    log_info("新しいツイートが見つからなかったため、スクロールを終了します。")
                    break

            log_success(f"フルいいね返しサイクル完了: 合計 {total_liked_back_count} 件のいいね返しを実行しました。")

        except Exception as e:
            log_error(f"フルいいね返しサイクル実行中に致命的なエラーが発生しました: {e}")

    def scroll_and_get_all_likers(self, page):
        all_handles = set()
        scroll_attempts = 0
        while scroll_attempts < self.config.getint('Likeback', 'MAX_LIKER_SCROLLS', 10):
            liker_cells = page.locator("[data-testid='UserCell']").all()
            current_handles = set()
            for cell in liker_cells:
                user_handle_locator = cell.locator("span:has-text('@')")
                if user_handle_locator.count() > 0:
                    current_handles.add(user_handle_locator.first.inner_text())
            
            if len(current_handles) == len(all_handles):
                log_info("いいね一覧の最後まで到達しました。")
                break

            all_handles.update(current_handles)
            page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            time.sleep(random.uniform(1, 2))
            scroll_attempts += 1
        return list(all_handles)

def main():
    app = PrometheusV12_2()
    app.run()

if __name__ == "__main__":
    main()
