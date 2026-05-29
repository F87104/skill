#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project Prometheus - Selenium自動いいね v6.2 (Scroll & Deduplication)
==================================================================
スクロール処理の強化と重複判定の防止により、効率的に新しいツイートをいいね。

改善点:
1. スクロール処理の最適化 - 判定ごとに適切にスクロールし、新しいツイートを読み込み
2. 重複判定の防止 - 1サイクル内で同じツイートを二度判定しない
3. ターゲットキーワードの調整 - より広範な投資関連ワードに対応
"""

import time
import random
import argparse
import sys
import os
import signal
import json
import subprocess
from pathlib import Path
from datetime import datetime

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
except ImportError:
    print("Seleniumがインストールされていません。")
    sys.exit(1)

try:
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    print("webdriver-managerがインストールされていません。")
    sys.exit(1)

# ===== 設定 =====
PROFILE_DIR = Path.home() / ".prometheus_selenium"
PID_FILE = PROFILE_DIR / "auto_like.pid"
LOG_FILE = PROFILE_DIR / "auto_like_daemon.log"
LIKED_USERS_FILE = PROFILE_DIR / "liked_users.json"
LAST_RESET_FILE = PROFILE_DIR / "last_reset.txt"

# ターゲットキーワード（より広範に）
TARGET_KEYWORDS = [
    "FX", "為替", "ドル円", "ユーロ", "ポンド", "豪ドル",
    "株", "日経", "投資", "トレード", "相場", "チャート",
    "損切り", "利確", "エントリー", "ポジション", "含み益", "含み損",
    "テクニカル", "ファンダ", "米国株", "仮想通貨", "ビットコイン",
    "先物", "オプション", "資産運用", "積立", "NISA"
]

# 除外キーワード
EXCLUDE_KEYWORDS = [
    "無料", "プレゼント", "LINE", "公式", "サロン", "コンサル",
    "月収", "稼ぐ", "稼げる", "利益確定", "爆益", "億",
    "プロフ見て", "プロフィール見て", "固定ツイ", "固ツイ",
    "詳細はこちら", "DMください", "リプください", "自動売買", "EA"
]

LIKES_PER_TIMELINE = 10
MIN_WAIT = 5
MAX_WAIT = 12
SCROLL_WAIT = 2
RESET_HOUR = 6

# ===== ログ出力管理 =====
class Logger:
    @staticmethod
    def _log(level, msg, color=None):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_msg = f"[{timestamp}][{level}] {msg}"
        if sys.stdout.isatty() and color:
            print(f"{color}{formatted_msg}\033[0m")
        else:
            print(formatted_msg)
        try:
            PROFILE_DIR.mkdir(exist_ok=True)
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(formatted_msg + "\n")
        except: pass

    @staticmethod
    def info(msg): Logger._log("INFO", msg, "\033[94m")
    @staticmethod
    def success(msg): Logger._log("SUCCESS", msg, "\033[92m")
    @staticmethod
    def warning(msg): Logger._log("WARNING", msg, "\033[93m")
    @staticmethod
    def error(msg): Logger._log("ERROR", msg, "\033[91m")
    @staticmethod
    def skip(msg): Logger._log("SKIP", msg, "\033[95m")
    @staticmethod
    def phase(msg):
        print(f"\n\033[96m\033[1m{msg}\033[0m")
        Logger._log("PHASE", msg)

# ===== プロセス管理 =====
def get_running_pid():
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            os.kill(pid, 0)
            return pid
        except: PID_FILE.unlink(missing_ok=True)
    return None

def stop_daemon():
    pid = get_running_pid()
    if pid:
        os.kill(pid, signal.SIGTERM)
        time.sleep(2)
        if get_running_pid(): os.kill(pid, signal.SIGKILL)
        PID_FILE.unlink(missing_ok=True)
        print("停止完了。")
    else: print("実行中のプロセスなし。")

def check_status():
    pid = get_running_pid()
    if pid:
        print(f"【実行中】 PID: {pid}")
        if LOG_FILE.exists():
            print("\n最新ログ:")
            subprocess.run(["tail", "-n", "15", str(LOG_FILE)])
    else: print("【停止中】")

def start_daemon():
    if get_running_pid(): sys.exit(0)
    try:
        pid = os.fork()
        if pid > 0: sys.exit(0)
    except: sys.exit(1)
    os.chdir("/")
    os.setsid()
    os.umask(0)
    try:
        pid = os.fork()
        if pid > 0: sys.exit(0)
    except: sys.exit(1)
    PROFILE_DIR.mkdir(exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))
    sys.stdout.flush()
    sys.stderr.flush()
    with open(LOG_FILE, "a") as f:
        os.dup2(f.fileno(), sys.stdout.fileno())
        os.dup2(f.fileno(), sys.stderr.fileno())

# ===== 履歴管理 =====
class LikedUsersManager:
    def __init__(self):
        self.liked_users = {}
        self.load()
    def load(self):
        if LIKED_USERS_FILE.exists():
            try: self.liked_users = json.loads(LIKED_USERS_FILE.read_text(encoding='utf-8'))
            except: self.liked_users = {}
    def save(self):
        PROFILE_DIR.mkdir(exist_ok=True)
        LIKED_USERS_FILE.write_text(json.dumps(self.liked_users, ensure_ascii=False, indent=2), encoding='utf-8')
    def add(self, username):
        if username:
            self.liked_users[username.lower()] = datetime.now().isoformat()
            self.save()
    def has_liked(self, username): return username.lower() in self.liked_users

# ===== Seleniumエンジン =====
class SeleniumAutoLike:
    def __init__(self, headless=False):
        self.driver = None
        self.headless = headless
        self.my_username = ""
        self.liked_manager = LikedUsersManager()
        self.processed_tweets = set() # 1サイクル内の重複防止

    def setup(self):
        options = Options()
        options.add_argument(f"--user-data-dir={PROFILE_DIR}")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        if self.headless:
            options.add_argument("--headless=new")
            options.add_argument("--window-size=1280,800")
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            return True
        except: return False

    def is_logged_in(self):
        try:
            self.driver.get("https://x.com/home")
            time.sleep(5)
            account_link = self.driver.find_element(By.CSS_SELECTOR, '[data-testid="AppTabBar_Profile_Link"]')
            self.my_username = account_link.get_attribute("href").split("/")[-1]
            return True
        except: return False

    def scroll_down(self, pixels=500):
        self.driver.execute_script(f"window.scrollBy(0, {pixels});")
        time.sleep(SCROLL_WAIT)

    def run_timeline_likes(self):
        Logger.phase("タイムライン巡回開始")
        self.driver.get("https://x.com/home")
        time.sleep(5)
        likes_done = 0
        attempts = 0
        self.processed_tweets.clear()

        while likes_done < LIKES_PER_TIMELINE and attempts < 30:
            tweets = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="tweet"]')
            found_new = False
            
            for tweet in tweets:
                try:
                    # ツイートの一意なID（またはテキストのハッシュ）で重複チェック
                    tweet_text = tweet.find_element(By.CSS_SELECTOR, '[data-testid="tweetText"]').text
                    tweet_id = hash(tweet_text)
                    
                    if tweet_id in self.processed_tweets: continue
                    self.processed_tweets.add(tweet_id)
                    found_new = True
                    
                    user_link = tweet.find_element(By.CSS_SELECTOR, 'a[href*="/status/"]').get_attribute("href")
                    username = user_link.split("/")[3]
                    
                    if username.lower() == self.my_username.lower(): continue
                    if self.liked_manager.has_liked(username):
                        Logger.skip(f"@{username} は既にいいね済み")
                        continue
                    
                    if any(kw in tweet_text for kw in EXCLUDE_KEYWORDS):
                        Logger.skip(f"@{username} 除外ワードあり")
                        continue
                        
                    if any(kw in tweet_text for kw in TARGET_KEYWORDS):
                        like_button = tweet.find_element(By.CSS_SELECTOR, '[data-testid="like"]')
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", like_button)
                        time.sleep(1)
                        like_button.click()
                        Logger.success(f"@{username} にいいねしました")
                        self.liked_manager.add(username)
                        likes_done += 1
                        time.sleep(random.randint(MIN_WAIT, MAX_WAIT))
                        if likes_done >= LIKES_PER_TIMELINE: break
                except: continue
            
            self.scroll_down(800)
            attempts += 1
            if not found_new: self.scroll_down(1200) # 新しいのがなければ大きくスクロール

    def close(self):
        if self.driver: self.driver.quit()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--stop", action="store_true")
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    if args.stop: stop_daemon(); return
    if args.status: check_status(); return
    if args.daemon: start_daemon(); args.headless = True

    engine = SeleniumAutoLike(headless=args.headless)
    try:
        if not engine.setup(): return
        if not engine.is_logged_in(): return
        if args.loop:
            while True:
                engine.run_timeline_likes()
                wait = random.randint(300, 600)
                Logger.info(f"待機: {wait}秒")
                time.sleep(wait)
        else: engine.run_timeline_likes()
    finally:
        engine.close()
        if args.daemon: PID_FILE.unlink(missing_ok=True)

if __name__ == "__main__": main()
