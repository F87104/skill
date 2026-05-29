"""
Project Prometheus - The Oracle: News Collector v2.0
=====================================================
プロ金融投資家会議の結論を反映したニュース・情報収集モジュール

情報源ランク（会議で決定）:
- Sランク: Bloomberg, Reuters（プロの標準）
- Aランク: 日経電子版, Fed/日銀公式
- Bランク: 信頼できるXアカウント
- Cランク: 一般ニュースサイト（非推奨）
- Dランク: TVニュース（使用禁止）
"""

import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).parent.parent))

from core import get_config, get_logger, DATA_DIR

logger = get_logger("oracle.collector")

@dataclass
class NewsItem:
    """ニュースアイテム"""
    id: str
    title: str
    summary: str
    source: str
    url: str
    published: Optional[datetime] = None
    category: str = "general"
    relevance_score: float = 0.0
    source_rank: str = "C"  # S, A, B, C, D
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "source": self.source,
            "url": self.url,
            "published": self.published.isoformat() if self.published else None,
            "category": self.category,
            "relevance_score": self.relevance_score,
            "source_rank": self.source_rank
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "NewsItem":
        published = None
        if data.get("published"):
            published = datetime.fromisoformat(data["published"])
        return cls(
            id=data["id"],
            title=data["title"],
            summary=data["summary"],
            source=data["source"],
            url=data["url"],
            published=published,
            category=data.get("category", "general"),
            relevance_score=data.get("relevance_score", 0.0),
            source_rank=data.get("source_rank", "C")
        )


class NewsCollector:
    """プロ品質ニュース収集エンジン v2.0"""
    
    # ==========================================
    # プロ金融投資家会議で決定した情報源ランク
    # ==========================================
    SOURCE_RANKS = {
        # Sランク: プロの標準
        "bloomberg": "S",
        "reuters": "S",
        "wsj": "S",
        "financial times": "S",
        
        # Aランク: 信頼性高い
        "nikkei": "A",
        "日経": "A",
        "日本経済新聞": "A",
        "federal reserve": "A",
        "日銀": "A",
        "bank of japan": "A",
        "ecb": "A",
        "imf": "A",
        
        # Bランク: 参考程度
        "yahoo finance": "B",
        "investing.com": "B",
        "marketwatch": "B",
        "cnbc": "B",
        "tradingview": "B",
        
        # Cランク: 一般ニュース（非推奨）
        "nhk": "C",
        "朝日": "C",
        "読売": "C",
        "毎日": "C",
        
        # Dランク: 使用禁止
        "ann": "D",
        "テレ朝": "D",
        "tbs": "D",
        "フジ": "D",
    }
    
    # プロ品質RSSフィード（Sランク・Aランク優先）
    PRO_RSS_FEEDS = [
        # Sランク
        "https://feeds.bloomberg.com/markets/news.rss",
        "https://feeds.reuters.com/reuters/businessNews",
        "https://feeds.reuters.com/reuters/topNews",
        
        # Aランク - 日経
        "https://www.nikkei.com/rss/markets.xml",
        "https://www.nikkei.com/rss/economy.xml",
        "https://www.nikkei.com/rss/financial.xml",
        
        # Bランク - 参考
        "https://finance.yahoo.com/rss/topstories",
        "https://www.investing.com/rss/news.rss",
    ]
    
    # 投資関連キーワード（関連性スコアリング用）- 強化版
    INVESTMENT_KEYWORDS = {
        "critical": [  # 最重要（+5.0）
            "FOMC", "日銀", "Fed", "利上げ", "利下げ", "金融政策",
            "雇用統計", "CPI", "インフレ", "GDP", "介入", "為替介入"
        ],
        "high": [  # 高重要（+3.0）
            "為替", "FX", "ドル円", "USDJPY", "ユーロ円", "ポンド円",
            "株価", "日経平均", "S&P500", "ダウ", "NASDAQ",
            "金利", "国債", "利回り", "10年債"
        ],
        "medium": [  # 中重要（+1.5）
            "経済", "市場", "投資", "資産", "円安", "円高",
            "株式", "債券", "金融", "景気", "成長", "recession", "相場",
            "リスクオン", "リスクオフ", "ボラティリティ"
        ],
        "low": [  # 低重要（+0.5）
            "ビジネス", "企業", "決算", "業績", "M&A", "IPO",
            "テクニカル", "サポート", "レジスタンス"
        ]
    }
    
    def __init__(self):
        self.config = get_config()
        self.cache_file = DATA_DIR / "news_cache.json"
        self._cache: Dict[str, NewsItem] = {}
        self._load_cache()
    
    def _load_cache(self):
        """キャッシュの読み込み"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._cache = {k: NewsItem.from_dict(v) for k, v in data.items()}
            except Exception as e:
                logger.warning(f"キャッシュ読み込みエラー: {e}")
                self._cache = {}
    
    def _save_cache(self):
        """キャッシュの保存"""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                data = {k: v.to_dict() for k, v in self._cache.items()}
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"キャッシュ保存エラー: {e}")
    
    def _generate_id(self, title: str, url: str) -> str:
        """ニュースIDの生成"""
        content = f"{title}:{url}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _get_source_rank(self, source_name: str) -> str:
        """ソースのランクを取得"""
        source_lower = source_name.lower()
        for keyword, rank in self.SOURCE_RANKS.items():
            if keyword in source_lower:
                return rank
        return "C"  # デフォルトはCランク
    
    def _calculate_relevance(self, title: str, summary: str, source_rank: str) -> float:
        """関連性スコアの計算（ソースランク考慮）"""
        text = f"{title} {summary}".lower()
        score = 0.0
        
        # キーワードスコア
        for keyword in self.INVESTMENT_KEYWORDS["critical"]:
            if keyword.lower() in text:
                score += 5.0
        
        for keyword in self.INVESTMENT_KEYWORDS["high"]:
            if keyword.lower() in text:
                score += 3.0
        
        for keyword in self.INVESTMENT_KEYWORDS["medium"]:
            if keyword.lower() in text:
                score += 1.5
        
        for keyword in self.INVESTMENT_KEYWORDS["low"]:
            if keyword.lower() in text:
                score += 0.5
        
        # ソースランクによるボーナス/ペナルティ
        rank_multiplier = {
            "S": 1.5,   # 50%ボーナス
            "A": 1.2,   # 20%ボーナス
            "B": 1.0,   # 変化なし
            "C": 0.7,   # 30%ペナルティ
            "D": 0.3,   # 70%ペナルティ（ほぼ使わない）
        }
        
        score *= rank_multiplier.get(source_rank, 1.0)
        
        return min(score, 15.0)  # 最大15.0
    
    def collect_from_rss(self, feed_url: str) -> List[NewsItem]:
        """RSSフィードからニュースを収集"""
        items = []
        
        try:
            feed = feedparser.parse(feed_url)
            source_name = feed.feed.get("title", "Unknown")
            source_rank = self._get_source_rank(source_name)
            
            # Dランクソースはスキップ
            if source_rank == "D":
                logger.warning(f"Dランクソースをスキップ: {source_name}")
                return []
            
            for entry in feed.entries[:20]:  # 最新20件
                title = entry.get("title", "")
                summary = entry.get("summary", entry.get("description", ""))
                url = entry.get("link", "")
                
                # HTMLタグの除去
                if summary:
                    soup = BeautifulSoup(summary, "html.parser")
                    summary = soup.get_text()[:500]
                
                # 日時のパース
                published = None
                if "published_parsed" in entry and entry.published_parsed:
                    try:
                        published = datetime(*entry.published_parsed[:6])
                    except:
                        pass
                
                news_id = self._generate_id(title, url)
                
                # 重複チェック
                if news_id in self._cache:
                    continue
                
                relevance = self._calculate_relevance(title, summary, source_rank)
                
                item = NewsItem(
                    id=news_id,
                    title=title,
                    summary=summary,
                    source=source_name,
                    url=url,
                    published=published,
                    relevance_score=relevance,
                    source_rank=source_rank
                )
                
                items.append(item)
                self._cache[news_id] = item
            
            rank_emoji = {"S": "🏆", "A": "⭐", "B": "📰", "C": "📄", "D": "❌"}
            logger.info(f"{rank_emoji.get(source_rank, '📄')} [{source_rank}] {source_name}: {len(items)}件")
            
        except Exception as e:
            logger.error(f"RSS収集エラー: {e}")
        
        return items
    
    def collect_all(self) -> List[NewsItem]:
        """全ソースからニュースを収集（プロ品質フィード優先）"""
        all_items = []
        
        # まずプロ品質フィードから収集
        logger.info("プロ品質フィードから収集中...")
        for feed_url in self.PRO_RSS_FEEDS:
            items = self.collect_from_rss(feed_url)
            all_items.extend(items)
        
        # 設定ファイルのフィードも追加（あれば）
        if hasattr(self.config.oracle, 'rss_feeds'):
            for feed_url in self.config.oracle.rss_feeds:
                if feed_url not in self.PRO_RSS_FEEDS:
                    items = self.collect_from_rss(feed_url)
                    all_items.extend(items)
        
        # キャッシュの保存
        self._save_cache()
        
        # 関連性スコアでソート
        all_items.sort(key=lambda x: x.relevance_score, reverse=True)
        
        # ランク別の統計
        rank_counts = {"S": 0, "A": 0, "B": 0, "C": 0, "D": 0}
        for item in all_items:
            rank_counts[item.source_rank] = rank_counts.get(item.source_rank, 0) + 1
        
        logger.info(f"収集完了: 合計{len(all_items)}件")
        logger.info(f"  Sランク: {rank_counts['S']}件 | Aランク: {rank_counts['A']}件 | Bランク: {rank_counts['B']}件")
        
        return all_items
    
    def get_top_news(self, count: int = 5, min_rank: str = "B") -> List[NewsItem]:
        """関連性の高いトップニュースを取得（ランクフィルター付き）"""
        items = self.collect_all()
        
        # ランクフィルター
        rank_order = {"S": 0, "A": 1, "B": 2, "C": 3, "D": 4}
        min_rank_value = rank_order.get(min_rank, 2)
        
        filtered_items = [
            item for item in items 
            if rank_order.get(item.source_rank, 4) <= min_rank_value
        ]
        
        # 24時間以内のニュースのみ
        cutoff = datetime.now() - timedelta(hours=24)
        recent_items = [
            item for item in filtered_items 
            if item.published is None or item.published > cutoff
        ]
        
        # 関連性スコアが2.0以上のもの（強化）
        relevant_items = [item for item in recent_items if item.relevance_score >= 2.0]
        
        logger.info(f"トップニュース: {len(relevant_items[:count])}件（{min_rank}ランク以上）")
        
        return relevant_items[:count]
    
    def get_breaking_news(self, hours: int = 1) -> List[NewsItem]:
        """直近の速報ニュースを取得（Sランク優先）"""
        items = self.collect_all()
        
        # 指定時間以内
        cutoff = datetime.now() - timedelta(hours=hours)
        recent_items = [
            item for item in items 
            if item.published and item.published > cutoff
        ]
        
        # Sランク・Aランクのみ
        high_rank_items = [
            item for item in recent_items 
            if item.source_rank in ["S", "A"]
        ]
        
        # 関連性スコアでソート
        high_rank_items.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return high_rank_items[:3]
    
    def clear_old_cache(self, days: int = 7):
        """古いキャッシュをクリア"""
        cutoff = datetime.now() - timedelta(days=days)
        
        old_keys = [
            k for k, v in self._cache.items()
            if v.published and v.published < cutoff
        ]
        
        for key in old_keys:
            del self._cache[key]
        
        self._save_cache()
        logger.info(f"古いキャッシュを{len(old_keys)}件削除")
