import time
import random
import sys
import json
import configparser
from pathlib import Path
from datetime import datetime
import os

# =====================================================
# Project Prometheus v10.0 [Senior Architect Edition]
# タイムアウト問題を根本解決し、安定性を極限まで高めた最終版
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

    def getboolean(self, section, option, default=False):
        try: return self.config.getboolean(section, option)
        except: return default

    def getlist(self, section, option, default=None):
        value = self.config.get(section, option, fallback='')
        return [item.strip() for item in value.split(',')] if value else (default or [])

class PrometheusSenior:
    def __init__(self, config_path=None):
        self.config = Config(config_path)
        self.user_data_dir = os.path.expanduser('~/.prometheus_v10_session')
        self.liked_users_file = Path(self.user_data_dir) / 'liked_users.json'
        self.liked_users = self._load_liked_users()

    def _load_liked_users(self):
        try:
            if self.liked_users_file.exists():
                with self.liked_users_file.open('r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            log_debug("いいね履歴の読み込みに失敗: " + str(e))
        return {}

    def _save_liked_users(self):
        try:
            self.liked_users_file.parent.mkdir(parents=True, exist_ok=True)
            with self.liked_users_file.open('w', encoding='utf-8') as f:
                json.dump(self.liked_users, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log_error("いいね履歴の保存に失敗: " + str(e))

    def run(self):
        log_info("--- Project Prometheus v10.0 [Senior Architect Edition] ---")
        with sync_playwright() as p:
            log_info("ブラウザを起動します... (ヘッドレスモードは使用しません)")
            context = p.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=False, # 常に画面表示モードで実行
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-infobars',
                    '--disable-extensions',
                ],
                ignore_default_args=['--enable-automation'],
                viewport={'width': 800, 'height': 600}
            )
            page = context.pages[0] if context.pages else context.new_page()
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")

            self.check_and_perform_login(page)

            log_success("自動いいね処理を開始します。ウィンドウは最小化して構いません。")

            try:
                while True:
                    self.run_cycle(page)
                    wait = random.randint(300, 600)
                    log_info("次のサイクルまで待機: " + str(wait // 60) + "分...")
                    time.sleep(wait)
            except KeyboardInterrupt:
                log_info("プログラムを停止します。")
            finally:
                log_info("ブラウザを閉じます。")
                context.close()

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

    def run_cycle(self, page):
        try:
            log_info("タイムラインのチェックを開始します...")
            for attempt in range(3):
                try:
                    page.goto("https://x.com/home", wait_until='domcontentloaded', timeout=30000)
                    time.sleep(random.uniform(3, 5))
                    log_debug("ページ遷移完了")
                    break
                except PlaywrightTimeoutError:
                    log_error("ページ読み込みがタイムアウトしました。(" + str(attempt + 1) + "/3)")
                    if attempt == 2:
                        log_error("3回試行しましたが失敗しました。サイクルをスキップします。")
                        return
                    time.sleep(5)

            for i in range(3):
                log_debug("スクロール実行 (" + str(i + 1) + "/3)")
                page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                time.sleep(random.uniform(2, 4))

            powerful_mode = self.config.getboolean('Behavior', 'POWERFUL_MODE', False)
            target_keywords = self.config.getlist('Keywords', 'TARGET_KEYWORDS')
            exclude_keywords = self.config.getlist('Keywords', 'EXCLUDE_KEYWORDS')
            target_count = self.config.getint('Limits', 'LIKES_PER_CYCLE_TARGET', 5)
            like_prob = self.config.getint('Behavior', 'LIKE_PROBABILITY', 90)

            tweets = page.locator("article[data-testid='tweet']").all()
            log_info(str(len(tweets)) + "件のツイートを検出しました。")
            liked_count = 0

            for tweet in tweets:
                if liked_count >= target_count: break
                try:
                    user_locator = tweet.locator("[data-testid='User-Name'] span:has-text('@')")
                    if user_locator.count() == 0: continue
                    user = user_locator.first.inner_text()
                    if user.lower() in self.liked_users: continue

                    text_locator = tweet.locator("[data-testid='tweetText']")
                    if text_locator.count() == 0: continue
                    text = text_locator.inner_text()

                    should_like = False
                    if powerful_mode:
                        if not any(k in text for k in exclude_keywords):
                            should_like = True
                    else:
                        if any(k in text for k in target_keywords) and not any(k in text for k in exclude_keywords):
                            should_like = True

                    if should_like and random.randint(1, 100) <= like_prob:
                        btn = tweet.locator("[data-testid='like']")
                        if btn.count() > 0:
                            btn.first.click()
                            preview = text[:30].replace('\n', ' ')
                            log_success("いいね成功: " + user + " -> 「" + preview + "...」")
                            self.liked_users[user.lower()] = datetime.now().isoformat()
                            self._save_liked_users()
                            liked_count += 1
                            time.sleep(random.randint(10, 20))
                except Exception as e:
                    log_debug("ツイート処理中にエラー: " + str(e))
                    continue
            
            log_info("サイクル完了: " + str(liked_count) + "件のいいねを実行しました。")
        except Exception as e:
            log_error("サイクル実行中に致命的なエラーが発生しました: " + str(e))

def main():
    app = PrometheusSenior()
    app.run()

if __name__ == "__main__":
    main()
