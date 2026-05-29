#!/usr/bin/env python3
"""
Trend Oracle v2.5.1 - Robust Edition
=====================================
API接続エラーに強い堅牢なバージョン

【エラー対策】
1. 複数のAPIエンドポイントに対応
2. タイムアウト時間を延長
3. リトライ機能を強化
4. 詳細なエラー診断
5. 手動でAPIキーを再入力可能

【使い方】
python3 ~/prometheus/trend_oracle_v2.5.1_robust.py --mode post
python3 ~/prometheus/trend_oracle_v2.5.1_robust.py --mode infographic
"""

import os
import sys
import argparse
import json
import time
import socket
from pathlib import Path

# OpenAIライブラリのインポート
try:
    from openai import OpenAI, AuthenticationError, APIConnectionError, RateLimitError, APITimeoutError
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# requestsライブラリ（フォールバック用）
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

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
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def log_info(msg):
    print(f"[INFO] {msg}")

def log_success(msg):
    print(f"{Colors.GREEN}[SUCCESS] {msg}{Colors.RESET}")

def log_warning(msg):
    print(f"{Colors.YELLOW}[WARNING] {msg}{Colors.RESET}")

def log_error(msg):
    print(f"{Colors.RED}[ERROR] {msg}{Colors.RESET}")

def log_debug(msg):
    print(f"{Colors.CYAN}[DEBUG] {msg}{Colors.RESET}")

# ===== ネットワーク診断 =====
def check_internet_connection():
    """インターネット接続を確認"""
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=5)
        return True
    except OSError:
        return False

def check_openai_reachable():
    """OpenAI APIサーバーへの到達性を確認"""
    try:
        socket.create_connection(("api.openai.com", 443), timeout=10)
        return True
    except OSError:
        return False

def diagnose_network():
    """ネットワーク診断を実行"""
    print(f"\n{Colors.CYAN}🔍 ネットワーク診断を実行中...{Colors.RESET}")
    
    internet_ok = check_internet_connection()
    print(f"  インターネット接続: {'✅ OK' if internet_ok else '❌ NG'}")
    
    if internet_ok:
        openai_ok = check_openai_reachable()
        print(f"  OpenAIサーバー到達: {'✅ OK' if openai_ok else '❌ NG'}")
        return openai_ok
    
    return False

# ===== プロンプト読み込み =====
def load_prompt(filename):
    prompt_path = SCRIPT_DIR / filename
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        log_error(f"プロンプトファイル '{prompt_path}' が見つかりません。")
        sys.exit(1)

# ===== APIキー管理 =====
def show_api_setup_guide():
    """APIキー取得方法のガイドを表示"""
    print("\n" + "=" * 60)
    print(f"{Colors.CYAN}{Colors.BOLD}📌 OpenAI APIキーの設定{Colors.RESET}")
    print("=" * 60)
    print("""
┌─────────────────────────────────────────────────────────┐
│ 【APIキーの取得方法】                                   │
│                                                         │
│ 1. https://platform.openai.com にアクセス              │
│ 2. ログイン（アカウントがなければ作成）                │
│ 3. 右上のアイコン → 「API keys」をクリック            │
│ 4. 「Create new secret key」をクリック                 │
│ 5. 表示されたキー（sk-で始まる文字列）をコピー        │
└─────────────────────────────────────────────────────────┘
""")

def get_api_key_interactive(force_input=False):
    """対話形式でAPIキーを取得"""
    
    if not force_input:
        # 1. 環境変数をチェック
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key and api_key.startswith("sk-"):
            log_info("環境変数からAPIキーを読み込みました。")
            return api_key

        # 2. キャッシュファイルをチェック
        if API_KEY_CACHE_FILE.exists():
            try:
                with open(API_KEY_CACHE_FILE, 'r') as f:
                    api_key = f.read().strip()
                    if api_key and api_key.startswith("sk-"):
                        log_info("保存済みのAPIキーを読み込みました。")
                        return api_key
            except:
                pass

    # 3. 対話形式で入力を求める
    show_api_setup_guide()
    
    while True:
        try:
            print(f"{Colors.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.RESET}")
            api_key = input(f"{Colors.BOLD}OpenAI APIキーを入力してください: {Colors.RESET}").strip()
            print(f"{Colors.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.RESET}")
            
            if not api_key:
                log_error("入力が空です。")
                continue
            
            if not api_key.startswith("sk-"):
                log_error("APIキーは 'sk-' で始まります。")
                continue
            
            # キャッシュに保存
            try:
                with open(API_KEY_CACHE_FILE, 'w') as f:
                    f.write(api_key)
                log_success("APIキーを保存しました。")
            except:
                pass
            
            return api_key
            
        except KeyboardInterrupt:
            print("\n")
            sys.exit(0)

# ===== API接続（堅牢版） =====
def call_openai_api_robust(api_key, messages, max_tokens=300, temperature=0.7, json_mode=False):
    """
    堅牢なOpenAI API呼び出し
    - 複数回リトライ
    - タイムアウト延長
    - 詳細なエラーハンドリング
    """
    
    # 方法1: OpenAIライブラリを使用
    if OPENAI_AVAILABLE:
        for attempt in range(3):
            try:
                log_info(f"API呼び出し中... (試行 {attempt + 1}/3)")
                
                client = OpenAI(
                    api_key=api_key,
                    timeout=60.0,  # タイムアウトを60秒に延長
                    max_retries=2
                )
                
                kwargs = {
                    "model": "gpt-4o-mini",
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature
                }
                
                if json_mode:
                    kwargs["response_format"] = {"type": "json_object"}
                
                response = client.chat.completions.create(**kwargs)
                return response.choices[0].message.content.strip()
                
            except AuthenticationError:
                log_error("APIキーが無効です。")
                return None
            except RateLimitError:
                log_warning("レート制限に達しました。30秒待機します...")
                time.sleep(30)
                continue
            except APITimeoutError:
                log_warning(f"タイムアウト。リトライします... ({attempt + 1}/3)")
                time.sleep(5)
                continue
            except APIConnectionError as e:
                log_warning(f"接続エラー: {e}")
                if attempt < 2:
                    log_info("5秒後にリトライします...")
                    time.sleep(5)
                continue
            except Exception as e:
                log_error(f"予期せぬエラー: {e}")
                if attempt < 2:
                    time.sleep(5)
                continue
    
    # 方法2: requestsライブラリを使用（フォールバック）
    if REQUESTS_AVAILABLE:
        log_info("代替方法（requests）で接続を試みます...")
        
        for attempt in range(3):
            try:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                
                data = {
                    "model": "gpt-4o-mini",
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature
                }
                
                if json_mode:
                    data["response_format"] = {"type": "json_object"}
                
                response = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=60
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result["choices"][0]["message"]["content"].strip()
                elif response.status_code == 401:
                    log_error("APIキーが無効です。")
                    return None
                elif response.status_code == 429:
                    log_warning("レート制限。30秒待機...")
                    time.sleep(30)
                    continue
                else:
                    log_error(f"APIエラー: {response.status_code} - {response.text}")
                    
            except requests.exceptions.Timeout:
                log_warning(f"タイムアウト ({attempt + 1}/3)")
                time.sleep(5)
            except requests.exceptions.ConnectionError:
                log_warning(f"接続エラー ({attempt + 1}/3)")
                time.sleep(5)
            except Exception as e:
                log_error(f"エラー: {e}")
                time.sleep(5)
    
    return None

def test_api_connection_robust(api_key):
    """堅牢なAPI接続テスト"""
    log_info("API接続をテスト中...")
    
    result = call_openai_api_robust(
        api_key,
        [{"role": "user", "content": "Say OK"}],
        max_tokens=5
    )
    
    if result:
        log_success("API接続に成功しました！")
        return True
    else:
        return False

# ===== ニュースキーワード入力 =====
def get_news_keyword_interactive():
    """対話形式でニュースキーワードを取得"""
    print("\n" + "=" * 60)
    print(f"{Colors.CYAN}{Colors.BOLD}📰 ニュースキーワードの入力{Colors.RESET}")
    print("=" * 60)
    print("""
【入力例】
・日銀が金利を引き上げ
・ドル円が150円を突破
・米国株が大幅下落
""")
    
    while True:
        try:
            keyword = input(f"{Colors.BOLD}ニュースを入力: {Colors.RESET}").strip()
            
            if not keyword:
                log_error("入力が空です。")
                continue
            
            if len(keyword) < 3:
                log_warning("もう少し詳しく入力してください。")
                continue
            
            return keyword
            
        except KeyboardInterrupt:
            print("\n")
            sys.exit(0)

# ===== 生成関数 =====
def generate_post(api_key, trend, prompt_template):
    log_info("投稿を生成中...")
    
    messages = [
        {"role": "system", "content": prompt_template},
        {"role": "user", "content": f"以下のニュースについて投稿を作成:\n\n{trend['keyword']}"}
    ]
    
    result = call_openai_api_robust(api_key, messages, max_tokens=300)
    
    if result:
        final_post = f"{result}\n\n投資家Fより💌"
        log_success("投稿が生成されました！")
        print(f"\n{'='*60}")
        print(f"{Colors.CYAN}{Colors.BOLD}📝 生成された投稿{Colors.RESET}")
        print(f"{'='*60}")
        print(f"\n{final_post}\n")
        print(f"{'='*60}")
        print(f"\n{Colors.YELLOW}↑ この投稿をコピーしてXに貼り付けてください{Colors.RESET}\n")
        return True
    else:
        log_error("投稿の生成に失敗しました。")
        return False

def generate_infographic(api_key, trend, infographic_template):
    log_info("図解用コンテンツを生成中...")
    
    content_gen_prompt = f'''
あなたは優秀な編集者です。以下のニュースをJSON形式で分解してください。

【ニュース】
{trend['keyword']}

【JSONフォーマット】
{{
    "headline": "タイトル（20文字以内）",
    "cause": "背景（30文字以内）",
    "situation": "現状（40文字以内）",
    "result": "今後の影響（30文字以内）",
    "point1": "ポイント1（25文字以内）",
    "point2": "ポイント2（25文字以内）",
    "point3": "ポイント3（25文字以内）",
    "f_comment": "Fのコメント（30文字以内）"
}}
'''
    
    messages = [
        {"role": "system", "content": "JSONを出力するAIです。"},
        {"role": "user", "content": content_gen_prompt}
    ]
    
    result = call_openai_api_robust(api_key, messages, max_tokens=500, json_mode=True)
    
    if result:
        try:
            content_dict = json.loads(result)
            
            copy_text = f'''
📊 図解用テキスト
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【大見出し】
{content_dict.get("headline", "")}

【原因は？🤔】
{content_dict.get("cause", "")}

【今どうなってるの？🗺️】
{content_dict.get("situation", "")}

【どうなるの？→】
{content_dict.get("result", "")}

【💡 3つのポイント】
① {content_dict.get("point1", "")}
② {content_dict.get("point2", "")}
③ {content_dict.get("point3", "")}

【💬 Fのコメント】
{content_dict.get("f_comment", "")}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
'''
            log_success("図解用コンテンツが生成されました！")
            print(f"\n{Colors.CYAN}{copy_text}{Colors.RESET}")
            return True
            
        except json.JSONDecodeError:
            log_error("JSONの解析に失敗しました。")
            return False
    else:
        log_error("図解の生成に失敗しました。")
        return False

# ===== メイン処理 =====
def main():
    parser = argparse.ArgumentParser(description="Trend Oracle v2.5.1 - Robust Edition")
    parser.add_argument('--mode', type=str, choices=['post', 'infographic'], default='post')
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print(f"{Colors.BOLD}{Colors.BLUE}🔮 Trend Oracle v2.5.1 - Robust Edition{Colors.RESET}")
    print(f"   モード: {Colors.CYAN}{'投稿生成' if args.mode == 'post' else '図解生成'}{Colors.RESET}")
    print("=" * 60)
    
    # ライブラリチェック
    if not OPENAI_AVAILABLE and not REQUESTS_AVAILABLE:
        log_error("必要なライブラリがインストールされていません。")
        print("\n以下のコマンドでインストールしてください：")
        print("  pip3 install openai requests\n")
        sys.exit(1)
    
    # プロンプトファイルを読み込み
    post_prompt_template = load_prompt("post_prompt.txt")
    infographic_prompt_template = load_prompt("infographic_prompt.txt")

    # ネットワーク診断
    if not diagnose_network():
        log_error("ネットワークに問題があります。")
        print(f"\n{Colors.YELLOW}対処法：{Colors.RESET}")
        print("  1. インターネット接続を確認してください")
        print("  2. VPNを使用している場合は一度オフにしてみてください")
        print("  3. しばらく待ってから再試行してください\n")
        
        retry = input("それでも続行しますか？ (y/n): ").strip().lower()
        if retry != 'y':
            sys.exit(1)

    # APIキー取得と接続テスト
    api_key = None
    force_input = False
    max_attempts = 3
    
    for attempt in range(max_attempts):
        api_key = get_api_key_interactive(force_input=force_input)
        
        if test_api_connection_robust(api_key):
            break
        else:
            log_error(f"API接続に失敗しました。({attempt + 1}/{max_attempts})")
            
            if attempt < max_attempts - 1:
                print(f"\n{Colors.YELLOW}オプション:{Colors.RESET}")
                print("  1. 別のAPIキーを入力する")
                print("  2. リトライする")
                print("  3. 終了する")
                
                choice = input("\n選択 (1/2/3): ").strip()
                
                if choice == '1':
                    force_input = True
                    API_KEY_CACHE_FILE.unlink(missing_ok=True)
                elif choice == '3':
                    sys.exit(1)
                # choice == '2' または他の入力は自動リトライ
            else:
                log_error("API接続に失敗しました。")
                print(f"\n{Colors.YELLOW}考えられる原因：{Colors.RESET}")
                print("  - APIキーが無効または期限切れ")
                print("  - OpenAIアカウントの支払い情報が未設定")
                print("  - ネットワークの問題")
                print(f"\n{Colors.CYAN}OpenAIダッシュボード: https://platform.openai.com{Colors.RESET}\n")
                sys.exit(1)

    # ニュースキーワードを取得
    keyword = get_news_keyword_interactive()
    trend = {"keyword": keyword}

    # 生成実行
    success = False
    if args.mode == 'post':
        success = generate_post(api_key, trend, post_prompt_template)
    elif args.mode == 'infographic':
        success = generate_infographic(api_key, trend, infographic_prompt_template)
    
    if success:
        print(f"{Colors.GREEN}✅ 処理が完了しました！{Colors.RESET}\n")
    else:
        print(f"{Colors.RED}❌ 処理に失敗しました。{Colors.RESET}\n")

if __name__ == "__main__":
    main()
