# 運用時の注意点

## Terraform state bucket

- WIF の IAM Condition を使う state bucket では Uniform bucket-level access が必須です。
- PR plan 用 SA は `terraform/state/docs-hub/` の prefix にだけアクセスできます。
- state を操作する個人管理者には `terraform/state/bootstrap/` prefix だけに `roles/storage.objectUser` を条件付きで付与します。`roles/storage.objectAdmin` は不要です。

## WIF と GitHub Actions

- WIF 条件は GitHub の `repository_id`、`ref`、`workflow_ref` を検証します。branch 名やリポジトリ名だけで信頼しません。
- apply は `main`、plan は PR 専用 SA を使います。Secrets を入れ替えないでください。
- Action の SHA は変更せず、更新時はレビュー済み release の SHA に置き換えます。

## Terraform CI

- `TFVARS_FILE` は Secret から一時生成されます。format 検査は `.tf` ファイルだけに適用します。
- `container_image` は mutable tag を使わず、`nginx@sha256:...` の digest を使います。

## docs 配信

- docs SA には対象 bucket の `roles/storage.objectAdmin` と `roles/storage.legacyBucketReader` が必要です。前者は同期、後者は `gcloud storage rsync` の bucket metadata 読取りに使います。
- 依存は `uv.lock` で固定し、CI とローカルで `uv sync --frozen` を使います。
