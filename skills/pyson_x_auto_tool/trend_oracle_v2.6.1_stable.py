#!/usr/bin/env python3
"""
Trend Oracle v2.6.1 - Stable Edition
=====================================
話題のニュースを自動取得して、Fらしい投稿文を生成
Mac環境で確実に動作する安定版

【使い方】
python3 ~/prometheus/trend_oracle_v2.6.1_stable.py
python3 ~/prometheus/trend_oracle_v2.6.1_stable.py --mode infographic
"""

import os
import sys
import argparse
import json
import time
import re
from pathlib import Path
from datetime import datetime

# requestsライブラリ
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# OpenAIライブラリ
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

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
        return get_default_prompt()

def get_default_prompt():
    return """あなたは「投資家F」というペルソナで投稿を作成します。

【投資家Fの特徴】
- 親しみやすく、フレンドリーな口調
- 難しいことを簡単に説明する
- 読者に寄り添う姿勢
- 絵文字を適度に使用
- 140文字程度で簡潔に

【ルール】
- 売買推奨や投資助言は絶対にしない
- 断定的な表現は避ける（「〜かも」「〜の可能性」）
- ポジティブな視点を心がける
- 読者が「なるほど」と思える内容に"""

# ===== ニュース取得機能（安定版）=====
def fetch_yahoo_finance_news():
    """Yahoo!ファイナンスからニュースを取得（複数URLを試行）"""
    news_list = []
    
    urls_to_try = [
        "https://finance.yahoo.co.jp/news",
        "https://news.yahoo.co.jp/categories/business",
        "https://news.yahoo.co.jp/topics/business",
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
    }
    
    for url in urls_to_try:
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                # HTMLからニュースタイトルを抽出（正規表現で）
                html = response.text
                
                # 様々なパターンでタイトルを抽出
                patterns = [
                    r'<a[^>]*href="[^"]*news[^"]*"[^>]*>([^<]{15,80})</a>',
                    r'<h[23][^>]*>([^<]{15,80})</h[23]>',
                    r'title="([^"]{15,80})"',
                ]
                
                seen = set()
                for pattern in patterns:
                    matches = re.findall(pattern, html)
                    for title in matches:
                        title = title.strip()
                        # 投資関連キーワードでフィルタ
                        keywords = ['円', '株', '日経', '金利', '経済', '市場', '投資', 'ドル', '為替', '日銀', '米国', '中国']
                        if any(kw in title for kw in keywords) and title not in seen:
                            seen.add(title)
                            news_list.append({
                                'title': title,
                                'description': '',
                                'source': 'Yahoo!ニュース'
                            })
                            if len(news_list) >= 10:
                                break
                    if len(news_list) >= 10:
                        break
                
                if news_list:
                    break
                    
        except Exception as e:
            continue
    
    return news_list

def fetch_google_news():
    """Googleニュースから投資関連ニュースを取得"""
    news_list = []
    
    try:
        # Google News RSS（日本語・ビジネス）
        url = "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtcGhHZ0pLVUNnQVAB?hl=ja&gl=JP&ceid=JP:ja"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            # XMLをシンプルな正規表現で解析（lxmlなしで動作）
            content = response.text
            
            # <title>タグを抽出
            titles = re.findall(r'<title><!\[CDATA\[(.*?)\]\]></title>', content)
            if not titles:
                titles = re.findall(r'<title>(.*?)</title>', content)
            
            seen = set()
            for title in titles[1:]:  # 最初はフィード名なのでスキップ
                title = title.strip()
                # HTMLエンティティをデコード
                title = title.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
                
                if len(title) > 10 and title not in seen:
                    seen.add(title)
                    news_list.append({
                        'title': title[:80],  # 長すぎる場合は切り詰め
                        'description': '',
                        'source': 'Googleニュース'
                    })
                    if len(news_list) >= 10:
                        break
                        
    except Exception as e:
        pass
    
    return news_list

def fetch_investing_news():
    """Investing.comからニュースを取得"""
    news_list = []
    
    try:
        url = "https://jp.investing.com/news/economy"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            html = response.text
            
            # 記事タイトルを抽出
            patterns = [
                r'<a[^>]*class="[^"]*title[^"]*"[^>]*>([^<]{15,100})</a>',
                r'data-test="article-title"[^>]*>([^<]{15,100})<',
                r'<h[23][^>]*>([^<]{15,100})</h[23]>',
            ]
            
            seen = set()
            for pattern in patterns:
                matches = re.findall(pattern, html)
                for title in matches:
                    title = title.strip()
                    if len(title) > 15 and title not in seen:
                        seen.add(title)
                        news_list.append({
                            'title': title,
                            'description': '',
                            'source': 'Investing.com'
                        })
                        if len(news_list) >= 8:
                            break
                if len(news_list) >= 8:
                    break
                    
    except Exception as e:
        pass
    
    return news_list

def get_market_topics():
    """定番の市場トピックを返す（フォールバック用）"""
    topics = [
        {'title': 'ドル円相場の動向について', 'description': '為替市場の最新動向', 'source': '定番トピック'},
        {'title': '日経平均株価の今後の見通し', 'description': '日本株市場の分析', 'source': '定番トピック'},
        {'title': '米国株式市場の動向', 'description': 'NYダウ・S&P500の動き', 'source': '定番トピック'},
        {'title': '日銀の金融政策について', 'description': '金利政策の影響', 'source': '定番トピック'},
        {'title': 'FRBの利下げ観測', 'description': '米国金融政策', 'source': '定番トピック'},
        {'title': '新NISA活用のポイント', 'description': '資産形成の基本', 'source': '定番トピック'},
        {'title': '長期投資のメリット', 'description': '投資の基本姿勢', 'source': '定番トピック'},
        {'title': '分散投資の重要性', 'description': 'リスク管理の基本', 'source': '定番トピック'},
    ]
    return topics

def fetch_all_news():
    """全ソースからニュースを取得"""
    all_news = []
    
    print(f"\n{Colors.CYAN}📰 ニュースを取得中...{Colors.RESET}")
    
    # 1. Yahoo!ニュースから取得
    log_info("Yahoo!ニュースから取得中...")
    yahoo_news = fetch_yahoo_finance_news()
    if yahoo_news:
        all_news.extend(yahoo_news)
        log_success(f"Yahoo!ニュースから{len(yahoo_news)}件取得")
    else:
        log_warning("Yahoo!ニュースから取得できませんでした")
    
    # 2. Googleニュースから取得
    log_info("Googleニュースから取得中...")
    google_news = fetch_google_news()
    if google_news:
        all_news.extend(google_news)
        log_success(f"Googleニュースから{len(google_news)}件取得")
    else:
        log_warning("Googleニュースから取得できませんでした")
    
    # 3. Investing.comから取得
    log_info("Investing.comから取得中...")
    investing_news = fetch_investing_news()
    if investing_news:
        all_news.extend(investing_news)
        log_success(f"Investing.comから{len(investing_news)}件取得")
    else:
        log_warning("Investing.comから取得できませんでした")
    
    # 4. ニュースが取得できなかった場合はフォールバック
    if not all_news:
        log_info("定番トピックを使用します...")
        all_news = get_market_topics()
        log_success(f"定番トピック{len(all_news)}件を追加")
    
    return all_news

def display_news_menu(news_list):
    """ニュース選択メニューを表示"""
    print(f"\n{'='*60}")
    print(f"{Colors.BOLD}{Colors.CYAN}📋 今日の話題ニュース{Colors.RESET}")
    print(f"{'='*60}\n")
    
    if not news_list:
        log_error("ニュースを取得できませんでした。")
        return None
    
    # 重複を除去
    seen = set()
    unique_news = []
    for news in news_list:
        if news['title'] not in seen:
            seen.add(news['title'])
            unique_news.append(news)
    
    # 最大15件表示
    display_news = unique_news[:15]
    
    for i, news in enumerate(display_news, 1):
        source_tag = f"[{news['source']}]" if news.get('source') else ""
        # タイトルが長すぎる場合は切り詰め
        title = news['title'][:55] + "..." if len(news['title']) > 55 else news['title']
        print(f"{Colors.YELLOW}{i:2}.{Colors.RESET} {title}")
        if source_tag:
            print(f"    {Colors.CYAN}{source_tag}{Colors.RESET}")
    
    print(f"\n{'='*60}")
    print(f"{Colors.BOLD}0. 自分でニュースを入力する{Colors.RESET}")
    print(f"{'='*60}\n")
    
    while True:
        try:
            choice = input(f"{Colors.BOLD}番号を選択してください (1-{len(display_news)}, 0=手動入力): {Colors.RESET}").strip()
            
            if choice == '0':
                custom_news = input(f"{Colors.BOLD}ニュースを入力: {Colors.RESET}").strip()
                if custom_news:
                    return {'title': custom_news, 'description': '', 'source': 'ユーザー入力'}
                continue
            
            choice_num = int(choice)
            if 1 <= choice_num <= len(display_news):
                return display_news[choice_num - 1]
            else:
                log_error(f"1〜{len(display_news)}の番号を入力してください。")
        except ValueError:
            log_error("数字を入力してください。")
        except KeyboardInterrupt:
            print("\n")
            sys.exit(0)

# ===== APIキー管理 =====
def get_api_key_interactive(force_input=False):
    """対話形式でAPIキーを取得"""
    
    if not force_input:
        # 環境変数から取得
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        
        # 余計な文字を除去
        if api_key:
            # 改行や余計な文字を除去
            api_key = api_key.split('\n')[0].strip()
            api_key = api_key.replace('"', '').replace("'", "")
            
            if api_key.startswith("sk-") and len(api_key) > 20:
                log_info("環境変数からAPIキーを読み込みました。")
                return api_key

        # キャッシュファイルから取得
        if API_KEY_CACHE_FILE.exists():
            try:
                with open(API_KEY_CACHE_FILE, 'r') as f:
                    api_key = f.read().strip()
                    if api_key and api_key.startswith("sk-"):
                        log_info("保存済みのAPIキーを読み込みました。")
                        return api_key
            except:
                pass

    # 対話入力
    print(f"\n{'='*60}")
    print(f"{Colors.YELLOW}📌 OpenAI APIキーの設定{Colors.RESET}")
    print(f"{'='*60}")
    print("\nAPIキーが設定されていません。")
    print("https://platform.openai.com でAPIキーを取得してください。\n")
    
    while True:
        try:
            api_key = input(f"{Colors.BOLD}OpenAI APIキーを入力: {Colors.RESET}").strip()
            
            if not api_key:
                continue
            
            # 余計な文字を除去
            api_key = api_key.replace('"', '').replace("'", "").strip()
            
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

# ===== API呼び出し =====
def call_openai_api(api_key, messages, max_tokens=300, temperature=0.7, json_mode=False):
    """OpenAI API呼び出し"""
    
    for attempt in range(3):
        try:
            log_info(f"投稿を生成中... (試行 {attempt + 1}/3)")
            
            if OPENAI_AVAILABLE:
                client = OpenAI(api_key=api_key, timeout=60.0, max_retries=2)
                
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
            
            elif REQUESTS_AVAILABLE:
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
                else:
                    log_warning(f"APIエラー: {response.status_code}")
                    
        except Exception as e:
            log_warning(f"エラー: {e}")
            time.sleep(3)
    
    return None

def test_api_connection(api_key):
    """API接続テスト"""
    log_info("API接続をテスト中...")
    result = call_openai_api(api_key, [{"role": "user", "content": "OK"}], max_tokens=5)
    if result:
        log_success("API接続に成功しました！")
        return True
    return False

# ===== 生成関数 =====
def generate_post(api_key, news, prompt_template):
    """投稿を生成"""
    
    news_text = news['title']
    if news.get('description'):
        news_text += f"\n{news['description']}"
    
    messages = [
        {"role": "system", "content": prompt_template},
        {"role": "user", "content": f"以下のニュースについて、投資家Fらしい投稿を作成してください。140文字程度で。\n\n【ニュース】\n{news_text}"}
    ]
    
    result = call_openai_api(api_key, messages, max_tokens=300)
    
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

def generate_infographic(api_key, news, infographic_template):
    """図解用コンテンツを生成"""
    
    news_text = news['title']
    if news.get('description'):
        news_text += f"\n{news['description']}"
    
    content_gen_prompt = f'''
以下のニュースをJSON形式で分解してください。

【ニュース】
{news_text}

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
    
    result = call_openai_api(api_key, messages, max_tokens=500, json_mode=True)
    
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
    parser = argparse.ArgumentParser(description="Trend Oracle v2.6.1 - Stable Edition")
    parser.add_argument('--mode', type=str, choices=['post', 'infographic'], default='post')
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print(f"{Colors.BOLD}{Colors.BLUE}🔮 Trend Oracle v2.6.1 - Stable Edition{Colors.RESET}")
    print(f"   モード: {Colors.CYAN}{'投稿生成' if args.mode == 'post' else '図解生成'}{Colors.RESET}")
    print("=" * 60)
    
    # ライブラリチェック
    if not REQUESTS_AVAILABLE:
        log_error("requestsライブラリが必要です。")
        print("  pip3 install requests")
        sys.exit(1)
    
    if not OPENAI_AVAILABLE:
        log_warning("openaiライブラリがインストールされていません。requestsで代替します。")
        print("  pip3 install openai")
    
    # プロンプトファイルを読み込み
    post_prompt_template = load_prompt("post_prompt.txt")
    infographic_prompt_template = load_prompt("infographic_prompt.txt")

    # ニュースを取得
    news_list = fetch_all_news()
    
    # ニュースを選択
    selected_news = display_news_menu(news_list)
    
    if not selected_news:
        log_error("ニュースが選択されませんでした。")
        sys.exit(1)
    
    print(f"\n{Colors.GREEN}選択されたニュース:{Colors.RESET}")
    print(f"  {selected_news['title']}\n")

    # API接続
    api_key = None
    force_input = False
    
    for attempt in range(3):
        api_key = get_api_key_interactive(force_input=force_input)
        
        if test_api_connection(api_key):
            break
        else:
            log_error(f"API接続に失敗しました。({attempt + 1}/3)")
            force_input = True
            API_KEY_CACHE_FILE.unlink(missing_ok=True)
    else:
        log_error("API接続に失敗しました。")
        sys.exit(1)

    # 生成実行
    success = False
    if args.mode == 'post':
        success = generate_post(api_key, selected_news, post_prompt_template)
    elif args.mode == 'infographic':
        success = generate_infographic(api_key, selected_news, infographic_prompt_template)
    
    if success:
        print(f"{Colors.GREEN}✅ 処理が完了しました！{Colors.RESET}\n")
        
        # 続けて生成するか確認
        try:
            again = input(f"{Colors.BOLD}別のニュースで投稿を作成しますか？ (y/n): {Colors.RESET}").strip().lower()
            if again == 'y':
                main()
        except KeyboardInterrupt:
            print("\n")
    else:
        print(f"{Colors.RED}❌ 処理に失敗しました。{Colors.RESET}\n")

if __name__ == "__main__":
    main()
