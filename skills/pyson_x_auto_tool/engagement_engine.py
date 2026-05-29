#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project Prometheus - Engagement Optimization Engine (EOE) v1.0
============================================================
エンゲージメント最適化エンジン

科学的根拠に基づいた「パワーワード」と心理的トリガーを戦略的に活用し、
SNS投稿のエンゲージメントを最大化する。
"""

import random

class EngagementOptimizationEngine:
    """
    エンゲージメント最適化エンジン (EOE)
    """

    POWER_WORDS = {
        "curiosity": ["秘密", "限定", "暴露", "裏側", "異変", "実は", "知ってましたか？", "衝撃の", "驚きの"],
        "urgency": ["今すぐ", "速報", "緊急", "ラストチャンス", "期間限定", "見逃さないで", "急いで"],
        "trust": ["実証済み", "専門家が解説", "完全ガイド", "〜の理由", "データが示す", "科学的根拠", "保証"],
        "community": ["教えて", "〜な人いますか？", "一緒に", "みんなはどう思う？", "〜仲間", "あなたの意見は？"],
    }

    def __init__(self):
        pass

    def analyze_context(self, trend_keyword: str) -> dict:
        """
        トレンドキーワードの文脈を分析する。
        簡易的なキーワードマッチングでポジティブ/ネガティブ/中立を判断。
        """
        context = {"sentiment": "neutral", "category": "unknown"}
        
        positive_keywords = ["上昇", "好調", "堅調", "拡大", "成功", "伸び"]
        negative_keywords = ["下落", "悪化", "懸念", "リスク", "失敗", "問題", "信じぬ"]

        if any(kw in trend_keyword for kw in positive_keywords):
            context["sentiment"] = "positive"
        elif any(kw in trend_keyword for kw in negative_keywords):
            context["sentiment"] = "negative"
            
        if any(kw in trend_keyword for kw in ["株", "日経", "ダウ", "為替", "ドル円", "金利", "債券", "市場"]):
            context["category"] = "market"
        elif any(kw in trend_keyword for kw in ["経済", "GDP", "CPI", "財政"]):
            context["category"] = "economy"
            
        return context

    def select_power_words(self, context: dict) -> list:
        """
        文脈に基づいて最適なパワーワードを選択する。
        """
        selected_words = []
        
        if context["sentiment"] == "negative":
            selected_words.extend(random.sample(self.POWER_WORDS["trust"], 1))
            selected_words.extend(random.sample(self.POWER_WORDS["community"], 1))
        elif context["sentiment"] == "positive":
            selected_words.extend(random.sample(self.POWER_WORDS["curiosity"], 1))
            selected_words.extend(random.sample(self.POWER_WORDS["urgency"], 1))
        else:
            selected_words.extend(random.sample(self.POWER_WORDS["curiosity"], 1))
            selected_words.extend(random.sample(self.POWER_WORDS["community"], 1))
            
        return selected_words

    def generate_dynamic_prompt(self, trend: dict, character_prompt: str) -> str:
        """
        EOEの分析結果を反映した動的プロンプトを生成する。
        """
        context = self.analyze_context(trend["keyword"])
        power_words = self.select_power_words(context)
        
        eoe_instruction = f"""\n【EOEからの追加指示】
- 文脈: {context['sentiment']}
- 使用を推奨するパワーワード: 「{power_words[0]}」「{power_words[1]}」
- これらのワードを投稿文のフックやアクションを促す部分に自然に組み込んでください。
"""
        
        base_prompt = f"""{character_prompt}\n\n以下のトレンド/ニュースについて、投資家Fとして投稿文を作成してください。\n\n【トレンド/ニュース】\n{trend['keyword']}\n\n【ソース】\n{trend['source']}
{eoe_instruction}
【注意事項】\n- 具体的な銘柄推奨や売買指示は絶対にしない\n- ニュースの事実をそのまま伝えるのではなく、Fの視点でコメントする\n- 読者が「いいね」したくなるような共感や気づきを含める\n- 200〜280文字（絵文字含む）\n\n投稿文のみを出力してください。"""
        
        return base_prompt

    def score_post(self, post_text: str, power_words: list) -> int:
        """
        生成された投稿をスコアリングする（簡易版）。
        """
        score = 0
        for word in power_words:
            if word in post_text:
                score += 10
        # 文字数も評価に入れる
        if 200 <= len(post_text) <= 280:
            score += 5
        return score
