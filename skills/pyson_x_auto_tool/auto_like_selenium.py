#!/usr/bin/env python3
"""
Project Prometheus - Selenium自動いいね v5.8
============================================
いいね返し＆フォロー中優先版 + いいね済みユーザー除外 + ヘッドレスモード対応

機能:
1. いいね返し - 自分のツイートにいいねしてくれた人にいいね
2. フォロー中へのいいね - フォローしている人のツイートにいいね
3. タイムラインいいね - 一般ユーザー優先（発信者除外）
4. いいね済みユーザーを記録して除外（ファイルに保存）
5. ヘッドレスモード（バックグラウンド実行）対応

使い方:
    python3 auto_like_selenium.py --loop --headless  # バックグラウンドで継続実行
    python3 auto_like_selenium.py --loop             # 画面を表示して継続実行
"""

import time
import random
import argparse
import sys
import re
import json
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

MAX_FOLLOWERS = 5000

CASUAL_KEYWORDS = [
    "かな", "だろう", "どうなる", "わからん", "わからない",
    "難しい", "むずい", "迷う", "悩む",
    "やっちゃった", "しまった", "失敗", "ミス",
    "初心者", "勉強中", "練習", "デモ",
    "今日は", "今週は", "さっき", "ついさっき",
    "どう思います", "教えて", "質問"
]

# 各モードでのいいね数
LIKES_PER_LIKEBACK = 5      # いいね返し
LIKES_PER_FOLLOWING = 5     # フォロー中
LIKES_PER_TIMELINE = 5      # タイムライン

MIN_WAIT = 8
MAX_WAIT = 20
SCROLL_WAIT = 3

PROFILE_DIR = Path.home() / ".prometheus_selenium"
LIKED_USERS_FILE = Path.home() / ".prometheus_selenium" / "liked_users.json"

# ===== カラー出力 =====
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def log_info(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{Colors.BLUE}[{timestamp}][INFO]{Colors.RESET} {msg}")

def log_success(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{Colors.GREEN}[{timestamp}][SUCCESS]{Colors.RESET} {msg}")

def log_warning(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{Colors.YELLOW}[{timestamp}][WARNING]{Colors.RESET} {msg}")

def log_error(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{Colors.RED}[{timestamp}][ERROR]{Colors.RESET} {msg}")

def log_skip(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{Colors.MAGENTA}[{timestamp}][SKIP]{Colors.RESET} {msg}")

def log_phase(msg):
    print(f"\n{Colors.CYAN}{Colors.BOLD}{msg}{Colors.RESET}")

BANNER = f"""
{Colors.CYAN}╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   ██████╗ ██████╗  ██████╗ ███╗   ███╗███████╗████████╗  ║
║   ██╔══██╗██╔══██╗██╔═══██╗████╗ ████║██╔════╝╚══██╔══╝  ║
║   ██████╔╝██████╔╝██║   ██║██╔████╔██║█████╗     ██║     ║
║   ██╔═══╝ ██╔══██╗██║   ██║██║╚██╔╝██║██╔══╝     ██║     ║
║   ██║     ██║  ██║╚██████╔╝██║ ╚═╝ ██║███████╗   ██║     ║
║   ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝   ╚═╝     ║
║                                                           ║
║   Selenium自動いいね v5.8 (Headless対応)                  ║
║   毎朝6時自動リセット機能付き                          ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝{Colors.RESET}
"""


# リセット時刻の設定
RESET_HOUR = 6  # 朝6時にリセット
LAST_RESET_FILE = Path.home() / ".prometheus_selenium" / "last_reset.txt"


class LikedUsersManager:
    """いいね済みユーザーを管理するクラス"""
    
    def __init__(self):
        self.liked_users = {}  # {username: timestamp}
        self.check_daily_reset()  # 毎日のリセットチェック
        self.load()
    
    def check_daily_reset(self):
        """毎朝6時に自動リセット"""
        now = datetime.now()
        today_reset_time = now.replace(hour=RESET_HOUR, minute=0, second=0, microsecond=0)
        
        # 最後のリセット日時を確認
        last_reset = None
        try:
            if LAST_RESET_FILE.exists():
                with open(LAST_RESET_FILE, 'r') as f:
                    last_reset = datetime.fromisoformat(f.read().strip())
        except:
            pass
        
        # リセットが必要か判定
        should_reset = False
        
        if last_reset is None:
            # 初回起動時はリセットしない（既存データを保持）
            should_reset = False
        elif now >= today_reset_time and last_reset < today_reset_time:
            # 今日のリセット時刻を過ぎていて、まだリセットしていない
            should_reset = True
        
        if should_reset:
            log_info(f"🔄 朝{RESET_HOUR}時の自動リセットを実行")
            # ファイルを削除してリセット
            try:
                if LIKED_USERS_FILE.exists():
                    LIKED_USERS_FILE.unlink()
            except:
                pass
            self.liked_users = {}
        
        # リセット日時を記録
        try:
            PROFILE_DIR.mkdir(exist_ok=True)
            with open(LAST_RESET_FILE, 'w') as f:
                f.write(now.isoformat())
        except:
            pass
    
    def load(self):
        """ファイルから読み込み"""
        try:
            if LIKED_USERS_FILE.exists():
                with open(LIKED_USERS_FILE, 'r', encoding='utf-8') as f:
                    self.liked_users = json.load(f)
                log_info(f"いいね済みユーザー: {len(self.liked_users)}人を読み込み")
        except Exception as e:
            log_warning(f"履歴読み込みエラー: {e}")
            self.liked_users = {}
    
    def save(self):
        """ファイルに保存"""
        try:
            PROFILE_DIR.mkdir(exist_ok=True)
            with open(LIKED_USERS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.liked_users, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log_warning(f"履歴保存エラー: {e}")
    
    def add(self, username: str):
        """ユーザーを追加"""
        if username:
            self.liked_users[username.lower()] = datetime.now().isoformat()
            self.save()
    
    def has_liked(self, username: str) -> bool:
        """既にいいね済みか確認"""
        return username.lower() in self.liked_users
    
    def clear(self):
        """履歴をクリア"""
        self.liked_users = {}
        self.save()
        log_info("いいね履歴をクリアしました")
    
    def count(self) -> int:
        """いいね済みユーザー数"""
        return len(self.liked_users)


class SeleniumAutoLike:
    """Selenium自動いいねエンジン"""
    
    def __init__(self, headless=False):
        self.driver = None
        self.headless = headless
        self.likes_today = 0
        self.my_username = ""
        self.liked_manager = LikedUsersManager()
    
    def setup(self):
        """ブラウザを起動"""
        log_info("Chromeを起動中...")
        
        PROFILE_DIR.mkdir(exist_ok=True)
        
        options = Options()
        options.add_argument(f"--user-data-dir={PROFILE_DIR}")
        options.add_argument("--profile-directory=Default")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--lang=ja")
        
        if self.headless:
            options.add_argument("--headless=new")
            options.add_argument("--window-size=1280,800")
            
        prefs = {"intl.accept_languages": "ja,ja-JP"}
        options.add_experimental_option("prefs", prefs)
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.set_window_size(1280, 800)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            log_success("Chrome起動完了")
            return True
        except Exception as e:
            log_error(f"Chrome起動エラー: {e}")
            return False
    
    def close(self):
        if self.driver:
            self.driver.quit()
    
    def is_logged_in(self) -> bool:
        try:
            self.driver.get("https://x.com/home")
            time.sleep(5)
            
            current_url = self.driver.current_url
            if "login" in current_url or "i/flow" in current_url:
                return False
            
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="tweet"]'))
                )
                # 自分のユーザー名を取得
                try:
                    account_link = self.driver.find_element(By.CSS_SELECTOR, '[data-testid="AppTabBar_Profile_Link"]')
                    href = account_link.get_attribute("href")
                    self.my_username = href.split("/")[-1]
                    log_info(f"ログインユーザー: @{self.my_username}")
                except:
                    pass
                return True
            except:
                return False
        except:
            return False
            
    def wait_for_login(self):
        log_warning("ログインが必要です。ブラウザでログインを完了してください。")
        if self.headless:
            log_error("ヘッドレスモードではログイン操作ができません。通常モードで一度ログインしてください。")
            return False
            
        while True:
            if self.is_logged_in():
                log_success("ログインを確認しました")
                return True
            time.sleep(5)
            
    def random_wait(self):
        wait = random.randint(MIN_WAIT, MAX_WAIT)
        log_info(f"待機中... ({wait}秒)")
        time.sleep(wait)
        
    def scroll_page(self):
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SCROLL_WAIT)
        
    def like_tweet(self, like_button) -> bool:
        try:
            # ボタンが見える位置までスクロール
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", like_button)
            time.sleep(1)
            
            # クリック
            like_button.click()
            return True
        except Exception as e:
            log_error(f"いいねクリックエラー: {e}")
            return False

    # ===== いいね返し機能 =====
    def run_likeback(self) -> int:
        """自分の通知からいいねしてくれた人にいいねを返す"""
        log_phase("=" * 50)
        log_phase("いいね返しモード")
        log_phase("=" * 50)
        
        likes_done = 0
        
        log_info("通知ページを確認中...")
        self.driver.get("https://x.com/notifications")
        time.sleep(5)
        
        try:
            # 「いいね」の通知をフィルタリング（もし可能なら）
            # ここでは全通知から「liked your tweet」的なものを探す
            notifications = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="notification"]')
            
            users_to_check = []
            for n in notifications:
                try:
                    # いいね通知かチェック（ハートアイコンがあるか、テキストに含まれるか）
                    text = n.text
                    if "liked your tweet" in text or "さんがあなたのポストをいいねしました" in text:
                        # ユーザー名を取得
                        links = n.find_elements(By.CSS_SELECTOR, 'a[role="link"]')
                        for link in links:
                            href = link.get_attribute("href")
                            if href and "x.com/" in href:
                                username = href.split("/")[-1]
                                if username and username not in users_to_check and username != self.my_username:
                                    # 既にいいね済みかチェック
                                    if not self.liked_manager.has_liked(username):
                                        users_to_check.append(username)
                except:
                    continue
            
            log_info(f"いいねしてくれたユーザー: {len(users_to_check)}人を発見")
            
            for username in users_to_check[:LIKES_PER_LIKEBACK]:
                if likes_done >= LIKES_PER_LIKEBACK:
                    break
                
                log_info(f"@{username} の最新ツイートをチェック中...")
                if self.like_user_tweet(username):
                    likes_done += 1
                    self.likes_today += 1
                    self.liked_manager.add(username)
                    log_success(f"✅ いいね返し成功！ @{username} (本日: {self.likes_today}件)")
                    self.random_wait()
                    
        except Exception as e:
            log_error(f"通知取得エラー: {e}")
            
        log_info(f"いいね返し完了: {likes_done}件")
        return likes_done

    def like_user_tweet(self, username: str) -> bool:
        """特定のユーザーの最新ツイートにいいねする"""
        try:
            # 現在のウィンドウを保存
            main_window = self.driver.current_window_handle
            
            # 新しいタブを開く
            initial_handles = self.driver.window_handles
            self.driver.execute_script("window.open('');")
            
            # タブが増えるまで待機
            wait_count = 0
            while len(self.driver.window_handles) <= len(initial_handles) and wait_count < 10:
                time.sleep(0.5)
                wait_count += 1
            
            liked = False
            if len(self.driver.window_handles) > len(initial_handles):
                # 新しいタブに切り替え
                self.driver.switch_to.window(self.driver.window_handles[-1])
                
                # ユーザーページに移動
                self.driver.get(f"https://x.com/{username}")
                time.sleep(4)
                
                # 最新ツイートを探す
                tweets = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="tweet"]')
                if tweets:
                    for tweet in tweets[:3]: # 上位3つまで確認
                        try:
                            # 広告やプロモーションを除外
                            if "Promoted" in tweet.text or "プロモーション" in tweet.text:
                                continue
                                
                            like_button = tweet.find_element(By.CSS_SELECTOR, '[data-testid="like"]')
                            if self.like_tweet(like_button):
                                liked = True
                                break
                        except:
                            continue
                
                # タブを閉じる（メインウィンドウでないことを確認）
                if self.driver.current_window_handle != main_window:
                    self.driver.close()
                
                # メインウィンドウに戻る
                self.driver.switch_to.window(main_window)
            else:
                log_warning("新しいタブを開けませんでした。メインタブで処理を継続します。")
                liked = False
            time.sleep(1)
            
            return liked
            
        except Exception as e:
            try:
                self.driver.switch_to.window(self.driver.window_handles[0])
            except:
                pass
            return False
    
    # ===== フォロー中へのいいね機能 =====
    def run_following_likes(self) -> int:
        """フォロー中の人のツイートにいいね"""
        log_phase("=" * 50)
        log_phase("フォロー中へのいいねモード")
        log_phase("=" * 50)
        
        if not self.my_username:
            log_error("ユーザー名が取得できていません")
            return 0
        
        likes_done = 0
        
        # フォロー中リストを取得
        log_info("フォロー中リストを取得中...")
        self.driver.get(f"https://x.com/{self.my_username}/following")
        time.sleep(5)
        
        following_users = []
        scroll_count = 0
        
        # フォロー中ユーザーを収集（最大30人）
        while len(following_users) < 30 and scroll_count < 5:
            try:
                user_cells = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="UserCell"]')
                
                for cell in user_cells:
                    try:
                        link = cell.find_element(By.CSS_SELECTOR, 'a[role="link"]')
                        href = link.get_attribute("href")
                        if href and "x.com/" in href:
                            username = href.split("/")[-1]
                            if username and username not in following_users:
                                # 既にいいね済みかチェック
                                if not self.liked_manager.has_liked(username):
                                    following_users.append(username)
                    except:
                        continue
                
                self.scroll_page()
                scroll_count += 1
                
            except Exception as e:
                log_error(f"フォロー中リスト取得エラー: {e}")
                break
        
        log_info(f"フォロー中（未いいね）: {len(following_users)}人を取得")
        
        # ランダムに選んでいいね
        random.shuffle(following_users)
        
        for username in following_users[:LIKES_PER_FOLLOWING * 2]:
            if likes_done >= LIKES_PER_FOLLOWING:
                break
            
            log_info(f"@{username} のツイートをチェック中...")
            
            if self.like_user_tweet(username):
                likes_done += 1
                self.likes_today += 1
                self.liked_manager.add(username)
                log_success(f"✅ フォロー中いいね成功！ @{username} (本日: {self.likes_today}件)")
                self.random_wait()
        
        log_info(f"フォロー中いいね完了: {likes_done}件")
        return likes_done
    
    # ===== タイムラインいいね =====
    def contains_url(self, text: str) -> bool:
        url_pattern = r'https?://|t\.co/|bit\.ly|goo\.gl'
        return bool(re.search(url_pattern, text))
    
    def contains_exclude_keyword(self, text: str) -> bool:
        text_lower = text.lower()
        for keyword in EXCLUDE_KEYWORDS:
            if keyword.lower() in text_lower:
                return True
        return False
    
    def score_tweet(self, text: str) -> tuple:
        text_lower = text.lower()
        
        if self.contains_url(text):
            return (-1, "URLを含む")
        
        if self.contains_exclude_keyword(text):
            for kw in EXCLUDE_KEYWORDS:
                if kw.lower() in text_lower:
                    return (-1, f"除外KW「{kw}」")
        
        score = 0
        for keyword in TARGET_KEYWORDS:
            if keyword.lower() in text_lower:
                score += 10
        
        if score == 0:
            return (0, "対象KWなし")
        
        for keyword in CASUAL_KEYWORDS:
            if keyword in text_lower:
                score += 5
        
        return (score, None)
    
    def run_timeline_likes(self) -> int:
        """タイムラインでいいね（一般ユーザー優先）"""
        log_phase("=" * 50)
        log_phase("タイムラインいいねモード（一般ユーザー優先）")
        log_phase("=" * 50)
        
        likes_done = 0
        
        log_info("タイムラインを読み込み中...")
        self.driver.get("https://x.com/home")
        time.sleep(5)
        
        scroll_count = 0
        max_scrolls = 15
        
        while likes_done < LIKES_PER_TIMELINE and scroll_count < max_scrolls:
            try:
                tweets = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="tweet"]')
                
                for tweet in tweets:
                    if likes_done >= LIKES_PER_TIMELINE:
                        break
                    
                    try:
                        # テキスト取得
                        try:
                            text_element = tweet.find_element(By.CSS_SELECTOR, '[data-testid="tweetText"]')
                            text = text_element.text
                        except:
                            text = ""
                        
                        # ユーザー名取得
                        username = ""
                        try:
                            user_links = tweet.find_elements(By.CSS_SELECTOR, 'a[role="link"]')
                            for link in user_links:
                                href = link.get_attribute("href")
                                if href and "x.com/" in href and "/status/" not in href:
                                    username = href.split("/")[-1]
                                    if username and username not in ["home", "explore"]:
                                        break
                        except:
                            pass
                        
                        # 既にいいね済みかチェック
                        if username and self.liked_manager.has_liked(username):
                            log_skip(f"いいね済み @{username}")
                            continue
                        
                        # スコアリング
                        score, skip_reason = self.score_tweet(text)
                        
                        if score < 0:
                            text_preview = text[:30].replace("\n", " ")
                            log_skip(f"@{username}: {text_preview}... ({skip_reason})")
                            continue
                        
                        if score > 0:
                            try:
                                like_button = tweet.find_element(By.CSS_SELECTOR, '[data-testid="like"]')
                                
                                text_preview = text[:40].replace("\n", " ")
                                log_info(f"対象 (スコア:{score}) @{username}: {text_preview}...")
                                
                                if self.like_tweet(like_button):
                                    likes_done += 1
                                    self.likes_today += 1
                                    if username:
                                        self.liked_manager.add(username)
                                    log_success(f"✅ タイムラインいいね成功！ @{username} (本日: {self.likes_today}件)")
                                    self.random_wait()
                            except NoSuchElementException:
                                pass  # 既にいいね済み
                                
                    except StaleElementReferenceException:
                        continue
                    except Exception:
                        continue
                
                if likes_done < LIKES_PER_TIMELINE:
                    log_info("スクロール中...")
                    self.scroll_page()
                    scroll_count += 1
                    
            except Exception as e:
                log_error(f"タイムライン取得エラー: {e}")
                break
        
        log_info(f"タイムラインいいね完了: {likes_done}件")
        return likes_done
    
    # ===== メインサイクル =====
    def run_full_cycle(self) -> dict:
        """全機能を実行"""
        result = {
            "likeback": 0,
            "following": 0,
            "timeline": 0
        }
        
        # 1. いいね返し
        result["likeback"] = self.run_likeback()
        time.sleep(5)
        
        # 2. フォロー中へのいいね
        result["following"] = self.run_following_likes()
        time.sleep(5)
        
        # 3. タイムラインいいね
        result["timeline"] = self.run_timeline_likes()
        
        return result


def main():
    parser = argparse.ArgumentParser(description="Selenium自動いいね v5.8")
    parser.add_argument("--loop", action="store_true", help="全機能を継続実行")
    parser.add_argument("--likeback", action="store_true", help="いいね返しのみ")
    parser.add_argument("--following", action="store_true", help="フォロー中へのいいねのみ")
    parser.add_argument("--timeline", action="store_true", help="タイムラインいいねのみ")
    parser.add_argument("--clear-history", action="store_true", help="いいね履歴をクリア")
    parser.add_argument("--headless", action="store_true", help="バックグラウンド実行モード")
    args = parser.parse_args()
    
    print(BANNER)
    
    # 履歴クリア
    if args.clear_history:
        manager = LikedUsersManager()
        manager.clear()
        return
    
    engine = SeleniumAutoLike(headless=args.headless)
    
    # いいね済みユーザー数を表示
    log_info(f"いいね済みユーザー: {engine.liked_manager.count()}人")
    
    try:
        if not engine.setup():
            return
        
        log_info("ログイン状態を確認中...")
        if not engine.is_logged_in():
            if not engine.wait_for_login():
                return
        else:
            log_success("ログイン済み")
        
        # モード選択
        if args.likeback:
            engine.run_likeback()
        elif args.following:
            engine.run_following_likes()
        elif args.timeline:
            engine.run_timeline_likes()
        elif args.loop:
            log_info("全機能継続モードで実行します（Ctrl+C で停止）")
            
            cycle = 1
            try:
                while True:
                    print()
                    log_phase(f"===== サイクル {cycle} =====")
                    log_info(f"いいね済みユーザー: {engine.liked_manager.count()}人")
                    
                    result = engine.run_full_cycle()
                    
                    total = result["likeback"] + result["following"] + result["timeline"]
                    log_phase(f"サイクル{cycle}完了: 合計{total}件")
                    print(f"  いいね返し: {result['likeback']}件")
                    print(f"  フォロー中: {result['following']}件")
                    print(f"  タイムライン: {result['timeline']}件")
                    print(f"  本日合計: {engine.likes_today}件")
                    print(f"  累計いいね済みユーザー: {engine.liked_manager.count()}人")
                    
                    wait_time = random.randint(120, 240)  # 2〜4分
                    log_info(f"次のサイクルまで {wait_time}秒 待機...")
                    time.sleep(wait_time)
                    
                    cycle += 1
                    
            except KeyboardInterrupt:
                print()
                log_info("停止しました")
                log_info(f"本日のいいね合計: {engine.likes_today}件")
                log_info(f"累計いいね済みユーザー: {engine.liked_manager.count()}人")
        else:
            # デフォルト: 全機能を1回実行
            result = engine.run_full_cycle()
            
            print()
            log_phase("【実行結果】")
            print(f"いいね返し: {result['likeback']}件")
            print(f"フォロー中: {result['following']}件")
            print(f"タイムライン: {result['timeline']}件")
            print(f"本日合計: {engine.likes_today}件")
            print(f"累計いいね済みユーザー: {engine.liked_manager.count()}人")
    
    finally:
        engine.close()


if __name__ == "__main__":
    main()
