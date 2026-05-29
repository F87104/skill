#!/usr/bin/env python3
"""
Project Prometheus - Trend Oracle v1.0
======================================
トレンド連動型投稿自動生成システム

情報ソース:
1. Yahoo!リアルタイム検索 - Xの話題をログインなしで取得
2. Bloomberg Japan - 専門的な金融ニュース

機能:
- トレンド取得 → フィルタリング → 投稿生成 → 確認用表示

使い方:
    python3 trend_oracle.py
"""

import time
import random
import sys
import os
import re
from datetime import datetime
from pathlib import Path

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
except ImportError:
    print("Seleniumがインストールされていません。")
    print("  pip3 install selenium")
    sys.exit(1)

try:
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    print("webdriver-managerがインストールされていません。")
    print("  pip3 install webdriver-manager")
    sys.exit(1)

try:
    from openai import OpenAI
except ImportError:
    print("OpenAIがインストールされていません。")
    print("  pip3 install openai")
    sys.exit(1)

# ===== 設定 =====

# 採用キーワード（これらを含むトレンドを優先）
INCLUDE_KEYWORDS = [
    # 為替
    "ドル円", "円安", "円高", "為替", "FX", "外国為替", "ユーロ", "ポンド",
    # 株式
    "日経平均", "株価", "TOPIX", "ダウ", "S&P500", "ナスダック", "株式", "日経",
    # 金融政策
    "日銀", "FRB", "利上げ", "利下げ", "金融政策", "インフレ", "金利", "植田",
    # 経済指標
    "GDP", "雇用統計", "CPI", "失業率", "景気", "経済", "物価",
    # 投資一般
    "投資", "資産運用", "NISA", "iDeCo", "積立", "配当", "ETF",
    # マインド系
    "成功", "失敗", "学び", "成長", "習慣", "時間", "お金", "人生",
    # 市場
    "相場", "マーケット", "市場", "トレード", "取引"
]

# 除外キーワード（これらを含むトレンドは除外）
EXCLUDE_KEYWORDS = [
    # 芸能
    "芸能", "アイドル", "ドラマ", "映画", "俳優", "女優", "ジャニーズ", "AKB",
    # スポーツ
    "野球", "サッカー", "オリンピック", "スポーツ", "プロ野球", "Jリーグ",
    # 事件
    "逮捕", "事故", "事件", "殺人", "犯罪", "容疑", "死亡",
    # その他
    "アニメ", "ゲーム", "漫画", "声優", "コスプレ"
]

# Fのキャラクター設定
F_CHARACTER = """
あなたは「投資家F」という投資の専門家キャラクターです。

【最重要】難しい内容を簡単に、でも具体的に伝える

■専門家だからこそ言える「具体的な影響」を伝える
■誰にでも言える抽象的な言葉は絶対にNG
■初心者でも「なるほど！」と思える内容にする
■読者と「一緒に成長する仲間」というスタンス

【投稿の構成：5ステップ】1万点構成

①フック+事実+共感（40〜50文字）
- 何が起きたか + 読者の気持ちに寄り添う
- 「〜のニュース、びっくりした人多いよね」
- 「〜って迷ってる人も多いと思う」

②独自の視点（40〜50文字）
- Fだからこそ言える分析
- 「実はね、〜」「あまり知られてないけど〜」
- 過去の例やパターンを紹介

③因果関係（50〜60文字）
- だから何が起きるか、連鎖反応を丁寧に
- 「〜すると〜になって、〜に影響が出やすいよ」
- 「ドル円」「株価」「金利」など具体的に

④具体的アクション（40〜50文字）
- だからどうすべきか明確に
- 「〜の人は〜がいいよ」
- 「今週は〜」「これから買う人は〜」

⑤パターン化+励まし+コミュニティ感（40〜60文字）
- 知識として蓄積できる形に
- 「これ覚えておくと〜」「このパターン知ってると強いよ」
- 「一緒に頑張ろうね」「私たちは〜」

【良い例】1万点構成

例1: FRB議長訴追の場合
「FRB議長が訴追されるかもってニュース、びっくりした人多いよね📚

実はね、2018年にも似たケースがあって、その時は市場は3ヶ月で落ち着いたんだ🐻

もし実現すると利下げ判断が遅れる可能性があって、そうなるとドル高・株安の圧力がかかりやすいよ🌷

ドル円ロング持ってる人は控えめに、今週は様子見がいいよ💭

『中央銀行リスク』のパターン、これで一つ覚えたね。
私も昔はこういうニュースで慌ててたけど、今は冷静に見れるようになった。
一緒に成長していこうね🌈😺💌🥰」

例2: 日経平均急騰の場合
「日経5万3000円突破したよ📚
史上最高値更新、すごいよね！でも「今から買っていいの？」って迷ってる人も多いと思う🐻

実はね、選挙後の法人税減税期待で海外勢が買ってるんだ。
でも急騰後は3〜5%の調整が入りやすいのがパターンなんだよね🌷

これから買う人は、一括じゃなくて2-3回に分けて入れるのが安心だよ💭

『急騰後の調整』、これ覚えておくと役立つよ。
焦らなくて大丈夫、私たちはゆっくり着実にいこうね🌈😺💌🥰」

例3: 金利上昇の場合
「長期金利が2.14%で27年ぶりの高さだって📚
「金利が上がると何が変わるの？」って思う人もいるよね🐻

実はね、金利が上がると住宅ローンの金利も上がるから、不動産株には向かい風になりやすいんだ。
逆に銀行株は、お金を貸す時の利ざやが増えるから追い風かも🌷

今は成長株より、高配当株やバリュー株に注目しておくのがいいよ💭

『金利上昇局面の投資先』、これ知ってると強いよ。
一緒に学んで、賢い投資家になっていこうね🌈😺💌🥰」

【絶対禁止】

× 抽象的な表現：
  - 「不透明感が増す」→ 何が不透明？具体的に！
  - 「リスク分散を心掛ける」→ 何をどう分散？
  - 「市場がザワついてる」→ だから何？
  - 「冷静に」「注視」「要注意」→ 具体的に何をする？

× 誰にでも言える言葉：
  - 「過度な動揺は控えて」
  - 「大事なのは情報収集」
  - 「こういう時こそ落ち着いて」

× 具体的な銘柄推奨や売買指示

【文章スタイル】
- 5〜6文の文章（改行で区切る）
- 各文の終わりに絵文字を1つ
- 最後の文は絵文字を2〜4個
- 柔らかい口調（「〜かも」「〜だね」「〜だよね」「〜だよ」）

【絵文字】
🌈🐻😺💌🥰✨💭🌷🐻‍❄️📚☕️🙏💪🕊️

【文字数】
- 200〜280文字（X Premiumなので140文字制限なし）
"""

PROFILE_DIR = Path.home() / ".prometheus_trend_oracle"

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

BANNER = f"""
{Colors.CYAN}╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   ████████╗██████╗ ███████╗███╗   ██╗██████╗              ║
║   ╚══██╔══╝██╔══██╗██╔════╝████╗  ██║██╔══██╗             ║
║      ██║   ██████╔╝█████╗  ██╔██╗ ██║██║  ██║             ║
║      ██║   ██╔══██╗██╔══╝  ██║╚██╗██║██║  ██║             ║
║      ██║   ██║  ██║███████╗██║ ╚████║██████╔╝             ║
║      ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═══╝╚═════╝              ║
║                                                           ║
║    ██████╗ ██████╗  █████╗  ██████╗██╗     ███████╗       ║
║   ██╔═══██╗██╔══██╗██╔══██╗██╔════╝██║     ██╔════╝       ║
║   ██║   ██║██████╔╝███████║██║     ██║     █████╗         ║
║   ██║   ██║██╔══██╗██╔══██║██║     ██║     ██╔══╝         ║
║   ╚██████╔╝██║  ██║██║  ██║╚██████╗███████╗███████╗       ║
║    ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚══════╝╚══════╝       ║
║                                                           ║
║   Trend Oracle v1.0 - トレンド連動型投稿生成              ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝{Colors.RESET}
"""


class TrendOracle:
    """トレンド連動型投稿生成エンジン"""
    
    def __init__(self):
        self.driver = None
        self.openai_client = None
        self.trends = []
    
    def setup_browser(self):
        """ブラウザを起動"""
        log_info("Chromeを起動中...")
        
        PROFILE_DIR.mkdir(exist_ok=True)
        
        options = Options()
        options.add_argument(f"--user-data-dir={PROFILE_DIR}")
        options.add_argument("--profile-directory=TrendOracle")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--lang=ja")
        prefs = {"intl.accept_languages": "ja,ja-JP"}
        options.add_experimental_option("prefs", prefs)
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.set_window_size(1280, 800)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            log_success("Chrome起動完了")
            return True
        except Exception as e:
            log_error(f"Chrome起動エラー: {e}")
            return False
    
    def setup_openai(self):
        """OpenAI APIをセットアップ"""
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            log_error("OPENAI_API_KEYが設定されていません")
            return False
        
        try:
            # 明示的にOpenAI公式APIを使用
            self.openai_client = OpenAI(
                api_key=api_key,
                base_url="https://api.openai.com/v1"
            )
            log_success("OpenAI API接続完了")
            return True
        except Exception as e:
            log_error(f"OpenAI API接続エラー: {e}")
            return False
    
    def close(self):
        if self.driver:
            self.driver.quit()
    
    # ===== 情報収集 =====
    
    def fetch_yahoo_realtime(self) -> list:
        """Yahoo!リアルタイム検索からトレンドを取得"""
        log_info("Yahoo!リアルタイム検索からトレンド取得中...")
        trends = []
        
        try:
            self.driver.get("https://search.yahoo.co.jp/realtime")
            time.sleep(3)
            
            # トレンドワードを取得
            trend_elements = self.driver.find_elements(By.CSS_SELECTOR, '[data-cl-params*="trend"]')
            
            if not trend_elements:
                # 別のセレクタを試す
                trend_elements = self.driver.find_elements(By.CSS_SELECTOR, '.trend a, .TrendWord a, a[href*="realtime/search"]')
            
            for elem in trend_elements[:20]:
                try:
                    text = elem.text.strip()
                    if text and len(text) > 1:
                        trends.append({
                            "source": "Yahoo!リアルタイム",
                            "keyword": text,
                            "type": "trend"
                        })
                except:
                    continue
            
            log_info(f"Yahoo!リアルタイム: {len(trends)}件取得")
            
        except Exception as e:
            log_warning(f"Yahoo!リアルタイム取得エラー: {e}")
        
        return trends
    
    def fetch_bloomberg_japan(self) -> list:
        """Bloomberg Japanからニュースを取得"""
        log_info("Bloomberg Japanからニュース取得中...")
        news = []
        
        try:
            self.driver.get("https://www.bloomberg.co.jp/")
            time.sleep(3)
            
            # ニュース見出しを取得
            headline_elements = self.driver.find_elements(By.CSS_SELECTOR, 'article h3, article h2, .story-package-module__headline, a[href*="/news/articles/"]')
            
            for elem in headline_elements[:15]:
                try:
                    text = elem.text.strip()
                    if text and len(text) > 5:
                        news.append({
                            "source": "Bloomberg",
                            "keyword": text,
                            "type": "news"
                        })
                except:
                    continue
            
            log_info(f"Bloomberg Japan: {len(news)}件取得")
            
        except Exception as e:
            log_warning(f"Bloomberg Japan取得エラー: {e}")
        
        return news
    
    def fetch_nikkei(self) -> list:
        """日本経済新聞からニュースを取得"""
        log_info("日本経済新聞からニュース取得中...")
        news = []
        
        try:
            self.driver.get("https://www.nikkei.com/")
            time.sleep(3)
            
            # ニュース見出しを取得
            headline_elements = self.driver.find_elements(By.CSS_SELECTOR, 'h3 a, h2 a, .k-card__title, article a')
            
            for elem in headline_elements[:15]:
                try:
                    text = elem.text.strip()
                    if text and len(text) > 5:
                        news.append({
                            "source": "日経新聞",
                            "keyword": text,
                            "type": "news"
                        })
                except:
                    continue
            
            log_info(f"日本経済新聞: {len(news)}件取得")
            
        except Exception as e:
            log_warning(f"日本経済新聞取得エラー: {e}")
        
        return news
    
    # ===== フィルタリング =====
    
    def score_trend(self, item: dict) -> int:
        """トレンドをスコアリング"""
        text = item["keyword"].lower()
        score = 0
        
        # 除外キーワードチェック
        for kw in EXCLUDE_KEYWORDS:
            if kw.lower() in text:
                return -1
        
        # 採用キーワードでスコアリング
        for kw in INCLUDE_KEYWORDS:
            if kw.lower() in text:
                score += 10
        
        # ソースによるボーナス
        if item["source"] == "Bloomberg":
            score += 5
        elif item["source"] == "日経新聞":
            score += 5
        
        return score
    
    def filter_trends(self, all_trends: list) -> list:
        """トレンドをフィルタリングしてスコア順にソート"""
        scored = []
        
        for item in all_trends:
            score = self.score_trend(item)
            if score > 0:
                item["score"] = score
                scored.append(item)
        
        # スコア順にソート
        scored.sort(key=lambda x: x["score"], reverse=True)
        
        # 重複を除去（キーワードが似ているものを除く）
        unique = []
        seen_keywords = set()
        
        for item in scored:
            # 簡易的な重複チェック
            keyword_lower = item["keyword"].lower()
            is_duplicate = False
            
            for seen in seen_keywords:
                if seen in keyword_lower or keyword_lower in seen:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique.append(item)
                seen_keywords.add(keyword_lower)
        
        return unique[:5]  # 上位5件
    
    # ===== 投稿生成 =====
    
    def generate_post(self, trend: dict) -> dict:
        """トレンドに基づいて投稿を生成"""
        prompt = f"""
{F_CHARACTER}

以下のトレンド/ニュースについて、投資家Fとして投稿文を作成してください。

【トレンド/ニュース】
{trend['keyword']}

【ソース】
{trend['source']}

【注意事項】
- 具体的な銘柄推奨や売買指示は絶対にしない
- ニュースの事実をそのまま伝えるのではなく、Fの視点でコメントする
- 読者が「いいね」したくなるような共感や気づきを含める
- 100〜140文字（絵文字含む）

投稿文のみを出力してください。
"""
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "あなたは投資家Fというキャラクターです。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.8
            )
            
            post_text = response.choices[0].message.content.strip()
            
            # Fらしさスコアを計算（簡易版）
            f_score = self.calculate_f_score(post_text)
            
            # 図解指示プロンプトを生成
            diagram_prompt = self.generate_diagram_prompt(trend, post_text)
            
            return {
                "trend": trend["keyword"],
                "source": trend["source"],
                "post": post_text,
                "f_score": f_score,
                "char_count": len(post_text),
                "diagram_prompt": diagram_prompt
            }
            
        except Exception as e:
            log_error(f"投稿生成エラー: {e}")
            return None
    
    def generate_diagram_prompt(self, trend: dict, post_text: str) -> str:
        """図解指示プロンプトを生成"""
        diagram_prompt = f"""
以下の投稿に合った図解を作成するための指示を作成してください。

【投稿内容】
{post_text}

【ニュースソース】
{trend['keyword']}

【投資家Fの図解スタイル】
※以下の特徴を厳守してください

■キャラクター:
- 銀髪の女の子キャラ（投資家Fのアバター）
- 猫耳フード付きの青いパーカーを着ている
- 可愛いデフォルメキャラ（くま、うさぎ）も配置

■デザイン:
- パステルカラー（水色、ピンク、クリーム色）
- 柔らかい雲や星のデコレーション
- 吹き出しを使った説明
- 手書き風フォント

■構成:
- タイトルは大きく目立つように（「〜とは？」「〜が出たよ！」など）
- 3つのポイントを分かりやすく配置（POINT1, POINT2, POINT3）
- 「Fからのメッセージ」で締める
- 絵文字を効果的に使用

■テキスト:
- 「〜だよ」「〜かも！」の柔らかい口調
- 簡潔で分かりやすい表現

以下の形式で出力してください：

タイトル: （図解のメインタイトル、「？」や「！」を使ってキャッチーに）
レイアウト: （上部にタイトル、中央にポイント、下部にFからのメッセージ）
Fキャラの配置: （どこにどんなポーズで配置するか）
Fキャラの吹き出し: （キャラが言うセリフ）
ポイント: （3つのポイントを箇条書き）
Fからのメッセージ: （図解の締めのメッセージ）
カラー: （メインカラー、アクセントカラー）
デコレーション: （雲、星、動物キャラなど）
"""
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "あなたは図解デザイナーです。Canvaや画像生成AIで使える具体的な図解指示を作成してください。"},
                    {"role": "user", "content": diagram_prompt}
                ],
                max_tokens=400,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            log_warning(f"図解プロンプト生成エラー: {e}")
            return "図解プロンプトを生成できませんでした"
    
    def calculate_f_score(self, text: str) -> int:
        """Fらしさスコアを計算（0-100）"""
        score = 50  # ベーススコア
        
        # 絵文字チェック
        emoji_pattern = re.compile(r'[\U0001F300-\U0001F9FF]')
        emojis = emoji_pattern.findall(text)
        if 5 <= len(emojis) <= 8:
            score += 20
        elif len(emojis) > 0:
            score += 10
        
        # 問いかけチェック
        if "?" in text or "？" in text or "かな" in text or "だろう" in text:
            score += 15
        
        # 柔らかい表現チェック
        soft_words = ["かもしれない", "と思う", "気がする", "大切", "大事"]
        for word in soft_words:
            if word in text:
                score += 5
        
        # 文字数チェック
        if len(text) <= 140:
            score += 10
        
        return min(score, 100)
    
    # ===== メイン処理 =====
    
    def run(self):
        """メイン処理"""
        print(BANNER)
        
        # セットアップ
        if not self.setup_browser():
            return
        
        if not self.setup_openai():
            self.close()
            return
        
        try:
            # 1. 情報収集
            log_phase("=" * 50)
            log_phase("Phase 1: 情報収集")
            log_phase("=" * 50)
            
            all_trends = []
            
            # Yahoo!リアルタイム
            yahoo_trends = self.fetch_yahoo_realtime()
            all_trends.extend(yahoo_trends)
            
            # Bloomberg Japan
            bloomberg_news = self.fetch_bloomberg_japan()
            all_trends.extend(bloomberg_news)
            
            # 日本経済新聞
            nikkei_news = self.fetch_nikkei()
            all_trends.extend(nikkei_news)
            
            log_info(f"合計: {len(all_trends)}件の情報を収集")
            
            # 2. フィルタリング
            log_phase("=" * 50)
            log_phase("Phase 2: フィルタリング")
            log_phase("=" * 50)
            
            filtered_trends = self.filter_trends(all_trends)
            
            if not filtered_trends:
                log_warning("投資・経済関連のトレンドが見つかりませんでした")
                self.close()
                return
            
            log_info(f"フィルタリング後: {len(filtered_trends)}件")
            
            print()
            for i, trend in enumerate(filtered_trends, 1):
                print(f"  {i}. [{trend['source']}] {trend['keyword']} (スコア: {trend['score']})")
            
            # 3. 投稿生成
            log_phase("=" * 50)
            log_phase("Phase 3: 投稿生成")
            log_phase("=" * 50)
            
            posts = []
            for trend in filtered_trends[:3]:  # 上位3件
                log_info(f"生成中: {trend['keyword'][:30]}...")
                post = self.generate_post(trend)
                if post:
                    posts.append(post)
                time.sleep(1)
            
            # 4. 結果表示
            log_phase("=" * 50)
            log_phase("Phase 4: 投稿案")
            log_phase("=" * 50)
            
            if not posts:
                log_error("投稿を生成できませんでした")
                self.close()
                return
            
            print()
            for i, post in enumerate(posts, 1):
                print(f"{Colors.CYAN}{'═' * 60}{Colors.RESET}")
                print(f"{Colors.BOLD}【投稿案 {i}】{Colors.RESET}")
                print(f"トレンド: {post['trend'][:40]}")
                print(f"ソース: {post['source']}")
                print(f"Fらしさ: {'⭐' * (post['f_score'] // 20)} ({post['f_score']}点)")
                print(f"文字数: {post['char_count']}文字")
                print()
                print(f"{Colors.GREEN}{post['post']}{Colors.RESET}")
                print()
                print(f"{Colors.MAGENTA}【図解指示プロンプト】{Colors.RESET}")
                print(f"{post['diagram_prompt']}")
                print()
            
            print(f"{Colors.CYAN}{'═' * 60}{Colors.RESET}")
            print()
            print(f"{Colors.YELLOW}💡 使い方:{Colors.RESET}")
            print(f"  1. 気に入った投稿をコピーしてXに投稿")
            print(f"  2. 図解指示プロンプトをCanvaやAI画像生成ツールで使用")
            print()
            
        finally:
            self.close()


def main():
    oracle = TrendOracle()
    oracle.run()


if __name__ == "__main__":
    main()
