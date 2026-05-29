#!/usr/bin/env python3
"""
Project Prometheus - Note Oracle v1.0
=====================================
note向け長文記事生成システム

特徴:
- 投資家「F」のペルソナで長文記事を生成
- トレンドを基にしたタイムリーな内容
- noteに最適化された構成（見出し、段落、まとめ）

使い方:
    python3 note_oracle.py
"""

import os
import sys
import re
import urllib.request
import urllib.error
import json
from datetime import datetime

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

def log_error(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{Colors.RED}[{timestamp}][ERROR]{Colors.RESET} {msg}")

def log_phase(msg):
    print(f"\n{Colors.CYAN}{Colors.BOLD}{msg}{Colors.RESET}")

# ===== バナー =====
BANNER = f"""
{Colors.MAGENTA}╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   ███╗   ██╗ ██████╗ ████████╗███████╗                   ║
║   ████╗  ██║██╔═══██╗╚══██╔══╝██╔════╝                   ║
║   ██╔██╗ ██║██║   ██║   ██║   █████╗                     ║
║   ██║╚██╗██║██║   ██║   ██║   ██╔══╝                     ║
║   ██║ ╚████║╚██████╔╝   ██║   ███████╗                   ║
║   ╚═╝  ╚═══╝ ╚═════╝    ╚═╝   ╚══════╝                   ║
║                                                           ║
║    ██████╗ ██████╗  █████╗  ██████╗██╗     ███████╗      ║
║   ██╔═══██╗██╔══██╗██╔══██╗██╔════╝██║     ██╔════╝      ║
║   ██║   ██║██████╔╝███████║██║     ██║     █████╗        ║
║   ██║   ██║██╔══██╗██╔══██║██║     ██║     ██╔══╝        ║
║   ╚██████╔╝██║  ██║██║  ██║╚██████╗███████╗███████╗      ║
║    ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚══════╝╚══════╝      ║
║                                                           ║
║   Note Oracle v1.0 - note向け記事生成                    ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝{Colors.RESET}
"""

# ===== Fのキャラクター設定（note版） =====
F_CHARACTER_NOTE = """
あなたは「投資家F」という投資の専門家キャラクターです。
noteで長文の投資解説記事を書きます。

【キャラクター】
- 難しいことを簡単に、でも本質は外さない
- 読者と「一緒に学ぶ仲間」というスタンス
- 柔らかいけど芯がある
- 優しい、でも甘くない

【文章スタイル】
- 「〜だね」「〜かも」「〜だよ」という柔らかい口調
- 絵文字を適度に使用: 📚🐻🌷🌈😺💌🥰✨💭
- 読者への問いかけを入れる
- 具体例や数字を必ず入れる

【記事構成】
1. タイトル（興味を引く、具体的な内容がわかる）
2. 導入（共感から入る、読者の悩みに寄り添う）
3. 本文（見出しで区切る、具体例を入れる）
4. まとめ（行動につながる、励まし）

【禁止事項】
× 抽象的な表現（「不透明感」「リスク分散」など）
× 誰にでも言える一般論
× 具体的な銘柄推奨や売買指示
× 上から目線の説教
"""

# ===== 記事テンプレート =====
ARTICLE_TEMPLATES = [
    {
        "type": "解説記事",
        "description": "特定のトピックを深掘りして解説",
        "structure": """
【タイトル】〇〇とは？初心者でもわかる完全ガイド

【導入】（200字程度）
- 読者の悩みや疑問に共感
- この記事を読むとわかること

【本文】
## 〇〇って何？基本をおさらい
（300字程度、基本的な説明）

## なぜ今〇〇が注目されているの？
（300字程度、背景や理由）

## 〇〇のメリット・デメリット
（400字程度、具体的に）

## 実際にどうすればいい？具体的なステップ
（400字程度、行動につながる内容）

【まとめ】（200字程度）
- 要点の整理
- 読者への励まし
"""
    },
    {
        "type": "トレンド分析",
        "description": "最新ニュースを分析して解説",
        "structure": """
【タイトル】〇〇が起きた！投資家が知っておくべき3つのポイント

【導入】（200字程度）
- ニュースの概要
- なぜこれが重要なのか

【本文】
## 何が起きたの？事実を整理
（300字程度、客観的な事実）

## これが意味すること
（400字程度、分析と解説）

## 私たちはどうすればいい？
（400字程度、具体的なアクション）

【まとめ】（200字程度）
- 要点の整理
- 冷静に対応することの大切さ
"""
    },
    {
        "type": "マインドセット",
        "description": "投資の考え方や心構えを伝える",
        "structure": """
【タイトル】〇〇で失敗しないために大切な考え方

【導入】（200字程度）
- 読者の不安や悩みに共感
- 自分の経験を少し交える

【本文】
## よくある失敗パターン
（300字程度、具体例）

## なぜそうなってしまうのか
（300字程度、心理的な分析）

## 成功する人の考え方
（400字程度、具体的なマインドセット）

## 今日からできること
（300字程度、小さな一歩）

【まとめ】（200字程度）
- 読者への励まし
- 一緒に成長していこうというメッセージ
"""
    }
]

# ===== トピック候補 =====
TOPIC_SUGGESTIONS = [
    # 基礎知識系
    "NISAの始め方",
    "iDeCoのメリット・デメリット",
    "投資信託と個別株の違い",
    "ドルコスト平均法とは",
    "複利の力",
    
    # トレンド系
    "円安が続く理由と対策",
    "米国株vs日本株",
    "高配当株投資の魅力",
    "インデックス投資の基本",
    "新NISA活用法",
    
    # マインドセット系
    "投資で焦らないコツ",
    "暴落時のメンタル管理",
    "長期投資を続けるために",
    "投資の失敗から学んだこと",
    "お金と幸せの関係",
]


def call_openai_api(api_key: str, messages: list) -> str:
    """OpenAI APIを直接呼び出す（urllib使用）"""
    url = "https://api.openai.com/v1/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    data = {
        "model": "gpt-4o-mini",
        "messages": messages,
        "temperature": 0.8,
        "max_tokens": 3000
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8'),
        headers=headers,
        method='POST'
    )
    
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result['choices'][0]['message']['content']
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        raise Exception(f"API Error {e.code}: {error_body}")
    except urllib.error.URLError as e:
        raise Exception(f"Connection Error: {e.reason}")


class NoteOracle:
    """note記事生成エンジン"""
    
    def __init__(self):
        self.api_key = None
    
    def setup_openai(self):
        """OpenAI APIをセットアップ"""
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            log_error("OPENAI_API_KEYが設定されていません")
            log_error("以下のコマンドで設定してください:")
            log_error('  export OPENAI_API_KEY="あなたのAPIキー"')
            return False
        
        log_success("OpenAI API設定完了")
        return True
    
    def select_topic(self) -> str:
        """トピックを選択"""
        log_phase("=" * 50)
        log_phase("トピック選択")
        log_phase("=" * 50)
        
        print("\n【トピック候補】")
        for i, topic in enumerate(TOPIC_SUGGESTIONS, 1):
            print(f"  {i}. {topic}")
        
        print(f"\n  0. 自分でトピックを入力")
        
        while True:
            try:
                choice = input(f"\n番号を選択 (0-{len(TOPIC_SUGGESTIONS)}): ").strip()
                
                if choice == "0":
                    custom_topic = input("トピックを入力: ").strip()
                    if custom_topic:
                        return custom_topic
                    print("トピックを入力してください")
                    continue
                
                idx = int(choice) - 1
                if 0 <= idx < len(TOPIC_SUGGESTIONS):
                    return TOPIC_SUGGESTIONS[idx]
                
                print(f"1〜{len(TOPIC_SUGGESTIONS)}の番号を入力してください")
            except ValueError:
                print("数字を入力してください")
    
    def select_template(self) -> dict:
        """記事テンプレートを選択"""
        log_phase("=" * 50)
        log_phase("記事タイプ選択")
        log_phase("=" * 50)
        
        print("\n【記事タイプ】")
        for i, template in enumerate(ARTICLE_TEMPLATES, 1):
            print(f"  {i}. {template['type']}: {template['description']}")
        
        while True:
            try:
                choice = input(f"\n番号を選択 (1-{len(ARTICLE_TEMPLATES)}): ").strip()
                idx = int(choice) - 1
                if 0 <= idx < len(ARTICLE_TEMPLATES):
                    return ARTICLE_TEMPLATES[idx]
                print(f"1〜{len(ARTICLE_TEMPLATES)}の番号を入力してください")
            except ValueError:
                print("数字を入力してください")
    
    def generate_article(self, topic: str, template: dict) -> str:
        """記事を生成"""
        log_phase("=" * 50)
        log_phase("記事生成中...")
        log_phase("=" * 50)
        
        prompt = f"""
以下のトピックについて、note向けの記事を書いてください。

【トピック】
{topic}

【記事タイプ】
{template['type']}

【構成】
{template['structure']}

【文字数】
1500〜2500文字程度

【注意事項】
- 見出しは「##」で始める（Markdown形式）
- 各セクションの間に空行を入れる
- 絵文字は見出しの最後や文末に適度に入れる
- 具体的な数字や例を必ず入れる
- 読者への問いかけを入れる
"""
        
        try:
            messages = [
                {"role": "system", "content": F_CHARACTER_NOTE},
                {"role": "user", "content": prompt}
            ]
            
            article = call_openai_api(self.api_key, messages)
            log_success("記事生成完了！")
            return article
            
        except Exception as e:
            log_error(f"記事生成エラー: {e}")
            return None
    
    def save_article(self, article: str, topic: str):
        """記事をファイルに保存"""
        # ファイル名を作成（日付 + トピック）
        date_str = datetime.now().strftime("%Y%m%d_%H%M")
        safe_topic = re.sub(r'[^\w\s]', '', topic)[:20].strip().replace(' ', '_')
        filename = f"note_article_{date_str}_{safe_topic}.md"
        
        filepath = os.path.join(os.path.dirname(__file__), filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(article)
        
        log_success(f"記事を保存しました: {filename}")
        return filepath
    
    def run(self):
        """メイン処理"""
        print(BANNER)
        
        # OpenAI APIセットアップ
        if not self.setup_openai():
            return
        
        # トピック選択
        topic = self.select_topic()
        log_info(f"選択されたトピック: {topic}")
        
        # テンプレート選択
        template = self.select_template()
        log_info(f"選択された記事タイプ: {template['type']}")
        
        # 記事生成
        article = self.generate_article(topic, template)
        
        if article:
            # 記事を表示
            log_phase("=" * 50)
            log_phase("生成された記事")
            log_phase("=" * 50)
            print()
            print(article)
            print()
            
            # 保存確認
            save = input("この記事を保存しますか？ (y/n): ").strip().lower()
            if save == 'y':
                filepath = self.save_article(article, topic)
                print()
                log_info("保存した記事はnoteにコピー&ペーストして投稿できます")
            
            # 再生成確認
            print()
            regenerate = input("別のトピックで記事を生成しますか？ (y/n): ").strip().lower()
            if regenerate == 'y':
                self.run()


def main():
    oracle = NoteOracle()
    oracle.run()


if __name__ == "__main__":
    main()
