# 社内ドキュメントポータルへようこそ

本サイトは、GitHub Actions による CI/CD パイプライン経由で自動ビルドされ、Google Cloud Platform (GCP) 上のセキュアなインフラ基盤上で配信されている社内専用ドキュメントサイトです。

---

## 🚀 主な特徴

- **高性能 & 高信頼性**: [MkDocs Material](https://squidfunk.github.io/mkdocs-material/) によるモダンなデザインと高速レスポンス。
- **ゼロトラストセキュリティ**: Google Cloud Identity-Aware Proxy (IAP) により、認証された社内メンバーのみアクセス可能。
- **フルオートメーション**: `main` ブランチへの Push を契機に、Workload Identity Federation 経由で GCS (Google Cloud Storage) へ静的コンテンツが自動同期されます。
- **サーバーレス運用**: Cloud Run の Direct GCS Volume Mount 機能を使用し、コンテナイメージを再作成・再デプロイすることなくリアルタイムにドキュメント更新を反映。

---

## 🛠 ドキュメント更新フロー

1. ローカル環境でドキュメントの編集・プレビューを行います。
   ```bash
   uv sync --frozen
   uv run mkdocs serve
   ```
2. 変更をコミットし、`main` ブランチへ Pull Request を作成・マージします。
3. GitHub Actions が自動で立ち上がり、ビルドおよび GCS 同期処理を実行します。

---

## 📚 目次

- [アーキテクチャ概要](architecture.md): インフラ構成図および各コンポーネントの詳細情報。
