"""
VIP List Manager
================
X(Twitter)のリストとの同期、VIPメンバーの管理
"""

import json
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict
from enum import Enum

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import get_config, get_logger, get_x_client

logger = get_logger("vip.list_manager")


class VIPTier(Enum):
    """VIPの階層"""
    TITANS = "titans"           # 世界的著名投資家
    INFLUENCERS = "influencers" # 国内有名トレーダー
    PRACTITIONERS = "practitioners"  # 中堅トレーダー
    MEDIA = "media"             # メディア・記者


@dataclass
class VIPMember:
    """VIPメンバー"""
    user_id: str
    username: str
    display_name: str
    tier: str
    followers_count: int = 0
    added_at: str = ""
    last_engaged_at: str = ""
    engagement_count: int = 0
    notes: str = ""
    
    def __post_init__(self):
        if not self.added_at:
            self.added_at = datetime.now().isoformat()


@dataclass
class VIPList:
    """VIPリスト"""
    list_id: str
    name: str
    tier: str
    description: str = ""
    member_count: int = 0
    members: List[VIPMember] = field(default_factory=list)
    synced_at: str = ""
    
    def to_dict(self) -> dict:
        return {
            "list_id": self.list_id,
            "name": self.name,
            "tier": self.tier,
            "description": self.description,
            "member_count": self.member_count,
            "members": [asdict(m) for m in self.members],
            "synced_at": self.synced_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "VIPList":
        members = [VIPMember(**m) for m in data.get("members", [])]
        return cls(
            list_id=data["list_id"],
            name=data["name"],
            tier=data["tier"],
            description=data.get("description", ""),
            member_count=data.get("member_count", 0),
            members=members,
            synced_at=data.get("synced_at", "")
        )


class ListManager:
    """VIPリスト管理クラス"""
    
    def __init__(self):
        self.config = get_config()
        self.x_client = get_x_client()
        self.data_dir = Path(__file__).parent.parent / "data" / "vip"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.lists_file = self.data_dir / "vip_lists.json"
        self.lists: Dict[str, VIPList] = {}
        self._load_lists()
    
    def _load_lists(self):
        """保存されたリストを読み込む"""
        if self.lists_file.exists():
            try:
                with open(self.lists_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for list_data in data.get("lists", []):
                        vip_list = VIPList.from_dict(list_data)
                        self.lists[vip_list.list_id] = vip_list
                logger.info(f"VIPリスト {len(self.lists)}件を読み込みました")
            except Exception as e:
                logger.error(f"リスト読み込みエラー: {e}")
    
    def _save_lists(self):
        """リストを保存する"""
        try:
            data = {
                "updated_at": datetime.now().isoformat(),
                "lists": [vip_list.to_dict() for vip_list in self.lists.values()]
            }
            with open(self.lists_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info("VIPリストを保存しました")
        except Exception as e:
            logger.error(f"リスト保存エラー: {e}")
    
    def get_my_lists(self) -> List[dict]:
        """自分のXリストを取得"""
        try:
            # X APIでリスト一覧を取得
            lists = self.x_client.get_owned_lists()
            logger.info(f"Xから {len(lists)}件のリストを取得")
            return lists
        except Exception as e:
            logger.error(f"リスト取得エラー: {e}")
            return []
    
    def sync_list(self, list_id: str, tier: str) -> Optional[VIPList]:
        """Xのリストをシステムに同期"""
        try:
            # リスト情報を取得
            list_info = self.x_client.get_list(list_id)
            if not list_info:
                logger.error(f"リスト {list_id} が見つかりません")
                return None
            
            # リストメンバーを取得
            members_data = self.x_client.get_list_members(list_id)
            
            members = []
            for m in members_data:
                member = VIPMember(
                    user_id=m["id"],
                    username=m["username"],
                    display_name=m.get("name", m["username"]),
                    tier=tier,
                    followers_count=m.get("public_metrics", {}).get("followers_count", 0)
                )
                members.append(member)
            
            # VIPListオブジェクトを作成
            vip_list = VIPList(
                list_id=list_id,
                name=list_info.get("name", ""),
                tier=tier,
                description=list_info.get("description", ""),
                member_count=len(members),
                members=members,
                synced_at=datetime.now().isoformat()
            )
            
            self.lists[list_id] = vip_list
            self._save_lists()
            
            logger.info(f"リスト '{vip_list.name}' を同期しました（{len(members)}名）")
            return vip_list
            
        except Exception as e:
            logger.error(f"リスト同期エラー: {e}")
            return None
    
    def add_manual_list(self, name: str, tier: str, usernames: List[str]) -> Optional[VIPList]:
        """手動でVIPリストを作成（Xリストを使わない場合）"""
        try:
            members = []
            for username in usernames:
                # ユーザー情報を取得
                user_info = self.x_client.get_user_by_username(username)
                if user_info:
                    member = VIPMember(
                        user_id=user_info["id"],
                        username=user_info["username"],
                        display_name=user_info.get("name", username),
                        tier=tier,
                        followers_count=user_info.get("public_metrics", {}).get("followers_count", 0)
                    )
                    members.append(member)
                    logger.info(f"  追加: @{username}")
                else:
                    logger.warning(f"  スキップ: @{username}（見つかりません）")
            
            # 手動リストはIDを生成
            list_id = f"manual_{tier}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            vip_list = VIPList(
                list_id=list_id,
                name=name,
                tier=tier,
                description=f"手動作成のVIPリスト（{tier}）",
                member_count=len(members),
                members=members,
                synced_at=datetime.now().isoformat()
            )
            
            self.lists[list_id] = vip_list
            self._save_lists()
            
            logger.info(f"手動リスト '{name}' を作成しました（{len(members)}名）")
            return vip_list
            
        except Exception as e:
            logger.error(f"手動リスト作成エラー: {e}")
            return None
    
    def get_all_vip_members(self) -> List[VIPMember]:
        """全VIPメンバーを取得"""
        all_members = []
        for vip_list in self.lists.values():
            all_members.extend(vip_list.members)
        return all_members
    
    def get_members_by_tier(self, tier: str) -> List[VIPMember]:
        """特定階層のVIPメンバーを取得"""
        members = []
        for vip_list in self.lists.values():
            if vip_list.tier == tier:
                members.extend(vip_list.members)
        return members
    
    def update_engagement(self, user_id: str):
        """エンゲージメント記録を更新"""
        for vip_list in self.lists.values():
            for member in vip_list.members:
                if member.user_id == user_id:
                    member.last_engaged_at = datetime.now().isoformat()
                    member.engagement_count += 1
        self._save_lists()
    
    def get_lists_summary(self) -> dict:
        """リストのサマリーを取得"""
        summary = {
            "total_lists": len(self.lists),
            "total_members": 0,
            "by_tier": {}
        }
        
        for vip_list in self.lists.values():
            summary["total_members"] += vip_list.member_count
            tier = vip_list.tier
            if tier not in summary["by_tier"]:
                summary["by_tier"][tier] = {"lists": 0, "members": 0}
            summary["by_tier"][tier]["lists"] += 1
            summary["by_tier"][tier]["members"] += vip_list.member_count
        
        return summary
    
    def show_lists(self):
        """リスト一覧を表示"""
        if not self.lists:
            print("登録されたVIPリストはありません")
            return
        
        print("\n" + "="*60)
        print("【VIPリスト一覧】")
        print("="*60)
        
        for vip_list in self.lists.values():
            print(f"\n📋 {vip_list.name}")
            print(f"   ID: {vip_list.list_id}")
            print(f"   階層: {vip_list.tier}")
            print(f"   メンバー数: {vip_list.member_count}名")
            print(f"   最終同期: {vip_list.synced_at[:10] if vip_list.synced_at else '未同期'}")
