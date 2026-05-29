import time
import random
import argparse
import sys
import json
import configparser
from pathlib import Path
from datetime import datetime
import os

# ==========================================
# Project Prometheus v6.0 [IMMORTAL EDITION]
# ブラウザの切断に強く、自動で立ち直る不死身バージョン
# ==========================================

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import WebDriverException
except ImportError:
    print("Error: Selenium is not installed.")
    sys.exit(1)

try:
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    print("Error: webdriver-manager is not installed.")
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

def log_warning(msg):
    print(f"{Colors.YELLOW}[{datetime.now().strftime('%H:%M:%S')}][WARNING]{Colors.RESET} {msg}")

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

class SeleniumAutoLikeV6:
    def __init__(self, headless=False, config_path=None):
        self.config = Config(config_path)
        self.headless = headless
        self.driver = None
        self.liked_users_file = Path(self.config.get('General', 'LIKED_USERS_FILE', '~/.prometheus_selenium/liked_users.json')).expanduser()
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

    def _setup_driver(self):
        log_info("ブラウザを起動しています...")
        options = Options()
        if self.headless:
            options.add_argument('--headless=new')
        
        # Mac安定化の決定版オプション
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        profile_dir = Path(self.config.get('General', 'PROFILE_DIR', '~/.prometheus_selenium')).expanduser()
        options.add_argument(f'--user-data-dir={profile_dir}')
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.set_page_load_timeout(30)
            log_success("ブラウザ起動成功")
        except Exception as e:
            log_error(f"ブラウザ起動失敗: {e}")
            raise

    def run_cycle(self):
        # 毎回ブラウザの状態を確認し、死んでいたら再起動する
        try:
            if self.driver is None:
                self._setup_driver()
            else:
                # ブラウザが生きているかチェック
                self.driver.current_url
        except:
            log_warning("ブラウザが切断されています。再起動します...")
            self._setup_driver()

        try:
            log_info("タイムラインを取得中...")
            self.driver.get("https://x.com/home")
            time.sleep(10) # 読み込み待ちを長めに

            tweets = self.driver.find_elements(By.XPATH, "//article[@data-testid='tweet']")
            liked_count = 0
            target = self.config.getint('Limits', 'LIKES_PER_CYCLE_TARGET', 10)
            
            target_keywords = self.config.getlist('Keywords', 'TARGET_KEYWORDS', [])
            exclude_keywords = self.config.getlist('Keywords', 'EXCLUDE_KEYWORDS', [])

            for tweet in tweets:
                if liked_count >= target: break
                try:
                    user = tweet.find_element(By.XPATH, ".//div[@data-testid='User-Name']//span[contains(text(), '@')]").text
                    if user.lower() in self.liked_users: continue

                    text = tweet.find_element(By.XPATH, ".//div[@data-testid='tweetText']").text
                    if any(k in text for k in target_keywords) and not any(k in text for k in exclude_keywords):
                        if random.randint(1, 100) <= self.config.getint('Behavior', 'LIKE_PROBABILITY', 90):
                            btn = tweet.find_element(By.XPATH, ".//div[@data-testid='like']")
                            self.driver.execute_script("arguments[0].click();", btn)
                            log_success(f"いいね: {user}")
                            self.liked_users[user.lower()] = datetime.now().isoformat()
                            self._save_liked_users()
                            liked_count += 1
                            time.sleep(random.randint(10, 30))
                except: continue
            
            log_info(f"サイクル完了: {liked_count}件")
        except Exception as e:
            log_error(f"エラー発生: {e}")
            if self.driver:
                try: self.driver.quit()
                except: pass
                self.driver = None

    def close(self):
        if self.driver:
            try: self.driver.quit()
            except: pass

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--headless', action='store_true')
    parser.add_argument('--loop', action='store_true')
    args, _ = parser.parse_known_args()

    log_info("Project Prometheus v6.0 [IMMORTAL] 起動")
    app = SeleniumAutoLikeV6(headless=args.headless)
    
    try:
        while True:
            app.run_cycle()
            if not args.loop: break
            wait = random.randint(300, 600)
            log_info(f"待機中: {wait//60}分...")
            time.sleep(wait)
    except KeyboardInterrupt:
        log_info("停止します")
    finally:
        app.close()

if __name__ == "__main__":
    main()
