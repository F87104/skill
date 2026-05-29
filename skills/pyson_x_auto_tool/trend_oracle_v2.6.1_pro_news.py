#!/usr/bin/env python3
"""
Trend Oracle v2.6.1 - Pro News Edition
========================================
信頼性の高い経済メディアからニュースを自動取得して、投資家Fらしい投稿文を生成

【アップデート内容】
- ニュース取得元をブルームバーグ、日経新聞、ロイター等の専門メディアに限定
- 一般的なポータルサイト（Yahoo/Google）を排除し、信憑性を向上
- 投資家Fの「品格のある口語体」を反映したプロンプトの強化
"""

import os
import sys
import argparse
import json
import time
import re
from pathlib import Path
from datetime import datetime

# 必要なライブラリのインポート
try:
    import requests
    from bs4 import BeautifulSoup
    from openai import OpenAI
except ImportError:
    print("必要なライブラリが不足しています。以下のコマンドでインストールしてください：")
    print("pip install requests beautifulsoup4 openai")
    sys.exit(1)

# ===== 定数 =====
SCRIPT_DIR = Path(__file__).parent

# 信頼性の高い経済ニュースソース
NEWS_SOURCES = {
    "bloomberg_jp": {
        "name": "ブルームバーグ (Bloomberg)",
        "url": "https://www.bloomberg.co.jp/",
        "type": "html",
        "selector": "a[data-resource-type='article']"
    },
    "nikkei_economy": {
        "name": "日本経済新聞 (経済)",
        "url": "https://www.nikkei.com/economy/",
        "type": "html",
        "selector": "a.k-card__title-link"
    },
    "reuters_business": {
        "name": "ロイター (ビジネス)",
        "url": "https://jp.reuters.com/business/",
        "type": "html",
        "selector": "a[data-testid='Heading']"
    }
}

# ===== カラー出力 =====
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

def log_info(msg): print(f"[INFO] {msg}")
def log_success(msg): print(f"{Colors.GREEN}[SUCCESS] {msg}{Colors.RESET}")
def log_warning(msg): print(f"{Colors.YELLOW}[WARNING] {msg}{Colors.RESET}")
def log_error(msg): print(f"{Colors.RED}[ERROR] {msg}{Colors.RESET}")

# ===== ニュース取得機能 =====
def fetch_pro_news():
    """専門メディアからニュースを取得"""
    all_news = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }

    print(f"\n{Colors.CYAN}📰 専門メディアから最新ニュースを取得中...{Colors.RESET}")

    for key, source in NEWS_SOURCES.items():
        log_info(f"{source['name']} から取得中...")
        try:
            response = requests.get(source['url'], headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            articles = soup.select(source['selector'])[:10]
            count = 0
            for article in articles:
                title = article.get_text(strip=True)
                if title and len(title) > 10:
                    all_news.append({
                        'title': title,
                        'source': source['name'],
                        'date': datetime.now().strftime('%Y-%m-%d')
                    })
                    count += 1
            if count > 0:
                log_success(f"{source['name']} から {count} 件取得しました")
            else:
                log_warning(f"{source['name']} からニュースを抽出できませんでした")
        except Exception as e:
            log_warning(f"{source['name']} 取得エラー: {e}")

    return all_news

# ===== 投稿生成機能 =====
def generate_f_post(api_key, news_item):
    """投資家Fのスタイルで投稿を生成"""
    client = OpenAI(api_key=api_key)
    
    prompt = f"""あなたは「投資家F」というペルソナで、最新の経済ニュースに基づいたX（Twitter）投稿を作成します。

【ニュース内容】
タイトル: {news_item['title']}
ソース: {news_item['source']}

【投資家Fの文体ルール】
- 挨拶は「こんにちは、Fです✨」から始める
- 専門用語を避け、中学生でもわかる平易な言葉で「本質」を解説する
- 「事実」「なぜ」「今後」「注意点」を盛り込みつつ、1分で読める長さにまとめる
- 品格のある口語体（「〜だよね」「〜かな」を適度に使用）
- 最後に「投資家Fより💌」と署名する
- ハッシュタグを3〜5個程度つける

【出力形式】
そのままコピペできる形式で出力してください。"""

    try:
        log_info("投資家Fの思考プロセスを再現中...")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        log_error(f"生成エラー: {e}")
        return None

# ===== メイン処理 =====
def main():
    parser = argparse.ArgumentParser(description='Trend Oracle v2.6.1 - Pro News Edition')
    args = parser.parse_args()

    # APIキーの取得（環境変数優先）
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        log_error("環境変数 OPENAI_API_KEY が設定されていません。")
        sys.exit(1)

    # ニュース取得
    news_list = fetch_pro_news()
    if not news_list:
        log_error("ニュースを取得できませんでした。終了します。")
        sys.exit(1)

    # メニュー表示
    print(f"\n{'='*60}")
    print(f"{Colors.BOLD}{Colors.CYAN}📋 今日の専門メディア厳選ニュース{Colors.RESET}")
    print(f"{'='*60}\n")

    for i, news in enumerate(news_list, 1):
        print(f"{Colors.YELLOW}{i:2}.{Colors.RESET} {news['title']}")
        print(f"    {Colors.CYAN}[{news['source']}]{Colors.RESET}")

    print(f"\n{'='*60}")
    
    try:
        choice = int(input(f"{Colors.BOLD}投稿を作成するニュースの番号を選択してください (1-{len(news_list)}): {Colors.RESET}"))
        selected_news = news_list[choice - 1]
        
        # 投稿生成
        post = generate_f_post(api_key, selected_news)
        if post:
            print(f"\n{Colors.BOLD}{Colors.GREEN}✨ 生成された投稿案 ✨{Colors.RESET}")
            print(f"{'-'*40}\n{post}\n{'-'*40}")
            log_success("処理が完了しました！")
            
    except (ValueError, IndexError):
        log_error("正しい番号を選択してください。")
    except KeyboardInterrupt:
        print("\n終了します。")

if __name__ == "__main__":
    main()
