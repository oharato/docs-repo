# GCP Workload Identity Federation (WIF) と IAP / Cloud Run の最小権限 & シンプル運用設計ガイド

## 1. 概要

GitHub Actions 等の外部 CI/CD パイプラインから OIDC (Workload Identity Federation) 認証経由で GCP インフラを Terraform 管理する際、セキュリティ上のベストプラクティスに基づき「過剰な広域権限（`roles/owner` や `roles/editor`）」を排除し、真に必要な最小限の IAM ロールのみを割り当てる設計およびシンプル運用ガイドです。

---

## 2. 最小 IAM ロール構成要件

GCP 上の Cloud Run, GCS, Artifact Registry, Global HTTP(S) Load Balancer (IAP 有効) を Terraform で更新・管理するために必要な最少 IAM ロール一覧は以下の 11 個に厳密に限定されます。

| ロール ID | ロール名称 | 割り当て目的 |
| :--- | :--- | :--- |
| `roles/iap.admin` | IAP 管理者 | IAP 認証の設定およびバックエンドサービスへの IAM ポリシー割り当て管理 |
| `roles/compute.networkAdmin` | Compute ネットワーク管理者 | Global Forwarding Rule や Target Proxy 等のネットワークリソース管理 |
| `roles/compute.loadBalancerAdmin` | Compute LB 管理者 | Load Balancer (URL Map, Backend Service, Serverless NEG) の構築 |
| `roles/compute.securityAdmin` | Compute セキュリティ管理者 | セキュリティポリシー・アクセス制御の調整 |
| `roles/run.admin` | Cloud Run 管理者 | Cloud Run サービスのプロビジョニングおよび設定更新 |
| `roles/storage.admin` | Storage 管理者 | GCS バケットおよびオブジェクトのプロビジョニング |
| `roles/artifactregistry.admin` | Artifact Registry 管理者 | Docker イメージリポジトリの設定管理 |
| `roles/resourcemanager.projectIamAdmin` | プロジェクト IAM 管理者 | リソースごとの IAM バインディングプロビジョニング |
| `roles/iam.serviceAccountAdmin` | サービスアカウント管理者 | サービスアカウントの作成・設定 |
| `roles/iam.serviceAccountUser` | サービスアカウントユーザー | サービスアカウントの他リソースへのアタッチ |
| `roles/iam.workloadIdentityPoolAdmin` | Workload Identity Pool 管理者 | OIDC WIF Pool / Provider の設定管理 |

> **[!NOTE]**
> `roles/iap.webServiceAdmin` などのリソース単位専用ロールはプロジェクトレベルの IAM Policy (`google_project_iam_member`) にバインドしようとすると `Error 400: Role is not supported for this resource` になるため、プロジェクトレベルでは `roles/iap.admin` を使用します。

---

## 3. オーバーエンジニアリングの排除とシンプル設計

### ① コンテナイメージ管理のシンプル化
静的ドキュメント (MkDocs) の配信において、独自の Nginx イメージビルドや Artifact Registry への毎回 Push は不要です。
Cloud Run では Docker Hub の公式イメージ **`nginx:1.27-alpine`** を利用し、コンテンツ本体は Cloud Run GCS volume mount 経由で直接参照します。静的ファイルは `docs-repo` 側の GitHub Actions が GCS (`gcloud storage rsync`) へ同期するだけで完結します。

### ② ワークフローの極限シンプル化
GitHub Actions (`.github/workflows/terraform.yml`) 内で手動の Docker ビルドや `force-unlock` などの不要な対症療法ステップを排除し、標準的な CI/CD パイプラインに統一します：

```yaml
steps:
  - name: Checkout Code
    uses: actions/checkout@v7

  - name: Authenticate to Google Cloud via WIF
    uses: google-github-actions/auth@v3
    with:
      workload_identity_provider: ${{ secrets.GCP_WORKLOAD_IDENTITY_PROVIDER }}
      service_account: ${{ secrets.GCP_SERVICE_ACCOUNT }}

  - name: Setup Terraform
    uses: hashicorp/setup-terraform@v4
    with:
      terraform_version: "1.9.5"

  - name: Terraform Init
    run: terraform init

  - name: Terraform Format & Validate
    run: |
      terraform fmt -check *.tf
      terraform validate -no-color

  - name: Terraform Apply
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    run: terraform apply -auto-approve -input=false
```

---

## 4. 秘匿情報・安全性のガイドライン

- **API キー・トークンの排除**: CI/CD や HCL 内に直接認証情報を記載せず、`<YOUR_GCP_PROJECT_ID>` や Secrets を使用すること。
- **再現性の担保**: アクションや依存関係のバージョンを明確に指定・管理すること。
