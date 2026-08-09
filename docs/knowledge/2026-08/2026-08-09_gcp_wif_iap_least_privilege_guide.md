# GCP Workload Identity Federation (WIF) と IAP / Cloud Run の最小権限 (Least Privilege) 設定ガイド

## 1. 概要

GitHub Actions 等の外部 CI/CD パイプラインから OIDC (Workload Identity Federation) 認証経由で GCP インフラを Terraform 管理する際、セキュリティ上のベストプラクティスに基づき「過剰な広域権限（`roles/owner` や `roles/editor`）」を排除し、真に必要な最小限の IAM ロールのみを割り当てる設計ガイドです。

---

## 2. 最小 IAM ロール構成要件

GCP 上の Cloud Run, GCS, Artifact Registry, Global HTTP(S) Load Balancer (IAP 有効) を Terraform で更新・管理するために必要な最少 IAM ロール一覧は以下の 9 つに限定されます。

| ロール ID | ロール名称 | 割り当て目的 |
| :--- | :--- | :--- |
| `roles/iap.admin` | IAP 管理者 | IAP 認証の設定 |
| `roles/iap.webServiceAdmin` | IAP Web サービス管理者 | IAP バックエンドサービス (`iap_web/compute/services/`) の IAM ポリシー設定 |
| `roles/compute.admin` | Compute Engine 管理者 | Load Balancer (URL Map, Forwarding Rule, Backend Service) の構築 |
| `roles/compute.securityAdmin` | Compute セキュリティ管理者 | セキュリティポリシー・アクセス制御の調整 |
| `roles/run.admin` | Cloud Run 管理者 | Cloud Run サービスのプロビジョニングおよび設定更新 |
| `roles/storage.admin` | Storage 管理者 | GCS バケットおよびオブジェクトのプロビジョニング |
| `roles/artifactregistry.admin` | Artifact Registry 管理者 | Docker イメージリポジトリの設定管理 |
| `roles/resourcemanager.projectIamAdmin` | プロジェクト IAM 管理者 | リソースごとの IAM バインディングプロビジョニング |
| `roles/iam.serviceAccountAdmin` | サービスアカウント管理者 | サービスアカウントの作成・設定 |
| `roles/iam.serviceAccountUser` | サービスアカウントユーザー | サービスアカウントの他リソースへのアタッチ |
| `roles/iam.workloadIdentityPoolAdmin` | Workload Identity Pool 管理者 | OIDC WIF Pool / Provider の設定管理 |

> **[!NOTE]**
> `roles/editor` や `roles/compute.securityAdmin` 等の重複・過剰権限はセキュリティ上のリスクとなるため、全排除されています。

---

## 3. Terraform におけるリフレッシュ順序制御 (デッドロックの回避)

GCP Provider で `google_iap_web_backend_service_iam_member` などの IAP 関連 IAM ポリシーリソースを操作する場合、GCP 側の IAM バインド権限 (`module.wif`) が Terraform 実行開始時にプロビジョニング未完了だと `403 Forbidden` エラーが発生します。

### 解決策: モジュール間明示的依存関係 (`depends_on`)
`main.tf` 内で IAP モジュールに `depends_on = [module.wif]` を明示指定することにより、GCP IAM ロールが 100% 適用完了した後に IAP リソースが評価・設定されるよう制御します。

```hcl
module "lb_iap" {
  source                 = "./modules/lb_iap"
  project_id             = var.project_id
  region                 = var.region
  name_prefix            = "docs-hub"
  cloud_run_service_name = module.cloud_run.service_name
  iap_client_id          = var.iap_client_id
  iap_client_secret      = var.iap_client_secret
  allowed_users          = var.allowed_users
  domain_name            = var.domain_name

  depends_on = [
    module.wif
  ]
}
```

---

## 4. 秘匿情報・安全性のガイドライン

- **API キー・トークンの排除**: CI/CD や HCL 内に直接認証情報を書かず、`secrets.GCP_WORKLOAD_IDENTITY_PROVIDER` 等の OIDC または GitHub Secrets を経由すること。
- **ロックファイルとキャッシュ**: `uv.lock` または `requirements.txt` を用いて CI のビルド再帰性を保証すること。
