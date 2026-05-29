"""
Project Prometheus - The Forge: Post Manager
=============================================
第2層: 鍛造レイヤー - レビュー・投稿管理モジュール
"""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

import sys
sys.path.append(str(Path(__file__).parent.parent))

from core import get_config, get_logger, get_x_client, DATA_DIR
from oracle import TweetDraft, ContentGenerator

logger = get_logger("forge.manager")

class ReviewAction(Enum):
    """レビューアクション"""
    APPROVE = "approve"      # 承認（そのまま投稿可能）
    EDIT = "edit"            # 編集して承認
    REJECT = "reject"        # 却下
    DEFER = "defer"          # 保留（後で再検討）


@dataclass
class PostRecord:
    """投稿記録"""
    draft_id: str
    tweet_id: str
    content: str
    keywords: List[str]
    posted_at: datetime
    engagement: Dict = field(default_factory=dict)  # いいね数、RT数など
    
    def to_dict(self) -> Dict:
        return {
            "draft_id": self.draft_id,
            "tweet_id": self.tweet_id,
            "content": self.content,
            "keywords": self.keywords,
            "posted_at": self.posted_at.isoformat(),
            "engagement": self.engagement
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "PostRecord":
        return cls(
            draft_id=data["draft_id"],
            tweet_id=data["tweet_id"],
            content=data["content"],
            keywords=data["keywords"],
            posted_at=datetime.fromisoformat(data["posted_at"]),
            engagement=data.get("engagement", {})
        )


class PostManager:
    """投稿管理エンジン"""
    
    def __init__(self):
        self.config = get_config()
        self.x_client = get_x_client()
        self.generator = ContentGenerator()
        self.records_file = DATA_DIR / "post_records.json"
        self._records: Dict[str, PostRecord] = {}
        self._load_records()
    
    def _load_records(self):
        """投稿記録の読み込み"""
        if self.records_file.exists():
            try:
                with open(self.records_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._records = {k: PostRecord.from_dict(v) for k, v in data.items()}
            except Exception as e:
                logger.warning(f"投稿記録読み込みエラー: {e}")
                self._records = {}
    
    def _save_records(self):
        """投稿記録の保存"""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.records_file, "w", encoding="utf-8") as f:
                data = {k: v.to_dict() for k, v in self._records.items()}
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"投稿記録保存エラー: {e}")
    
    def get_pending_drafts(self) -> List[TweetDraft]:
        """レビュー待ちの下書きを取得"""
        return self.generator.get_pending_drafts()
    
    def review_draft(self, draft_id: str, action: ReviewAction, 
                     edited_content: Optional[str] = None) -> Tuple[bool, str]:
        """下書きをレビュー"""
        draft = self.generator.get_draft(draft_id)
        
        if not draft:
            return False, "下書きが見つかりません"
        
        if action == ReviewAction.APPROVE:
            self.generator.approve_draft(draft_id)
            return True, "承認しました。投稿準備完了です。"
        
        elif action == ReviewAction.EDIT:
            if not edited_content:
                return False, "編集内容が指定されていません"
            
            # 文字数チェック
            if len(edited_content) > self.config.persona.max_tweet_length:
                return False, f"文字数オーバーです（{len(edited_content)}/{self.config.persona.max_tweet_length}）"
            
            # 内容を更新して承認
            draft.content = edited_content
            draft.approved = True
            self.generator._save_drafts()
            return True, "編集して承認しました。"
        
        elif action == ReviewAction.REJECT:
            self.generator.delete_draft(draft_id)
            return True, "却下しました。"
        
        elif action == ReviewAction.DEFER:
            return True, "保留しました。後で再検討します。"
        
        return False, "不明なアクションです"
    
    def can_post_now(self) -> Tuple[bool, str]:
        """現在投稿可能かチェック"""
        # 本日の投稿数をチェック
        today = datetime.now().date()
        today_posts = [
            r for r in self._records.values()
            if r.posted_at.date() == today
        ]
        
        if len(today_posts) >= self.config.forge.max_posts_per_day:
            return False, f"本日の投稿上限（{self.config.forge.max_posts_per_day}件）に達しています"
        
        # 最後の投稿からの経過時間をチェック
        if today_posts:
            last_post = max(today_posts, key=lambda x: x.posted_at)
            elapsed = datetime.now() - last_post.posted_at
            min_interval = timedelta(minutes=self.config.forge.min_interval_minutes)
            
            if elapsed < min_interval:
                remaining = min_interval - elapsed
                return False, f"次の投稿まであと{int(remaining.total_seconds() / 60)}分お待ちください"
        
        return True, "投稿可能です"
    
    def post_draft(self, draft_id: str) -> Tuple[bool, str]:
        """承認済みの下書きを投稿"""
        draft = self.generator.get_draft(draft_id)
        
        if not draft:
            return False, "下書きが見つかりません"
        
        if not draft.approved:
            return False, "この下書きは未承認です"
        
        if draft.posted:
            return False, "この下書きは既に投稿済みです"
        
        # 投稿可能かチェック
        can_post, message = self.can_post_now()
        if not can_post:
            return False, message
        
        # 重複チェック
        if self.config.forge.check_duplicate:
            for record in self._records.values():
                if record.content == draft.content:
                    return False, "同じ内容が既に投稿されています"
        
        # 投稿実行
        tweet_id = self.x_client.post_tweet(draft.content)
        
        if not tweet_id:
            return False, "投稿に失敗しました"
        
        # 記録の保存
        record = PostRecord(
            draft_id=draft_id,
            tweet_id=tweet_id,
            content=draft.content,
            keywords=draft.keywords,
            posted_at=datetime.now()
        )
        
        self._records[tweet_id] = record
        self._save_records()
        
        # 下書きを投稿済みにマーク
        self.generator.mark_as_posted(draft_id)
        
        logger.success(f"投稿完了: {tweet_id}")
        return True, f"投稿完了しました（ID: {tweet_id}）"
    
    def get_recent_posts(self, count: int = 10) -> List[PostRecord]:
        """最近の投稿を取得"""
        records = list(self._records.values())
        records.sort(key=lambda x: x.posted_at, reverse=True)
        return records[:count]
    
    def get_today_posts(self) -> List[PostRecord]:
        """本日の投稿を取得"""
        today = datetime.now().date()
        return [r for r in self._records.values() if r.posted_at.date() == today]
    
    def get_latest_keywords(self) -> List[str]:
        """最新の投稿からキーワードを取得（Echo層との連携用）"""
        recent = self.get_recent_posts(5)
        keywords = []
        for record in recent:
            keywords.extend(record.keywords)
        
        # 重複を除去しつつ順序を保持
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)
        
        return unique_keywords[:self.config.echo.max_keywords]
