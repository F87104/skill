#!/usr/bin/env python3
"""
Trend Oracle v2.7.0 - Pro Edition
=====================================
投資のプロ向け：信頼性の高い金融ニュースソースのみを使用
ロイター、日経、みんかぶFX、外為どっとコムから最新ニュースを取得

【使い方】
python3 ~/prometheus/trend_oracle_v2.7.0_pro.py
python3 ~/prometheus/trend_oracle_v2.7.0_pro.py --mode infographic
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

# 金融ニュース専用キーワード（厳格なフィルタ）
FINANCE_KEYWORDS = [
    # 為替
    'ドル', '円', 'ユーロ', 'ポンド', '豪ドル', '為替', 'FX', '外為',
    # 株式
    '日経', 'TOPIX', 'ダウ', 'S&P', 'ナスダック', '株価', '株式', '上場',
    # 金融政策
    '日銀', 'FRB', 'ECB', '金利', '利上げ', '利下げ', '金融政策', 'QE', 'QT',
    # 経済指標
    'GDP', 'CPI', 'PPI', '雇用統計', '失業率', 'ISM', 'PMI', 'IFO',
    # 商品
    '原油', 'WTI', 'ブレント', '金価格', 'ゴールド', '商品先物',
    # 債券
    '国債', '利回り', '長期金利', '短期金利',
    # その他金融
    '市場', '相場', '投資', 'ファンド', 'ETF', 'REIT', '決算', '業績',
]

# 除外キーワード（金融と無関係なニュース）
EXCLUDE_KEYWORDS = [
    'スポーツ', '芸能', 'エンタメ', '天気', '事件', '事故', '犯罪',
    '選挙', '政治家', '訃報', '結婚', '離婚', 'ドラマ', '映画',
    '宇宙船', 'ロケット', 'NASA', '火星', '月面',
]

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

# ===== ニュースフィルタリング =====
def is_finance_news(title):
    """金融ニュースかどうかを判定"""
    title_lower = title.lower()
    
    # 除外キーワードチェック
    for kw in EXCLUDE_KEYWORDS:
        if kw in title:
            return False
    
    # 金融キーワードチェック
    for kw in FINANCE_KEYWORDS:
        if kw in title or kw.lower() in title_lower:
            return True
    
    return False

def get_news_category(title):
    """ニュースのカテゴリを判定"""
    if any(kw in title for kw in ['ドル', '円', 'ユーロ', 'ポンド', '為替', 'FX']):
        return '💱 為替'
    elif any(kw in title for kw in ['日経', 'TOPIX', 'ダウ', 'S&P', '株価', '株式']):
        return '📈 株式'
    elif any(kw in title for kw in ['日銀', 'FRB', 'ECB', '金利', '利上げ', '利下げ']):
        return '🏦 金融政策'
    elif any(kw in title for kw in ['GDP', 'CPI', '雇用統計', '失業率', 'ISM', 'PMI']):
        return '📊 経済指標'
    elif any(kw in title for kw in ['原油', 'WTI', '金価格', 'ゴールド']):
        return '🛢️ 商品'
    elif any(kw in title for kw in ['国債', '利回り', '長期金利']):
        return '📜 債券'
    else:
        return '📰 マーケット'

# ===== ニュース取得機能（プロ向け）=====
def fetch_reuters_news():
    """ロイター日本版からマーケットニュースを取得"""
    news_list = []
    
    urls = [
        "https://jp.reuters.com/markets/",
        "https://jp.reuters.com/markets/currencies/",
        "https://jp.reuters.com/markets/japan/",
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
    }
    
    seen = set()
    
    for url in urls:
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                html = response.text
                
                # ロイターの記事タイトルパターン
                patterns = [
                    r'<a[^>]*href="/[^"]*/"[^>]*>([^<]{20,100})</a>',
                    r'"headline":"([^"]{20,100})"',
                    r'<h[23][^>]*>([^<]{20,100})</h[23]>',
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, html)
                    for title in matches:
                        title = title.strip()
                        title = re.sub(r'\s+', ' ', title)
                        
                        if title not in seen and is_finance_news(title):
                            seen.add(title)
                            news_list.append({
                                'title': title,
                                'source': 'ロイター',
                                'category': get_news_category(title)
                            })
                            
        except Exception as e:
            continue
    
    return news_list[:10]

def fetch_nikkei_news():
    """日経新聞からマーケットニュースを取得"""
    news_list = []
    
    urls = [
        "https://www.nikkei.com/markets/",
        "https://www.nikkei.com/markets/kawase/",
        "https://www.nikkei.com/markets/kabu/",
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    
    seen = set()
    
    for url in urls:
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                html = response.text
                
                patterns = [
                    r'<a[^>]*class="[^"]*title[^"]*"[^>]*>([^<]{15,80})</a>',
                    r'"headline":"([^"]{15,80})"',
                    r'<span[^>]*class="[^"]*headline[^"]*"[^>]*>([^<]{15,80})</span>',
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, html)
                    for title in matches:
                        title = title.strip()
                        title = re.sub(r'\s+', ' ', title)
                        
                        if title not in seen and is_finance_news(title) and len(title) > 15:
                            seen.add(title)
                            news_list.append({
                                'title': title,
                                'source': '日経新聞',
                                'category': get_news_category(title)
                            })
                            
        except Exception as e:
            continue
    
    return news_list[:8]

def fetch_minkabu_fx_news():
    """みんかぶFXからニュースを取得"""
    news_list = []
    
    try:
        url = "https://fx.minkabu.jp/news"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            html = response.text
            
            patterns = [
                r'<a[^>]*href="/news/[^"]*"[^>]*>([^<]{15,100})</a>',
                r'<h[234][^>]*>([^<]{15,100})</h[234]>',
            ]
            
            seen = set()
            for pattern in patterns:
                matches = re.findall(pattern, html)
                for title in matches:
                    title = title.strip()
                    title = re.sub(r'\s+', ' ', title)
                    
                    if title not in seen and is_finance_news(title):
                        seen.add(title)
                        news_list.append({
                            'title': title,
                            'source': 'みんかぶFX',
                            'category': get_news_category(title)
                        })
                        if len(news_list) >= 8:
                            break
                            
    except Exception as e:
        pass
    
    return news_list

def fetch_gaitame_news():
    """外為どっとコムからニュースを取得"""
    news_list = []
    
    try:
        url = "https://www.gaitame.com/markets/news/"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            html = response.text
            
            patterns = [
                r'<a[^>]*>([^<]*(?:ドル|円|ユーロ|為替|FX)[^<]*)</a>',
                r'<h[234][^>]*>([^<]{15,100})</h[234]>',
            ]
            
            seen = set()
            for pattern in patterns:
                matches = re.findall(pattern, html)
                for title in matches:
                    title = title.strip()
                    title = re.sub(r'\s+', ' ', title)
                    
                    if title not in seen and is_finance_news(title) and len(title) > 15:
                        seen.add(title)
                        news_list.append({
                            'title': title,
                            'source': '外為どっとコム',
                            'category': get_news_category(title)
                        })
                        if len(news_list) >= 6:
                            break
                            
    except Exception as e:
        pass
    
    return news_list

def fetch_bloomberg_rss():
    """ブルームバーグのRSSフィードから取得を試みる"""
    news_list = []
    
    try:
        # ブルームバーグのRSSフィード
        url = "https://www.bloomberg.co.jp/feed/podcast/etf.xml"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            content = response.text
            
            titles = re.findall(r'<title>([^<]+)</title>', content)
            
            seen = set()
            for title in titles[1:]:  # 最初はフィード名
                title = title.strip()
                if title not in seen and is_finance_news(title):
                    seen.add(title)
                    news_list.append({
                        'title': title,
                        'source': 'ブルームバーグ',
                        'category': get_news_category(title)
                    })
                    if len(news_list) >= 5:
                        break
                        
    except Exception as e:
        pass
    
    return news_list

def fetch_all_finance_news():
    """全ソースから金融ニュースを取得"""
    all_news = []
    
    print(f"\n{Colors.CYAN}📰 プロ向け金融ニュースを取得中...{Colors.RESET}")
    print(f"{Colors.CYAN}（信頼性の高いソースのみ使用）{Colors.RESET}\n")
    
    # 1. ロイター（最も信頼性が高い）
    log_info("ロイターから取得中...")
    reuters_news = fetch_reuters_news()
    if reuters_news:
        all_news.extend(reuters_news)
        log_success(f"ロイターから{len(reuters_news)}件取得")
    else:
        log_warning("ロイターから取得できませんでした")
    
    # 2. 日経新聞
    log_info("日経新聞から取得中...")
    nikkei_news = fetch_nikkei_news()
    if nikkei_news:
        all_news.extend(nikkei_news)
        log_success(f"日経新聞から{len(nikkei_news)}件取得")
    else:
        log_warning("日経新聞から取得できませんでした")
    
    # 3. みんかぶFX
    log_info("みんかぶFXから取得中...")
    minkabu_news = fetch_minkabu_fx_news()
    if minkabu_news:
        all_news.extend(minkabu_news)
        log_success(f"みんかぶFXから{len(minkabu_news)}件取得")
    else:
        log_warning("みんかぶFXから取得できませんでした")
    
    # 4. 外為どっとコム
    log_info("外為どっとコムから取得中...")
    gaitame_news = fetch_gaitame_news()
    if gaitame_news:
        all_news.extend(gaitame_news)
        log_success(f"外為どっとコムから{len(gaitame_news)}件取得")
    else:
        log_warning("外為どっとコムから取得できませんでした")
    
    # 5. ブルームバーグ（RSS）
    log_info("ブルームバーグから取得中...")
    bloomberg_news = fetch_bloomberg_rss()
    if bloomberg_news:
        all_news.extend(bloomberg_news)
        log_success(f"ブルームバーグから{len(bloomberg_news)}件取得")
    
    # 重複除去と金融ニュースのみフィルタ
    seen = set()
    filtered_news = []
    for news in all_news:
        if news['title'] not in seen and is_finance_news(news['title']):
            seen.add(news['title'])
            filtered_news.append(news)
    
    if not filtered_news:
        log_warning("金融ニュースが取得できませんでした。手動入力をお使いください。")
    
    return filtered_news

def display_news_menu(news_list):
    """ニュース選択メニューを表示（カテゴリ付き）"""
    print(f"\n{'='*70}")
    print(f"{Colors.BOLD}{Colors.CYAN}📋 最新の金融・経済ニュース（プロ向け）{Colors.RESET}")
    print(f"{'='*70}\n")
    
    if not news_list:
        log_error("金融ニュースを取得できませんでした。")
        print("\n手動入力で続行します。\n")
        custom_news = input(f"{Colors.BOLD}ニュースを入力: {Colors.RESET}").strip()
        if custom_news:
            return {'title': custom_news, 'source': 'ユーザー入力', 'category': '📰 マーケット'}
        return None
    
    # カテゴリ別に整理
    by_category = {}
    for news in news_list:
        cat = news.get('category', '📰 マーケット')
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(news)
    
    # 表示用リスト
    display_list = []
    idx = 1
    
    for category in ['💱 為替', '📈 株式', '🏦 金融政策', '📊 経済指標', '🛢️ 商品', '📜 債券', '📰 マーケット']:
        if category in by_category:
            print(f"{Colors.YELLOW}{Colors.BOLD}{category}{Colors.RESET}")
            print("-" * 50)
            for news in by_category[category][:5]:  # 各カテゴリ最大5件
                title = news['title'][:60] + "..." if len(news['title']) > 60 else news['title']
                source = news['source']
                print(f"  {Colors.GREEN}{idx:2}.{Colors.RESET} {title}")
                print(f"      {Colors.CYAN}[{source}]{Colors.RESET}")
                display_list.append(news)
                idx += 1
            print()
    
    print(f"{'='*70}")
    print(f"{Colors.BOLD}0. 自分でニュースを入力する{Colors.RESET}")
    print(f"{'='*70}\n")
    
    while True:
        try:
            choice = input(f"{Colors.BOLD}番号を選択してください (1-{len(display_list)}, 0=手動入力): {Colors.RESET}").strip()
            
            if choice == '0':
                custom_news = input(f"{Colors.BOLD}ニュースを入力: {Colors.RESET}").strip()
                if custom_news:
                    return {'title': custom_news, 'source': 'ユーザー入力', 'category': '📰 マーケット'}
                continue
            
            choice_num = int(choice)
            if 1 <= choice_num <= len(display_list):
                return display_list[choice_num - 1]
            else:
                log_error(f"1〜{len(display_list)}の番号を入力してください。")
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
        
        if api_key:
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
            
            api_key = api_key.replace('"', '').replace("'", "").strip()
            
            if not api_key.startswith("sk-"):
                log_error("APIキーは 'sk-' で始まります。")
                continue
            
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
    source = news.get('source', '')
    category = news.get('category', '')
    
    messages = [
        {"role": "system", "content": prompt_template},
        {"role": "user", "content": f"""以下の金融ニュースについて、投資家Fらしい投稿を作成してください。
140文字程度で、プロの投資家として正確で洞察力のある内容にしてください。

【ニュース】
{news_text}

【カテゴリ】{category}
【ソース】{source}"""}
    ]
    
    result = call_openai_api(api_key, messages, max_tokens=300)
    
    if result:
        final_post = f"{result}\n\n投資家Fより💌"
        log_success("投稿が生成されました！")
        print(f"\n{'='*70}")
        print(f"{Colors.CYAN}{Colors.BOLD}📝 生成された投稿{Colors.RESET}")
        print(f"{'='*70}")
        print(f"\n{final_post}\n")
        print(f"{'='*70}")
        print(f"\n{Colors.YELLOW}↑ この投稿をコピーしてXに貼り付けてください{Colors.RESET}\n")
        return True
    else:
        log_error("投稿の生成に失敗しました。")
        return False

def generate_infographic(api_key, news, infographic_template):
    """図解用コンテンツを生成"""
    
    news_text = news['title']
    
    content_gen_prompt = f'''
以下の金融ニュースをJSON形式で分解してください。
投資のプロ向けに、正確で専門的な内容にしてください。

【ニュース】
{news_text}

【JSONフォーマット】
{{
    "headline": "タイトル（20文字以内）",
    "background": "背景・経緯（40文字以内）",
    "current": "現状・数値（40文字以内）",
    "impact": "市場への影響（40文字以内）",
    "point1": "ポイント1（30文字以内）",
    "point2": "ポイント2（30文字以内）",
    "point3": "ポイント3（30文字以内）",
    "outlook": "今後の見通し（40文字以内）",
    "f_comment": "Fのコメント（30文字以内）"
}}
'''
    
    messages = [
        {"role": "system", "content": "金融の専門家として、正確なJSONを出力します。"},
        {"role": "user", "content": content_gen_prompt}
    ]
    
    result = call_openai_api(api_key, messages, max_tokens=600, json_mode=True)
    
    if result:
        try:
            content_dict = json.loads(result)
            
            copy_text = f'''
📊 図解用テキスト（プロ向け）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【大見出し】
{content_dict.get("headline", "")}

【背景・経緯】
{content_dict.get("background", "")}

【現状・数値】
{content_dict.get("current", "")}

【市場への影響】
{content_dict.get("impact", "")}

【💡 3つのポイント】
① {content_dict.get("point1", "")}
② {content_dict.get("point2", "")}
③ {content_dict.get("point3", "")}

【今後の見通し】
{content_dict.get("outlook", "")}

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
    parser = argparse.ArgumentParser(description="Trend Oracle v2.7.0 - Pro Edition")
    parser.add_argument('--mode', type=str, choices=['post', 'infographic'], default='post')
    args = parser.parse_args()

    print("\n" + "=" * 70)
    print(f"{Colors.BOLD}{Colors.BLUE}🔮 Trend Oracle v2.7.0 - Pro Edition{Colors.RESET}")
    print(f"   {Colors.CYAN}投資のプロ向け：信頼性の高い金融ニュースソースのみ使用{Colors.RESET}")
    print(f"   モード: {Colors.CYAN}{'投稿生成' if args.mode == 'post' else '図解生成'}{Colors.RESET}")
    print("=" * 70)
    
    # ライブラリチェック
    if not REQUESTS_AVAILABLE:
        log_error("requestsライブラリが必要です。")
        print("  pip3 install requests")
        sys.exit(1)
    
    if not OPENAI_AVAILABLE:
        log_warning("openaiライブラリがインストールされていません。requestsで代替します。")
    
    # プロンプトファイルを読み込み
    post_prompt_template = load_prompt("post_prompt.txt")
    infographic_prompt_template = load_prompt("infographic_prompt.txt")

    # 金融ニュースを取得
    news_list = fetch_all_finance_news()
    
    # ニュースを選択
    selected_news = display_news_menu(news_list)
    
    if not selected_news:
        log_error("ニュースが選択されませんでした。")
        sys.exit(1)
    
    print(f"\n{Colors.GREEN}選択されたニュース:{Colors.RESET}")
    print(f"  {selected_news['title']}")
    print(f"  {Colors.CYAN}[{selected_news.get('source', '')}] {selected_news.get('category', '')}{Colors.RESET}\n")

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
