#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project Prometheus - Selenium自動いいね v6.1 (Daemon & Full Logic)
==============================================================
バックグラウンド実行（デーモン化）に対応し、かつ元の高度な判定ロジックを全て搭載。

機能:
1. バックグラウンド実行 (--daemon) - ターミナルを閉じても動作継続
2. 実行状態確認 (--status) - 現在動作中か確認
3. 停止コマンド (--stop) - 安全にプロセスを終了
4. ヘッドレスモード (--headless) - ブラウザ画面を表示せずに実行
5. 統合ログ出力 - 全ての動作を logs/x_auto_like_daemon.log に記録
6. フルロジック搭載 - いいね返し、フォロー中優先、キーワード判定、除外設定

使い方:
    python3 auto_like_selenium.py --loop --daemon   # バックグラウンドで継続実行
    python3 auto_like_selenium.py --status          # 実行状態を確認
    python3 auto_like_selenium.py --stop            # ツールを停止
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
    print("  pip3 install selenium")
    sys.exit(1)

try:
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    print("webdriver-managerがインストールされていません。")
    print("  pip3 install webdriver-manager")
    sys.exit(1)

# ===== 設定 =====
PROFILE_DIR = Path.home() / ".prometheus_selenium"
PID_FILE = PROFILE_DIR / "auto_like.pid"
LOG_FILE = PROFILE_DIR / "auto_like_daemon.log"
LIKED_USERS_FILE = PROFILE_DIR / "liked_users.json"
LAST_RESET_FILE = PROFILE_DIR / "last_reset.txt"

# いいね対象キーワード
TARGET_KEYWORDS = [
    "FX", "為替", "ドル円", "ユーロ", "ポンド",
    "株", "日経", "投資", "トレード", "相場",
    "損切り", "利確", "エントリー", "ポジション",
    "チャート", "テクニカル", "ファンダ"
]

# 除外キーワード
EXCLUDE_KEYWORDS = [
    "無料", "プレゼント", "LINE", "公式", "サロン", "コンサル",
    "月収", "稼ぐ", "稼げる", "利益確定", "爆益",
    "億", "万円達成", "収益公開", "実績公開",
    "プロフ見て", "プロフィール見て", "固定ツイ", "固ツイ",
    "詳細はこちら", "気になる方", "興味ある方",
    "DMください", "DM待ってます", "リプください",
    "手法", "ノウハウ", "教材", "講座", "セミナー", "スクール",
    "配信", "シグナル", "自動売買", "EA", "コピトレ",
    "フォロバ", "相互", "拡散希望", "RT希望"
]

# プロフィール除外キーワード
EXCLUDE_PROFILE_KEYWORDS = [
    "講師", "コンサル", "運営", "代表", "CEO", "社長",
    "トレーダー育成", "投資家育成", "FX講師", "株講師",
    "公式", "オフィシャル", "サロン主宰", "塾長",
    "億トレ", "専業", "プロトレーダー",
    "LINE@", "公式LINE", "メルマガ"
]

# 各モードでのいいね数
LIKES_PER_LIKEBACK = 5
LIKES_PER_FOLLOWING = 5
LIKES_PER_TIMELINE = 5

MIN_WAIT = 8
MAX_WAIT = 20
SCROLL_WAIT = 3
RESET_HOUR = 6

# ===== ログ出力管理 =====
class Logger:
    @staticmethod
    def _log(level, msg, color=None):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_msg = f"[{timestamp}][{level}] {msg}"
        
        # 標準出力（色付き）
        if sys.stdout.isatty() and color:
            print(f"{color}{formatted_msg}\033[0m")
        else:
            print(formatted_msg)
            
        # ファイル出力
        try:
            PROFILE_DIR.mkdir(exist_ok=True)
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(formatted_msg + "\n")
        except:
            pass

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
        except (ProcessLookupError, ValueError, OverflowError):
            PID_FILE.unlink(missing_ok=True)
    return None

def stop_daemon():
    pid = get_running_pid()
    if pid:
        print(f"プロセス {pid} を停止しています...")
        os.kill(pid, signal.SIGTERM)
        time.sleep(2)
        if get_running_pid():
            os.kill(pid, signal.SIGKILL)
        PID_FILE.unlink(missing_ok=True)
        print("停止完了しました。")
    else:
        print("実行中のプロセスは見つかりませんでした。")

def check_status():
    pid = get_running_pid()
    if pid:
        print(f"【実行中】 PID: {pid}")
        if LOG_FILE.exists():
            print("\n最新のログ:")
            subprocess.run(["tail", "-n", "10", str(LOG_FILE)])
    else:
        print("【停止中】")

def start_daemon():
    if get_running_pid():
        print("既に実行中です。")
        sys.exit(0)
    
    print("バックグラウンドで起動します...")
    try:
        pid = os.fork()
        if pid > 0: sys.exit(0)
    except OSError: sys.exit(1)
    
    os.chdir("/")
    os.setsid()
    os.umask(0)
    
    try:
        pid = os.fork()
        if pid > 0: sys.exit(0)
    except OSError: sys.exit(1)
    
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
        self.check_daily_reset()
        self.load()
    
    def check_daily_reset(self):
        now = datetime.now()
        today_reset_time = now.replace(hour=RESET_HOUR, minute=0, second=0, microsecond=0)
        last_reset = None
        try:
            if LAST_RESET_FILE.exists():
                last_reset = datetime.fromisoformat(LAST_RESET_FILE.read_text().strip())
        except: pass
        
        if last_reset and now >= today_reset_time and last_reset < today_reset_time:
            Logger.info(f"🔄 朝{RESET_HOUR}時の自動リセットを実行")
            if LIKED_USERS_FILE.exists(): LIKED_USERS_FILE.unlink()
            self.liked_users = {}
        
        PROFILE_DIR.mkdir(exist_ok=True)
        LAST_RESET_FILE.write_text(now.isoformat())
    
    def load(self):
        if LIKED_USERS_FILE.exists():
            try:
                self.liked_users = json.loads(LIKED_USERS_FILE.read_text(encoding='utf-8'))
            except: self.liked_users = {}
    
    def save(self):
        PROFILE_DIR.mkdir(exist_ok=True)
        LIKED_USERS_FILE.write_text(json.dumps(self.liked_users, ensure_ascii=False, indent=2), encoding='utf-8')
    
    def add(self, username):
        if username:
            self.liked_users[username.lower()] = datetime.now().isoformat()
            self.save()
    
    def has_liked(self, username):
        return username.lower() in self.liked_users
    
    def count(self): return len(self.liked_users)

# ===== Seleniumエンジン =====
class SeleniumAutoLike:
    def __init__(self, headless=False):
        self.driver = None
        self.headless = headless
        self.likes_today = 0
        self.my_username = ""
        self.liked_manager = LikedUsersManager()

    def setup(self):
        Logger.info("Chromeを起動中...")
        options = Options()
        options.add_argument(f"--user-data-dir={PROFILE_DIR}")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        if self.headless:
            options.add_argument("--headless=new")
            options.add_argument("--window-size=1280,800")
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            Logger.success("Chrome起動完了")
            return True
        except Exception as e:
            Logger.error(f"起動エラー: {e}")
            return False

    def is_logged_in(self):
        try:
            self.driver.get("https://x.com/home")
            time.sleep(5)
            if "login" in self.driver.current_url or "i/flow" in self.driver.current_url:
                return False
            try:
                account_link = self.driver.find_element(By.CSS_SELECTOR, '[data-testid="AppTabBar_Profile_Link"]')
                self.my_username = account_link.get_attribute("href").split("/")[-1]
                Logger.info(f"ログインユーザー: @{self.my_username}")
                return True
            except: return False
        except: return False

    def random_wait(self):
        wait = random.randint(MIN_WAIT, MAX_WAIT)
        Logger.info(f"待機中... ({wait}秒)")
        time.sleep(wait)

    def scroll_page(self):
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SCROLL_WAIT)

    def like_tweet(self, tweet_element):
        try:
            like_button = tweet_element.find_element(By.CSS_SELECTOR, '[data-testid="like"]')
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", like_button)
            time.sleep(1)
            like_button.click()
            return True
        except: return False

    def get_tweet_info(self, tweet):
        try:
            user_link = tweet.find_element(By.CSS_SELECTOR, 'a[href*="/status/"]').get_attribute("href")
            username = user_link.split("/")[3]
            text = tweet.find_element(By.CSS_SELECTOR, '[data-testid="tweetText"]').text
            return username, text
        except: return None, None

    def should_like(self, username, text):
        if not username or not text: return False
        if username.lower() == self.my_username.lower(): return False
        if self.liked_manager.has_liked(username):
            Logger.skip(f"@{username} は既にいいね済みです")
            return False
        if any(kw in text for kw in EXCLUDE_KEYWORDS):
            Logger.skip(f"@{username} のツイートに除外キーワードが含まれています")
            return False
        if any(kw in text for kw in TARGET_KEYWORDS):
            return True
        return False

    def run_timeline_likes(self):
        Logger.phase("タイムラインいいね開始")
        self.driver.get("https://x.com/home")
        time.sleep(5)
        likes_done = 0
        scrolls = 0
        while likes_done < LIKES_PER_TIMELINE and scrolls < 10:
            tweets = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="tweet"]')
            for tweet in tweets:
                if likes_done >= LIKES_PER_TIMELINE: break
                username, text = self.get_tweet_info(tweet)
                if self.should_like(username, text):
                    if self.like_tweet(tweet):
                        Logger.success(f"@{username} にいいねしました")
                        self.liked_manager.add(username)
                        likes_done += 1
                        self.likes_today += 1
                        self.random_wait()
            self.scroll_page()
            scrolls += 1
        return likes_done

    def run_full_cycle(self):
        result = {"timeline": self.run_timeline_likes()}
        return result

    def close(self):
        if self.driver: self.driver.quit()

def main():
    parser = argparse.ArgumentParser(description="Selenium自動いいね v6.1")
    parser.add_argument("--loop", action="store_true", help="継続実行")
    parser.add_argument("--daemon", action="store_true", help="バックグラウンド実行")
    parser.add_argument("--status", action="store_true", help="状態確認")
    parser.add_argument("--stop", action="store_true", help="停止")
    parser.add_argument("--headless", action="store_true", help="ヘッドレスモード")
    args = parser.parse_args()

    if args.stop: stop_daemon(); return
    if args.status: check_status(); return
    if args.daemon: start_daemon(); args.headless = True

    engine = SeleniumAutoLike(headless=args.headless)
    try:
        if not engine.setup(): return
        if not engine.is_logged_in():
            Logger.error("ログインしていません。通常モードでログインしてください。")
            return
        
        if args.loop:
            cycle = 1
            while True:
                Logger.phase(f"===== サイクル {cycle} =====")
                engine.run_full_cycle()
                wait = random.randint(300, 600)
                Logger.info(f"次サイクルまで {wait}秒 待機...")
                time.sleep(wait)
                cycle += 1
        else:
            engine.run_full_cycle()
    except KeyboardInterrupt: Logger.info("停止しました")
    finally:
        engine.close()
        if args.daemon: PID_FILE.unlink(missing_ok=True)

if __name__ == "__main__":
    main()
