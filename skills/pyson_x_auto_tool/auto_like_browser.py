#!/usr/bin/env python3
"""
Project Prometheus - ブラウザ自動いいね v5.0
============================================
Playwrightを使用したブラウザ自動化版
API制限を受けずに、自然なペースでいいねを実行

特徴:
- X API不要（ブラウザ経由）
- 15分5回の制限なし
- 人間らしいランダムな間隔
- ログイン状態を保存（2回目以降は自動ログイン）

使い方:
    python3 auto_like_browser.py           # 1サイクル実行
    python3 auto_like_browser.py --loop    # 継続実行（Ctrl+Cで停止）
    python3 auto_like_browser.py --setup   # 初回セットアップ（ログイン）
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
    print("  playwright install chromium")
    sys.exit(1)

# ===== 設定 =====
KEYWORDS = ["FX", "為替", "ドル円", "株式", "日経平均", "投資", "経済", "マーケット", "トレード", "相場"]
LIKES_PER_CYCLE = 10  # 1サイクルあたりのいいね数
MIN_WAIT = 5  # いいね間の最小待機秒数
MAX_WAIT = 15  # いいね間の最大待機秒数
SCROLL_WAIT = 2  # スクロール後の待機秒数

# ユーザーデータ保存先
USER_DATA_DIR = Path.home() / ".prometheus_browser"

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
║   ブラウザ自動いいね v5.0                                 ║
║   API制限なし・自然なペースでいいね                       ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝{Colors.RESET}
"""


class BrowserAutoLike:
    """ブラウザ自動いいねエンジン"""
    
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        self.likes_count = 0
        self.likes_today = 0
    
    async def setup(self):
        """ブラウザを起動"""
        log_info("ブラウザを起動中...")
        
        # ユーザーデータディレクトリを作成
        USER_DATA_DIR.mkdir(exist_ok=True)
        
        self.playwright = await async_playwright().start()
        
        # Chromiumを起動（ユーザーデータを保存してログイン状態を維持）
        self.browser = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=str(USER_DATA_DIR),
            headless=self.headless,
            viewport={"width": 1280, "height": 800},
            locale="ja-JP",
            timezone_id="Asia/Tokyo"
        )
        
        # 既存のページを使用するか、新しいページを作成
        if self.browser.pages:
            self.page = self.browser.pages[0]
        else:
            self.page = await self.browser.new_page()
        
        log_success("ブラウザ起動完了")
    
    async def close(self):
        """ブラウザを閉じる"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def is_logged_in(self) -> bool:
        """ログイン状態を確認"""
        try:
            await self.page.goto("https://x.com/home", wait_until="networkidle", timeout=30000)
            await asyncio.sleep(3)
            
            # ログインページにリダイレクトされたかチェック
            current_url = self.page.url
            if "login" in current_url or "i/flow" in current_url:
                return False
            
            # タイムラインが表示されているかチェック
            try:
                await self.page.wait_for_selector('[data-testid="tweet"]', timeout=10000)
                return True
            except:
                return False
                
        except Exception as e:
            log_error(f"ログイン確認エラー: {e}")
            return False
    
    async def wait_for_login(self):
        """ユーザーにログインを促す"""
        log_phase("=" * 50)
        log_phase("Xにログインしてください")
        log_phase("=" * 50)
        print()
        print("ブラウザウィンドウが開きました。")
        print("Xにログインしてください。")
        print("ログインが完了したら、このターミナルに戻ってEnterキーを押してください。")
        print()
        
        await self.page.goto("https://x.com/login", wait_until="networkidle")
        
        input("ログイン完了後、Enterキーを押してください...")
        
        # ログイン確認
        if await self.is_logged_in():
            log_success("ログイン確認完了！")
            return True
        else:
            log_error("ログインが確認できませんでした。もう一度お試しください。")
            return False
    
    async def get_timeline_tweets(self) -> list:
        """タイムラインからツイートを取得"""
        tweets = []
        
        try:
            # ツイート要素を取得
            tweet_elements = await self.page.query_selector_all('[data-testid="tweet"]')
            
            for element in tweet_elements:
                try:
                    # ツイートテキストを取得
                    text_element = await element.query_selector('[data-testid="tweetText"]')
                    text = await text_element.inner_text() if text_element else ""
                    
                    # いいねボタンを取得
                    like_button = await element.query_selector('[data-testid="like"]')
                    
                    # 既にいいね済みかチェック（unlikeボタンがあるか）
                    unlike_button = await element.query_selector('[data-testid="unlike"]')
                    already_liked = unlike_button is not None
                    
                    if like_button and not already_liked:
                        tweets.append({
                            "text": text,
                            "like_button": like_button,
                            "element": element
                        })
                except Exception as e:
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
            await asyncio.sleep(0.5)
            return True
        except Exception as e:
            log_warning(f"いいねエラー: {e}")
            return False
    
    async def scroll_page(self):
        """ページをスクロール"""
        await self.page.evaluate("window.scrollBy(0, 500)")
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
        
        # ホームタイムラインに移動
        log_info("タイムラインを読み込み中...")
        await self.page.goto("https://x.com/home", wait_until="networkidle", timeout=30000)
        await asyncio.sleep(3)
        
        likes_this_cycle = 0
        scroll_count = 0
        max_scrolls = 10
        
        while likes_this_cycle < LIKES_PER_CYCLE and scroll_count < max_scrolls:
            # ツイートを取得
            tweets = await self.get_timeline_tweets()
            log_info(f"取得ツイート: {len(tweets)}件")
            
            # スコアリングしていいね
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
                        
                        # ランダムな待機時間
                        wait_time = random.uniform(MIN_WAIT, MAX_WAIT)
                        log_info(f"次のいいねまで {wait_time:.1f}秒 待機...")
                        await asyncio.sleep(wait_time)
                else:
                    result["skipped"] += 1
            
            # スクロール
            if likes_this_cycle < LIKES_PER_CYCLE:
                log_info("スクロール中...")
                await self.scroll_page()
                scroll_count += 1
        
        log_phase(f"サイクル完了: {result['success']}件いいね")
        return result


async def main_async(args):
    """メイン処理（非同期）"""
    print(BANNER)
    
    # ヘッドレスモード（--setupの場合はブラウザを表示）
    headless = not args.setup and not args.visible
    
    engine = BrowserAutoLike(headless=headless)
    
    try:
        await engine.setup()
        
        # ログイン確認
        if not await engine.is_logged_in():
            log_warning("ログインが必要です")
            if not await engine.wait_for_login():
                return
        else:
            log_success("ログイン済み")
        
        # セットアップモードの場合はここで終了
        if args.setup:
            log_success("セットアップ完了！次回からは自動でログインされます。")
            return
        
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
                    
                    # 次のサイクルまで待機
                    wait_time = random.randint(60, 120)  # 1〜2分
                    log_info(f"次のサイクルまで {wait_time}秒 待機...")
                    await asyncio.sleep(wait_time)
                    
                    cycle += 1
                    
            except KeyboardInterrupt:
                print()
                log_info("停止しました")
                log_info(f"本日のいいね合計: {engine.likes_today}件")
        else:
            # 1回実行
            result = await engine.run_cycle()
            
            print()
            log_phase("【実行結果】")
            print(f"成功: {result['success']}件")
            print(f"スキップ: {result['skipped']}件")
            print(f"本日合計: {engine.likes_today}件")
    
    finally:
        await engine.close()


def main():
    parser = argparse.ArgumentParser(description="ブラウザ自動いいね v5.0")
    parser.add_argument("--loop", action="store_true", help="継続実行モード")
    parser.add_argument("--setup", action="store_true", help="初回セットアップ（ログイン）")
    parser.add_argument("--visible", action="store_true", help="ブラウザを表示して実行")
    args = parser.parse_args()
    
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
