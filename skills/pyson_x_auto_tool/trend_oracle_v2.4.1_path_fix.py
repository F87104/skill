#!/usr/bin/env python3
"""
Trend Oracle v2.4.1 - Path Fix
================================
プロンプトファイルのパス問題を修正したバージョン
"""

import os
import sys
import argparse
import json
from pathlib import Path
from openai import OpenAI, AuthenticationError, APIConnectionError

# ===== 定数 =====
SCRIPT_DIR = Path(__file__).parent
API_KEY_CACHE_FILE = Path.home() / ".prometheus_api_key_cache"

# ===== カラー出力 =====
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    RESET = '\033[0m'

def log_info(msg):
    print(f"[INFO] {msg}")

def log_success(msg):
    print(f"{Colors.GREEN}[SUCCESS] {msg}{Colors.RESET}")

def log_warning(msg):
    print(f"{Colors.YELLOW}[WARNING] {msg}{Colors.RESET}")

def log_error(msg):
    print(f"{Colors.RED}[ERROR] {msg}{Colors.RESET}")

# ===== プロンプト読み込み =====
def load_prompt(filename):
    # スクリプトと同じディレクトリにあるプロンプトファイルを読み込む
    prompt_path = SCRIPT_DIR / filename
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        log_error(f"プロンプトファイル '{prompt_path}' が見つかりません。")
        log_error("スクリプトと同じフォルダにプロンプトファイルがあるか確認してください。")
        sys.exit(1)

# ===== API関連関数 =====
def get_api_key():
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        log_info("環境変数からAPIキーを読み込みました。")
        return api_key

    if API_KEY_CACHE_FILE.exists():
        with open(API_KEY_CACHE_FILE, 'r') as f:
            api_key = f.read().strip()
            if api_key:
                log_info("キャッシュからAPIキーを読み込みました。")
                return api_key

    while True:
        log_warning("APIキーが設定されていません。")
        try:
            api_key = input(f"{Colors.YELLOW}OpenAI APIキーを入力してください: {Colors.RESET}")
            if api_key.startswith("sk-"):
                with open(API_KEY_CACHE_FILE, 'w') as f:
                    f.write(api_key)
                log_info(f"APIキーをキャッシュしました ({API_KEY_CACHE_FILE})。")
                return api_key
            else:
                log_error("無効な形式です。'sk-'で始まるキーを入力してください。")
        except (KeyboardInterrupt, EOFError):
            log_error("入力をキャンセルしました。")
            sys.exit(1)

def test_api_connection(api_key):
    log_info("OpenAI APIへの接続をテスト中...")
    try:
        client = OpenAI(api_key=api_key, max_retries=1, timeout=15.0)
        client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5
        )
        log_success("API接続に成功しました！")
        return client
    except AuthenticationError:
        log_error("APIキーが無効です。キャッシュを削除して再試行します。")
        API_KEY_CACHE_FILE.unlink(missing_ok=True)
        return None
    except APIConnectionError as e:
        log_error(f"APIサーバーに接続できませんでした: {e.__cause__}")
        return None
    except Exception as e:
        log_error(f"予期せぬエラーが発生しました: {e}")
        return None

# ===== プロンプト生成関数 =====
def generate_post(openai_client, trend, prompt_template):
    log_info("完全固定構成プロンプトに基づいて投稿を生成します...")
    user_prompt = f"以下のニュースについて、ルールを厳守して投稿を作成してください。\n\n【ニュース】\n{trend['keyword']}"
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt_template},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=300,
            temperature=0.7
        )
        post_body = response.choices[0].message.content.strip()
        final_post = f"POST_TEXT\n{post_body}\n\n投資家Fより💌"
        log_success("Fらしい投稿が生成されました！")
        print(f"\n--- 生成された投稿 ---\n{Colors.CYAN}{final_post}{Colors.RESET}\n--------------------\n")
    except Exception as e:
        log_error(f"投稿生成中にエラーが発生しました: {e}")

def generate_infographic(openai_client, trend, infographic_template):
    log_info("図解用プロンプトのコンテンツを生成します (JSONモード活用)...")
    content_gen_prompt = f'''
    あなたは優秀な編集者です。以下のニュースを、中学2年生でも理解できるように、指定されたJSON形式で分解・要約してください。

    【ニュース】
    {trend['keyword']}

    【JSONフォーマット】
    {{
        "headline": "ニュースを一言で表す、キャッチーなタイトル（20文字以内）",
        "cause": "このニュースが起きた背景やきっかけ（30文字以内）",
        "situation": "今、何がどうなっているのか（40文字以内）",
        "result": "これからどうなりそうか、どんな影響がありそうか（30文字以内）",
        "point1": "注目すべき点その1（25文字以内）",
        "point2": "注目すべき点その2（25文字以内）",
        "point3": "注目すべき点その3（25文字以内）",
        "f_comment": "投資家Fとして、読者に語りかける一言（30文字以内）"
    }}

    【ルール】
    - 抽象的な言葉は使わない
    - 因果関係がわかるように書く
    - 売買推奨や投資助言は絶対にしない
    - 断定的な表現は避ける（「〜かも」「〜の可能性」）
    '''
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "あなたはJSONを出力するAIです。"},
                {"role": "user", "content": content_gen_prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        content_dict = json.loads(response.choices[0].message.content)

        infographic_prompt = infographic_template.format(
            HEADLINE=content_dict.get("headline", ""),
            CAUSE=content_dict.get("cause", ""),
            SITUATION=content_dict.get("situation", ""),
            RESULT=content_dict.get("result", ""),
            POINT1=content_dict.get("point1", ""),
            POINT2=content_dict.get("point2", ""),
            POINT3=content_dict.get("point3", ""),
            F_COMMENT=content_dict.get("f_comment", "")
        )

        copy_text = f'''
# COPY_TEXT

## 大見出し
{content_dict.get("headline", "")}

## 原因は？🤔
{content_dict.get("cause", "")}

## 今どうなってるの？🗺️
{content_dict.get("situation", "")}

## どうなるの？→
{content_dict.get("result", "")}

## 💡 3つのポイント
- POINT 1: {content_dict.get("point1", "")}
- POINT 2: {content_dict.get("point2", "")}
- POINT 3: {content_dict.get("point3", "")}

## 💬 Fのコメント
{content_dict.get("f_comment", "")}
'''
        log_success("図解用プロンプトが生成されました！")
        print(f"\n{Colors.MAGENTA}{infographic_prompt}{Colors.RESET}")
        print(f"\n{Colors.CYAN}{copy_text}{Colors.RESET}")

    except json.JSONDecodeError as e:
        log_error(f"LLMからのJSONレスポンスのパースに失敗しました: {e}")
    except Exception as e:
        log_error(f"図解プロンプト生成中にエラーが発生しました: {e}")

# ===== メイン処理 =====
def main():
    parser = argparse.ArgumentParser(description="Trend Oracle v2.4.1 - Path Fix")
    parser.add_argument('--mode', type=str, choices=['post', 'infographic'], default='post', help="生成モードを選択")
    args = parser.parse_args()

    print(f"\n--- Trend Oracle v2.4.1 Path Fix --- (Mode: {args.mode})")
    
    post_prompt_template = load_prompt("post_prompt.txt")
    infographic_prompt_template = load_prompt("infographic_prompt.txt")

    openai_client = None
    while not openai_client:
        api_key = get_api_key()
        openai_client = test_api_connection(api_key)

    dummy_trend = {"keyword": "日本の株式市場、今後の見通し", "type": "news", "source": "内部生成"}

    if args.mode == 'post':
        generate_post(openai_client, dummy_trend, post_prompt_template)
    elif args.mode == 'infographic':
        generate_infographic(openai_client, dummy_trend, infographic_prompt_template)

if __name__ == "__main__":
    main()
