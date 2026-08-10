# セットアップと運用手順

## 初回セットアップ

管理者だけが次を実行します。通常の GitHub Actions は `bootstrap/` を実行しません。

```bash
cd infra-terraform
gcloud auth application-default login
gcloud storage buckets update gs://try-gcp-504903-tfstate \
  --uniform-bucket-level-access
cp bootstrap/terraform.tfvars.example bootstrap/terraform.tfvars
# bootstrap/terraform.tfvars の project_id を設定する
terraform -chdir=bootstrap init
terraform -chdir=bootstrap apply
```

次に `bootstrap` の出力を GitHub Secrets に設定します。

| Repository | Secrets |
| --- | --- |
| `infra-terraform` | `GCP_PLAN_WORKLOAD_IDENTITY_PROVIDER`, `GCP_PLAN_SERVICE_ACCOUNT`, `GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_SERVICE_ACCOUNT`, `TFVARS_FILE`, `GCS_BUCKET` |
| `docs-repo` | `GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_SERVICE_ACCOUNT`, `GCS_BUCKET` |

`TFVARS_FILE` には `infra-terraform/terraform.tfvars` の内容を設定します。`container_image` は `nginx@sha256:<digest>` のように digest 固定します。

ルートスタックを適用します。

```bash
cd infra-terraform
terraform init
terraform apply
```

DNS では `domain_name` の A レコードを `load_balancer_ip` に向けます。Google 管理 SSL 証明書の発行後、HTTPS で IAP 経由のアクセスを確認します。

## 日常運用

| 変更 | 実行者 | 操作 |
| --- | --- | --- |
| ドキュメント更新 | docs 編集者 | `docs-repo` の `main` へ push |
| インフラ変更 | インフラ担当者 | PR で plan を確認して `main` へ merge |
| WIF / SA の変更 | GCP 管理者 | `infra-terraform/bootstrap` を明示的に apply |

ローカルの docs 確認は以下です。

```bash
cd docs-repo
uv sync --frozen
uv run mkdocs serve
```
