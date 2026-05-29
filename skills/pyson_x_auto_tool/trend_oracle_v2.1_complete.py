#!/usr/bin/env python3
"""
Trend Oracle v2.1 - Complete
============================
API接続の安定性を確保しつつ、Fのキャラクター設定とEOEを完全に統合したバージョン
"""

import os
import sys
import time
import random
from openai import OpenAI, AuthenticationError, APIConnectionError

# EOEモジュールはv1.xから流用
try:
    from engagement_engine import EngagementOptimizationEngine
except ImportError:
    print("engagement_engine.py が見つかりません。trend_oracle_v1.2_eoe.py と同じフォルダに配置してください。")
    sys.exit(1)

# ===== カラー出力 =====
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    RESET = '\033[0m'

def log_info(msg):
    print(f"[INFO] {msg}")

def log_success(msg):
    print(f"{Colors.GREEN}[SUCCESS] {msg}{Colors.RESET}")

def log_warning(msg):
    print(f"{Colors.YELLOW}[WARNING] {msg}{Colors.RESET}")

def log_error(msg):
    print(f"{Colors.RED}[ERROR] {msg}{Colors.RESET}")

# Fのキャラクター設定 (v1.xより)
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

【絶対禁止】

× 抽象的な表現：
  - 「不透明感が増す」→ 何が不透明？具体的に！
  - 「リスク分散を心掛ける」→ 何をどう分散？

× 誰にでも言える言葉：
  - 「過度な動揺は控えて」
  - 「大事なのは情報収集」

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

def get_api_key():
    """APIキーを取得する関数"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        log_info("環境変数からAPIキーを読み込みました。")
        return api_key
    
    while True:
        log_warning("APIキーが設定されていません。")
        try:
            api_key = input(f"{Colors.YELLOW}OpenAI APIキーを入力してください: {Colors.RESET}")
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
    print("\n--- Trend Oracle v2.1 Complete ---")
    
    # 1. APIキーの取得とテスト
    openai_client = None
    while not openai_client:
        api_key = get_api_key()
        openai_client = test_api_connection(api_key)
        if not openai_client:
            os.environ.pop("OPENAI_API_KEY", None)

    # 2. EOEの初期化
    eoe = EngagementOptimizationEngine()
    
    # 3. 投稿生成
    log_info("Fのキャラクター設定とEOEを統合して投稿を生成します...")
    
    # ダミーのトレンド情報
    dummy_trend = {"keyword": "日本の株式市場、今後の見通し", "type": "news"}
    
    # EOEによる動的プロンプト生成
    prompt = eoe.generate_dynamic_prompt(dummy_trend, F_CHARACTER)
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは投資家Fというキャラクターです。提供されたキャラクター設定と構成を厳守してください。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.8
        )
        post = response.choices[0].message.content.strip()
        log_success("Fらしい投稿が生成されました！")
        print("\n--- 生成された投稿 ---")
        print(f"{Colors.CYAN}{post}{Colors.RESET}")
        print("--------------------\n")
    except Exception as e:
        log_error(f"投稿生成中にエラーが発生しました: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
