#!/usr/bin/env python3
"""
Project Prometheus - note自動スキ v1.0
======================================
noteの記事に自動で「スキ」をつけるスクリプト

特徴:
- Chromeプロファイルを使用（ログイン状態を維持）
- キーワードベースのフィルタリング
- 人間らしい動作をシミュレート

使い方:
    python3 auto_like_note.py           # 1サイクル実行
    python3 auto_like_note.py --loop    # 継続実行（Ctrl+Cで停止）

注意:
    実行前にChromeを完全に終了してください
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
# スキをつける対象のキーワード（投資・金融関連）
KEYWORDS = [
    "投資", "資産運用", "株式", "FX", "為替", "ドル円",
    "NISA", "iDeCo", "積立", "配当", "ETF",
    "日経平均", "S&P500", "米国株", "高配当",
    "経済", "金融", "マネー", "お金", "副業",
    "不労所得", "FIRE", "セミリタイア", "資産形成"
]

# 除外キーワード
EXCLUDE_KEYWORDS = [
    "詐欺", "情報商材", "稼げる", "簡単に", "誰でも"
]

LIKES_PER_CYCLE = 10  # 1サイクルあたりのスキ数
MIN_WAIT = 10  # スキ間の最小待機秒数
MAX_WAIT = 25  # スキ間の最大待機秒数
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

def log_phase(msg):
    print(f"\n{Colors.CYAN}{Colors.BOLD}{msg}{Colors.RESET}")

# ===== バナー =====
BANNER = f"""
{Colors.MAGENTA}╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   ███╗   ██╗ ██████╗ ████████╗███████╗                   ║
║   ████╗  ██║██╔═══██╗╚══██╔══╝██╔════╝                   ║
║   ██╔██╗ ██║██║   ██║   ██║   █████╗                     ║
║   ██║╚██╗██║██║   ██║   ██║   ██╔══╝                     ║
║   ██║ ╚████║╚██████╔╝   ██║   ███████╗                   ║
║   ╚═╝  ╚═══╝ ╚═════╝    ╚═╝   ╚══════╝                   ║
║                                                           ║
║   ███████╗██╗  ██╗██╗                                    ║
║   ██╔════╝██║ ██╔╝██║                                    ║
║   ███████╗█████╔╝ ██║                                    ║
║   ╚════██║██╔═██╗ ██║                                    ║
║   ███████║██║  ██╗██║                                    ║
║   ╚══════╝╚═╝  ╚═╝╚═╝                                    ║
║                                                           ║
║   note自動スキ v1.0 - Chromeプロファイル版               ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝{Colors.RESET}
"""


def check_chrome_running():
    """Chromeが起動中かチェック"""
    import subprocess
    result = subprocess.run(['pgrep', '-x', 'Google Chrome'], capture_output=True)
    return result.returncode == 0


class NoteAutoLike:
    """note自動スキエンジン"""
    
    def __init__(self):
        self.playwright = None
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
                channel="chrome",
                headless=False,
                viewport={"width": 1280, "height": 800},
                locale="ja-JP",
                timezone_id="Asia/Tokyo",
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--profile-directory=Default"
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
        """noteにログインしているか確認"""
        try:
            await self.page.goto("https://note.com/", wait_until="networkidle", timeout=30000)
            await asyncio.sleep(3)
            
            # ログインボタンがあるかチェック（あればログインしていない）
            login_button = await self.page.query_selector('a[href*="login"]')
            
            # プロフィールアイコンがあるかチェック（あればログイン済み）
            profile_icon = await self.page.query_selector('[class*="UserIcon"], [class*="avatar"], img[alt*="プロフィール"]')
            
            if profile_icon:
                return True
            
            # 別の方法でログイン確認
            try:
                await self.page.goto("https://note.com/notes", wait_until="networkidle", timeout=15000)
                await asyncio.sleep(2)
                current_url = self.page.url
                if "login" not in current_url:
                    return True
            except:
                pass
            
            return False
                
        except Exception as e:
            log_error(f"ログイン確認エラー: {e}")
            return False
    
    async def search_articles(self, keyword: str) -> list:
        """キーワードで記事を検索"""
        articles = []
        
        try:
            search_url = f"https://note.com/search?q={keyword}&context=note&mode=search"
            await self.page.goto(search_url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(3)
            
            # 記事カードを取得
            article_elements = await self.page.query_selector_all('a[href*="/n/"]')
            
            for elem in article_elements[:20]:
                try:
                    href = await elem.get_attribute("href")
                    if href and "/n/" in href and not any(ex in href for ex in ["/m/", "/c/"]):
                        # 完全なURLを構築
                        if not href.startswith("http"):
                            href = f"https://note.com{href}"
                        
                        text = await elem.inner_text()
                        
                        # 除外キーワードチェック
                        if any(ex.lower() in text.lower() for ex in EXCLUDE_KEYWORDS):
                            continue
                        
                        articles.append({
                            "url": href,
                            "title": text[:50] if text else "タイトル不明"
                        })
                except:
                    continue
            
        except Exception as e:
            log_warning(f"検索エラー ({keyword}): {e}")
        
        return articles
    
    async def like_article(self, url: str) -> bool:
        """記事にスキをつける"""
        try:
            await self.page.goto(url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(2)
            
            # スキボタンを探す（複数のセレクタを試す）
            like_button = None
            selectors = [
                'button[class*="like"]',
                'button[aria-label*="スキ"]',
                '[data-testid="like-button"]',
                'button:has-text("スキ")',
                '[class*="LikeButton"]',
            ]
            
            for selector in selectors:
                try:
                    like_button = await self.page.query_selector(selector)
                    if like_button:
                        break
                except:
                    continue
            
            if not like_button:
                # SVGのハートアイコンを探す
                like_button = await self.page.query_selector('button svg[class*="heart"], button svg path[d*="M12"]')
                if like_button:
                    like_button = await like_button.evaluate_handle("el => el.closest('button')")
            
            if not like_button:
                log_warning("スキボタンが見つかりません")
                return False
            
            # すでにスキ済みかチェック
            button_class = await like_button.get_attribute("class") or ""
            aria_pressed = await like_button.get_attribute("aria-pressed")
            
            if "liked" in button_class.lower() or aria_pressed == "true":
                log_info("すでにスキ済み")
                return False
            
            # スキをクリック
            await like_button.click()
            await asyncio.sleep(1.5)
            
            return True
            
        except Exception as e:
            log_warning(f"スキエラー: {e}")
            return False
    
    async def run_cycle(self) -> dict:
        """1サイクル実行"""
        log_phase("=" * 50)
        log_phase("note自動スキサイクル開始")
        log_phase("=" * 50)
        
        result = {
            "success": 0,
            "skipped": 0,
            "total_checked": 0
        }
        
        likes_this_cycle = 0
        
        # ランダムにキーワードを選択
        keywords_to_search = random.sample(KEYWORDS, min(3, len(KEYWORDS)))
        
        for keyword in keywords_to_search:
            if likes_this_cycle >= LIKES_PER_CYCLE:
                break
            
            log_info(f"検索中: {keyword}")
            articles = await self.search_articles(keyword)
            log_info(f"取得記事: {len(articles)}件")
            
            # シャッフルしてランダムに選択
            random.shuffle(articles)
            
            for article in articles[:5]:
                if likes_this_cycle >= LIKES_PER_CYCLE:
                    break
                
                result["total_checked"] += 1
                title_preview = article["title"][:30].replace("\n", " ")
                log_info(f"記事: {title_preview}...")
                
                success = await self.like_article(article["url"])
                
                if success:
                    result["success"] += 1
                    likes_this_cycle += 1
                    self.likes_today += 1
                    log_success(f"💚 スキ成功！ (本日: {self.likes_today}件)")
                    
                    wait_time = random.uniform(MIN_WAIT, MAX_WAIT)
                    log_info(f"次のスキまで {wait_time:.1f}秒 待機...")
                    await asyncio.sleep(wait_time)
                else:
                    result["skipped"] += 1
                    await asyncio.sleep(2)
        
        log_phase(f"サイクル完了: {result['success']}件スキ")
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
    
    engine = NoteAutoLike()
    
    try:
        if not await engine.setup():
            return
        
        # ログイン確認
        log_info("noteログイン状態を確認中...")
        if not await engine.is_logged_in():
            log_error("noteにログインしていません。")
            log_error("開いたChromeでnoteにログインしてください。")
            log_error("ログイン後、このプログラムを再実行してください。")
            input("Enterキーを押すとChromeを閉じます...")
            return
        
        log_success("ログイン確認OK！")
        
        print()
        log_info(f"キーワード: {', '.join(KEYWORDS[:5])}...")
        log_info(f"1サイクルあたり: {LIKES_PER_CYCLE}件")
        log_info(f"スキ間隔: {MIN_WAIT}〜{MAX_WAIT}秒")
        
        if args.loop:
            log_info("継続モードで実行します（Ctrl+C で停止）")
            
            cycle = 1
            try:
                while True:
                    print()
                    log_phase(f"===== サイクル {cycle} =====")
                    
                    result = await engine.run_cycle()
                    
                    wait_time = random.randint(120, 240)  # 2〜4分
                    log_info(f"次のサイクルまで {wait_time}秒 待機...")
                    await asyncio.sleep(wait_time)
                    
                    cycle += 1
                    
            except KeyboardInterrupt:
                print()
                log_info("停止しました")
                log_info(f"本日のスキ合計: {engine.likes_today}件")
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
    parser = argparse.ArgumentParser(description="note自動スキ v1.0")
    parser.add_argument("--loop", action="store_true", help="継続実行モード")
    args = parser.parse_args()
    
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
