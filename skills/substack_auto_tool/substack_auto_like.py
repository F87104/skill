#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Substack Selenium自動いいねツール (メインプロフィール直結版)
========================================================
【重要】実行前に必ず普通のChromeを完全に終了(Command + Q)させてください。
"""

import time
import random
import sys
import os
from datetime import datetime

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
except ImportError:
    print("必要なライブラリがありません。 'pip3 install selenium' を実行してください。")
    sys.exit(1)

try:
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    print("webdriver-managerがありません。 'pip3 install webdriver-manager' を実行してください。")
    sys.exit(1)

# ===== 運用設定 =====
MIN_WAIT = 8        # いいね間の最低待機秒数
MAX_WAIT = 20       # いいね間の最大待機秒数
MAX_LIKES = 20      # 1回の実行でする「いいね」の上限数


class SubstackSelenium:
    def __init__(self):
        self.driver = None
        self.likes_done = 0

    def setup(self):
        """普段使いのChromeプロフィールを読み込んで起動"""
        options = Options()

        user_data_dir = os.path.expanduser("~/.substack_prometheus")
        options.add_argument(f"--user-data-dir={user_data_dir}")
        options.add_argument("--profile-directory=Default")

        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            return True
        except Exception:
            print("\n" + "!" * 50)
            print("【エラー】Chromeを起動できませんでした。")
            print("原因: おそらく普通のChromeが開いたままです。")
            print("対策: Chromeを完全に終了(Command + Q)してから、もう一度実行してください。")
            print("!" * 50 + "\n")
            return False

    def run_likes(self):
        """いいね巡回メインロジック"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Substackにアクセスしています...")
        self.driver.get("https://substack.com/home")
        time.sleep(8)

        if "login" in self.driver.current_url or "sign-in" in self.driver.current_url:
            print("【警告】ログインが確認できませんでした。ブラウザで一度ログインを済ませてください。")
            return

        print(f"[{datetime.now().strftime('%H:%M:%S')}] ログインを確認しました。巡回を開始します...")

        scroll_count = 0
        while self.likes_done < MAX_LIKES and scroll_count < 20:
            try:
                buttons = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    'button[aria-label*="like"], button[aria-label*="いいね"]',
                )

                for btn in buttons:
                    if self.likes_done >= MAX_LIKES:
                        break

                    try:
                        if btn.get_attribute("aria-pressed") == "true":
                            continue

                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({block: 'center'});", btn
                        )
                        time.sleep(2)

                        btn.click()
                        self.likes_done += 1

                        ts = datetime.now().strftime("%H:%M:%S")
                        print(f"[{ts}] SUCCESS: {self.likes_done}件目のいいねをしました")

                        wait_time = random.uniform(MIN_WAIT, MAX_WAIT)
                        print(f"   (次の操作まで {wait_time:.1f}秒 待機中...)")
                        time.sleep(wait_time)
                    except Exception:
                        continue

                self.driver.execute_script("window.scrollBy(0, 800);")
                scroll_count += 1
                time.sleep(3)

            except Exception as e:
                print(f"ループ中にエラーが発生しました: {e}")
                break

        print("\n" + "=" * 50)
        print(f"実行完了: 合計 {self.likes_done} 件のいいねをしました。")
        print("=" * 50)

    def close(self):
        """ブラウザを閉じる"""
        if self.driver:
            self.driver.quit()


if __name__ == "__main__":
    engine = SubstackSelenium()
    if engine.setup():
        try:
            engine.run_likes()
        except KeyboardInterrupt:
            print("\n中断されました。")
        finally:
            engine.close()
            print("ツールを終了しました。")
