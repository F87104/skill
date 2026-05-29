#!/usr/bin/env python3
"""
Project Prometheus - Chrome自動いいね v5.1
==========================================
通常のChromeブラウザのプロファイルを使用する安全版

特徴:
- 普段使っているChromeのログイン状態をそのまま使用
- Googleの自動化検出を回避
- パスワード再入力不要
- API制限なし

使い方:
    python3 auto_like_chrome.py           # 1サイクル実行
    python3 auto_like_chrome.py --loop    # 継続実行（Ctrl+Cで停止）

注意:
    実行前にChromeを完全に終了してください（Dockのアイコンを右クリック→終了）
"""

import asyncio
import random
import argparse
import sys
import os
from pathlib import Path
from datetime import datetime

# Playwrightのインポート
try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("Playwrightがインストールされていません。")
    print("以下のコマンドでインストールしてください:")
    print("  pip3 install playwright")
    print("  python3 -m playwright install chromium")
    sys.exit(1)

# ===== 設定 =====
KEYWORDS = ["FX", "為替", "ドル円", "株式", "日経平均", "投資", "経済", "マーケット", "トレード", "相場"]
LIKES_PER_CYCLE = 10  # 1サイクルあたりのいいね数
MIN_WAIT = 8  # いいね間の最小待機秒数
MAX_WAIT = 20  # いいね間の最大待機秒数
SCROLL_WAIT = 3  # スクロール後の待機秒数

# macOSのChromeユーザーデータパス
CHROME_USER_DATA = Path.home() / "Library/Application Support/Google/Chrome"

# ===== カラー出力 =====
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
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

def log_phase(msg):
    print(f"\n{Colors.CYAN}{Colors.BOLD}{msg}{Colors.RESET}")

# ===== バナー =====
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
║   Chrome自動いいね v5.1 - 安全版                          ║
║   通常のChromeプロファイルを使用                          ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝{Colors.RESET}
"""


def check_chrome_running():
    """Chromeが起動中かチェック"""
    import subprocess
    result = subprocess.run(['pgrep', '-x', 'Google Chrome'], capture_output=True)
    return result.returncode == 0


class ChromeAutoLike:
    """Chrome自動いいねエンジン"""
    
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.likes_count = 0
        self.likes_today = 0
    
    async def setup(self):
        """ブラウザを起動"""
        log_info("Chromeを起動中...")
        
        # Chromeが起動中かチェック
        if check_chrome_running():
            log_error("Chromeが起動中です！")
            log_error("Chromeを完全に終了してから再実行してください。")
            log_error("（Dockのアイコンを右クリック → 終了）")
            return False
        
        # Chromeプロファイルの存在確認
        if not CHROME_USER_DATA.exists():
            log_error("Chromeのユーザーデータが見つかりません。")
            log_error("Google Chromeがインストールされていることを確認してください。")
            return False
        
        self.playwright = await async_playwright().start()
        
        # 通常のChromeを起動（ユーザープロファイルを使用）
        try:
            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=str(CHROME_USER_DATA),
                channel="chrome",  # インストール済みのChromeを使用
                headless=False,  # ブラウザを表示
                viewport={"width": 1280, "height": 800},
                locale="ja-JP",
                timezone_id="Asia/Tokyo",
                args=[
                    "--disable-blink-features=AutomationControlled",  # 自動化検出を回避
                    "--profile-directory=Default"  # デフォルトプロファイルを使用
                ]
            )
        except Exception as e:
            log_error(f"Chrome起動エラー: {e}")
            log_error("Chromeが完全に終了していることを確認してください。")
            return False
        
        # ページを取得または作成
        if self.context.pages:
            self.page = self.context.pages[0]
        else:
            self.page = await self.context.new_page()
        
        log_success("Chrome起動完了")
        return True
    
    async def close(self):
        """ブラウザを閉じる"""
        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def is_logged_in(self) -> bool:
        """ログイン状態を確認"""
        try:
            await self.page.goto("https://x.com/home", wait_until="networkidle", timeout=30000)
            await asyncio.sleep(3)
            
            current_url = self.page.url
            if "login" in current_url or "i/flow" in current_url:
                return False
            
            try:
                await self.page.wait_for_selector('[data-testid="tweet"]', timeout=10000)
                return True
            except:
                return False
                
        except Exception as e:
            log_error(f"ログイン確認エラー: {e}")
            return False
    
    async def get_timeline_tweets(self) -> list:
        """タイムラインからツイートを取得"""
        tweets = []
        
        try:
            tweet_elements = await self.page.query_selector_all('[data-testid="tweet"]')
            
            for element in tweet_elements:
                try:
                    text_element = await element.query_selector('[data-testid="tweetText"]')
                    text = await text_element.inner_text() if text_element else ""
                    
                    like_button = await element.query_selector('[data-testid="like"]')
                    unlike_button = await element.query_selector('[data-testid="unlike"]')
                    already_liked = unlike_button is not None
                    
                    if like_button and not already_liked:
                        tweets.append({
                            "text": text,
                            "like_button": like_button,
                            "element": element
                        })
                except:
                    continue
            
        except Exception as e:
            log_error(f"ツイート取得エラー: {e}")
        
        return tweets
    
    def score_tweet(self, text: str) -> int:
        """ツイートをスコアリング"""
        score = 0
        text_lower = text.lower()
        
        for keyword in KEYWORDS:
            if keyword.lower() in text_lower:
                score += 10
        
        return score
    
    async def like_tweet(self, like_button) -> bool:
        """いいねを実行"""
        try:
            await like_button.click()
            await asyncio.sleep(1)
            return True
        except Exception as e:
            log_warning(f"いいねエラー: {e}")
            return False
    
    async def scroll_page(self):
        """ページをスクロール"""
        await self.page.evaluate("window.scrollBy(0, 600)")
        await asyncio.sleep(SCROLL_WAIT)
    
    async def run_cycle(self) -> dict:
        """1サイクル実行"""
        log_phase("=" * 50)
        log_phase("自動いいねサイクル開始")
        log_phase("=" * 50)
        
        result = {
            "success": 0,
            "skipped": 0,
            "total_checked": 0
        }
        
        log_info("タイムラインを読み込み中...")
        await self.page.goto("https://x.com/home", wait_until="networkidle", timeout=30000)
        await asyncio.sleep(3)
        
        likes_this_cycle = 0
        scroll_count = 0
        max_scrolls = 10
        
        while likes_this_cycle < LIKES_PER_CYCLE and scroll_count < max_scrolls:
            tweets = await self.get_timeline_tweets()
            log_info(f"取得ツイート: {len(tweets)}件")
            
            for tweet in tweets:
                if likes_this_cycle >= LIKES_PER_CYCLE:
                    break
                
                result["total_checked"] += 1
                score = self.score_tweet(tweet["text"])
                
                if score > 0:
                    text_preview = tweet["text"][:40].replace("\n", " ")
                    log_info(f"対象ツイート (スコア:{score}): {text_preview}...")
                    
                    success = await self.like_tweet(tweet["like_button"])
                    
                    if success:
                        result["success"] += 1
                        likes_this_cycle += 1
                        self.likes_today += 1
                        log_success(f"✅ いいね成功！ (本日: {self.likes_today}件)")
                        
                        wait_time = random.uniform(MIN_WAIT, MAX_WAIT)
                        log_info(f"次のいいねまで {wait_time:.1f}秒 待機...")
                        await asyncio.sleep(wait_time)
                else:
                    result["skipped"] += 1
            
            if likes_this_cycle < LIKES_PER_CYCLE:
                log_info("スクロール中...")
                await self.scroll_page()
                scroll_count += 1
        
        log_phase(f"サイクル完了: {result['success']}件いいね")
        return result


async def main_async(args):
    """メイン処理（非同期）"""
    print(BANNER)
    
    # Chrome起動チェック
    if check_chrome_running():
        log_error("")
        log_error("⚠️  Chromeが起動中です！")
        log_error("")
        log_error("このプログラムは通常のChromeプロファイルを使用するため、")
        log_error("Chromeを完全に終了してから実行してください。")
        log_error("")
        log_error("【終了方法】")
        log_error("  DockのChromeアイコンを右クリック → 「終了」")
        log_error("")
        return
    
    engine = ChromeAutoLike()
    
    try:
        if not await engine.setup():
            return
        
        # ログイン確認
        log_info("ログイン状態を確認中...")
        if not await engine.is_logged_in():
            log_error("Xにログインしていません。")
            log_error("開いたChromeでXにログインしてください。")
            log_error("ログイン後、このプログラムを再実行してください。")
            input("Enterキーを押すとChromeを閉じます...")
            return
        
        log_success("ログイン確認OK！")
        
        print()
        log_info(f"キーワード: {', '.join(KEYWORDS)}")
        log_info(f"1サイクルあたり: {LIKES_PER_CYCLE}件")
        log_info(f"いいね間隔: {MIN_WAIT}〜{MAX_WAIT}秒")
        
        if args.loop:
            log_info("継続モードで実行します（Ctrl+C で停止）")
            
            cycle = 1
            try:
                while True:
                    print()
                    log_phase(f"===== サイクル {cycle} =====")
                    
                    result = await engine.run_cycle()
                    
                    wait_time = random.randint(90, 180)  # 1.5〜3分
                    log_info(f"次のサイクルまで {wait_time}秒 待機...")
                    await asyncio.sleep(wait_time)
                    
                    cycle += 1
                    
            except KeyboardInterrupt:
                print()
                log_info("停止しました")
                log_info(f"本日のいいね合計: {engine.likes_today}件")
        else:
            result = await engine.run_cycle()
            
            print()
            log_phase("【実行結果】")
            print(f"成功: {result['success']}件")
            print(f"スキップ: {result['skipped']}件")
            print(f"本日合計: {engine.likes_today}件")
    
    finally:
        await engine.close()


def main():
    parser = argparse.ArgumentParser(description="Chrome自動いいね v5.1")
    parser.add_argument("--loop", action="store_true", help="継続実行モード")
    args = parser.parse_args()
    
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
