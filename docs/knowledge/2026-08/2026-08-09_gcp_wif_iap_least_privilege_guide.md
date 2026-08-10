# GCP WIF / IAP / Cloud Run の最小権限ガイド

> 更新日: 2026-08-10

## 結論

GitHub Actions の認証は用途別に分離し、通常の CI/CD にプロジェクト IAM や WIF 管理の権限を与えません。WIF / SA を作る `bootstrap/` は GCP 管理者だけが実行します。

## WIF の構成

| 用途 | GitHub 条件 | 権限 |
| --- | --- | --- |
| Terraform PR plan | `infra-terraform` PR の `terraform.yml` | 読取り専用と state prefix 限定 object access |
| Terraform apply | `infra-terraform` の `main` の `terraform.yml` | GCS、Cloud Run、LB、IAP の管理 |
| docs 公開 | `docs-repo` の `main` の `deploy.yml` | 対象 bucket の同期と metadata 読取り |

全 Provider は `assertion.repository_id`、`assertion.ref`、`assertion.workflow_ref` を検証します。リポジトリ名だけの判定は使用しません。

## State と bucket IAM

- Terraform state bucket は Uniform bucket-level access を有効にする。これにより IAM Condition で PR plan の state prefix を限定できる。
- 管理者の bootstrap state 操作も `terraform/state/bootstrap/` prefix の `roles/storage.objectUser` に限定する。
- docs 公開 SA には、対象 bucket にだけ `roles/storage.objectAdmin` と `roles/storage.legacyBucketReader` を付与する。後者は `gcloud storage rsync` に必要な bucket metadata 読取り用である。
- Cloud Run runtime SA には、対象 bucket の `roles/storage.objectViewer` だけを付与する。

## 配信構成

- GCS は public access prevention と uniform IAM を有効にする。
- Cloud Run は internal load balancer ingress に固定し、IAP SA だけに `roles/run.invoker` を付与する。
- Load Balancer は HTTP を HTTPS へ redirect する。
- 公式 NGINX は `nginx@sha256:...` の immutable digest で使う。Artifact Registry と独自イメージ build は不要である。

## 再現性

- Terraform 1.15.8、Google / Google Beta Provider 7.43.0 を使用する。
- GitHub Actions は完全な commit SHA に pin する。
- docs の Python 依存は `uv.lock` に固定し、CI は `uv sync --frozen` を実行する。

## 管理者の最短手順

```bash
cd infra-terraform
gcloud auth application-default login
gcloud storage buckets update gs://try-gcp-504903-tfstate \
  --uniform-bucket-level-access
terraform -chdir=bootstrap apply
terraform apply
```

`bootstrap` の output で GitHub Secrets を更新してから、通常 workflow を実行します。Secrets の対応表は `infra-terraform/README.md` を参照してください。
