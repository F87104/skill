import time
import random
import sys
import json
import configparser
from pathlib import Path
from datetime import datetime
import os

# =====================================================
# Project Prometheus v9.0 [FINAL]
# f-stringを完全廃止し、Python 3.9互換性を保証
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
        if config_path is None or not os.path.exists(str(config_path)):
            config_path = os.path.expanduser('~/prometheus/config.ini')
        
        if not os.path.exists(config_path):
            log_error("config.iniが見つかりません: " + str(config_path))
            sys.exit(1)
            
        self.config.read(config_path, encoding='utf-8')
        log_info("設定読み込み完了: " + str(config_path))

    def get(self, section, option, default=None):
        return self.config.get(section, option, fallback=default)

    def getint(self, section, option, default=None):
        try:
            return self.config.getint(section, option, fallback=default)
        except Exception:
            return default

    def getboolean(self, section, option, default=False):
        try:
            return self.config.getboolean(section, option, fallback=default)
        except Exception:
            return default

    def getlist(self, section, option, default=None):
        if self.config.has_option(section, option):
            raw_value = self.config.get(section, option)
            return [item.strip() for item in raw_value.split(',') if item.strip()]
        if default is None:
            return []
        return default

class PrometheusFinal:
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
        except Exception:
            pass
        return {}

    def _save_liked_users(self):
        try:
            self.liked_users_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.liked_users_file, 'w', encoding='utf-8') as f:
                json.dump(self.liked_users, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def run(self):
        log_info("--- Project Prometheus v9.0 [FINAL] ---")
        with sync_playwright() as p:
            default_path = Path(self.user_data_dir).joinpath("Default")
            if not default_path.exists():
                self.perform_manual_login(p)
            else:
                log_success("既存のログイン情報が見つかりました。")

            log_info("バックグラウンドモードでブラウザを起動中...")
            context = p.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=True,
                args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-gpu'],
                ignore_default_args=['--enable-automation']
            )
            page = context.new_page()
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            log_success("バックグラウンドで自動いいねを開始します！")

            try:
                while True:
                    self.run_cycle(page)
                    wait = random.randint(300, 600)
                    wait_minutes = wait // 60
                    log_info("次のサイクルまで待機: " + str(wait_minutes) + "分...")
                    time.sleep(wait)
            except KeyboardInterrupt:
                log_info("プログラムを停止します。")
            finally:
                context.close()

    def perform_manual_login(self, playwright_instance):
        log_info("初回起動のため、手動ログインが必要です。")
        context = playwright_instance.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=False,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--start-maximized'],
            ignore_default_args=['--enable-automation']
        )
        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined}); window.chrome = { runtime: {} };")
        
        page.goto("https://x.com/home", timeout=60000)
        time.sleep(3)
        
        log_info("=" * 50)
        log_info("開いたブラウザでXにログインしてください。")
        log_info("ログイン完了後、このターミナルでEnterキーを押してください。")
        log_info("=" * 50)
        input()
        
        log_success("ログイン情報を保存しました！")
        context.close()

    def run_cycle(self, page):
        try:
            log_info("タイムラインのチェックを開始します...")
            page.goto("https://x.com/home", timeout=60000, wait_until='networkidle')
            log_debug("ページ遷移完了、ネットワーク待機OK")

            for i in range(3):
                scroll_msg = "スクロール実行 (" + str(i + 1) + "/3)"
                log_debug(scroll_msg)
                page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                time.sleep(random.uniform(2, 4))

            powerful_mode = self.config.getboolean('Behavior', 'POWERFUL_MODE', False)
            target_keywords = self.config.getlist('Keywords', 'TARGET_KEYWORDS')
            exclude_keywords = self.config.getlist('Keywords', 'EXCLUDE_KEYWORDS')
            target_count = self.config.getint('Limits', 'LIKES_PER_CYCLE_TARGET', 5)
            like_prob = self.config.getint('Behavior', 'LIKE_PROBABILITY', 90)

            mode_str = "ON" if powerful_mode else "OFF"
            log_debug("全力モード: " + mode_str)
            log_debug("ターゲットキーワード: " + str(target_keywords))

            tweets = page.locator("article[data-testid='tweet']").all()
            log_info(str(len(tweets)) + "件のツイートを検出しました。")
            liked_count = 0
            processed_tweets = 0

            for tweet in tweets:
                if liked_count >= target_count:
                    break
                processed_tweets += 1
                try:
                    user_locator = tweet.locator("[data-testid='User-Name'] span:has-text('@')")
                    if user_locator.count() == 0:
                        continue
                    user = user_locator.first.inner_text()
                    
                    if user.lower() in self.liked_users:
                        continue

                    text_locator = tweet.locator("[data-testid='tweetText']")
                    if text_locator.count() == 0:
                        continue
                    text = text_locator.inner_text()

                    should_like = False
                    if powerful_mode:
                        has_exclude = any(k in text for k in exclude_keywords)
                        should_like = not has_exclude
                    else:
                        has_target = any(k in text for k in target_keywords)
                        has_exclude = any(k in text for k in exclude_keywords)
                        should_like = has_target and not has_exclude

                    if should_like and random.randint(1, 100) <= like_prob:
                        btn = tweet.locator("[data-testid='like']")
                        if btn.count() > 0:
                            btn.first.click()
                            newline_char = '\n'
                            preview = text[:30].replace(newline_char, ' ')
                            success_msg = "いいね成功: " + user + " -> 「" + preview + "...」"
                            log_success(success_msg)
                            self.liked_users[user.lower()] = datetime.now().isoformat()
                            self._save_liked_users()
                            liked_count += 1
                            time.sleep(random.randint(10, 20))
                except Exception as e:
                    error_msg = "ツイート" + str(processed_tweets) + "の処理中にエラー: " + str(e)
                    log_debug(error_msg)
                    continue
            
            result_msg = "サイクル完了: " + str(liked_count) + "件のいいねを実行しました。"
            log_info(result_msg)
        except Exception as e:
            error_msg = "サイクル実行中に致命的なエラーが発生しました: " + str(e)
            log_error(error_msg)

def main():
    app = PrometheusFinal()
    app.run()

if __name__ == "__main__":
    main()
