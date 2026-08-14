# 技術ドキュメントポータルへようこそ

本サイトは、GitHub Actions による CI/CD パイプライン経由で自動ビルドされ、GitHub Pages 上で完全無料かつ全自動で配信されている技術ドキュメントサイトです。

---

## 🚀 主な特徴

- **高性能 & 高信頼性**: [MkDocs Material](https://squidfunk.github.io/mkdocs-material/) によるモダンなデザインと高速レスポンス。
- **コスト完全 $0**: GitHub Pages によりインフラ維持基本料金ゼロで運用。
- **フルオートメーション**: `main` ブランチへの Push を契機に、GitHub Actions 経由でサイトが自動構築・デプロイされます。
- **生 HTML レポート対応**: Markdown だけでなく、独自の分析ダッシュボード等の独立生 HTML も自動目次インデックス生成付きで Pass-through 配信。

---

## 🛠 ドキュメント更新フロー

1. ローカル環境でドキュメントの編集・プレビューを行います。
   ```bash
   uv sync --frozen
   uv run mkdocs serve
   ```
2. 変更をコミットし、`main` ブランチへ Push または Pull Request をマージします。
3. GitHub Actions が自動で立ち上がり、ビルドおよび GitHub Pages デプロイ処理を実行します。

---

## 📚 目次

- [アーキテクチャ概要](architecture.md): インフラ構成図および各コンポーネントの詳細情報。
