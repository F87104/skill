# AIエージェント スキルリポジトリ

このリポジトリは、AIエージェントが特定のタスクを遂行するための「スキル」を管理する場所です。各スキルは、特定のペルソナ、文体、知識、またはタスク実行手順を定義しており、AIエージェントがより高品質で専門的なアウトプットを生成するために利用されます。

## 📚 スキル一覧（インデックス）

現在、以下のスキルが登録されています。各リンクから詳細な指示書（`SKILL.md`）を確認できます。

| スキル名 | 概要 | 指示書リンク | 関連スクリプト |
| :--- | :--- | :--- | :--- |
| **投資家F (investor_f)** | 投資家F氏の独特な感性、鋭い洞察、SNSリズムを再現し、X投稿を生成するスキル。 | [SKILL.md](./skills/investor_f/SKILL.md) | [trend_oracle_v2.8.0.py](./skills/investor_f/trend_oracle_v2.8.0_pro_news_triple_choice.py) |
| **投稿用Pythonエージェント (py_post_agent)** | ニュースの自動取得、事実要約、複数投稿案の生成プロセスを管理するエージェントスキル。 | [SKILL.md](./skills/py_post_agent/SKILL.md) | [trend_oracle_v2.8.0.py](./skills/py_post_agent/trend_oracle_v2.8.0_pro_news_triple_choice.py) |
| **Substack自動ツール (substack_auto_tool)** | 人間らしい動作で凍結を防止する、Substackの自動いいね＆フォローツール。 | [SKILL.md](./skills/substack_auto_tool/SKILL.md) | [substack-auto-like-safe.zip](./skills/substack_auto_tool/substack-auto-like-safe.zip) |

## 📂 ファイル構成ガイド

リポジトリ内のディレクトリとファイルの役割は以下の通りです。

```
github_skills/
├── README.md             # このファイル（リポジトリ全体のインデックスとガイド）
├── skills/               # 各スキルを格納するディレクトリ
│   ├── investor_f/       # 投資家F再現スキル
│   │   ├── SKILL.md      # F氏の文体・語彙・SNSリズムの定義
│   │   └── trend_oracle_v2.8.0_pro_news_triple_choice.py # 投稿生成スクリプト
│   ├── py_post_agent/    # 投稿用Pythonエージェントスキル
│   │   ├── SKILL.md      # エージェントの動作プロセス・運用マニュアル
│   │   └── trend_oracle_v2.8.0_pro_news_triple_choice.py # 投稿生成スクリプト
│   └── substack_auto_tool/ # Substack自動いいね＆フォローツール
│       ├── SKILL.md      # ツールの安全機能と使い方の定義
│       └── substack-auto-like-safe.zip # ソースコード一式
└── templates/            # 新しいスキルを作成するためのテンプレート
    └── SKILL_TEMPLATE.md # 新規スキル作成用のテンプレートファイル
```

## 🚀 クイックスタート

1.  **投資家Fの投稿を作りたい場合**:
    *   `skills/investor_f/SKILL.md` をAIエージェントに読み込ませます。
    *   `skills/investor_f/trend_oracle_v2.8.0_pro_news_triple_choice.py` を実行して投稿案を生成します。
2.  **新しいスキルを追加したい場合**:
    *   `templates/SKILL_TEMPLATE.md` をコピーして、新しいスキルディレクトリ内に `SKILL.md` を作成してください。

## ✨ 新しいスキルの追加手順

1.  `skills/` 内に新ディレクトリ作成: `mkdir -p skills/[skill_name]`
2.  テンプレートをコピー: `cp templates/SKILL_TEMPLATE.md skills/[skill_name]/SKILL.md`
3.  `SKILL.md` を編集し、ペルソナやルールを定義。
4.  本 `README.md` の「スキル一覧」に新しいスキルを追記。

---
**運用上の注意**:
各スキルの `SKILL.md` は、AIエージェントがその役割を完璧に演じるための「魂」です。新しい知見やルールが見つかった際は、随時アップデートしてください。
