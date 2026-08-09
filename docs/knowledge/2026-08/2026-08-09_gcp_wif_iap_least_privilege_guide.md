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
