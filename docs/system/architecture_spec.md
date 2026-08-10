# 詳細システム設計仕様

## リソース

| 層 | 構成 | 制約 |
| --- | --- | --- |
| State | GCS `terraform/state/bootstrap` と `terraform/state/docs-hub` | Uniform bucket-level access を有効化 |
| コンテンツ | 非公開 GCS bucket | public access prevention、uniform IAM、バージョニング |
| 実行 | Cloud Run v2 | internal load balancer ingress、専用 runtime SA、GCS は read-only mount |
| 公開 | Global HTTPS LB + IAP | HTTP は HTTPS へ redirect、IAP SA だけが Cloud Run を invoke |
| イメージ | 公式 NGINX | SHA-256 digest を Terraform input で固定 |

Artifact Registry と独自コンテナビルドは使用しません。静的コンテンツの更新では Cloud Run を再デプロイせず、GCS 同期だけを行います。

## WIF 設計

`bootstrap/` は 3 つの WIF Provider と SA を作成します。

| ID | トリガー | 信頼条件 | 権限 |
| --- | --- | --- | --- |
| Terraform plan | `infra-terraform` PR | repository ID、`refs/pull/<number>/merge`、固定 workflow | 読取り専用、state prefix の object access |
| Terraform apply | `infra-terraform` main | repository ID、`refs/heads/main`、固定 workflow | GCS、Cloud Run、LB、IAP の管理 |
| docs publisher | `docs-repo` main | repository ID、`refs/heads/main`、固定 workflow | 対象 bucket の object 同期と bucket metadata 読取り |

WIF attribute condition は `repository_id`、`ref`、`workflow_ref` をすべて検証します。`projectIamAdmin`、`workloadIdentityPoolAdmin`、`serviceAccountAdmin` は通常 CI に付与しません。

## CI/CD

- Actions は完全な commit SHA に pin する。
- Terraform workflow は `.tf` ファイルだけを format 検査し、Secret から生成する `terraform.tfvars` を対象外にする。
- docs workflow は `uv.lock` を使い `uv sync --frozen` で依存を再現する。
- docs workflow は `gcloud storage rsync` を使用するため、docs SA には `roles/storage.objectAdmin` に加えて対象 bucket の `roles/storage.legacyBucketReader` が必要である。
