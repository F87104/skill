#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trend Oracle v2.8.0 - Pro News Triple Choice Edition
========================================
信頼性の高い経済メディアからニュースを取得し、
「客観的な事実」と「投資家Fの3つの異なる投稿案」を提供します。

【アップデート内容】
- 情緒的な表現（体温、静かに、感情のぶつけ合い、肌で感じるなど）を徹底排除
- 無機質でプロフェッショナルな「需給」「資金の質」に基づいた洞察を強化
- 一度に3つの異なる投稿案（バリエーション）を生成
- Mac環境でのエンコーディングエラー対策済み
"""

import os
import sys
import json
import time
import re
import urllib.parse
from datetime import datetime

# 警告の抑制
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 必要なライブラリのインポート
try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("必要なライブラリが不足しています。以下のコマンドでインストールしてください：")
    print("pip install requests beautifulsoup4")
    sys.exit(1)

# ===== 定数 =====
NEWS_SOURCES = {
    "nikkei": {
        "name": "日本経済新聞 (経済)",
        "query": "site:nikkei.com/economy"
    },
    "bloomberg": {
        "name": "ブルームバーグ (Bloomberg)",
        "query": "site:bloomberg.co.jp"
    },
    "reuters": {
        "name": "ロイター (ビジネス)",
        "query": "site:jp.reuters.com/business"
    },
    "wsj": {
        "name": "ウォール・ストリート・ジャーナル (WSJ)",
        "query": "site:jp.wsj.com"
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

# ===== APIキーのクレンジング機能 =====
def get_super_cleansed_api_key():
    raw_key = os.environ.get("OPENAI_API_KEY", "")
    if not raw_key: return None
    key = raw_key.strip()
    if key.count("sk-proj-") > 1:
        key = "sk-proj-" + key.split("sk-proj-")[-1]
    match = re.search(r'(sk-[a-zA-Z0-9]{20,})', key)
    if match: return match.group(1)
    return key.replace('"', '').replace("'", "").split('\n')[0].split(' ')[0]

# ===== ニュース取得機能 =====
def fetch_pro_news():
    all_news = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    print(f"\n{Colors.CYAN}📰 専門メディアから最新ニュースを取得中...{Colors.RESET}")

    for key, source in NEWS_SOURCES.items():
        log_info(f"{source['name']} から取得中...")
        try:
            encoded_query = urllib.parse.quote(source['query'])
            rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ja&gl=JP&ceid=JP:ja"
            
            time.sleep(1)
            response = requests.get(rss_url, headers=headers, timeout=20, verify=False)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'xml')
            items = soup.find_all('item')[:5]
            
            count = 0
            for item in items:
                title_tag = item.find('title')
                link_tag = item.find('link')
                if title_tag and link_tag:
                    raw_title = title_tag.get_text(strip=True)
                    clean_title = raw_title.rsplit(' - ', 1)[0] if ' - ' in raw_title else raw_title
                    link = link_tag.get_text(strip=True)
                    
                    if clean_title and len(clean_title) > 10:
                        all_news.append({
                            'title': clean_title,
                            'link': link,
                            'source': source['name'],
                            'date': datetime.now().strftime('%Y-%m-%d')
                        })
                        count += 1

            if count > 0:
                log_success(f"{source['name']} から {count} 件取得しました")
            else:
                log_warning(f"{source['name']} からニュースが見つかりませんでした")
                
        except Exception as e:
            log_warning(f"{source['name']} 取得エラー: {e}")

    return all_news

# ===== 生成機能 =====
def generate_content(api_key, news_item, mode="f_post"):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    if mode == "fact_summary":
        prompt = f"""以下のニュースについて、客観的な事実関係を箇条書きでまとめてください。
特に「具体的な数字」「日付」「登場人物・組織」「これまでの経緯」を重視してください。

タイトル: {news_item['title']}
ソース: {news_item['source']}
URL: {news_item['link']}"""
    else:
        prompt = f"""あなたは「投資家F」というペルソナで、最新の経済ニュースに基づいたX（旧Twitter）投稿を【3つの異なるバリエーション】で作成します。

【ニュース内容】
タイトル: {news_item['title']}
ソース: {news_item['source']}

【投資家Fの文体ルール】
- 挨拶は「こんにちは、Fです✨」から始める。
- 一人称は必ず「私」を使用する。
- ニュース内の具体的な「固有名詞」「数字」「仕組み」を必ず文章に組み込み、何が起きているのかを鮮明に描写する。
- 表面的な感想（「興味津々」「楽しみ」など）を避け、その事象が「相場の需給」や「投資家心理」にどう影響するかというプロの鋭い洞察を提示する。
- 投資家としての「実体験」や「直近の行動」を想起させる一言（例：「私も以前、似たような局面で…」「昨夜のチャートを見ていて感じたのは…」）を自然に挿入し、リアリティを持たせる。
- ニュースの表面的な意味とは逆の可能性（例：「大口の仕込み」「需給の反転」など）を必ず1つ提示し、逆説的な視点を持たせる。
- 精神論や情緒的なポエム表現（「嵐の目」「不動の心」「心の平穏」「明るい未来」「相場の体温」「肌で感じる」「静かに」「感情のぶつけ合い」など）を徹底排除し、具体的な「投資行動（キャッシュ比率の調整、指値の置き方など）」や「マーケットのメカニズム」に踏み込んだアドバイスをする。
- 専門用語を避け、中学生でもわかる平易な言葉で「本質」を解説する。
- 読者に語りかけるような、親しみやすく人間味のある口語体を使用する（例：「〜だよね」「〜かな」「〜ってこと」「〜らしい」「〜なのかも」）。
- 投資家としての「需給の動き」や「資金の質」を表現する具体的な言葉を選ぶ（例：「相場の呼吸」「胸のざわつき」「裏側の糸」「心臓部を揺さぶる」「投げ売りの連鎖」「資金の逃げ足」「板の薄さ」「需給の偏り」「ポジションの解消」「実需の動き」「流動性の低下」「情報の裏側」「ボラティリティの質」「資金の滞留状況」）。
- 相場の不確実性を考慮し、強い断定（「〜だ」「〜である」）を避け、含みを持たせた表現（「〜しているらしい」「〜なのかもしれない」）を意識する。
- 絵文字の直後に句点（。）をつけない。文末が絵文字の場合はそのまま終わらせる。
- 誰でも言えるような一般的・教科書的・抽象的な言葉（「冷静」「心配」「第一歩」「見えない連鎖」「明るい未来」「心の平穏」「相場の呼吸が荒い中」「市場の歪み」「火花の散り方」「黄金の鍵」「嵐の目」「不動の心」「相場の体温」「肌で感じる」「静かに」「感情のぶつけ合い」など）を徹底的に排除し、F氏ならではの鋭い感性が光る表現に置き換える。
- 感情表現や以下の絵文字を適切に活用する: 😺🐻🐻‍❄️🥰✅🌈🌸。
- 最後に「投資家Fより💌」と署名する。

【排除するAI特有・一般的・教科書的な表現】
以下の単語や言い回しは一切使用しないでください。
- 〜が重要です、〜が求められます、〜に注意が必要です、〜と言えるでしょう、〜と考えられます、〜ではないでしょうか、一見すると、しかしながら、一方で、網羅的、包括的、多角的、鑑みるに、踏まえる、示唆する、喚起する、〜の観点から、〜の側面から、本稿では、本記事では、結論として、総じて、〜であると言えます
- 推進する、貢献する、考慮する、背景に、呈する、鑑みて、享受する、包含する、網羅する、促進する、最適化する、最大化する、最小化する、強化する、改善する、向上させる、確保する、維持する、達成する、追求する、創出する、構築する、実装する、展開する、分析する、評価する、検討する、議論する、考察する、提唱する、提案する、提示する、明示する、言及する、指摘する、強調する、認識する、理解する、把握する、洞察する、予見する、予測する、展望する、期待する、懸念する、危惧する、憂慮する、注視する、監視する、警戒する、考慮に入れる、念頭に置く、視野に入れる、織り込む、反映する、体現する、象徴する、代表する、構成する、形成する、確立する
- 冷静、心配、第一歩、見えない連鎖、重要、必要、不可欠、基本的、一般的、通常、普通、当たり前、当然、明白、明確、具体的、抽象的、論理的、客観的、主観的、相対的、絶対的、本質的、根本的、包括的、多角的、網羅的、体系的、構造的、機能的、効果的、効率的、合理的、現実的、理想的、積極的、消極的、肯定的、否定的、楽観的、悲観的な、慎重、大胆、果敢、冷静沈着、一喜一憂、試行錯誤、紆余曲折、千載一遇、一石二鳥、一挙両得、一朝一夕、一進一退、一触即発、一蓮托生、一心不乱、一生懸命、一心同体、一期一会、明るい未来、心の平穏、興味津々、楽しみ、期待、不安、安心、安全、信頼、信用、希望、絶望、成功、失敗、成長、衰退、変化、維持、安定、不安定、複雑、単純、容易、困難、可能、不可能、適切、不適切、正当、不当、有効、無効、有益、無益、有利、不利、優位、劣位、最高、最低、最大、最小、最適、最善、最悪、最初、最後、以前、以後、現在、過去、未来、今日、明日、昨日、今回、次回、前回、今回も、次回も、前回も、常に、時々、たまに、決して、全く、非常に、大変、とても、少し、わずかに、かなり、相当、随分、随分と、もっと、さらに、ますます、いよいよ、ついに、ようやく、やっと、ついに、いよいよ、ますます、さらに、もっと、随分と、相当、かなり、わずかに、少し、とても、大変、非常に、全く、決して、たまに、時々、常に、前回も、次回も、今回も、前回、次回、今回、昨日、明日、今日、未来、過去、現在、以後、以前、最後、最初、最悪、最善、最適、最小、最大、最低、最高、劣位、優位、不利、有利、無益、有益、無効、有効、不当、正当、不適切、適切、不可能、可能、困難、容易、単純、複雑、不安定、安定、維持、変化、衰退、成長、失敗、成功、絶望、希望、信用、信頼、安全、安心、不安、期待、楽しみ、興味津々、心の平穏、明るい未来、一期一会、一心同体、一生懸命、一心不乱、一蓮托生、一触即発、一進一退、一朝一夕、一挙両得、一石二鳥、千載一遇、紆余曲折、試行錯誤、一喜一憂、冷静沈着、果敢、大胆、慎重、悲観的、楽観的、否定的、肯定的、消極的、積極的、理想的、現実的、合理的、効率的、効果的、機能的、構造的、体系的、網羅的、多角的、包括的、根本的、本質的、絶対的、相対的、主観的、客観的、論理的、抽象的、具体的、明確、明白、当然、当たり前、普通、通常、一般的、基本的、不可欠、必要、重要、見えない連鎖、第一歩、心配、冷静、嵐の目、不動の心、黄金の鍵、火花の散り方、市場の歪み、相場の呼吸が荒い中、相場の体温、肌で感じる、静かに、感情のぶつけ合い

【出力形式】
- 3つの投稿案を、それぞれ「案1」「案2」「案3」として出力してください。
- 各案は以下の構成を守ってください。
  - タイトル: 「＼📣ニュースタイトル　絵文字🐻／」
  - ### 要約：今、何が起きているのか😺
  - ### まとめ：なぜ、そして何が懸念されるのか🐻‍❄️
  - ### 深掘り：Fが考える「今後」と「注意点」🌈
- ハッシュタグは一切つけないでください。
- そのままコピペできる形式で出力してください。"""

    data = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.8
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=60, verify=False)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content'].strip()
        else:
            log_error(f"APIエラー: {response.status_code}")
            return None
    except Exception as e:
        log_warning(f"通信エラー: {e}")
        return None

# ===== メイン処理 =====
def main():
    print(f"\n{Colors.BOLD}{Colors.CYAN}🚀 Trend Oracle v2.8.0 - Triple Choice Edition 起動中...{Colors.RESET}")
    
    api_key = get_super_cleansed_api_key()
    if not api_key:
        log_error("環境変数 OPENAI_API_KEY が設定されていません。")
        sys.exit(1)

    news_list = fetch_pro_news()
    if not news_list:
        log_error("ニュースを取得できませんでした。")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"{Colors.BOLD}{Colors.CYAN}📋 今日の専門メディア厳選ニュース{Colors.RESET}")
    print(f"{'='*60}\n")

    for i, news in enumerate(news_list, 1):
        print(f"{Colors.YELLOW}{i:2}.{Colors.RESET} {news['title']}")
        print(f"    {Colors.CYAN}[{news['source']}]{Colors.RESET}")

    print(f"\n{'='*60}")
    
    try:
        choice_input = input(f"{Colors.BOLD}詳細を確認し、3つの投稿案を作成するニュースの番号を選択してください (1-{len(news_list)}): {Colors.RESET}")
        choice = int(choice_input)
        selected_news = news_list[choice - 1]
        
        print(f"\n{Colors.BOLD}{Colors.CYAN}🔍 ニュースの詳細と事実関係を整理中...{Colors.RESET}")
        fact_summary = generate_content(api_key, selected_news, mode="fact_summary")
        
        print(f"\n{Colors.BOLD}{Colors.YELLOW}📌 【客観的事実・数字】{Colors.RESET}")
        print(f"{'-'*40}")
        print(f"タイトル: {selected_news['title']}")
        print(f"ソース  : {selected_news['source']}")
        print(f"URL     : {selected_news['link']}")
        print(f"\n{fact_summary}")
        print(f"{'-'*40}")
        
        print(f"\n{Colors.BOLD}{Colors.CYAN}✨ 投資家Fの視点で3つの投稿案を生成中...{Colors.RESET}")
        f_posts = generate_content(api_key, selected_news, mode="f_post")
        
        if f_posts:
            print(f"\n{Colors.BOLD}{Colors.GREEN}💌 投資家FのX投稿案（3つのバリエーション） ✨{Colors.RESET}")
            print(f"{'='*40}\n{f_posts}\n{'='*40}")
            log_success("すべての処理が完了しました！最適な案を選んでください。")
        else:
            log_error("投稿の生成に失敗しました。")
            
    except (ValueError, IndexError):
        log_error("正しい番号を選択してください。")
    except KeyboardInterrupt:
        print("\n終了します。")

if __name__ == "__main__":
    main()
