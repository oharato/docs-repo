# GCP WIF / IAP / Cloud Run の最小権限 & アーキテクチャガイド

> 更新日: 2026-08-12

## 1. 概要と基本構成

本システムは、Google Cloud Platform (GCP) 上で非公開の社内ドキュメント基盤（MkDocs Material + 生 HTML レポート）を安全かつサーバーレスに配信するためのインフラ・配信パイプラインです。

```mermaid
flowchart LR
  Docs[docs-repo main] --> DocsWF[Docs workflow]
  Infra[infra-terraform main] --> ApplyWF[Terraform apply workflow]
  PR[infra-terraform PR] --> PlanWF[Terraform plan workflow]

  DocsWF --> DocsWIF[docs publisher WIF / SA]
  ApplyWF --> ApplyWIF[Terraform apply WIF / SA]
  PlanWF --> PlanWIF[Terraform plan WIF / SA]

  DocsWIF --> GCS[Private GCS bucket]
  ApplyWIF --> GCP[Terraform-managed GCP resources]
  PlanWIF --> State[Terraform state prefix]
  GCS --> Run[Cloud Run v2: GCS Direct Volume Mount]
  Run --> LB[External HTTPS Load Balancer]
  LB --> IAP[Identity-Aware Proxy]
  IAP --> User[Authorized User]
```

---

## 2. 最小権限と WIF (Workload Identity Federation) 設計

GitHub Actions から GCP への認証には永続キー（SA キー JSON）を一切使用せず、短時間有効な OIDC トークンに基づく Workload Identity Federation を採用しています。用途に応じて Identity/SA を 3 つに完全分離し、最小権限原則（Least Privilege）を徹底しています。

| サービス | WIF Identity / SA | 信頼条件 (Claim Validation) | 付与権限・用途 |
| --- | --- | --- | --- |
| **Terraform Plan** | `github-terraform-plan` | `repository_id=1327451305`<br>`ref=refs/pull/*/merge`<br>`workflow_ref` 固定 | 読取り専用ロール + State バケットの `terraform/state/docs-hub/` Prefix 限定 objectUser |
| **Terraform Apply** | `github-terraform-deployer` | `repository_id=1327451305`<br>`ref=refs/heads/main`<br>`workflow_ref` 固定 | GCS、Cloud Run、LB、IAP のリソース管理ロール |
| **Docs Publisher** | `github-docs-publisher` | `repository_id=1327472883`<br>`ref=refs/heads/main`<br>`workflow_ref` 固定 | 対象ドキュメント GCS バケットの `roles/storage.objectAdmin` & `roles/storage.legacyBucketReader` |

> [!IMPORTANT]
> - すべての WIF Provider で `assertion.repository_id`、`assertion.ref`、`assertion.workflow_ref` を厳格に検証しています。
> - `projectIamAdmin` や `workloadIdentityPoolAdmin` などの広範な特権は CI サービスアカウントに付与しません。

---

## 3. ストレージ & セキュリティ設計

### GCS バケットセキュリティ
- **ドキュメント配信バケット**: Uniform bucket-level access を強制適用し、`public_access_prevention = "enforced"` にて公開を抑止。オブジェクトのバージョニングを有効化し 30 日前の古いバージョンを自動削除。
- **State バケット**: Uniform bucket-level access を有効化し、IAM Condition による Prefix スケーピング（`terraform/state/docs-hub/`）を可能にしています。

### Cloud Run & 配信コンテナ
- **Direct GCS Volume Mount**: Cloud Run v2 のボリューム機能で GCS バケットを `/usr/share/nginx/html` へ `read_only` マウント。ドキュメント更新時に Cloud Run の再デプロイが不要。
- **公式 NGINX Digest 固定**: コンテナイメージは可変タグ（`latest` 等）を使わず、`nginx@sha256:...` の immutable digest で固定。
- **ネットワーク境界**: Cloud Run の Ingress を `INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER` に限定。IAP システム SA のみに `roles/run.invoker` を付与し、外部からの直アクセスを完全遮断。

---

## 4. ドキュメント配信パイプライン & 生 HTML 対応

1. **MkDocs & 生 HTML 配信**:
   - `docs/` 配下の Markdown は MkDocs Material で HTML 化。
   - `docs/html/` 配下の生 HTML（独立した分析レポートやダッシュボード等）は Pass-through 配信。
2. **目次インデックス自動生成**:
   - `python scripts/generate_html_index.py` により `docs/html/` 配下の HTML から `<title>` や `<h1>` を抽出し、`mkdocs.yml` の左ナビゲーションツリーへ動的挿入。
3. **再現性 & 依存管理**:
   - Python 依存関係は `uv.lock` で完全固定し、CI/CD 内では `uv sync --frozen` を実行。

---

## 5. 動作検証結果と運用手順

### 開発・検証ステータス (2026-08-12 時点)
- **Terraform 構文・設定検証**: `infra-terraform`（ルートおよび `bootstrap/`）にて `terraform validate` 正常終了（Terraform `1.15.8` / Google Provider `7.43.0`）。
- **MkDocs 構築検証**: `docs-repo` にて `uv run mkdocs build --strict` 正常終了。

### GCP 管理者向け最短セットアップ手順
```bash
# 1. State バケットの Uniform Bucket-level Access 有効化
gcloud storage buckets update gs://<YOUR_STATE_BUCKET> \
  --uniform-bucket-level-access

# 2. Bootstrap スタックの適用 (WIF / SA 作成)
cd infra-terraform/bootstrap
terraform init
terraform apply

# 3. ルートスタックの適用 (インフラ作成)
cd ..
terraform init
terraform apply
```

---

## 6. Cloud Load Balancing 課金メカニズムとコスト削減・$0/月化手法 (2026-08-14 追記)

### 課金発生の原因
Cloud Load Balancing (External Application Load Balancer) は、リクエストやトラフィックが存在しない場合でも **Forwarding Rule (転送ルール) が存在するだけで固定維持費が発生** します（最初の 5 転送ルールまで約 $0.025/時間 ≒ 日額約 $0.60 / 月額約 $18〜$25）。

### カスタムドメイン廃止の影響
カスタムドメイン設定（`domain_name`）を解除するだけでは、HTTP リダイレクト用 Forwarding Rule やグローバル IP、バックエンドサービスが維持されるため、日額の固定課金は止まりません。

### コスト削減・廃止の選択肢比較

| アプローチ | 費用 | 構成変更 | 認証・アクセス制御 |
| --- | --- | --- | --- |
| **A. Cloud Run 直アクセス + NGINX Basic 認証** | **完全 $0/月** (従量・無料枠) | GCLB / IAP を完全廃止。<br>Cloud Run の Ingress を `allUsers` 許可。 | NGINX の `default.conf` に `auth_basic` を設定。 |
| **B. Cloud Run 直アクセス + Cloudflare Access** | **完全 $0/月** (Free Plan) | GCLB / IAP を完全廃止。<br>Cloudflare Access 経由で配信。 | Google / GitHub などの SSO 認証を Cloudflare 上で設定。 |
| **C. オンデマンド運用 (`terraform destroy`)** | 稼働時間のみ日割り | 不要時は `terraform destroy` でインフラ削除。 | 現行の IAP + GCLB 構成をそのまま維持。 |

---

## 7. GCP リソース完全クリーンアップ手順 (2026-08-14 追記)

学習・検証完了後にすべての課金を確実に停止するためのリソース削除手順です。

### 方法 1: GCP プロジェクト全体を削除（推奨・確実）
プロジェクト（`try-gcp-504903`）自体が不要になった場合は、プロジェクトをシャットダウンすることで、すべてのリソース・GCSバケット・ネットワーク・WIFが即座に削除され、将来の誤課金リスクを完全排除できます。

```bash
gcloud projects delete try-gcp-504903
```

### 方法 2: Terraform で特定リソースのみ順次削除
GCP プロジェクト自体を残し、インフラリソースのみを削除する場合：

```bash
# 1. State バケットへの一時権限付与（IAM Condition 制限回避）
gcloud storage buckets add-iam-policy-binding gs://try-gcp-504903-tfstate \
  --member="user:<YOUR_EMAIL>" \
  --role="roles/storage.objectAdmin"

# 2. ルートスタックの削除 (Cloud Run, LB, GCS, IAM)
cd infra-terraform
terraform destroy

# 3. Bootstrap スタックの削除 (WIF Pools, Service Accounts)
cd bootstrap
terraform destroy

# 4. State バケットの削除
gcloud storage buckets delete gs://try-gcp-504903-tfstate
```

