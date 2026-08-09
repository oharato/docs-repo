# GCP WIF / IAP / Cloud Run: 最小権限・運用設計レビュー

> 調査日: 2026-08-10
> 対象: `infra-terraform/` および `docs-repo/`

## 概要

この構成は、IAP、Cloud Run の内部 LB ingress、GCS の Uniform bucket-level access と Public Access Prevention を有効にしており、基礎的な防御はできています。一方で、ドキュメント配信とインフラ管理で同一の WIF サービスアカウントを共有し、プロジェクト全体の IAM 管理権限を与えているため、最小権限ではありません。

## 最重要: WIF サービスアカウントを分離する

`modules/wif/main.tf` は、許可リポジトリの OIDC トークンをリポジトリ名だけで信頼し、その主体に `roles/resourcemanager.projectIamAdmin` を含む 11 個のプロジェクトロールを付与しています。

`projectIamAdmin` を持つ主体はプロジェクト IAM を変更できるため、侵害された許可リポジトリやそのワークフローは永続的な管理権限へ昇格できます。特に `docs-repo` は静的ファイル同期だけを行うため、インフラ管理用の権限を取得できてはいけません。

以下の 3 つのサービスアカウントに分けます。

| 用途 | 信頼するリポジトリ・条件 | 必要な権限の範囲 |
| --- | --- | --- |
| ドキュメント公開 | `docs-repo` の protected `main` の公開ワークフローのみ | 対象バケットのオブジェクト更新権限のみ |
| アプリイメージ公開 | イメージを作成するリポジトリの protected workflow のみ | 対象 Artifact Registry リポジトリへの書込みのみ |
| Terraform 基盤変更 | `infra-terraform` の protected `main` と承認済み workflow のみ | 作成するリソース単位の管理権限。IAM と WIF の作成・変更は別の bootstrap 手順に分離 |

WIF の属性条件には少なくとも固定の `repository_id`、`ref == "refs/heads/main"`、`job_workflow_ref` を含めます。`repository` 名だけを条件にせず、リポジトリ転送・名前変更の影響を受けない ID を使います。

```hcl
attribute_mapping = {
  "google.subject"                 = "assertion.sub"
  "attribute.repository_id"        = "assertion.repository_id"
  "attribute.ref"                  = "assertion.ref"
  "attribute.job_workflow_ref"     = "assertion.job_workflow_ref"
}

# 値は対象リポジトリと、保護したデプロイ workflow に固定する。
attribute_condition = <<-EOT
  attribute.repository_id == "<REPOSITORY_ID>" &&
  attribute.ref == "refs/heads/main" &&
  attribute.job_workflow_ref == "<OWNER>/<REPOSITORY>/.github/workflows/deploy.yml@refs/heads/main"
EOT
```

## レビュー結果

| 優先度 | 場所 | 内容と対応 |
| --- | --- | --- |
| Critical | `modules/wif/main.tf:20,38,45-50,64` | リポジトリ名だけを信頼する WIF 主体が `roles/resourcemanager.projectIamAdmin` を取得する。上記の分離と条件固定を先に実施する。 |
| High | `infra-terraform/.github/workflows/terraform.yml:39,50,56`、`docs-repo/.github/workflows/deploy.yml:20,25,32` | Actions を可変タグで参照している。リリースのコミット SHA に pin し、Dependabot/Renovate で更新する。 |
| Medium | `modules/wif/main.tf:60-77` | 11 個のプロジェクトレベル管理ロールは「最小」ではない。`projectIamAdmin`、`serviceAccountAdmin`、`workloadIdentityPoolAdmin` は通常のデプロイ主体から外し、バケット・リポジトリ・サービス単位の IAM に置換する。 |
| Medium | `modules/cloud_run/main.tf:41` | `var.container_image` が渡されているが使われず、`nginx:1.27-alpine` に固定される。Artifact Registry も参照されないため、イメージを変えられず不要なリソースとコストが残る。変数を使用するか、Artifact Registry モジュールと変数を削除する。イメージは digest で固定する。 |
| Medium | `provider.tf:2,7,11`、`.terraform.lock.hcl`、`.github/workflows/terraform.yml:58` | lock されている Google/Google Beta Provider は `6.50.0`、CI の Terraform は `1.9.5`。調査日時点の最新は Provider `7.43.0`、Terraform `1.15.8`。互換性を検証してから major upgrade し、lock file を更新する。 |
| Medium | `docs-repo/requirements.txt` | `>=` の範囲指定だけで lock file がない。ビルド時期で異なる依存グラフになり再現できない。`uv.lock` をコミットし、CI は `uv sync --frozen` を使用する。 |
| Low | `infra-terraform/.github/workflows/terraform.yml:17-20` | `pull-requests: write` を使用していないため削除する。 |
| Low | `modules/lb_iap/main.tf:61-83` | `domain_name` が空でも HTTP のみ作成し HTTPS へリダイレクトするため、アクセス不能になる。ドメインを必須にするか、HTTP リダイレクトも HTTPS リソースと同じ条件で作成する。 |

## バージョンと再現性

| 対象 | 現在の指定 | 調査日時点の状況 |
| --- | --- | --- |
| Terraform | CI は `1.9.5` | `1.15.8` が最新。`required_version = ">= 1.9.0"` は上限を設けず互換性検証を弱める。 |
| `hashicorp/google` / `google-beta` | `~> 6.0`、lock は `6.50.0` | `7.43.0` が最新。Terraform plan を確認しながら更新する。 |
| NGINX | `nginx:1.27-alpine` | `1.30.4-alpine` が最新。ただしタグ更新ではなく検証済み digest を固定する。 |
| `actions/checkout` | `@v7` | v7 系の可変タグ。バージョンの鮮度とは別に SHA pin が必要。 |
| MkDocs dependencies | `>=9.6,<10` / `>=0.8,<1` | 新版を解決できるが lock がない。最新版への追随と再現性を両立するには lock file を更新運用する。 |

## 維持する設定

- GCS の `uniform_bucket_level_access = true`、`public_access_prevention = "enforced"`、バージョニング
- Cloud Run の `INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER`
- Cloud Run 用サービスアカウントへの、対象バケットだけの `roles/storage.objectViewer`
- GitHub Actions の OIDC 利用。長期サービスアカウントキーを発行しないこと

## 実施済み: CI と依存関係の再現性改善

2026-08-10 に、WIF の信頼条件およびサービスアカウントの権限を変更せず、次の是正を実施した。

- Terraform とドキュメント配信の workflow にある全ての Actions を、リリースを示すコメント付きの完全なコミット SHA に固定した。
- Terraform workflow の未使用 `pull-requests: write` 権限を削除し、`contents: read` と `id-token: write` のみを維持した。
- Terraform CLI を `1.15.8`、Google / Google Beta Provider を `7.43.0` に固定し、ルートスタックの lock file を Terraform に再生成させた。
- MkDocs の直接依存をバージョン固定し、`pyproject.toml` と `uv.lock` を追加した。CI とローカル手順は `uv sync --frozen` に統一した。

## 実施順序

1. WIF をサービスアカウント別に分離し、`docs-repo` からインフラ管理権限を外す。
2. プロジェクト IAM 管理、WIF 管理、サービスアカウント管理を通常の CI/CD ロールから外す。
3. Actions を SHA pin し、未使用の `pull-requests: write` を削除する。
4. Cloud Run のイメージ入力と Artifact Registry のどちらを採用するか決め、不要な方を削除する。
5. Terraform Provider と Terraform を互換性確認の上で更新し、Python 依存を lock する。

## 承認済みの是正設計

> 承認日: 2026-08-10

### 構成

- `bootstrap/` は WIF pool/provider と 2 つのサービスアカウントを管理する。実行は管理者の明示的な Terraform 操作に限定し、通常の GitHub Actions からは実行しない。
- 通常の Terraform スタックは GCS、Cloud Run、Load Balancer、IAP と、それらに必要なリソース IAM だけを管理する。bootstrap リソースを state に含めない。
- Terraform 用 SA は `infra-terraform` の protected `main` にある Terraform workflow だけを信頼する。docs 配信用 SA は `docs-repo` の protected `main` にある deploy workflow だけを信頼する。
- 各 WIF provider の条件は GitHub の不変な `repository_id`、`refs/heads/main`、固定の `job_workflow_ref` を必須にする。リポジトリ名・actor・任意 branch だけで認証を許可しない。
- docs 配信用 SA は対象 GCS bucket の `roles/storage.objectAdmin` だけを受ける。Terraform 用 SA にも `projectIamAdmin`、`workloadIdentityPoolAdmin`、広域のサービスアカウント管理権限を付与しない。

### デプロイの流れ

1. 管理者が bootstrap を適用し、Terraform 用と docs 用の WIF provider / SA を作成する。
2. GitHub Secrets の provider と service-account email を用途別の値へ一括で更新する。
3. Terraform workflow が通常スタックを適用し、GCS bucket と docs SA への bucket 単位の権限を作成する。
4. docs workflow が docs 用 SA で MkDocs site を対象 bucket へ同期する。
5. 旧共有 SA、旧 provider、旧 WIF binding、不要な project-level IAM binding を同じ変更で削除する。

### 構成の簡素化と依存管理

- Artifact Registry module、変数、output を削除する。Cloud Run は公式 NGINX の検証済み immutable digest を `container_image` 入力から使う。
- `domain_name` は必須にし、HTTPS endpoint と HTTP-to-HTTPS redirect を常に対で作る。
- Terraform CLI は `1.15.8`、Google / Google Beta Provider は `7.43.0` へ更新し、lock file を再生成する。
- Python 依存は `uv.lock` をコミットし、CI を `uv sync --frozen` に変更する。
- すべての GitHub Actions はリリース済みコミット SHA に固定する。Terraform workflow の未使用 `pull-requests: write` は削除する。

### エラー処理と検証

- `repository_id`、workflow reference、container image digest、domain name は必須入力とし、Terraform variable validation で空値を拒否する。
- bootstrap と通常スタックは別 state とする。通常 CI に bootstrap 権限がない場合は失敗して停止し、権限不足を補う広域ロールの追加で回避しない。
- Terraform は `fmt -check -recursive`、`validate`、plan を実行する。docs は lock 済み依存で `mkdocs build --strict` を実行する。
- WIF 条件、SA の有効権限、Cloud Run の ingress、IAP 経由のアクセスを適用後に確認する。

## Infrastructure Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the shared, privileged WIF identity with isolated bootstrap, Terraform, and documentation-publishing identities while making the deployment reproducible and removing unused infrastructure.

**Architecture:** `infra-terraform/bootstrap/` owns the WIF pool, providers, and service accounts in a dedicated state. The root Terraform stack owns the serving infrastructure and resource-scoped IAM only. GitHub workflows use the corresponding WIF identity, exact action SHAs, and locked dependencies.

**Tech Stack:** Terraform 1.15.8, Google and Google Beta Provider 7.43.0, GitHub Actions OIDC, GCS, Cloud Run v2, MkDocs Material, uv.

---

### Task 1: Create the bootstrap stack

**Files:**
- Create: `infra-terraform/bootstrap/provider.tf`
- Create: `infra-terraform/bootstrap/main.tf`
- Create: `infra-terraform/bootstrap/variables.tf`
- Create: `infra-terraform/bootstrap/outputs.tf`
- Create: `infra-terraform/bootstrap/terraform.tfvars.example`
- Modify: `infra-terraform/main.tf`
- Modify: `infra-terraform/variables.tf`
- Modify: `infra-terraform/outputs.tf`

- [ ] **Step 1: Add a bootstrap backend and provider configuration**

```hcl
terraform {
  required_version = "= 1.15.8"
  backend "gcs" {
    bucket = "try-gcp-504903-tfstate"
    prefix = "terraform/state/bootstrap"
  }
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "= 7.43.0"
    }
  }
}
```

- [ ] **Step 2: Define both WIF trust inputs as required variables**

```hcl
variable "terraform_repository_id" { type = string }
variable "docs_repository_id" { type = string }
variable "project_id" { type = string }
```

Validate each ID with `can(regex("^[0-9]+$", var.terraform_repository_id))`; set `terraform_repository_id = "1327451305"` and `docs_repository_id = "1327472883"` in the bootstrap tfvars; declare fixed workflow paths in locals, not as user inputs.

- [ ] **Step 3: Implement two service accounts and two WIF providers**

Create `terraform_deployer` and `docs_publisher` service accounts. Map `assertion.repository_id`, `assertion.ref`, and `assertion.job_workflow_ref`; give each provider a condition requiring its repository ID, `refs/heads/main`, and respectively `.github/workflows/terraform.yml@refs/heads/main` or `.github/workflows/deploy.yml@refs/heads/main`. Bind each service account only to its provider's repository-ID principal set.

- [ ] **Step 4: Grant bootstrap-defined roles**

Grant the docs account no project role. In the root stack, grant it `roles/storage.objectAdmin` on `module.gcs.bucket_name`. Give the Terraform account only the roles required to create and update GCS, Cloud Run, Compute LB, IAP, and Artifact Registry-free service accounts; do not grant `roles/resourcemanager.projectIamAdmin`, `roles/iam.workloadIdentityPoolAdmin`, or `roles/iam.serviceAccountAdmin`.

- [ ] **Step 5: Remove the old shared WIF module from the root stack**

Delete `module "wif"` and the `github_repositories` variable and outputs. Replace them with required bootstrap outputs documented as the values for the GitHub Secrets.

- [ ] **Step 6: Validate the bootstrap and root stacks**

Run:

```bash
terraform -chdir=infra-terraform/bootstrap init -upgrade
terraform -chdir=infra-terraform/bootstrap fmt -check -recursive
terraform -chdir=infra-terraform/bootstrap validate
terraform -chdir=infra-terraform fmt -check -recursive
terraform -chdir=infra-terraform validate
```

- [ ] **Step 7: Commit**

```bash
git -C infra-terraform add bootstrap main.tf variables.tf outputs.tf modules/wif
git -C infra-terraform commit -m "feat: isolate WIF bootstrap identities"
```

### Task 2: Perform the explicit WIF state and secret cutover

**Files:**
- Create: `infra-terraform/bootstrap/MIGRATION.md`
- Modify: `infra-terraform/README.md`

- [ ] **Step 1: Document the state migration commands**

Require an administrator to back up both state files before moving the existing WIF resources from the root state into the bootstrap state. The guide must use `terraform state pull > root-before-wif-migration.tfstate` and require a reviewed `terraform plan` before every apply.

- [ ] **Step 2: Apply and cut over**

Run bootstrap apply with administrator credentials, set `GCP_WORKLOAD_IDENTITY_PROVIDER` and `GCP_SERVICE_ACCOUNT` in each repository to its corresponding bootstrap outputs, then run root plan/apply with the new Terraform identity. Remove the old shared provider, binding, and service account only after both workflows succeed.

- [ ] **Step 3: Commit**

```bash
git -C infra-terraform add bootstrap/MIGRATION.md README.md
git -C infra-terraform commit -m "docs: add WIF cutover procedure"
```

### Task 3: Simplify serving infrastructure

**Files:**
- Delete: `infra-terraform/modules/artifact_registry/main.tf`
- Delete: `infra-terraform/modules/artifact_registry/variables.tf`
- Delete: `infra-terraform/modules/artifact_registry/outputs.tf`
- Modify: `infra-terraform/main.tf`
- Modify: `infra-terraform/variables.tf`
- Modify: `infra-terraform/outputs.tf`
- Modify: `infra-terraform/modules/cloud_run/main.tf`
- Modify: `infra-terraform/modules/lb_iap/main.tf`
- Modify: `infra-terraform/terraform.tfvars.example`

- [ ] **Step 1: Write the configuration assertions**

Use `terraform validate` against an example with an empty `domain_name` and expect validation to fail. Use a second example with a digest-form image (`nginx@sha256:` followed by 64 lowercase hexadecimal characters) and expect validation to pass.

- [ ] **Step 2: Implement the smallest configuration**

Delete the Artifact Registry module, `repository_id`, and all related outputs. Change Cloud Run from:

```hcl
image = "nginx:1.27-alpine"
```

to:

```hcl
image = var.container_image
```

Require `domain_name` and a digest-form `container_image` with Terraform validation. Remove every conditional `count` from the HTTPS resources so port 80 redirect and port 443 endpoint are always created together.

- [ ] **Step 3: Resolve and pin the NGINX digest**

Obtain the immutable digest for the reviewed official `nginx:1.30.4-alpine` image, place the full `nginx@sha256:...` reference in `terraform.tfvars.example`, and set the same digest as the variable default. Do not use a mutable tag.

- [ ] **Step 4: Validate and commit**

```bash
terraform -chdir=infra-terraform fmt -check -recursive
terraform -chdir=infra-terraform validate
git -C infra-terraform add -A
git -C infra-terraform commit -m "refactor: simplify Cloud Run image delivery"
```

### Task 4: Make CI deterministic and least-privileged

**Files:**
- Modify: `infra-terraform/.github/workflows/terraform.yml`
- Modify: `docs-repo/.github/workflows/deploy.yml`
- Modify: `docs-repo/requirements.txt`
- Create: `docs-repo/uv.lock`

- [ ] **Step 1: Pin action revisions**

Replace every `uses:` tag with these full release SHAs and retain the release in an inline comment:

```yaml
uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
uses: google-github-actions/auth@7c6bc770dae815cd3e89ee6cdf493a5fab2cc093 # v3.0.0
uses: hashicorp/setup-terraform@5e8dbf3c6d9deaf4193ca7a8fb23f2ac83bb6c85 # v4.0.0
uses: astral-sh/setup-uv@c771a70e6277c0a99b617c7a806ffedaca235ff9 # v9.0.0
```

- [ ] **Step 2: Restrict workflow permissions**

Remove `pull-requests: write` from the Terraform workflow. Retain only `contents: read` and `id-token: write` in both workflows.

- [ ] **Step 3: Update Terraform and workflow validation**

Set the setup action Terraform version to `1.15.8`, replace `terraform fmt -check *.tf` with `terraform fmt -check -recursive`, and retain non-interactive `validate`, `plan`, and `apply`.

- [ ] **Step 4: Lock Python dependencies**

Replace range-only requirements with direct requirements, run `uv lock`, commit `uv.lock`, and replace:

```yaml
uv venv
uv pip install -r requirements.txt
```

with:

```yaml
uv sync --frozen
echo "$GITHUB_WORKSPACE/.venv/bin" >> "$GITHUB_PATH"
```

- [ ] **Step 5: Validate and commit**

```bash
docs-repo/.venv/bin/mkdocs build --strict --config-file docs-repo/mkdocs.yml
git -C docs-repo add .github/workflows/deploy.yml requirements.txt uv.lock
git -C docs-repo commit -m "build: lock documentation deployment dependencies"
```

### Task 5: Upgrade Terraform dependencies and update operational documentation

**Files:**
- Modify: `infra-terraform/provider.tf`
- Modify: `infra-terraform/.terraform.lock.hcl`
- Modify: `infra-terraform/README.md`
- Modify: `docs-repo/docs/knowledge/2026-08/2026-08-09_gcp_wif_iap_least_privilege_guide.md`

- [ ] **Step 1: Upgrade providers**

Set both provider constraints to `= 7.43.0`, run `terraform -chdir=infra-terraform init -upgrade`, and review the complete plan before applying. Do not manually edit `.terraform.lock.hcl`.

- [ ] **Step 2: Document final required secrets and recovery**

Document the four purpose-specific secret values, the bootstrap-only execution rule, the state backup location, and rollback as restoring the reviewed state backup before re-running the prior root plan.

- [ ] **Step 3: Run final checks and commit**

```bash
terraform -chdir=infra-terraform fmt -check -recursive
terraform -chdir=infra-terraform validate
docs-repo/.venv/bin/mkdocs build --strict --config-file docs-repo/mkdocs.yml
git -C infra-terraform add provider.tf .terraform.lock.hcl README.md
git -C infra-terraform commit -m "build: upgrade Terraform toolchain"
git -C docs-repo add docs/knowledge/2026-08/2026-08-09_gcp_wif_iap_least_privilege_guide.md
git -C docs-repo commit -m "docs: record infrastructure remediation"
```
