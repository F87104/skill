import time
import random
import sys
import json
import configparser
from pathlib import Path
from datetime import datetime, timedelta
import os

# =====================================================
# Project Prometheus v11.0 [Intelligent Growth Edition]
# AIターゲティング・フォロー機能と自動アンフォロー機能を搭載
# =====================================================

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

class PrometheusV11:
    def __init__(self, config_path=None):
        self.config = Config(config_path)
        self.user_data_dir = os.path.expanduser('~/.prometheus_v11_session')
        self.liked_users_file = Path(self.user_data_dir) / 'liked_users.json'
        self.followed_users_file = Path(self.user_data_dir) / 'followed_users.json'
        self.liked_users = self._load_json(self.liked_users_file, "いいね履歴")
        self.followed_users = self._load_json(self.followed_users_file, "フォロー履歴")

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
        log_info("--- Project Prometheus v11.0 [Intelligent Growth Edition] ---")
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
                cycle_counter = 0
                while True:
                    cycle_counter += 1
                    log_info("--- Cycle " + str(cycle_counter) + " ---")
                    # 3サイクルに1回、アンフォロー処理を実行
                    if self.config.getboolean('Growth', 'ENABLE_UNFOLLOW', False) and cycle_counter % 3 == 0:
                        self.run_unfollow_cycle(page)
                    else:
                        self.run_like_and_follow_cycle(page)
                    
                    wait = random.randint(300, 600)
                    log_info("次のサイクルまで待機: " + str(wait // 60) + "分...")
                    time.sleep(wait)
            except KeyboardInterrupt:
                log_info("プログラムを停止します。")
            finally:
                log_info("ブラウザを閉じます。")
                context.close()

    def check_and_perform_login(self, page):
        # (v10から変更なし)
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

    def run_like_and_follow_cycle(self, page):
        log_info("いいね＆フォローサイクルを開始します...")
        # (v10のrun_cycleをベースに、フォロー機能を追加)
        try:
            page.goto("https://x.com/home", wait_until='domcontentloaded', timeout=30000)
            time.sleep(random.uniform(3, 5))

            for i in range(3):
                page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                time.sleep(random.uniform(2, 4))

            tweets = page.locator("article[data-testid='tweet']").all()
            log_info(str(len(tweets)) + "件のツイートを検出しました。")

            # 設定読み込み
            enable_follow = self.config.getboolean('Growth', 'ENABLE_FOLLOW', False)
            likes_target = self.config.getint('Limits', 'LIKES_PER_CYCLE_TARGET', 5)
            follows_target = self.config.getint('Growth', 'FOLLOWS_PER_CYCLE', 2)
            like_prob = self.config.getint('Behavior', 'LIKE_PROBABILITY', 90)
            follow_prob = self.config.getint('Growth', 'FOLLOW_PROBABILITY', 20)
            target_keywords = self.config.getlist('Keywords', 'TARGET_KEYWORDS')
            exclude_keywords = self.config.getlist('Keywords', 'EXCLUDE_KEYWORDS')

            liked_count = 0
            followed_count = 0

            for tweet in tweets:
                if liked_count >= likes_target and followed_count >= follows_target: break
                try:
                    user_locator = tweet.locator("[data-testid='User-Name'] span:has-text('@')")
                    if user_locator.count() == 0: continue
                    user = user_locator.first.inner_text()

                    text_locator = tweet.locator("[data-testid='tweetText']")
                    if text_locator.count() == 0: continue
                    text = text_locator.inner_text()

                    is_target = any(k in text for k in target_keywords) and not any(k in text for k in exclude_keywords)

                    # いいね処理
                    if liked_count < likes_target and is_target and random.randint(1, 100) <= like_prob:
                        if user.lower() not in self.liked_users:
                            btn = tweet.locator("[data-testid='like']")
                            if btn.count() > 0:
                                btn.first.click()
                                preview = text[:30].replace('\n', ' ')
                                log_success("いいね成功: " + user + " -> 「" + preview + "...」")
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
                                log_follow("フォロー成功: " + user)
                                self.followed_users[user.lower()] = {'followed_at': datetime.now().isoformat(), 'status': 'pending'}
                                self._save_json(self.followed_users, self.followed_users_file, "フォロー履歴")
                                followed_count += 1
                                time.sleep(random.uniform(5, 10))

                except Exception as e:
                    log_debug("ツイート処理中にエラー: " + str(e))
                    continue
            
            log_info("サイクル完了: " + str(liked_count) + "件のいいね, " + str(followed_count) + "件のフォローを実行しました。")
        except Exception as e:
            log_error("サイクル実行中に致命的なエラーが発生しました: " + str(e))

    def run_unfollow_cycle(self, page):
        log_info("アンフォローサイクルを開始します...")
        unfollow_after_days = self.config.getint('Growth', 'UNFOLLOW_AFTER_DAYS', 7)
        unfollows_target = self.config.getint('Growth', 'UNFOLLOWS_PER_CYCLE', 5)
        
        users_to_unfollow = []
        now = datetime.now()

        for user, data in self.followed_users.items():
            if data.get('status') == 'pending':
                followed_at = datetime.fromisoformat(data['followed_at'])
                if now - followed_at > timedelta(days=unfollow_after_days):
                    users_to_unfollow.append(user)

        if not users_to_unfollow:
            log_info("アンフォロー対象のユーザーはいません。")
            return

        log_info(str(len(users_to_unfollow)) + "件のアンフォロー候補を検出しました。")
        unfollowed_count = 0

        for user in users_to_unfollow:
            if unfollowed_count >= unfollows_target: break
            try:
                user_profile_url = "https://x.com/" + user.lstrip('@')
                page.goto(user_profile_url, wait_until='domcontentloaded', timeout=30000)
                time.sleep(random.uniform(2, 4))
                
                unfollow_button = page.locator("[data-testid$='-unfollow']")
                if unfollow_button.count() > 0:
                    unfollow_button.first.click()
                    # 確認ダイアログのボタンをクリック
                    page.locator("[data-testid='confirmationSheetConfirm']").click()
                    log_unfollow("アンフォロー成功: " + user)
                    self.followed_users[user]['status'] = 'unfollowed'
                    unfollowed_count += 1
                    time.sleep(random.uniform(10, 20))
                else:
                    # フォローされていなかった場合（手動で解除したなど）
                    self.followed_users[user]['status'] = 'not_following'
                    log_debug(user + "は既にアンフォロー済み、またはフォローしていませんでした。")

            except Exception as e:
                log_error("アンフォロー処理中にエラー (" + user + "): " + str(e))
                continue
        
        self._save_json(self.followed_users, self.followed_users_file, "フォロー履歴")
        log_info("アンフォローサイクル完了: " + str(unfollowed_count) + "件のアンフォローを実行しました。")

def main():
    app = PrometheusV11()
    app.run()

if __name__ == "__main__":
    main()
