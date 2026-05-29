# Project Prometheus v3.0 "Odyssey"

> **「冷静な分析者。普段は淡々と、ここぞという時に大胆に。」**

**VIPリスト監視・自動いいね機能を搭載した投資家Fのアカウント成長支援システム**

```
╔═══════════════════════════════════════════════════════════╗
║   Project Prometheus v3.0 "Odyssey"                       ║
║   VIPリスト監視・自動いいね機能搭載                       ║
╚═══════════════════════════════════════════════════════════╝
```

---

## 新機能（v3.0）★NEW★

### VIPリスト管理・自動いいね

X(Twitter)のリスト機能と連携し、**VIP（重要人物）のツイートに戦略的にいいね**を実行します。

| 機能 | コマンド | 説明 |
|:---|:---|:---|
| リスト一覧 | `vip lists` | Xのリスト一覧を表示 |
| リスト同期 | `vip sync` | Xリストをシステムに同期 |
| 手動追加 | `vip add` | ユーザー名を指定してVIPを追加 |
| 監視実行 | `vip watch` | VIPタイムラインを監視していいね |
| 統計表示 | `vip status` | VIP統計を表示 |

### 4層ポートフォリオ戦略

VIPを4つの階層に分類し、戦略的にエンゲージメントを行います。

| 階層 | 対象 | 目的 |
|:---|:---|:---|
| **Titans** | 世界的著名投資家（Ray Dalio, El-Erianなど） | 認知獲得、究極目標 |
| **Influencers** | 国内有名トレーダー（テスタ、バフェット太郎など） | リーチ拡大、相互送客 |
| **Practitioners** | 中堅トレーダー、アナリスト | 情報交換、議論 |
| **Media** | メディア・記者（Bloomberg, 日経など） | 引用・取材機会 |

---

## クイックスタート

```bash
# 1. prometheusフォルダに移動
cd ~/prometheus

# 2. 必要なライブラリをインストール
pip3 install -r requirements.txt

# 3. 朝の相場観ツイートを生成
python3 prometheus.py oracle --morning

# 4. レビューして投稿
python3 prometheus.py forge

# 5. VIPリストを同期（★NEW★）
python3 prometheus.py vip sync

# 6. VIP監視を開始（★NEW★）
python3 prometheus.py vip watch -c
```

---

## VIP機能の使い方（★NEW★）

### Step 1: Xでリストを作成

まず、X(Twitter)アプリまたはウェブで「リスト」を作成し、VIPにしたいユーザーを追加してください。

### Step 2: リストをシステムに同期

```bash
python3 prometheus.py vip sync
```

1. 同期するリストを選択
2. 階層（Titans/Influencers/Practitioners/Media）を選択
3. 自動的にメンバー情報を取得・保存

### Step 3: VIP監視を開始

```bash
# 継続実行（30分間隔）
python3 prometheus.py vip watch -c

# 特定の階層のみ監視
python3 prometheus.py vip watch -c --tier influencers
```

### 手動でVIPを追加（リストなしでもOK）

```bash
python3 prometheus.py vip add
```

ユーザー名を直接入力してVIPリストを作成できます。

---

## 全コマンド一覧

### Oracle（神託レイヤー）- ツイート案生成

```bash
python3 prometheus.py oracle              # 通常（3パターン）
python3 prometheus.py oracle --morning    # 朝の相場観
python3 prometheus.py oracle --breaking   # 速報リアクション
python3 prometheus.py oracle --edu        # 学びのスレッド
python3 prometheus.py oracle --discuss    # 議論誘発型
python3 prometheus.py oracle --position   # ポジション公開
```

### Forge（鍛造レイヤー）- レビュー・投稿

```bash
python3 prometheus.py forge
```

### Echo（反響レイヤー）- キーワードベースいいね

```bash
python3 prometheus.py echo                # 1回実行
python3 prometheus.py echo -c             # 継続実行
```

### VIP（Watchtower）- VIPリスト管理★NEW★

```bash
python3 prometheus.py vip lists           # Xのリスト一覧
python3 prometheus.py vip sync            # リスト同期
python3 prometheus.py vip add             # 手動追加
python3 prometheus.py vip watch           # 監視（1回）
python3 prometheus.py vip watch -c        # 監視（継続）
python3 prometheus.py vip watch -c --tier titans  # 階層指定
python3 prometheus.py vip status          # 統計表示
```

### その他

```bash
python3 prometheus.py full                # 全レイヤー統合実行
python3 prometheus.py status              # システム状態確認
```

---

## 推奨運用フロー

### 毎日のルーティン

```
【朝 7:00-8:00】
1. python3 prometheus.py oracle --morning  # 朝の相場観を生成
2. python3 prometheus.py forge             # レビュー・投稿

【日中】
3. python3 prometheus.py vip watch -c      # VIP監視を開始（バックグラウンド）

【夜 21:00-22:00】
4. python3 prometheus.py oracle            # 通常ツイート生成
5. python3 prometheus.py forge             # レビュー・投稿
```

### 週末のメンテナンス

```bash
# VIPリストの更新・追加
python3 prometheus.py vip sync

# 統計確認
python3 prometheus.py status
```

---

## 安全装置

| 項目 | Echo | VIP Watch |
|:---|:---|:---|
| 1日の上限 | 500件 | 100件 |
| 15分間の上限 | 45件 | - |
| 同一ユーザー間隔 | - | 12時間以上 |

---

## プロ発信の6つの鉄則

1. **数字で語る** - 「上がりそう」→「148.50超えで149.50目標」
2. **時間軸を明示** - 「短期」「今週中」「年末まで」
3. **根拠を示す** - なぜそう思うのかを必ず添える
4. **間違いを認める** - 外れたらすぐ認める。これが信頼になる
5. **リスクリワードを示す** - 「リスク50pips、リワード150pips」
6. **シナリオを複数持つ** - メインとサブの両方を提示

---

## 4層アーキテクチャ

| レイヤー | 名称 | 機能 |
|:---|:---|:---|
| **第1層** | **The Oracle（神託）** | プロ品質のツイート案を生成 |
| **第2層** | **The Forge（鍛造）** | AI生成案をレビューし投稿 |
| **第3層** | **The Echo（反響）** | キーワードベースの戦略的いいね |
| **第4層** | **The Watchtower（監視塔）**★NEW★ | VIPリスト監視・自動いいね |

---

## ファイル構成

```
prometheus/
├── prometheus.py          # メインスクリプト
├── requirements.txt       # 依存ライブラリ
├── README.md             # このファイル
├── config/               # 設定ファイル
├── core/                 # コアモジュール
├── oracle/               # 神託レイヤー
├── forge/                # 鍛造レイヤー
├── echo/                 # 反響レイヤー
├── vip/                  # VIPモジュール★NEW★
│   ├── list_manager.py   # リスト管理
│   └── watchtower.py     # 監視エンジン
└── data/                 # データ保存
    └── vip/              # VIPデータ★NEW★
```

---

## トラブルシューティング

### 「いいねレート制限」が出続ける

X APIの一時的な制限です。1-2時間待ってから再実行してください。

### 「No module named 'xxx'」エラー

```bash
pip3 install -r requirements.txt
```

### VIPリストが空

```bash
# まずXでリストを作成し、メンバーを追加してから
python3 prometheus.py vip sync
```

---

## バージョン履歴

- **v3.0 "Odyssey"** - VIPリスト監視・自動いいね機能を追加
- **v2.0 "Pro Investor Edition"** - プロ金融投資家会議の結論を反映
- **v1.0** - 初期リリース

---

*Project Prometheus v3.0 "Odyssey" - 投資家Fの成長を支援するAIシステム*

*「このリストは、君のSNS上の『取締役会』だ。彼らのタイムラインを毎日見ることで、君自身の視座が引き上げられる。」 - 高橋 誠一（元ゴールドマン・サックス MD）*
