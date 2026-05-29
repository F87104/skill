import time
import random
import sys
import json
import configparser
from pathlib import Path
from datetime import datetime
import os

# =====================================================
# Project Prometheus v8.0 [Manual Login + Stealth]
# 手動ログイン対応・自動操作検知を回避する究極版
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

class PrometheusManual:
    def __init__(self, config_path=None):
        self.config = Config(config_path)
        self.user_data_dir = os.path.expanduser('~/.prometheus_manual_login')
        self.liked_users_file = Path(os.path.expanduser('~/.prometheus_manual_login/liked_users.json'))
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
            log_info("ステルスモードでブラウザを起動中...")
            
            # ステルス設定付きで永続的コンテキストを起動
            context = p.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=False,  # 最初は画面を出す（ログイン用）
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-infobars',
                    '--disable-extensions',
                    '--start-maximized'
                ],
                ignore_default_args=['--enable-automation']
            )
            page = context.new_page()
            
            # 自動操作であることを隠すためのJavaScript
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.chrome = { runtime: {} };
            """)

            # ログイン確認
            page.goto("https://x.com/home", timeout=60000)
            time.sleep(3)
            
            if "login" in page.url:
                log_info("=" * 50)
                log_info("ログインが必要です。")
                log_info("開いたブラウザでXにログインしてください。")
                log_info("ログイン完了後、このターミナルでEnterキーを押してください。")
                log_info("=" * 50)
                input()
                log_success("ログイン情報を保存しました！")
            else:
                log_success("既にログイン済みです。")

            # ブラウザを閉じて、ヘッドレスで再起動
            context.close()
            log_info("バックグラウンドモードに切り替えます...")
            
            context = p.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=True,  # 今度は画面なし
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-gpu'
                ],
                ignore_default_args=['--enable-automation']
            )
            page = context.new_page()
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            log_success("バックグラウンドで自動いいねを開始します！")

            try:
                while True:
                    self.run_cycle(page)
                    wait = random.randint(300, 600)
                    log_info(f"待機中: {wait//60}分...")
                    time.sleep(wait)
            except KeyboardInterrupt:
                log_info("停止します。")
            finally:
                context.close()

    def run_cycle(self, page):
        try:
            log_info("タイムラインをチェック中...")
            page.goto("https://x.com/home", timeout=60000)
            page.wait_for_selector("article[data-testid='tweet']", timeout=30000)

            target_keywords = self.config.getlist('Keywords', 'TARGET_KEYWORDS', [])
            exclude_keywords = self.config.getlist('Keywords', 'EXCLUDE_KEYWORDS', [])
            target_count = self.config.getint('Limits', 'LIKES_PER_CYCLE_TARGET', 10)
            like_prob = self.config.getint('Behavior', 'LIKE_PROBABILITY', 90)

            tweets = page.locator("article[data-testid='tweet']").all()
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
                    
                    if any(k in text for k in target_keywords) and not any(k in text for k in exclude_keywords):
                        if random.randint(1, 100) <= like_prob:
                            btn = tweet.locator("[data-testid='like']")
                            if btn.count() > 0:
                                btn.first.click()
                                log_success(f"いいね成功: {user}")
                                self.liked_users[user.lower()] = datetime.now().isoformat()
                                self._save_liked_users()
                                liked_count += 1
                                time.sleep(random.randint(10, 20))
                except: continue
            
            log_info(f"サイクル完了: {liked_count}件")
        except Exception as e:
            log_error(f"エラー: {e}")

def main():
    log_info("Project Prometheus v8.0 [Manual Login + Stealth] 起動")
    app = PrometheusManual()
    app.run()

if __name__ == "__main__":
    main()
