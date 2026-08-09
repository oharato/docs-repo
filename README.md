# Docs Repository (Markdownコンテンツ・自動デプロイ)

本リポジトリは、社内ドキュメントのソースコード (Markdown) と MkDocs 設定、および GCS への自動同期用 GitHub Actions ワークフローを管理します。

---

## 📁 ディレクトリ構造

```text
docs-repo/
├── .github/
│   └── workflows/
│       └── deploy.yml          # WIF 認証による GCS 同期 CI/CD ワークフロー
├── docs/                        # Markdownドキュメント群
│   ├── index.md                # メインページ
│   ├── architecture.md         # システム構成解説
│   ├── extra.css               # カスタムスタイル
│   └── extra.js                # カスタムスクリプト
├── mkdocs.yml                  # MkDocs (Material theme) 設定
└── README.md                   # 本ドキュメント
```

---

## 💻 開発・ローカルプレビュー手順

### 1. 前提条件
Python 3.10 以上がインストールされていることを確認します。

### 2. パッケージのインストールとコミット前検証フックの有効化
```bash
# uv を使う場合 (超高速推奨)
uv pip install -r requirements.txt

# または pip を使う場合
pip install -r requirements.txt

# 別PC/初回クローン時にローカルコミット前検証フックを有効化
git config core.hooksPath .githooks
```

### 3. ローカルサーバーの起動
```bash
mkdocs serve
```
起動後、ブラウザで [http://127.0.0.1:8000](http://127.0.0.1:8000) にアクセスしてプレビューを確認します。ファイル更新時はリアルタイムで自動リロードされます。

---

## 🔐 GitHub Secrets 設定手順

本リポジトリの Actions を正常に動作させるため、GitHub リポジトリの **Settings > Secrets and variables > Actions** にて以下の Secrets を設定してください。

※ 各設定値は `infra-terraform` ディレクトリで `terraform apply` を実行した後の output から取得できます。

| Secret 名 | 説明 | 取得元 (Terraform Output) |
| :--- | :--- | :--- |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | WIF Provider のリソース名全称 | `wif_provider_name` |
| `GCP_SERVICE_ACCOUNT` | GitHub Actions デプロイ専用 GCP SA メールアドレス | `wif_service_account_email` |
| `GCS_BUCKET` | ドキュメント同期先の GCS バケット名 | `gcs_bucket_name` |

---

## 🚀 デプロイ仕様

- `main` ブランチへのコミット Push 時にワークフローが自動トリガーされます。
- GitHub サービス認証は **Workload Identity Federation (WIF)** を利用し、短時間有効な OIDC アクセストークンを自動取得します（サービスアカウントキー JSON の発行は不要）。
- `mkdocs build` により生成された `site/` ディレクトリ配下のファイル群を、`gcloud storage rsync --recursive --delete-unmatched-destination-objects` コマンドで GCS バケットへ差分同期します。
