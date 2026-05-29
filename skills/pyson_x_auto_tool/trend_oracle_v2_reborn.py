#!/usr/bin/env python3
"""
Trend Oracle v2.0 - Reborn
==========================
ゼロから完全に再設計した、確実に動作するバージョン
"""

import os
import sys
from openai import OpenAI, AuthenticationError, APIConnectionError

# ===== カラー出力 =====
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'

def log_info(msg):
    print(f"[INFO] {msg}")

def log_success(msg):
    print(f"{Colors.GREEN}[SUCCESS] {msg}{Colors.RESET}")

def log_warning(msg):
    print(f"{Colors.YELLOW}[WARNING] {msg}{Colors.RESET}")

def log_error(msg):
    print(f"{Colors.RED}[ERROR] {msg}{Colors.RESET}")

def get_api_key():
    """APIキーを取得する関数"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        log_info("環境変数からAPIキーを読み込みました。")
        return api_key
    
    while True:
        log_warning("APIキーが設定されていません。")
        try:
            api_key = input("OpenAI APIキーを入力してください: ")
            if api_key.startswith("sk-"):
                return api_key
            else:
                log_error("無効な形式です。'sk-'で始まるキーを入力してください。")
        except (KeyboardInterrupt, EOFError):
            log_error("入力をキャンセルしました。")
            sys.exit(1)

def test_api_connection(api_key):
    """API接続をテストする関数"""
    log_info("OpenAI APIへの接続をテスト中...")
    try:
        client = OpenAI(api_key=api_key, max_retries=1, timeout=10.0)
        client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5
        )
        log_success("API接続に成功しました！")
        return client
    except AuthenticationError:
        log_error("APIキーが無効です。正しいキーを入力してください。")
        return None
    except APIConnectionError as e:
        log_error(f"APIサーバーに接続できませんでした: {e.__cause__}")
        log_error("ネットワーク設定（VPN、ファイアウォール）を確認してください。")
        return None
    except Exception as e:
        log_error(f"予期せぬエラーが発生しました: {e}")
        return None

def main():
    """メイン処理"""
    print("\n--- Trend Oracle v2.0 ---")
    
    # 1. APIキーの取得とテスト
    openai_client = None
    while not openai_client:
        api_key = get_api_key()
        openai_client = test_api_connection(api_key)
        if not openai_client:
            # 環境変数が間違っている可能性もあるので、一度クリアする
            os.environ.pop("OPENAI_API_KEY", None)

    # 2. 投稿生成
    log_info("投稿を生成します...")
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "日本の株式市場について、投資家向けの短いコメントを生成してください。"}],
            max_tokens=150
        )
        post = response.choices[0].message.content.strip()
        log_success("投稿が生成されました！")
        print("\n--- 生成された投稿 ---")
        print(post)
        print("--------------------\n")
    except Exception as e:
        log_error(f"投稿生成中にエラーが発生しました: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
