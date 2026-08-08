# GCP + Cloud Run (GCS Volume Mount) + IAP ドキュメント配信システム

GitHub に Markdown を Push すると、Google Cloud Platform (GCP) 上の GCS に自動同期され、**Identity-Aware Proxy (IAP)** によるアクセス制限のもとで安全に配信されるドキュメント閲覧システムです。

---

## 🏛️ アーキテクチャ

詳細なシステムアーキテクチャについては [`ARCHITECTURE.md`](ARCHITECTURE.md) を参照してください。

```text
[User] -> [HTTPS Load Balancer] -> [IAP 認証 (Google Group 限定)]
                                          |
                                          v
                              [Cloud Run (Nginx)]
                                          | (GCS Volume Mount)
                                          v
                              [GCS Bucket (HTML/CSS/JS)]
                                          ^
                                          | (gcloud storage rsync)
[GitHub (docs-repo)] -> [GitHub Actions (WIF)]
```

---

## 📂 ディレクトリ構成

- [`docs-repo/`](docs-repo/): Markdown ドキュメントと GitHub Actions CI/CD ワークフロー (GCS への自動同期)
- [`infra-terraform/`](infra-terraform/): GCP インフラを一括構築する Terraform コード、Nginx 設定、および Terraform 用 GitHub Actions (PR で `plan` 表示 / `main` マージで `apply` 実行)

---

## ⚙️ 全体設定手順 (セットアップガイド)

以下のステップに従って、GCP インフラ構築からドキュメントの自動配信までを設定します。

---

### Step 1: GCP 前準備

1. **GCP CLI のログイン**
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

2. **必要な GCP API の有効化**
   ```bash
   gcloud services enable \
     compute.googleapis.com \
     run.googleapis.com \
     iam.googleapis.com \
     artifactregistry.googleapis.com \
     storage.googleapis.com \
     iap.googleapis.com \
     sts.googleapis.com \
     cloudresourcemanager.googleapis.com
   ```

3. **OAuth 2.0 クライアント ID の作成 (IAP 用 / 個人アカウント対応)**
   - GCP コンソール: [API とサービス] > [OAuth 同意画面] に移動。
   - User Type（ユーザーの種類）: 組織のない個人 GCP アカウントの場合は **外部 (External)** を選択して「作成」。
   - **公開ステータス**: **テスト (Testing)** のままにします（Verification審査不要）。
   - **テストユーザー**: 自分と友人の Gmail アカウント（例: `friend@gmail.com`, `your-account@gmail.com`）を追加登録します。
   - [API とサービス] > [認証情報] > [認証情報を作成] > [OAuth クライアント ID]
   - 種類: **ウェブ アプリケーション**
   - 承認済みのリダイレクト URI:
     `https://iap.googleapis.com/v1/oauth/clientIds/YOUR_CLIENT_ID:handleRedirect`
   - 発行された **クライアント ID** と **クライアント シークレット** を控えメモします。

---

### Step 2: Terraform によるインフラ構築 (`infra-terraform`)

1. ディレクトリ移動:
   ```bash
   cd infra-terraform
   ```

2. 変数設定ファイルの作成:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

3. `terraform.tfvars` を編集:
   ```hcl
   project_id           = "your-gcp-project-id"
   region               = "asia-northeast1"
   bucket_name          = "your-gcp-project-id-docs-bucket"              # GCSバケット名は世界で一意(ユニーク)な名前
   github_repositories  = ["your-github-username/docs-repo", "your-github-username/infra-terraform"]
   iap_client_id        = "your-client-id.apps.googleusercontent.com"
   iap_client_secret    = "your-client-secret"
   allowed_users        = ["friend@gmail.com", "your-account@gmail.com"]  # 閲覧許可するGmailアカウント
   domain_name          = "docs.your-domain.com"                          # お持ちのドメイン (サブドメイン)

   # ※初回 apply 時は container_image をコメントアウト(デフォルト nginx:1.27-alpine を使用)しておきます
   # container_image    = "asia-northeast1-docker.pkg.dev/your-gcp-project-id/docs-nginx-repo/docs-nginx:latest"
   ```

4. **GCP 認証ログイン (Application Default Credentials)**:
   ```bash
   gcloud auth application-default login
   ```

5. **初回インフラ構築 (ブートストラップ)**:
   ```bash
   terraform init
   terraform plan
   terraform apply
   ```

6. **実行出力のメモ**:
   適用後に表示される以下の output 値をメモします。
   - `wif_provider_name`
   - `wif_service_account_email`
   - `gcs_bucket_name`
   - `load_balancer_ip` (ロードバランサの外部 IP アドレス)

---

### Step 2.1: 外部 DNS サービスでの A レコード登録 (外部管理ドメイン)

GCP 以外のドメイン管理サービス（お名前.com, Cloudflare, AWS Route 53, Value Domain 等）の DNS 設定画面で、A レコードを追加します。

- **レコード種別**: `A`
- **ホスト名 / 名前**: `docs` (または指定したサブドメイン名)
- **値 / IPv4 アドレス**: Step 2 の `load_balancer_ip` の値 (例: `34.xxx.xxx.xxx`)

> 💡 **SSL証明書の自動発行**: DNS 設定完了後、GCP が自動的に Google-managed SSL 証明書 (`https://docs.your-domain.com`) を検証・発行します（発行完了まで 15〜30 分程度かかります）。

---

### Step 2.5: Terraform CI/CD の設定 (`infra-terraform`)

Terraform 変更時の `plan` コメント機能と `main` マージ時の自動 `apply` を有効化します。

1. `infra-terraform` ディレクトリのコードを GitHub リポジトリ（`infra-terraform` またはモノリポジトリ）に Push します。
2. GitHub リポジトリの **Settings** > **Secrets and variables** > **Actions** に以下の Secret を登録します：
   - **WIF 認証用**:
     - `GCP_WORKLOAD_IDENTITY_PROVIDER`: `wif_provider_name` の出力値
     - `GCP_SERVICE_ACCOUNT`: `wif_service_account_email` の出力値
   - **Terraform パラメータ用 (推奨方法 A)**:
     - `TFVARS_FILE`: ローカルの `terraform.tfvars` ファイルの内容全体をそのまま値として貼り付け登録します。
3. 開発ブランチで Terraform コード変更を含めた Pull Request (MR) を作成すると、自動的に `terraform plan` が実行され、実行計画が PR コメントに投稿されます。
4. PR を `main` ブランチに Merge すると、`terraform apply -auto-approve` が自動実行され、GCP リソースが更新されます。
   *(※ `.md` などのドキュメント変更時は `paths-ignore` 設定により自動的にワークフローがスキップされ、無駄な `apply` は実行されません)*

---

### Step 3: Nginx カスタムコンテナイメージのビルド & Push

初回 `terraform apply` で Artifact Registry (`docs-nginx-repo`) が構築されたため、カスタム Nginx イメージをビルド・Push し、Cloud Run に反映します。

```bash
# Artifact Registry への Docker 認証
gcloud auth configure-docker asia-northeast1-docker.pkg.dev

# コンテナイメージのビルド & Push
cd dockerfiles/nginx
docker build -t asia-northeast1-docker.pkg.dev/YOUR_PROJECT_ID/docs-nginx-repo/nginx:latest .
docker push asia-northeast1-docker.pkg.dev/YOUR_PROJECT_ID/docs-nginx-repo/nginx:latest
cd ../..
```

Push 完了後、`infra-terraform/terraform.tfvars` の最終行 `container_image` のコメントアウト `#` を解除し、再度 `terraform apply` を実行して Cloud Run へ適用します。

---

### Step 4: GitHub Actions (CD) の設定 (`docs-repo`)

1. ドキュメント用 GitHub リポジトリ（`docs-repo`）を GitHub に作成・Push します。
2. GitHub リポジトリの **Settings** > **Secrets and variables** > **Actions** に移動します。
3. 以下の **Repository secrets** を追加します:

| Secret 名 | 設定する値 (Step 2 の Output 値) |
| :--- | :--- |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | `wif_provider_name` の値 (例: `projects/123/locations/global/workloadIdentityPools/...`) |
| `GCP_SERVICE_ACCOUNT` | `wif_service_account_email` の値 (例: `github-actions-gcs-deployer@...`) |
| `GCS_BUCKET` | `gcs_bucket_name` の値 (例: `your-unique-docs-bucket-name`) |

---

### Step 5: ドキュメント更新と動作確認

1. `docs-repo/docs/index.md` などの Markdown ドキュメントを編集します。
2. 変更を `main` ブランチに Push します:
   ```bash
   git add .
   git commit -m "docs: update portal index"
   git push origin main
   ```
3. GitHub Actions ワークフローが起動し、自動で MkDocs がビルドされ GCS にデプロイされます。
4. ブラウザで HTTPS Load Balancer の IP アドレス（または設定したカスタムドメイン）にアクセスします。
5. **Google ログイン画面** にリダイレクトされ、指定した Google グループに所属するアカウントでのみサイトが閲覧できることを確認します。

---

## 🔍 トラブルシューティング

- **IAP 403 Forbidden になる場合**: `allowed_google_group` に登録された Google アカウントでログインしているか確認してください。IAP 設定が全体に反映されるまで数分待機が必要な場合があります。
- **GCS 同期エラー**: GitHub Actions のログで WIF 認証権限 (`roles/storage.objectAdmin`) や Secret の値が正しくセットされているか確認してください。

---

## 🔌 (任意) GCP ドキュメント・リソース参照用 MCP サーバーの設定

開発・保守時に GCP 公式ドキュメントの参照や `gcloud` リソース確認を AI と連携して行う場合、プロジェクト直下に `.agents/mcp_config.json` を作成して MCP サーバーを導入できます。

```json
{
  "mcpServers": {
    "gcloud": {
      "command": "npx",
      "args": [
        "-y",
        "@google-cloud/gcloud-mcp"
      ]
    },
    "fetch-docs": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-fetch"
      ]
    }
  }
}
```
