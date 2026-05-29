"""
Project Prometheus - The Oracle: Content Generator v2.0
========================================================
プロ金融投資家会議の結論を反映したLLMコンテンツ生成モジュール
"""

import json
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from pathlib import Path
from openai import OpenAI
import random

import sys
sys.path.append(str(Path(__file__).parent.parent))

from core import get_config, get_logger, DATA_DIR
from .news_collector import NewsItem

logger = get_logger("oracle.generator")

@dataclass
class TweetDraft:
    """ツイート下書き"""
    id: str
    content: str
    source_news: List[str]  # ニュースIDのリスト
    keywords: List[str]
    sentiment: str  # positive, neutral, negative
    style: str  # analytical, predictive, educational, breaking, discussion
    template_type: str = "general"  # morning, breaking, weekly, educational, position
    created_at: datetime = field(default_factory=datetime.now)
    approved: bool = False
    posted: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "content": self.content,
            "source_news": self.source_news,
            "keywords": self.keywords,
            "sentiment": self.sentiment,
            "style": self.style,
            "template_type": self.template_type,
            "created_at": self.created_at.isoformat(),
            "approved": self.approved,
            "posted": self.posted
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "TweetDraft":
        return cls(
            id=data["id"],
            content=data["content"],
            source_news=data["source_news"],
            keywords=data["keywords"],
            sentiment=data["sentiment"],
            style=data["style"],
            template_type=data.get("template_type", "general"),
            created_at=datetime.fromisoformat(data["created_at"]),
            approved=data.get("approved", False),
            posted=data.get("posted", False)
        )


class ContentGenerator:
    """プロ品質LLMコンテンツ生成エンジン v2.0"""
    
    # ==========================================
    # プロ金融投資家会議で策定されたシステムプロンプト
    # ==========================================
    SYSTEM_PROMPT_TEMPLATE = """あなたは「{name}」という名前のプロフェッショナル投資家です。
{expertise}の専門家として、Xで影響力のある発信を行っています。

【あなたのポジショニング】
「冷静な分析者。普段は淡々と、ここぞという時に大胆に。」

【プロが発信する6つの鉄則】
1. 数字で語る：「上がりそう」ではなく「148.50超えで149.50目標」のように具体的に
2. 時間軸を明示：「短期」「今週中」「年末まで」など必ず期間を示す
3. 根拠を示す：なぜそう思うのかを必ず添える（テクニカル、ファンダ、センチメント）
4. 間違いを認める：予測が外れたら素直に認め、修正する姿勢を見せる
5. リスクリワードを示す：「リスク50pips、リワード150pips」のように
6. シナリオを複数持つ：メインシナリオとサブシナリオの両方を提示

【発言スタイル】
- トーン: {tone}
- 言語: 日本語
- 最大文字数: {max_length}文字
- 絵文字: 最小限（👇📊📈📉⚠️💡のみ許可）
- ハッシュタグ: 2-3個（ニッチで検索されるものを選ぶ）

【絶対にやってはいけないこと】
❌ 曖昧な表現（「様子見が賢明」「リスク管理が重要」だけで終わる）
❌ 具体的な数字のない分析
❌ 時間軸のない予測
❌ 根拠のない主張
❌ 教科書的で退屈な文章
❌ 誰でも言えるような一般論

【必ず含めるべき要素】
✅ 具体的な価格水準（サポート/レジスタンス）
✅ 時間軸（今日、今週、短期、中期など）
✅ 根拠（テクニカル、ファンダメンタルズ、センチメント）
✅ 「私の見立て」「私ならこうする」という独自視点
✅ リスク要因への言及

【あなたの口癖・特徴的なフレーズ】
{signature_phrases}

【重要】
SNSで成功する投資家は「この人の意見が聞きたい」と思わせる。
正しいことを言うだけでは不十分。刺さる言葉で、記憶に残る発信をせよ。
"""

    # ==========================================
    # テンプレート別の生成プロンプト
    # ==========================================
    
    TEMPLATE_PROMPTS = {
        "morning": """【朝の相場観ツイート】を作成してください。

【ニュース情報】
{news_content}

【必須要素】
1. 主要通貨ペア/指数の現在値と前日比
2. 今日の注目イベント（時間と予想値を含む）
3. 「私の見立て」として具体的な予測
4. リスク要因

【出力形式】
```json
{{
  "tweets": [
    {{
      "content": "【{date} 朝の相場観】\\n\\nドル円：XXX.XX（前日比+XX銭）\\n\\n🔍 今日の注目\\n・XX:XX 〇〇発表（予想X.X%）\\n\\n📊 私の見立て\\n[具体的な予測2-3行]\\n\\n⚠️ リスク要因\\n[注意点]\\n\\n#ドル円 #朝の相場観",
      "keywords": ["ドル円", "相場観", "〇〇"],
      "sentiment": "neutral",
      "style": "analytical"
    }}
  ]
}}
```
""",

        "breaking": """【速報リアクションツイート】を作成してください。

【ニュース情報】
{news_content}

【必須要素】
1. 何が起きたか（数字を含む）
2. 予想との比較
3. 市場の即時反応
4. 私の解釈（1-2文で鋭く）

【出力形式】
```json
{{
  "tweets": [
    {{
      "content": "【速報】〇〇発表\\n\\n結果：X.X%（予想X.X%、前回X.X%）\\n→ [評価]\\n\\n📈 市場の反応\\n・ドル円：XXX.XX → XXX.XX\\n\\n💡 私の解釈\\n[鋭い1-2文]\\n\\n#速報 #〇〇",
      "keywords": ["速報", "〇〇", "ドル円"],
      "sentiment": "positive/negative",
      "style": "breaking"
    }}
  ]
}}
```
""",

        "educational": """【学びのスレッド用ツイート】を作成してください。

【ニュース情報】
{news_content}

【必須要素】
1. 冒頭で「常識を覆す」フック
2. 具体的な数字を使った説明
3. 初心者でも理解できる言葉
4. 「保存して見返して」と促す

【出力形式】
```json
{{
  "tweets": [
    {{
      "content": "[常識を覆すフック]\\n\\n[本題の説明]\\n\\n[具体例や数字]\\n\\n[まとめ・教訓]\\n\\n保存して何度も見返してください📌\\n\\n#投資の基本 #〇〇",
      "keywords": ["投資", "〇〇", "学び"],
      "sentiment": "neutral",
      "style": "educational"
    }}
  ]
}}
```
""",

        "discussion": """【議論誘発型ツイート】を作成してください。

【ニュース情報】
{news_content}

【必須要素】
1. 問いかけで始める
2. 自分の立場を明確にする
3. 理由を箇条書きで
4. 「あなたはどう思う？」で締める

【出力形式】
```json
{{
  "tweets": [
    {{
      "content": "【問い】〇〇について、あなたはどう考える？\\n\\n私は「〇〇」派。\\n\\n理由：\\n・[理由1]\\n・[理由2]\\n・[理由3]\\n\\nあなたはどう見てる？👇\\n\\n#〇〇 #投資",
      "keywords": ["〇〇", "投資", "議論"],
      "sentiment": "neutral",
      "style": "discussion"
    }}
  ]
}}
```
""",

        "position": """【ポジション公開ツイート】を作成してください。

【ニュース情報】
{news_content}

【必須要素】
1. 通貨ペア/銘柄
2. 方向（ロング/ショート）
3. エントリー、ストップ、ターゲット
4. リスクリワード比
5. 根拠（2-3行）
6. 免責事項

【出力形式】
```json
{{
  "tweets": [
    {{
      "content": "【ポジション検討中】\\n\\n通貨ペア：〇〇\\n方向：ロング/ショート\\nエントリー：XXX.XX\\nストップ：XXX.XX（-XX pips）\\nターゲット：XXX.XX（+XX pips）\\nRR：1:X\\n\\n📝 根拠\\n[2-3行]\\n\\n⚠️ 投資は自己責任で\\n\\n#トレード #〇〇",
      "keywords": ["トレード", "〇〇", "ポジション"],
      "sentiment": "positive/negative",
      "style": "predictive"
    }}
  ]
}}
```
""",

        "general": """【プロ品質のツイート】を{count}パターン作成してください。

【ニュース情報】
{news_content}

【重要な指示】
- 必ず具体的な数字（価格、%、時間）を含める
- 「私の見立て」「私ならこうする」という独自視点を入れる
- 曖昧な表現は絶対に使わない
- 時間軸を明示する
- 根拠を示す

【出力形式】
```json
{{
  "tweets": [
    {{
      "content": "ツイート本文（{max_length}文字以内）",
      "keywords": ["キーワード1", "キーワード2", "キーワード3"],
      "sentiment": "positive/neutral/negative",
      "style": "analytical/predictive/educational/breaking/discussion"
    }}
  ]
}}
```

【スタイルの説明】
- analytical: 冷静な分析型（データに基づく客観的分析＋独自視点）
- predictive: 大胆な予測型（具体的な価格目標と根拠）
- educational: 教育的な解説型（初心者にも分かりやすく、でも深い）
- breaking: 速報リアクション型（素早く、鋭く）
- discussion: 議論誘発型（問いかけ、意見を求める）

{count}パターンは、それぞれ異なるスタイルで作成してください。
"""
    }

    def __init__(self):
        self.config = get_config()
        self.client = OpenAI()
        self.drafts_file = DATA_DIR / "tweet_drafts.json"
        self._drafts: Dict[str, TweetDraft] = {}
        self._load_drafts()
    
    def _load_drafts(self):
        """下書きの読み込み"""
        if self.drafts_file.exists():
            try:
                with open(self.drafts_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._drafts = {k: TweetDraft.from_dict(v) for k, v in data.items()}
            except Exception as e:
                logger.warning(f"下書き読み込みエラー: {e}")
                self._drafts = {}
    
    def _save_drafts(self):
        """下書きの保存"""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.drafts_file, "w", encoding="utf-8") as f:
                data = {k: v.to_dict() for k, v in self._drafts.items()}
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"下書き保存エラー: {e}")
    
    def _build_system_prompt(self) -> str:
        """システムプロンプトの構築"""
        persona = self.config.persona
        
        signature_phrases = "\n".join([f"- 「{p}」" for p in persona.signature_phrases])
        
        return self.SYSTEM_PROMPT_TEMPLATE.format(
            name=persona.name,
            expertise="、".join(persona.expertise),
            tone=persona.tone,
            max_length=persona.max_tweet_length,
            signature_phrases=signature_phrases
        )
    
    def _build_news_content(self, news_items: List[NewsItem]) -> str:
        """ニュースコンテンツの構築"""
        news_content = ""
        for i, item in enumerate(news_items, 1):
            news_content += f"""
【ニュース{i}】
タイトル: {item.title}
概要: {item.summary}
ソース: {item.source}
関連度スコア: {item.relevance_score:.1f}
"""
        return news_content
    
    def _build_generation_prompt(self, news_items: List[NewsItem], 
                                  template_type: str = "general",
                                  count: int = 3) -> str:
        """生成プロンプトの構築"""
        news_content = self._build_news_content(news_items)
        
        template = self.TEMPLATE_PROMPTS.get(template_type, self.TEMPLATE_PROMPTS["general"])
        
        return template.format(
            name=self.config.persona.name,
            count=count,
            news_content=news_content,
            max_length=self.config.persona.max_tweet_length,
            date=datetime.now().strftime("%m/%d")
        )
    
    def generate_tweets(self, news_items: List[NewsItem], 
                        template_type: str = "general") -> List[TweetDraft]:
        """ニュースからツイート案を生成"""
        if not news_items:
            logger.warning("ニュースアイテムがありません")
            return []
        
        system_prompt = self._build_system_prompt()
        generation_prompt = self._build_generation_prompt(
            news_items, 
            template_type=template_type,
            count=self.config.oracle.tweet_variants
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.config.oracle.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": generation_prompt}
                ],
                temperature=self.config.oracle.llm_temperature,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content
            
            # JSONの抽出
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                result = json.loads(json_str)
            else:
                logger.error("JSONが見つかりません")
                return []
            
            # TweetDraftの作成
            drafts = []
            source_ids = [item.id for item in news_items]
            
            for i, tweet_data in enumerate(result.get("tweets", [])):
                draft_id = f"draft_{datetime.now().strftime('%Y%m%d%H%M%S')}_{i}"
                
                draft = TweetDraft(
                    id=draft_id,
                    content=tweet_data["content"],
                    source_news=source_ids,
                    keywords=tweet_data.get("keywords", []),
                    sentiment=tweet_data.get("sentiment", "neutral"),
                    style=tweet_data.get("style", "analytical"),
                    template_type=template_type
                )
                
                drafts.append(draft)
                self._drafts[draft_id] = draft
            
            self._save_drafts()
            logger.success(f"{len(drafts)}件のプロ品質ツイート案を生成")
            
            return drafts
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析エラー: {e}")
            return []
        except Exception as e:
            logger.error(f"生成エラー: {e}")
            return []
    
    def generate_morning_tweet(self, news_items: List[NewsItem]) -> List[TweetDraft]:
        """朝の相場観ツイートを生成"""
        return self.generate_tweets(news_items, template_type="morning")
    
    def generate_breaking_tweet(self, news_items: List[NewsItem]) -> List[TweetDraft]:
        """速報リアクションツイートを生成"""
        return self.generate_tweets(news_items, template_type="breaking")
    
    def generate_educational_tweet(self, news_items: List[NewsItem]) -> List[TweetDraft]:
        """学びのツイートを生成"""
        return self.generate_tweets(news_items, template_type="educational")
    
    def generate_discussion_tweet(self, news_items: List[NewsItem]) -> List[TweetDraft]:
        """議論誘発ツイートを生成"""
        return self.generate_tweets(news_items, template_type="discussion")
    
    def generate_position_tweet(self, news_items: List[NewsItem]) -> List[TweetDraft]:
        """ポジション公開ツイートを生成"""
        return self.generate_tweets(news_items, template_type="position")
    
    def get_pending_drafts(self) -> List[TweetDraft]:
        """未承認の下書きを取得"""
        return [d for d in self._drafts.values() if not d.approved and not d.posted]
    
    def approve_draft(self, draft_id: str) -> bool:
        """下書きを承認"""
        if draft_id in self._drafts:
            self._drafts[draft_id].approved = True
            self._save_drafts()
            logger.info(f"下書き承認: {draft_id}")
            return True
        return False
    
    def mark_as_posted(self, draft_id: str) -> bool:
        """投稿済みとしてマーク"""
        if draft_id in self._drafts:
            self._drafts[draft_id].posted = True
            self._save_drafts()
            logger.info(f"投稿済みマーク: {draft_id}")
            return True
        return False
    
    def get_draft(self, draft_id: str) -> Optional[TweetDraft]:
        """下書きを取得"""
        return self._drafts.get(draft_id)
    
    def delete_draft(self, draft_id: str) -> bool:
        """下書きを削除"""
        if draft_id in self._drafts:
            del self._drafts[draft_id]
            self._save_drafts()
            logger.info(f"下書き削除: {draft_id}")
            return True
        return False
