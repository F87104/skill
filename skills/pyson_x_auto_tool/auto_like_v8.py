import time
import random
import sys
import json
import configparser
from pathlib import Path
from datetime import datetime
import os

# =====================================================
# Project Prometheus v8.0 [Playwright Edition]
# AI 10名が設計した、最新技術による究極の安定版
# =====================================================

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
except ImportError:
    print("Error: Playwrightがインストールされていません。")
    print("解決策: ターミナルで pip3 install playwright を実行してください。")
    sys.exit(1)

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def log_info(msg):
    print(f"{Colors.BLUE}[{datetime.now().strftime('%H:%M:%S')}][INFO]{Colors.RESET} {msg}")

def log_success(msg):
    print(f"{Colors.GREEN}[{datetime.now().strftime('%H:%M:%S')}][SUCCESS]{Colors.RESET} {msg}")

def log_error(msg):
    print(f"{Colors.RED}[{datetime.now().strftime('%H:%M:%S')}][ERROR]{Colors.RESET} {msg}")

class Config:
    def __init__(self, config_path=None):
        self.config = configparser.ConfigParser()
        if config_path is None or not os.path.exists(config_path):
            config_path = os.path.expanduser('~/prometheus/config.ini')
        
        if not os.path.exists(config_path):
            log_error(f"config.iniが見つかりません: {config_path}")
            sys.exit(1)
            
        self.config.read(config_path, encoding='utf-8')
        log_info(f"設定読み込み完了: {config_path}")

    def get(self, section, option, default=None):
        return self.config.get(section, option, fallback=default)

    def getint(self, section, option, default=None):
        try: return self.config.getint(section, option, fallback=default)
        except: return default

    def getlist(self, section, option, default=None):
        if self.config.has_option(section, option):
            return [item.strip() for item in self.config.get(section, option).split(',') if item.strip()]
        return default

class PrometheusV8:
    def __init__(self, config_path=None):
        self.config = Config(config_path)
        self.auth_file = Path(self.config.get('General', 'PROFILE_DIR', '~/.prometheus_playwright')).expanduser() / 'auth.json'
        self.liked_users_file = Path(self.config.get('General', 'LIKED_USERS_FILE', '~/.prometheus_playwright/liked_users.json')).expanduser()
        self.liked_users = self._load_liked_users()

    def _load_liked_users(self):
        try:
            if self.liked_users_file.exists():
                with open(self.liked_users_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except: pass
        return {}

    def _save_liked_users(self):
        try:
            self.liked_users_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.liked_users_file, 'w', encoding='utf-8') as f:
                json.dump(self.liked_users, f, ensure_ascii=False, indent=2)
        except: pass

    def run(self):
        with sync_playwright() as p:
            # ログイン処理
            if not self.auth_file.exists():
                log_info("初回ログインが必要です。ブラウザを起動しますので、Xにログインしてください。")
                browser = p.chromium.launch(headless=False)
                page = browser.new_page()
                page.goto("https://x.com/login")
                log_info("ログインが完了し、タイムラインが表示されたら、このターミナルに戻ってEnterキーを押してください...")
                input() # ユーザーのログイン完了を待つ
                page.context.storage_state(path=self.auth_file)
                log_success("ログイン情報を保存しました！次回から自動ログインします。")
                browser.close()

            # メインループ
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(storage_state=self.auth_file)
            page = context.new_page()
            log_success("ブラウザを起動し、ログインしました。")

            try:
                while True:
                    self.run_cycle(page)
                    wait = random.randint(300, 600)
                    log_info(f"次のサイクルまで {wait//60}分 待機します...")
                    time.sleep(wait)
            except KeyboardInterrupt:
                log_info("停止します。")
            finally:
                browser.close()

    def run_cycle(self, page):
        try:
            log_info("タイムラインを取得中...")
            page.goto("https://x.com/home", timeout=60000)
            page.wait_for_selector("//article[@data-testid='tweet']", timeout=30000)

            tweets = page.locator("//article[@data-testid='tweet']").all()
            liked_count = 0
            target = self.config.getint('Limits', 'LIKES_PER_CYCLE_TARGET', 10)
            
            target_keywords = self.config.getlist('Keywords', 'TARGET_KEYWORDS', [])
            exclude_keywords = self.config.getlist('Keywords', 'EXCLUDE_KEYWORDS', [])
            like_prob = self.config.getint('Behavior', 'LIKE_PROBABILITY', 90)

            for tweet in tweets:
                if liked_count >= target: break
                try:
                    user_locator = tweet.locator(".//div[@data-testid='User-Name']//span[contains(text(), '@')]")
                    if user_locator.count() == 0: continue
                    user = user_locator.inner_text()
                    
                    if user.lower() in self.liked_users: continue

                    text_locator = tweet.locator(".//div[@data-testid='tweetText']")
                    if text_locator.count() == 0: continue
                    text = text_locator.inner_text()
                    
                    if any(k in text for k in target_keywords) and not any(k in text for k in exclude_keywords):
                        if random.randint(1, 100) <= like_prob:
                            btn = tweet.locator(".//div[@data-testid='like']")
                            btn.click()
                            log_success(f"いいね成功: {user}")
                            self.liked_users[user.lower()] = datetime.now().isoformat()
                            self._save_liked_users()
                            liked_count += 1
                            time.sleep(random.randint(10, 20))
                except Exception as e:
                    # log_warning(f"個別ツイート処理エラー: {e}")
                    continue
            
            log_info(f"サイクル完了: {liked_count}件のいいねをしました。")
        except PlaywrightTimeoutError:
            log_error("タイムラインの読み込みに失敗しました。ネットワーク接続を確認してください。")
        except Exception as e:
            log_error(f"予期せぬエラーが発生しました: {e}")

def main():
    log_info("Project Prometheus v8.0 [Playwright Edition] 起動")
    app = PrometheusV8()
    app.run()

if __name__ == "__main__":
    main()
