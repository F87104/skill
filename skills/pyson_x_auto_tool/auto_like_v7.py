import time
import random
import sys
import json
import configparser
from pathlib import Path
from datetime import datetime
import os

# ==========================================
# Project Prometheus v7.0 [REMOTE CONNECT]
# ブラウザを直接起動せず、起動済みのChromeに接続する新方式
# ==========================================

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import WebDriverException
except ImportError:
    print("Error: Selenium is not installed. Run: pip3 install selenium")
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

class PrometheusV7:
    def __init__(self, config_path=None):
        self.config = Config(config_path)
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

    def connect_to_chrome(self):
        log_info("起動中のChromeに接続を試みています (port: 9222)...")
        options = Options()
        options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        
        try:
            # ChromeDriverのパスを自動で見つけるか、標準的な場所を指定
            self.driver = webdriver.Chrome(options=options)
            log_success("Chromeへの接続に成功しました！")
        except Exception as e:
            log_error("Chromeに接続できません。先にChromeをデバッグモードで起動してください。")
            log_error(f"詳細: {e}")
            sys.exit(1)

    def run_cycle(self):
        try:
            log_info("タイムラインをチェック中...")
            self.driver.get("https://x.com/home")
            time.sleep(5)

            target_keywords = self.config.getlist('Keywords', 'TARGET_KEYWORDS', [])
            exclude_keywords = self.config.getlist('Keywords', 'EXCLUDE_KEYWORDS', [])
            target_count = self.config.getint('Limits', 'LIKES_PER_CYCLE_TARGET', 10)
            like_prob = self.config.getint('Behavior', 'LIKE_PROBABILITY', 90)

            tweets = self.driver.find_elements(By.XPATH, "//article[@data-testid='tweet']")
            liked_count = 0

            for tweet in tweets:
                if liked_count >= target_count: break
                try:
                    user = tweet.find_element(By.XPATH, ".//div[@data-testid='User-Name']//span[contains(text(), '@')]").text
                    if user.lower() in self.liked_users: continue

                    text = tweet.find_element(By.XPATH, ".//div[@data-testid='tweetText']").text
                    
                    if any(k in text for k in target_keywords) and not any(k in text for k in exclude_keywords):
                        if random.randint(1, 100) <= like_prob:
                            btn = tweet.find_element(By.XPATH, ".//div[@data-testid='like']")
                            self.driver.execute_script("arguments[0].click();", btn)
                            log_success(f"いいね成功: {user}")
                            self.liked_users[user.lower()] = datetime.now().isoformat()
                            self._save_liked_users()
                            liked_count += 1
                            time.sleep(random.randint(10, 20))
                except: continue
            
            log_info(f"サイクル完了: {liked_count}件のいいねをしました。")
        except Exception as e:
            log_error(f"エラーが発生しました: {e}")

def main():
    log_info("Project Prometheus v7.0 [REMOTE CONNECT] 起動")
    app = PrometheusV7()
    app.connect_to_chrome()
    
    try:
        while True:
            app.run_cycle()
            wait = random.randint(300, 600)
            log_info(f"待機中: {wait//60}分...")
            time.sleep(wait)
    except KeyboardInterrupt:
        log_info("停止します。")

if __name__ == "__main__":
    main()
