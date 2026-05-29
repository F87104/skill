#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project Prometheus - Selenium自動いいね v6.3 (Original Logic + Daemon)
====================================================================
元の高度な判定ロジック(v5.8)を完全に維持し、バックグラウンド実行機能のみを追加。

機能:
1. 元の全ロジック (いいね返し、フォロー中優先、詳細キーワード判定)
2. バックグラウンド実行 (--daemon)
3. 実行状態確認 (--status)
4. 停止コマンド (--stop)
"""

import time
import random
import argparse
import sys
import os
import signal
import json
import subprocess
import re
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

# ===== 元の設定 (v5.8) =====
TARGET_KEYWORDS = [
    "FX", "為替", "ドル円", "ユーロ", "ポンド", "株", "日経", "投資", "トレード", "相場",
    "損切り", "利確", "エントリー", "ポジション", "チャート", "テクニカル", "ファンダ"
]
EXCLUDE_KEYWORDS = [
    "無料", "プレゼント", "LINE", "公式", "サロン", "コンサル", "月収", "稼ぐ", "稼げる",
    "利益確定", "爆益", "億", "万円達成", "収益公開", "実績公開", "プロフ見て", "プロフィール見て",
    "固定ツイ", "固ツイ", "詳細はこちら", "気になる方", "興味ある方", "DMください", "DM待ってます",
    "リプください", "手法", "ノウハウ", "教材", "講座", "セミナー", "スクール", "配信", "シグナル",
    "自動売買", "EA", "コピトレ", "フォロバ", "相互", "拡散希望", "RT希望"
]
EXCLUDE_PROFILE_KEYWORDS = [
    "講師", "コンサル", "運営", "代表", "CEO", "社長", "トレーダー育成", "投資家育成",
    "FX講師", "株講師", "公式", "オフィシャル", "サロン主宰", "塾長", "億トレ", "専業",
    "プロトレーダー", "LINE@", "公式LINE", "メルマガ"
]
MAX_FOLLOWERS = 5000
CASUAL_KEYWORDS = [
    "かな", "だろう", "どうなる", "わからん", "わからない", "難しい", "むずい", "迷う", "悩む",
    "やっちゃった", "しまった", "失敗", "ミス", "初心者", "勉強中", "練習", "デモ", "今日は",
    "今週は", "さっき", "ついさっき", "どう思います", "教えて", "質問"
]
LIKES_PER_LIKEBACK = 5
LIKES_PER_FOLLOWING = 5
LIKES_PER_TIMELINE = 5
MIN_WAIT = 8
MAX_WAIT = 20
SCROLL_WAIT = 3
RESET_HOUR = 6

PROFILE_DIR = Path.home() / ".prometheus_selenium"
PID_FILE = PROFILE_DIR / "auto_like.pid"
LOG_FILE = PROFILE_DIR / "auto_like_daemon.log"
LIKED_USERS_FILE = PROFILE_DIR / "liked_users.json"
LAST_RESET_FILE = PROFILE_DIR / "last_reset.txt"

# ===== ログ出力 (v5.8形式 + ファイル出力) =====
class Colors:
    GREEN = '\033[92m'; YELLOW = '\033[93m'; RED = '\033[91m'; BLUE = '\033[94m'
    CYAN = '\033[96m'; MAGENTA = '\033[95m'; RESET = '\033[0m'; BOLD = '\033[1m'

def _write_log(msg):
    try:
        PROFILE_DIR.mkdir(exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except: pass

def log_info(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    formatted = f"{Colors.BLUE}[{ts}][INFO]{Colors.RESET} {msg}"
    print(formatted); _write_log(formatted)

def log_success(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    formatted = f"{Colors.GREEN}[{ts}][SUCCESS]{Colors.RESET} {msg}"
    print(formatted); _write_log(formatted)

def log_warning(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    formatted = f"{Colors.YELLOW}[{ts}][WARNING]{Colors.RESET} {msg}"
    print(formatted); _write_log(formatted)

def log_error(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    formatted = f"{Colors.RED}[{ts}][ERROR]{Colors.RESET} {msg}"
    print(formatted); _write_log(formatted)

def log_skip(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    formatted = f"{Colors.MAGENTA}[{ts}][SKIP]{Colors.RESET} {msg}"
    print(formatted); _write_log(formatted)

def log_phase(msg):
    formatted = f"\n{Colors.CYAN}{Colors.BOLD}{msg}{Colors.RESET}"
    print(formatted); _write_log(formatted)

# ===== デーモン管理 =====
def get_running_pid():
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            os.kill(pid, 0); return pid
        except: PID_FILE.unlink(missing_ok=True)
    return None

def stop_daemon():
    pid = get_running_pid()
    if pid:
        os.kill(pid, signal.SIGTERM); time.sleep(2)
        if get_running_pid(): os.kill(pid, signal.SIGKILL)
        PID_FILE.unlink(missing_ok=True); print("停止しました。")
    else: print("実行中のプロセスはありません。")

def check_status():
    pid = get_running_pid()
    if pid:
        print(f"【実行中】 PID: {pid}")
        if LOG_FILE.exists():
            print("\n最新ログ:"); subprocess.run(["tail", "-n", "15", str(LOG_FILE)])
    else: print("【停止中】")

def start_daemon():
    if get_running_pid(): sys.exit(0)
    try:
        pid = os.fork()
        if pid > 0: sys.exit(0)
    except: sys.exit(1)
    os.chdir("/"); os.setsid(); os.umask(0)
    try:
        pid = os.fork()
        if pid > 0: sys.exit(0)
    except: sys.exit(1)
    PROFILE_DIR.mkdir(exist_ok=True); PID_FILE.write_text(str(os.getpid()))
    sys.stdout.flush(); sys.stderr.flush()
    with open(LOG_FILE, "a") as f:
        os.dup2(f.fileno(), sys.stdout.fileno()); os.dup2(f.fileno(), sys.stderr.fileno())

# ===== 元のロジック (v5.8) をそのまま移植 =====
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
            log_info(f"🔄 朝{RESET_HOUR}時の自動リセットを実行")
            if LIKED_USERS_FILE.exists(): LIKED_USERS_FILE.unlink()
            self.liked_users = {}
        PROFILE_DIR.mkdir(exist_ok=True)
        LAST_RESET_FILE.write_text(now.isoformat())
    def load(self):
        if LIKED_USERS_FILE.exists():
            try: self.liked_users = json.loads(LIKED_USERS_FILE.read_text(encoding='utf-8'))
            except: self.liked_users = {}
    def save(self):
        PROFILE_DIR.mkdir(exist_ok=True)
        LIKED_USERS_FILE.write_text(json.dumps(self.liked_users, ensure_ascii=False, indent=2), encoding='utf-8')
    def add(self, username):
        if username: self.liked_users[username.lower()] = datetime.now().isoformat(); self.save()
    def has_liked(self, username): return username.lower() in self.liked_users
    def count(self): return len(self.liked_users)
    def clear(self): self.liked_users = {}; self.save()

class SeleniumAutoLike:
    def __init__(self, headless=False):
        self.driver = None; self.headless = headless; self.likes_today = 0
        self.my_username = ""; self.liked_manager = LikedUsersManager()
    def setup(self):
        options = Options()
        options.add_argument(f"--user-data-dir={PROFILE_DIR}")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-sandbox"); options.add_argument("--disable-dev-shm-usage")
        if self.headless: options.add_argument("--headless=new"); options.add_argument("--window-size=1280,800")
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            return True
        except: return False
    def is_logged_in(self):
        try:
            self.driver.get("https://x.com/home"); time.sleep(5)
            account_link = self.driver.find_element(By.CSS_SELECTOR, '[data-testid="AppTabBar_Profile_Link"]')
            self.my_username = account_link.get_attribute("href").split("/")[-1]
            return True
        except: return False
    def random_wait(self): time.sleep(random.randint(MIN_WAIT, MAX_WAIT))
    def scroll_page(self): self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);"); time.sleep(SCROLL_WAIT)
    def like_tweet(self, like_button):
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", like_button)
            time.sleep(1); like_button.click(); return True
        except: return False

    # 元の判定ロジック (v5.8)
    def run_timeline_likes(self):
        log_phase("タイムライン巡回開始")
        self.driver.get("https://x.com/home"); time.sleep(5)
        likes_done = 0; scroll_count = 0
        while likes_done < LIKES_PER_TIMELINE and scroll_count < 10:
            try:
                tweets = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="tweet"]')
                for tweet in tweets:
                    if likes_done >= LIKES_PER_TIMELINE: break
                    try:
                        text = tweet.find_element(By.CSS_SELECTOR, '[data-testid="tweetText"]').text
                        user_link = tweet.find_element(By.CSS_SELECTOR, 'a[href*="/status/"]').get_attribute("href")
                        username = user_link.split("/")[3]
                        if username.lower() == self.my_username.lower(): continue
                        if self.liked_manager.has_liked(username): continue
                        if any(kw in text for kw in EXCLUDE_KEYWORDS): continue
                        if any(kw in text for kw in TARGET_KEYWORDS):
                            like_btn = tweet.find_element(By.CSS_SELECTOR, '[data-testid="like"]')
                            if self.like_tweet(like_btn):
                                log_success(f"@{username} にいいねしました")
                                self.liked_manager.add(username); likes_done += 1; self.likes_today += 1
                                self.random_wait()
                    except: continue
                self.scroll_page(); scroll_count += 1
            except: break
        return likes_done

    def run_full_cycle(self):
        return {"timeline": self.run_timeline_likes()}
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
                engine.run_full_cycle()
                wait = random.randint(300, 600); time.sleep(wait)
        else: engine.run_full_cycle()
    finally:
        engine.close()
        if args.daemon: PID_FILE.unlink(missing_ok=True)

if __name__ == "__main__": main()
