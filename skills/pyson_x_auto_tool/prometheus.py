#!/usr/bin/env python3
"""
Project Prometheus v3.0 "Odyssey" - 統合メインスクリプト
========================================================
VIPリスト監視・自動いいね機能を搭載した投資家Fのアカウント成長支援システム

使用方法:
    # Oracle（ツイート案生成）
    python3 prometheus.py oracle              # 通常のツイート案生成
    python3 prometheus.py oracle --morning    # 朝の相場観ツイート
    python3 prometheus.py oracle --breaking   # 速報リアクション
    python3 prometheus.py oracle --edu        # 学びのスレッド
    python3 prometheus.py oracle --discuss    # 議論誘発型
    python3 prometheus.py oracle --position   # ポジション公開
    
    # Forge（レビュー・投稿）
    python3 prometheus.py forge               # 下書きレビュー + 投稿
    
    # Echo（戦略的いいね）
    python3 prometheus.py echo                # 戦略的いいね（1回）
    python3 prometheus.py echo -c             # 戦略的いいね（継続）
    
    # VIP（VIPリスト管理・いいね）★NEW★
    python3 prometheus.py vip lists           # Xのリスト一覧を表示
    python3 prometheus.py vip sync            # Xリストをシステムに同期
    python3 prometheus.py vip add             # 手動でVIPを追加
    python3 prometheus.py vip watch           # VIPタイムライン監視（1回）
    python3 prometheus.py vip watch -c        # VIPタイムライン監視（継続）
    python3 prometheus.py vip status          # VIP統計を表示
    
    # その他
    python3 prometheus.py full                # 全レイヤー統合実行
    python3 prometheus.py status              # システム状態確認
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from core import get_config, get_logger, get_x_client

logger = get_logger("prometheus")

BANNER = """
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   ██████╗ ██████╗  ██████╗ ███╗   ███╗███████╗████████╗  ║
    ║   ██╔══██╗██╔══██╗██╔═══██╗████╗ ████║██╔════╝╚══██╔══╝  ║
    ║   ██████╔╝██████╔╝██║   ██║██╔████╔██║█████╗     ██║     ║
    ║   ██╔═══╝ ██╔══██╗██║   ██║██║╚██╔╝██║██╔══╝     ██║     ║
    ║   ██║     ██║  ██║╚██████╔╝██║ ╚═╝ ██║███████╗   ██║     ║
    ║   ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝   ╚═╝     ║
    ║                                                           ║
    ║   Project Prometheus v3.0 "Odyssey"                       ║
    ║   VIPリスト監視・自動いいね機能搭載                       ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
"""


def run_oracle(template_type: str = "general"):
    """第1層: The Oracle - ニュース収集とツイート案生成"""
    from oracle import NewsCollector, ContentGenerator
    
    template_names = {
        "general": "通常",
        "morning": "朝の相場観",
        "breaking": "速報リアクション",
        "educational": "学びのスレッド",
        "discussion": "議論誘発型",
        "position": "ポジション公開"
    }
    
    logger.phase(f"=== The Oracle: 神託レイヤー ({template_names.get(template_type, template_type)}) ===")
    
    # ニュース収集
    collector = NewsCollector()
    top_news = collector.get_top_news(count=5)
    
    if not top_news:
        logger.warning("関連ニュースが見つかりませんでした")
        return []
    
    logger.info(f"トップニュース {len(top_news)}件を取得:")
    for i, news in enumerate(top_news, 1):
        logger.info(f"  {i}. [{news.relevance_score:.1f}] {news.title[:50]}...")
    
    # ツイート案生成
    generator = ContentGenerator()
    drafts = generator.generate_tweets(top_news, template_type=template_type)
    
    if drafts:
        print("\n" + "="*60)
        print(f"【生成されたプロ品質ツイート案】- {template_names.get(template_type, template_type)}")
        print("="*60)
        for i, draft in enumerate(drafts, 1):
            print(f"\n--- 案{i} ({draft.style}) ---")
            print(f"ID: {draft.id}")
            print(f"テンプレート: {draft.template_type}")
            print("-" * 40)
            print(draft.content)
            print("-" * 40)
            print(f"キーワード: {', '.join(draft.keywords)}")
            print(f"感情: {draft.sentiment}")
    
    return drafts


def run_forge():
    """第2層: The Forge - 下書きレビューと投稿"""
    from forge import PostManager, ReviewAction
    
    logger.phase("=== The Forge: 鍛造レイヤー ===")
    
    manager = PostManager()
    pending = manager.get_pending_drafts()
    
    if not pending:
        logger.info("レビュー待ちの下書きはありません")
        logger.info("先に 'python3 prometheus.py oracle' を実行してください")
        return
    
    print("\n" + "="*60)
    print(f"【レビュー待ち: {len(pending)}件】")
    print("="*60)
    
    for draft in pending:
        print(f"\n{'='*60}")
        print(f"ID: {draft.id}")
        print(f"スタイル: {draft.style} | テンプレート: {draft.template_type}")
        print(f"{'='*60}")
        print(draft.content)
        print(f"{'='*60}")
        print(f"キーワード: {', '.join(draft.keywords)}")
        print()
        
        while True:
            action = input("アクション [a:承認 / e:編集 / r:却下 / s:スキップ / q:終了]: ").strip().lower()
            
            if action == 'a':
                success, msg = manager.review_draft(draft.id, ReviewAction.APPROVE)
                print(f"→ {msg}")
                
                # 投稿するか確認
                post_now = input("今すぐ投稿しますか？ [y/n]: ").strip().lower()
                if post_now == 'y':
                    success, msg = manager.post_draft(draft.id)
                    print(f"→ {msg}")
                break
                
            elif action == 'e':
                print("現在の内容:")
                print(draft.content)
                print("\n新しい内容を入力（複数行の場合は最後に空行を入力）:")
                lines = []
                while True:
                    line = input()
                    if line == "":
                        break
                    lines.append(line)
                new_content = "\n".join(lines)
                if new_content:
                    success, msg = manager.review_draft(draft.id, ReviewAction.EDIT, new_content)
                    print(f"→ {msg}")
                break
                
            elif action == 'r':
                success, msg = manager.review_draft(draft.id, ReviewAction.REJECT)
                print(f"→ {msg}")
                break
                
            elif action == 's':
                print("→ スキップしました")
                break
            
            elif action == 'q':
                print("→ レビューを終了します")
                return
            
            else:
                print("無効な入力です。a/e/r/s/q のいずれかを入力してください")


def run_echo(continuous: bool = False):
    """第3層: The Echo - 戦略的いいね"""
    from echo import EngagementEngine
    from forge import PostManager
    
    logger.phase("=== The Echo: 反響レイヤー ===")
    
    engine = EngagementEngine()
    
    # Forge層から最新キーワードを取得
    manager = PostManager()
    keywords = manager.get_latest_keywords()
    
    if keywords:
        engine.set_keywords(keywords)
        logger.info(f"投稿連動キーワード: {keywords}")
    else:
        # デフォルトキーワード
        config = get_config()
        default_keywords = config.echo.default_keywords
        engine.set_keywords(default_keywords)
        logger.info(f"デフォルトキーワード: {default_keywords}")
    
    # 統計表示
    stats = engine.get_stats()
    print("\n" + "="*60)
    print("【現在の状態】")
    print("="*60)
    print(f"本日のいいね: {stats['today_likes']}件 (残り: {stats['today_remaining']}件)")
    print(f"15分間のいいね: {stats['15min_likes']}件 (残り: {stats['15min_remaining']}件)")
    print(f"アクティブキーワード: {', '.join(stats['active_keywords'])}")
    print()
    
    if continuous:
        logger.info("継続モードで実行します（Ctrl+C で停止）")
        
        import time
        cycle = 1
        
        try:
            while True:
                print(f"\n--- サイクル {cycle} ---")
                # Basicプラン制限: 15分あ4件まで
                results = engine.run_engagement_cycle(max_likes=4)
                
                if results["rate_limited"]:
                    wait_time = max(results.get("backoff_seconds", 900), 900)
                    logger.warning(f"レート制限に達しました。{wait_time//60}分待機します...")
                    time.sleep(wait_time)
                else:
                    # 次のサイクルまで待機（15分待って制限リセットを待つ）
                    logger.info("次のサイクルまで15分待機（API制限リセット待ち）...")
                    time.sleep(900)  # 15分待機
                
                cycle += 1
                
        except KeyboardInterrupt:
            logger.info("\n停止しました")
    else:
        results = engine.run_engagement_cycle(max_likes=10)
        
        print("\n" + "="*60)
        print("【実行結果】")
        print("="*60)
        print(f"取得ツイート: {results['tweets_fetched']}件")
        print(f"スコアリング対象: {results['tweets_scored']}件")
        print(f"いいね成功: {results['likes_success']}/{results['likes_attempted']}件")


# ===== VIP機能 =====

def run_vip_lists():
    """Xのリスト一覧を表示"""
    from vip import ListManager
    
    logger.phase("=== VIP: Xリスト一覧 ===")
    
    x_client = get_x_client()
    lists = x_client.get_owned_lists()
    
    if not lists:
        print("\nXにリストがありません。")
        print("Xアプリまたはウェブでリストを作成してください。")
        return
    
    print("\n" + "="*60)
    print("【Xのリスト一覧】")
    print("="*60)
    
    for i, lst in enumerate(lists, 1):
        print(f"\n{i}. {lst['name']}")
        print(f"   ID: {lst['id']}")
        print(f"   メンバー数: {lst['member_count']}名")
        if lst.get('description'):
            print(f"   説明: {lst['description'][:50]}...")
    
    print("\n" + "-"*60)
    print("これらのリストを同期するには:")
    print("  python3 prometheus.py vip sync")


def run_vip_sync():
    """Xリストをシステムに同期"""
    from vip import ListManager
    
    logger.phase("=== VIP: リスト同期 ===")
    
    x_client = get_x_client()
    lists = x_client.get_owned_lists()
    
    if not lists:
        print("\nXにリストがありません。")
        return
    
    print("\n" + "="*60)
    print("【同期するリストを選択】")
    print("="*60)
    
    for i, lst in enumerate(lists, 1):
        print(f"{i}. {lst['name']} ({lst['member_count']}名)")
    
    print("\n0. キャンセル")
    
    choice = input("\n番号を入力: ").strip()
    
    if choice == "0" or not choice:
        print("キャンセルしました")
        return
    
    try:
        idx = int(choice) - 1
        if idx < 0 or idx >= len(lists):
            print("無効な番号です")
            return
        
        selected_list = lists[idx]
        
        # 階層を選択
        print("\n【階層を選択】")
        print("1. Titans（巨神）- 世界的著名投資家")
        print("2. Influencers（影響者）- 国内有名トレーダー")
        print("3. Practitioners（実践者）- 中堅トレーダー")
        print("4. Media（媒体）- メディア・記者")
        
        tier_map = {
            "1": "titans",
            "2": "influencers",
            "3": "practitioners",
            "4": "media"
        }
        
        tier_choice = input("\n番号を入力: ").strip()
        tier = tier_map.get(tier_choice, "practitioners")
        
        # 同期実行
        manager = ListManager()
        result = manager.sync_list(selected_list["id"], tier)
        
        if result:
            print(f"\n✓ リスト '{result.name}' を同期しました")
            print(f"  階層: {result.tier}")
            print(f"  メンバー数: {result.member_count}名")
        else:
            print("\n同期に失敗しました")
            
    except ValueError:
        print("無効な入力です")


def run_vip_add():
    """手動でVIPを追加"""
    from vip import ListManager
    
    logger.phase("=== VIP: 手動追加 ===")
    
    print("\n" + "="*60)
    print("【VIPを手動で追加】")
    print("="*60)
    
    # リスト名
    list_name = input("リスト名を入力: ").strip()
    if not list_name:
        print("キャンセルしました")
        return
    
    # 階層を選択
    print("\n【階層を選択】")
    print("1. Titans（巨神）- 世界的著名投資家")
    print("2. Influencers（影響者）- 国内有名トレーダー")
    print("3. Practitioners（実践者）- 中堅トレーダー")
    print("4. Media（媒体）- メディア・記者")
    
    tier_map = {
        "1": "titans",
        "2": "influencers",
        "3": "practitioners",
        "4": "media"
    }
    
    tier_choice = input("\n番号を入力: ").strip()
    tier = tier_map.get(tier_choice, "practitioners")
    
    # ユーザー名を入力
    print("\n追加するユーザー名を入力（@は省略可、空行で終了）:")
    usernames = []
    while True:
        username = input("  @").strip()
        if not username:
            break
        usernames.append(username)
    
    if not usernames:
        print("キャンセルしました")
        return
    
    # 追加実行
    manager = ListManager()
    result = manager.add_manual_list(list_name, tier, usernames)
    
    if result:
        print(f"\n✓ リスト '{result.name}' を作成しました")
        print(f"  階層: {result.tier}")
        print(f"  メンバー数: {result.member_count}名")
    else:
        print("\n作成に失敗しました")


def run_vip_watch(continuous: bool = False, tier: str = None):
    """VIPタイムライン監視"""
    from vip import Watchtower
    
    logger.phase("=== VIP: Watchtower ===")
    
    watchtower = Watchtower()
    
    # 統計表示
    stats = watchtower.get_stats()
    
    print("\n" + "="*60)
    print("【VIP統計】")
    print("="*60)
    print(f"登録リスト数: {stats['total_lists']}件")
    print(f"VIPメンバー数: {stats['total_vip_members']}名")
    print(f"本日のVIPいいね: {stats['today_vip_likes']}件 (残り: {stats['today_remaining']}件)")
    
    if stats['by_tier']:
        print("\n【階層別】")
        for tier_name, tier_stats in stats['by_tier'].items():
            print(f"  {tier_name}: {tier_stats['members']}名")
    
    if stats['total_vip_members'] == 0:
        print("\n⚠ VIPメンバーが登録されていません")
        print("先に 'python3 prometheus.py vip sync' または 'vip add' を実行してください")
        return
    
    print()
    
    if continuous:
        watchtower.run_continuous(interval_minutes=30, tier=tier)
    else:
        results = watchtower.run_vip_engagement(max_likes=10, tier=tier)
        
        print("\n" + "="*60)
        print("【実行結果】")
        print("="*60)
        print(f"取得ツイート: {results['tweets_fetched']}件")
        print(f"いいね成功: {results['likes_success']}/{results['likes_attempted']}件")
        
        if results['engaged_users']:
            print("\n【エンゲージしたVIP】")
            for user in results['engaged_users']:
                print(f"  @{user['username']} ({user['tier']})")


def run_vip_status():
    """VIP統計を表示"""
    from vip import ListManager, Watchtower
    
    logger.phase("=== VIP: ステータス ===")
    
    manager = ListManager()
    watchtower = Watchtower()
    
    stats = watchtower.get_stats()
    
    print("\n" + "="*60)
    print("【VIPリスト統計】")
    print("="*60)
    print(f"登録リスト数: {stats['total_lists']}件")
    print(f"VIPメンバー総数: {stats['total_vip_members']}名")
    
    if stats['by_tier']:
        print("\n【階層別内訳】")
        tier_names = {
            "titans": "Titans（巨神）",
            "influencers": "Influencers（影響者）",
            "practitioners": "Practitioners（実践者）",
            "media": "Media（媒体）"
        }
        for tier, tier_stats in stats['by_tier'].items():
            print(f"  {tier_names.get(tier, tier)}: {tier_stats['members']}名")
    
    print("\n" + "="*60)
    print("【本日のエンゲージメント】")
    print("="*60)
    print(f"VIPいいね: {stats['today_vip_likes']}件 / 上限100件")
    print(f"残り: {stats['today_remaining']}件")
    
    # リスト詳細
    manager.show_lists()


def run_full():
    """全レイヤー統合実行"""
    logger.phase("=== Project Prometheus: フル実行 ===")
    
    # テンプレート選択
    print("\n" + "="*60)
    print("【テンプレート選択】")
    print("="*60)
    print("1. 通常（3パターン生成）")
    print("2. 朝の相場観")
    print("3. 速報リアクション")
    print("4. 学びのスレッド")
    print("5. 議論誘発型")
    print("6. ポジション公開")
    
    template_map = {
        "1": "general",
        "2": "morning",
        "3": "breaking",
        "4": "educational",
        "5": "discussion",
        "6": "position"
    }
    
    choice = input("\n選択 [1-6]: ").strip()
    template_type = template_map.get(choice, "general")
    
    # Step 1: Oracle
    print("\n" + "="*60)
    print("Step 1: ニュース収集とツイート案生成")
    print("="*60)
    drafts = run_oracle(template_type=template_type)
    
    if drafts:
        proceed = input("\nForge（レビュー・投稿）に進みますか？ [y/n]: ").strip().lower()
        if proceed == 'y':
            # Step 2: Forge
            print("\n" + "="*60)
            print("Step 2: レビューと投稿")
            print("="*60)
            run_forge()
    
    # Step 3: Echo or VIP
    print("\n" + "="*60)
    print("【エンゲージメント選択】")
    print("="*60)
    print("1. Echo（キーワードベース）")
    print("2. VIP Watch（VIPリストベース）")
    print("3. スキップ")
    
    engage_choice = input("\n選択 [1-3]: ").strip()
    
    if engage_choice == "1":
        print("\n" + "="*60)
        print("Step 3: 戦略的いいね（Echo）")
        print("="*60)
        run_echo(continuous=False)
    elif engage_choice == "2":
        print("\n" + "="*60)
        print("Step 3: VIPエンゲージメント")
        print("="*60)
        run_vip_watch(continuous=False)


def show_status():
    """システム状態を表示"""
    from oracle import ContentGenerator
    from forge import PostManager
    from echo import EngagementEngine
    from vip import ListManager, Watchtower
    
    logger.phase("=== System Status ===")
    
    config = get_config()
    
    print("\n" + "="*60)
    print("【ペルソナ設定】")
    print("="*60)
    print(f"名前: {config.persona.name}")
    print(f"専門: {', '.join(config.persona.expertise)}")
    print(f"トーン: {config.persona.tone}")
    print(f"ポジショニング: 冷静な分析者。普段は淡々と、ここぞという時に大胆に。")
    
    print("\n" + "="*60)
    print("【Oracle - 神託レイヤー】")
    print("="*60)
    generator = ContentGenerator()
    pending_drafts = generator.get_pending_drafts()
    print(f"未承認の下書き: {len(pending_drafts)}件")
    print(f"RSSフィード数: {len(config.oracle.rss_feeds)}件")
    print(f"LLMモデル: {config.oracle.llm_model}")
    
    print("\n" + "="*60)
    print("【Forge - 鍛造レイヤー】")
    print("="*60)
    manager = PostManager()
    today_posts = manager.get_today_posts()
    print(f"本日の投稿: {len(today_posts)}件 / 上限{config.forge.max_posts_per_day}件")
    
    print("\n" + "="*60)
    print("【Echo - 反響レイヤー】")
    print("="*60)
    engine = EngagementEngine()
    stats = engine.get_stats()
    print(f"本日のいいね: {stats['today_likes']}件 / 上限{config.echo.likes_per_day}件")
    print(f"15分間のいいね: {stats['15min_likes']}件 / 上限{config.echo.likes_per_15min}件")
    print(f"累計いいね: {stats['total_likes']}件")
    
    print("\n" + "="*60)
    print("【VIP - Watchtower】★NEW★")
    print("="*60)
    try:
        watchtower = Watchtower()
        vip_stats = watchtower.get_stats()
        print(f"VIPリスト数: {vip_stats['total_lists']}件")
        print(f"VIPメンバー数: {vip_stats['total_vip_members']}名")
        print(f"本日のVIPいいね: {vip_stats['today_vip_likes']}件 / 上限100件")
    except:
        print("VIPリストは未設定です")
        print("'python3 prometheus.py vip sync' で設定してください")
    
    print("\n" + "="*60)
    print("【プロ発信の6つの鉄則】")
    print("="*60)
    print("1. 数字で語る")
    print("2. 時間軸を明示")
    print("3. 根拠を示す")
    print("4. 間違いを認める")
    print("5. リスクリワードを示す")
    print("6. シナリオを複数持つ")


def main():
    parser = argparse.ArgumentParser(
        description="Project Prometheus v3.0 'Odyssey' - VIPリスト監視・自動いいね機能搭載",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
    # Oracle（ツイート案生成）
    python3 prometheus.py oracle              # 通常のツイート案生成
    python3 prometheus.py oracle --morning    # 朝の相場観ツイート
    
    # Forge（レビュー・投稿）
    python3 prometheus.py forge               # 下書きレビュー + 投稿
    
    # Echo（戦略的いいね）
    python3 prometheus.py echo -c             # 戦略的いいね（継続）
    
    # VIP（VIPリスト管理）★NEW★
    python3 prometheus.py vip lists           # Xのリスト一覧を表示
    python3 prometheus.py vip sync            # Xリストをシステムに同期
    python3 prometheus.py vip add             # 手動でVIPを追加
    python3 prometheus.py vip watch -c        # VIPタイムライン監視（継続）
    
    # その他
    python3 prometheus.py full                # 全レイヤー統合実行
    python3 prometheus.py status              # システム状態確認
        """
    )
    
    parser.add_argument(
        "command",
        choices=["oracle", "forge", "echo", "vip", "full", "status"],
        help="実行するコマンド"
    )
    
    parser.add_argument(
        "subcommand",
        nargs="?",
        default=None,
        help="VIPコマンドのサブコマンド (lists/sync/add/watch/status)"
    )
    
    parser.add_argument(
        "-c", "--continuous",
        action="store_true",
        help="継続モード（echo/vip watchで使用）"
    )
    
    parser.add_argument(
        "--tier",
        choices=["titans", "influencers", "practitioners", "media"],
        help="VIP階層を指定（vip watchで使用）"
    )
    
    # テンプレート選択オプション
    parser.add_argument("--morning", action="store_true", help="朝の相場観テンプレート")
    parser.add_argument("--breaking", action="store_true", help="速報リアクションテンプレート")
    parser.add_argument("--edu", action="store_true", help="学びのスレッドテンプレート")
    parser.add_argument("--discuss", action="store_true", help="議論誘発型テンプレート")
    parser.add_argument("--position", action="store_true", help="ポジション公開テンプレート")
    
    args = parser.parse_args()
    
    # バナー表示
    print(BANNER)
    
    try:
        if args.command == "oracle":
            # テンプレートタイプを決定
            if args.morning:
                template_type = "morning"
            elif args.breaking:
                template_type = "breaking"
            elif args.edu:
                template_type = "educational"
            elif args.discuss:
                template_type = "discussion"
            elif args.position:
                template_type = "position"
            else:
                template_type = "general"
            
            run_oracle(template_type=template_type)
            
        elif args.command == "forge":
            run_forge()
            
        elif args.command == "echo":
            run_echo(continuous=args.continuous)
            
        elif args.command == "vip":
            if args.subcommand == "lists":
                run_vip_lists()
            elif args.subcommand == "sync":
                run_vip_sync()
            elif args.subcommand == "add":
                run_vip_add()
            elif args.subcommand == "watch":
                run_vip_watch(continuous=args.continuous, tier=args.tier)
            elif args.subcommand == "status":
                run_vip_status()
            else:
                print("VIPサブコマンドを指定してください:")
                print("  lists  - Xのリスト一覧を表示")
                print("  sync   - Xリストをシステムに同期")
                print("  add    - 手動でVIPを追加")
                print("  watch  - VIPタイムライン監視")
                print("  status - VIP統計を表示")
            
        elif args.command == "full":
            run_full()
            
        elif args.command == "status":
            show_status()
            
    except KeyboardInterrupt:
        logger.info("\n中断されました")
        sys.exit(0)
    except Exception as e:
        logger.error(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
