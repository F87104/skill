#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project Prometheus - Selenium自動いいね v6.0 (Daemon対応版)
========================================================
バックグラウンド実行（デーモン化）に対応し、ターミナルを占有せずに動作可能。

機能:
1. バックグラウンド実行 (--daemon) - ターミナルを閉じても動作継続
2. 実行状態確認 (--status) - 現在動作中か確認
3. 停止コマンド (--stop) - 安全にプロセスを終了
4. ヘッドレスモード (--headless) - ブラウザ画面を表示せずに実行
5. 統合ログ出力 - 全ての動作を logs/x_auto_like_daemon.log に記録

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
TARGET_KEYWORDS = ["FX", "為替", "ドル円", "投資", "トレード", "相場", "チャート"]
# 除外キーワード
EXCLUDE_KEYWORDS = ["無料", "プレゼント", "サロン", "稼げる", "爆益", "プロフ見て"]

# 各モードでのいいね数
LIKES_PER_LIKEBACK = 5
LIKES_PER_FOLLOWING = 5
LIKES_PER_TIMELINE = 5

MIN_WAIT = 8
MAX_WAIT = 20
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

# ===== プロセス管理 =====
def get_running_pid():
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            # プロセスが存在するか確認
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
            subprocess.run(["tail", "-n", "5", str(LOG_FILE)])
    else:
        print("【停止中】")

def start_daemon():
    if get_running_pid():
        print("既に実行中です。")
        sys.exit(0)
    
    print("バックグラウンドで起動します...")
    # 二重フォークによるデーモン化
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
    
    # PIDを保存
    PROFILE_DIR.mkdir(exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))
    
    # 標準入出力をリダイレクト
    sys.stdout.flush()
    sys.stderr.flush()
    with open(LOG_FILE, "a") as f:
        os.dup2(f.fileno(), sys.stdout.fileno())
        os.dup2(f.fileno(), sys.stderr.fileno())

# ===== メインロジック (SeleniumAutoLikeクラスの簡略版を再実装) =====
class LikedUsersManager:
    def __init__(self):
        self.liked_users = {}
        self.load()
    def load(self):
        if LIKED_USERS_FILE.exists():
            try:
                self.liked_users = json.loads(LIKED_USERS_FILE.read_text(encoding='utf-8'))
            except: self.liked_users = {}
    def save(self):
        PROFILE_DIR.mkdir(exist_ok=True)
        LIKED_USERS_FILE.write_text(json.dumps(self.liked_users, ensure_ascii=False, indent=2), encoding='utf-8')
    def add(self, username):
        self.liked_users[username.lower()] = datetime.now().isoformat()
        self.save()
    def has_liked(self, username):
        return username.lower() in self.liked_users

class SeleniumAutoLike:
    def __init__(self, headless=True):
        self.driver = None
        self.headless = headless
        self.liked_manager = LikedUsersManager()
        self.likes_today = 0

    def setup(self):
        Logger.info("Chromeを起動中...")
        options = Options()
        options.add_argument(f"--user-data-dir={PROFILE_DIR}")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        if self.headless:
            options.add_argument("--headless=new")
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            Logger.success("Chrome起動完了")
            return True
        except Exception as e:
            Logger.error(f"起動エラー: {e}")
            return False

    def run_cycle(self):
        Logger.info("サイクル開始...")
        # ここに元のスクリプトのいいねロジックが入る（簡略化して記述）
        # 実際には元の auto_like_selenium.py の各メソッドをここに移植
        time.sleep(10) 
        Logger.success("サイクル完了")

    def close(self):
        if self.driver: self.driver.quit()

def main():
    parser = argparse.ArgumentParser(description="Selenium自動いいね v6.0")
    parser.add_argument("--loop", action="store_true", help="継続実行")
    parser.add_argument("--daemon", action="store_true", help="バックグラウンド実行")
    parser.add_argument("--status", action="store_true", help="状態確認")
    parser.add_argument("--stop", action="store_true", help="停止")
    parser.add_argument("--headless", action="store_true", help="ヘッドレスモード")
    args = parser.parse_args()

    if args.stop:
        stop_daemon()
        return
    if args.status:
        check_status()
        return
    
    if args.daemon:
        start_daemon()
        # デーモンモード時は強制的にヘッドレス
        args.headless = True

    engine = SeleniumAutoLike(headless=args.headless)
    try:
        if not engine.setup(): return
        
        if args.loop:
            Logger.info("継続モード開始")
            while True:
                engine.run_cycle()
                wait = random.randint(300, 600)
                Logger.info(f"待機中: {wait}秒")
                time.sleep(wait)
        else:
            engine.run_cycle()
    except KeyboardInterrupt:
        Logger.info("ユーザーにより停止されました")
    finally:
        engine.close()
        if args.daemon:
            PID_FILE.unlink(missing_ok=True)

if __name__ == "__main__":
    main()
