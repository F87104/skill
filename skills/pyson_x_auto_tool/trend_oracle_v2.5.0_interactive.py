#!/usr/bin/env python3
"""
Trend Oracle v2.5.0 - Interactive Edition
==========================================
API設定を対話形式で入力できるようにした初心者向けバージョン

【変更点】
- APIキーが未設定の場合、わかりやすいガイド付きで入力を求める
- エラー時も丁寧なメッセージで再入力を促す
- ニュースのキーワードも対話形式で入力可能

【使い方】
python3 ~/prometheus/trend_oracle_v2.5.0_interactive.py --mode post
python3 ~/prometheus/trend_oracle_v2.5.0_interactive.py --mode infographic
"""

import os
import sys
import argparse
import json
from pathlib import Path

try:
    from openai import OpenAI, AuthenticationError, APIConnectionError
except ImportError:
    print("\n" + "=" * 60)
    print("エラー: OpenAIライブラリがインストールされていません。")
    print("=" * 60)
    print("\n以下のコマンドでインストールしてください：")
    print("\n  pip3 install openai\n")
    sys.exit(1)

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

# ===== プロンプト読み込み =====
def load_prompt(filename):
    prompt_path = SCRIPT_DIR / filename
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        log_error(f"プロンプトファイル '{prompt_path}' が見つかりません。")
        log_error("スクリプトと同じフォルダにプロンプトファイルがあるか確認してください。")
        sys.exit(1)

# ===== API設定の対話入力 =====
def show_api_setup_guide():
    """APIキー取得方法のガイドを表示"""
    print("\n" + "=" * 60)
    print(f"{Colors.CYAN}{Colors.BOLD}📌 OpenAI APIキーの設定{Colors.RESET}")
    print("=" * 60)
    print("""
APIキーが設定されていません。以下の手順で取得してください：

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
    print(f"{Colors.YELLOW}※ APIキーは一度しか表示されません。必ずコピーしてください。{Colors.RESET}")
    print(f"{Colors.YELLOW}※ APIの利用には料金がかかります（少額から利用可能）。{Colors.RESET}")
    print()

def get_api_key_interactive():
    """対話形式でAPIキーを取得"""
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
                log_error("入力が空です。APIキーを入力してください。")
                continue
            
            if not api_key.startswith("sk-"):
                log_error("無効な形式です。APIキーは 'sk-' で始まります。")
                print(f"\n{Colors.YELLOW}例: sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx{Colors.RESET}\n")
                continue
            
            # キャッシュに保存
            try:
                with open(API_KEY_CACHE_FILE, 'w') as f:
                    f.write(api_key)
                log_success(f"APIキーを保存しました。次回から自動で読み込まれます。")
            except Exception as e:
                log_warning(f"APIキーの保存に失敗しました: {e}")
            
            return api_key
            
        except KeyboardInterrupt:
            print("\n")
            log_info("キャンセルしました。")
            sys.exit(0)
        except EOFError:
            print("\n")
            log_error("入力エラーが発生しました。")
            sys.exit(1)

def test_api_connection(api_key):
    """API接続をテスト"""
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
        log_error("APIキーが無効です。")
        print(f"\n{Colors.YELLOW}考えられる原因：{Colors.RESET}")
        print("  - APIキーが間違っている")
        print("  - APIキーが無効化されている")
        print("  - 支払い情報が未設定")
        print()
        # キャッシュを削除
        API_KEY_CACHE_FILE.unlink(missing_ok=True)
        return None
    except APIConnectionError as e:
        log_error(f"APIサーバーに接続できませんでした。")
        print(f"\n{Colors.YELLOW}考えられる原因：{Colors.RESET}")
        print("  - インターネット接続がない")
        print("  - OpenAIサーバーが一時的にダウン")
        print()
        return None
    except Exception as e:
        log_error(f"予期せぬエラーが発生しました: {e}")
        return None

def get_news_keyword_interactive():
    """対話形式でニュースキーワードを取得"""
    print("\n" + "=" * 60)
    print(f"{Colors.CYAN}{Colors.BOLD}📰 ニュースキーワードの入力{Colors.RESET}")
    print("=" * 60)
    print("""
投稿を生成したいニュースや話題を入力してください。

┌─────────────────────────────────────────────────────────┐
│ 【入力例】                                              │
│                                                         │
│ ・日銀が金利を引き上げ                                 │
│ ・ドル円が150円を突破                                  │
│ ・米国株が大幅下落                                     │
│ ・日経平均が4万円台回復                                │
│ ・FRBがハト派姿勢に転換                                │
└─────────────────────────────────────────────────────────┘
""")
    
    while True:
        try:
            print(f"{Colors.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.RESET}")
            keyword = input(f"{Colors.BOLD}ニュースを入力してください: {Colors.RESET}").strip()
            print(f"{Colors.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.RESET}")
            
            if not keyword:
                log_error("入力が空です。ニュースを入力してください。")
                continue
            
            if len(keyword) < 5:
                log_warning("入力が短すぎます。もう少し詳しく入力してください。")
                continue
            
            return keyword
            
        except KeyboardInterrupt:
            print("\n")
            log_info("キャンセルしました。")
            sys.exit(0)

# ===== プロンプト生成関数 =====
def generate_post(openai_client, trend, prompt_template):
    log_info("投稿を生成中...")
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
        final_post = f"{post_body}\n\n投資家Fより💌"
        log_success("投稿が生成されました！")
        print(f"\n{'='*60}")
        print(f"{Colors.CYAN}{Colors.BOLD}📝 生成された投稿{Colors.RESET}")
        print(f"{'='*60}")
        print(f"\n{final_post}\n")
        print(f"{'='*60}\n")
        
        # コピー用にも表示
        print(f"{Colors.YELLOW}↑ この投稿をコピーしてXに貼り付けてください{Colors.RESET}\n")
        
    except Exception as e:
        log_error(f"投稿生成中にエラーが発生しました: {e}")

def generate_infographic(openai_client, trend, infographic_template):
    log_info("図解用コンテンツを生成中...")
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
        print(f"\n{'='*60}")
        print(f"{Colors.MAGENTA}{Colors.BOLD}🎨 図解生成用プロンプト（AIに貼り付け）{Colors.RESET}")
        print(f"{'='*60}")
        print(f"\n{infographic_prompt}\n")
        print(f"{'='*60}")
        print(f"\n{Colors.CYAN}{copy_text}{Colors.RESET}")
        
    except json.JSONDecodeError as e:
        log_error(f"レスポンスの解析に失敗しました: {e}")
    except Exception as e:
        log_error(f"図解生成中にエラーが発生しました: {e}")

# ===== メイン処理 =====
def main():
    parser = argparse.ArgumentParser(
        description="Trend Oracle v2.5.0 - Interactive Edition",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python3 trend_oracle_v2.5.0_interactive.py --mode post         # 投稿を生成
  python3 trend_oracle_v2.5.0_interactive.py --mode infographic  # 図解用コンテンツを生成
        """
    )
    parser.add_argument('--mode', type=str, choices=['post', 'infographic'], default='post', 
                        help="生成モードを選択 (post=投稿, infographic=図解)")
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print(f"{Colors.BOLD}{Colors.BLUE}🔮 Trend Oracle v2.5.0 - Interactive Edition{Colors.RESET}")
    print(f"   モード: {Colors.CYAN}{'投稿生成' if args.mode == 'post' else '図解生成'}{Colors.RESET}")
    print("=" * 60)
    
    # プロンプトファイルを読み込み
    post_prompt_template = load_prompt("post_prompt.txt")
    infographic_prompt_template = load_prompt("infographic_prompt.txt")

    # API接続（対話形式）
    openai_client = None
    retry_count = 0
    max_retries = 3
    
    while not openai_client:
        api_key = get_api_key_interactive()
        openai_client = test_api_connection(api_key)
        
        if not openai_client:
            retry_count += 1
            if retry_count >= max_retries:
                log_error("API接続に3回失敗しました。")
                print(f"\n{Colors.YELLOW}ヒント: APIキーが正しいか、支払い情報が設定されているか確認してください。{Colors.RESET}")
                print(f"{Colors.YELLOW}OpenAIダッシュボード: https://platform.openai.com{Colors.RESET}\n")
                sys.exit(1)
            print(f"\n{Colors.YELLOW}再試行してください（{retry_count}/{max_retries}）{Colors.RESET}\n")

    # ニュースキーワードを対話形式で取得
    keyword = get_news_keyword_interactive()
    trend = {"keyword": keyword, "type": "news", "source": "ユーザー入力"}

    # 生成実行
    if args.mode == 'post':
        generate_post(openai_client, trend, post_prompt_template)
    elif args.mode == 'infographic':
        generate_infographic(openai_client, trend, infographic_prompt_template)
    
    print(f"{Colors.GREEN}✅ 処理が完了しました！{Colors.RESET}\n")

if __name__ == "__main__":
    main()
