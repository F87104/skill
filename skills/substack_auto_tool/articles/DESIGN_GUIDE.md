# Brain / Substack 有料記事 — デザイン装飾ガイド

## 用意した素材

| ファイル | 用途 | 挿入位置 |
|---------|------|----------|
| `assets/brain_article_cover.png` | サムネイル・冒頭ヒーロー | タイトル直下 |
| `assets/brain_section_title_compare.png` | 売れやすいタイトル比較 | 導入部「2つを比べて」 |
| `assets/brain_section_4steps.png` | 4ステップ図解 | 第5章 |
| `assets/brain_section_roadmap.png` | 3日ロードマップ | 第12章 |
| `assets/brain_section_checklist.png` | 公開前チェック | 第13章 |

## Substack への貼り付け手順

1. Substackエディタで新規投稿を作成
2. **有料ライン**（Paywall）を「この記事でわかること」の**直前**に設定（無料部分でフック → 有料部分で本編）
3. 画像は `/` → Image からアップロード（上記PNG）
4. 本文は `brain_paid_article_styled.md` をコピペ
5. Substackの **Pull quote** で `╭─ ... ╰─` 風の吹き出し部分を引用ブロックに変換するとLINE風に近づく

## 推奨 Paywall 位置

```
無料（フリー）:
  - タイトル + カバー画像
  - 導入〜「買う理由があるテーマにすること」
  - タイトル比較画像
  - 【この記事でわかること】一覧
  - 【向いている人】
  - 【先に結論】

有料（Paid）:
  - 第1章〜付録（本編すべて）
```

## LINE風に見せるコツ（Substack上）

- **見出し**: `▶` や絵文字を先頭に（Markdownの `##`）
- **区切り**: `---` または Substack の Divider
- **強調ボックス**: Pull quote + 背景色（エディタの Quote ブロック）
- **リスト**: 番号より ✅ 📌 💡 などのアイコン行
- **比較**: 2列は画像（title_compare）で代替 — Substackは2列Markdown非対応
- **チェックリスト**: `- [ ]` または ✅ 付きリスト

## Canva で追加デザインする場合

- サイズ: 1200×630px（OGP）、1080×1080（Instagram告知用）
- フォント: Noto Sans JP / M PLUS Rounded（LINEに近い丸ゴシック）
- カラー: `#06C755`（LINEグリーン）+ `#F7F7F7`（背景）+ `#333333`（本文）

## 告知用コピー例

```
【有料記事】
売れているBrain・noteをリサーチして、
自分だけの初商品テーマを作る方法📚

✅ リサーチ15項目シート付き
✅ AIプロンプト5本
✅ 3日ロードマップ

▼ 続きはこちら
```
