# コードレビュー結果および対応状況

> **対象**: `docs-repo` / `infra-terraform`
> **実施日**: 2026-08-08
> **ステータス**: **全 28 件の対応完了 (100% COMPLETE)**

---

## 🔴 Critical（対応完了）

### 1. WIF サービスアカウントへの過剰権限 — `roles/owner` + `roles/editor`
- **ファイル**: [modules/wif/main.tf](file:///home/oharato/workspace/try-gcp/infra-terraform/modules/wif/main.tf)
- **対応結果**: ✅ `roles/owner` および `roles/editor` を削除し、8 つの最小権限ロールに特定・制限しました。

### 2. Cloud Run の `allUsers` invoker バインディング
- **ファイル**: [modules/cloud_run/main.tf](file:///home/oharato/workspace/try-gcp/infra-terraform/modules/cloud_run/main.tf)
- **対応結果**: ✅ `allUsers` への `roles/run.invoker` バインディングを削除し、IAP SA のみに限定しました。

### 3. HTTP → HTTPS リダイレクト実装（IAP バイパスリスク）
- **ファイル**: [modules/lb_iap/main.tf](file:///home/oharato/workspace/try-gcp/infra-terraform/modules/lb_iap/main.tf)
- **対応結果**: ✅ `google_compute_url_map.http_redirect` を新規作成し、HTTP 通信をすべて HTTPS へ強制リダイレクトするように修正しました。

### 4. Mermaid CDN の二重読み込み
- **ファイル**: [mkdocs.yml](file:///home/oharato/workspace/try-gcp/docs-repo/mkdocs.yml)
- **対応結果**: ✅ `extra_javascript` から外部 CDN 指定を削除し、MkDocs Material ネイティブサポートのみを利用するように改善しました。

---

## 🟠 High（対応完了）

### 5. `.gitignore` の `*.tfvars` が example ファイルも除外
- **ファイル**: [.gitignore](file:///home/oharato/workspace/try-gcp/infra-terraform/.gitignore)
- **対応結果**: ✅ `!terraform.tfvars.example` 例外ルールを追加しました。

### 6. CI/CD の concurrency 制御なし
- **ファイル**: [terraform.yml](file:///home/oharato/workspace/try-gcp/infra-terraform/.github/workflows/terraform.yml)
- **対応結果**: ✅ `concurrency` グループを設定し、複数実行時の State ロック競合を防止しました。

### 7. pip パッケージのバージョン未固定
- **ファイル**: [deploy.yml](file:///home/oharato/workspace/try-gcp/docs-repo/.github/workflows/deploy.yml), [requirements.txt](file:///home/oharato/workspace/try-gcp/docs-repo/requirements.txt)
- **対応結果**: ✅ `requirements.txt` を新規作成し、`mkdocs-material` および `mkdocs-minify-plugin` のバージョンを明示的に固定しました。

---

## 🟡 Medium（対応完了）

| # | リポジトリ | ファイル | 内容 | ステータス |
|:--|:--|:--|:--|:--|
| 8 | infra-terraform | `variables.tf` | 単数系変数を整理し、`github_repositories` および `allowed_users` のリスト形式に統一 | ✅ 修正済み |
| 9 | infra-terraform | `variables.tf` | `container_image` のデフォルト値を `"nginx:1.27-alpine"` に固定 | ✅ 修正済み |
| 10 | infra-terraform | `Dockerfile` | ベースイメージを `nginx:1.27.5-alpine3.21` パッチバージョン固定 | ✅ 修正済み |
| 11 | infra-terraform | `Dockerfile` | 非 root ユーザー (`nginx`) での起動権限設定を追加 | ✅ 修正済み |
| 12 | infra-terraform | `default.conf` | `server_tokens off;` によるバージョン情報漏洩防止を追加 | ✅ 修正済み |
| 13 | infra-terraform | `default.conf` | gzip 圧縮、Content-Security-Policy 等のセキュリティヘッダーを最適化 | ✅ 修正済み |
| 14 | infra-terraform | `README.md` | Terraform 要件バージョン記載を `v1.9.0 以上` に修正 | ✅ 修正済み |
| 15 | infra-terraform | `terraform.yml` | `terraform.tfvars` の自動削除ステップをワークフロー最終行へ移動 | ✅ 修正済み |
| 16 | docs-repo | `README.md` | Python バージョン要求記載を `3.10 以上` に修正 | ✅ 修正済み |
| 17 | docs-repo | `README.md` | ローカルセットアップ手順に `requirements.txt` 使用方法を反映 | ✅ 修正済み |
| 18 | docs-repo | `extra.css` | ズームモーダルの背景色にダークモード (`[data-md-color-scheme="slate"]`) スタイルを追加 | ✅ 修正済み |
| 19 | infra-terraform | `variables.tf`, `main.tf` | `repository_id`, `service_name` を変数化 | ✅ 修正済み |

---

## 🟢 Low（対応完了）

| # | リポジトリ | 内容 | ステータス |
|:--|:--|:--|:--|
| 20 | docs-repo | `mkdocs.yml`: ダーク/ライトモード切替トグルを日本語化 | ✅ 修正済み |
| 21 | docs-repo | `extra.css`: レスポンシブ用メディアクエリ (`@media (min-width: 768px)`) を追加 | ✅ 修正済み |
| 22 | docs-repo | `architecture.md`: Mermaid 図に WIF 経由フロールートを追加 | ✅ 修正済み |
| 23 | docs-repo | `README.md`: ディレクトリ構成図に `extra.css`, `extra.js` を追記 | ✅ 修正済み |
| 24 | infra-terraform | `modules/gcs/`: 30日後に非最新バージョンを自動削除するライフサイクルルールを追加 | ✅ 修正済み |
| 25 | infra-terraform | `modules/artifact_registry/`: `immutable_tags = true` を適用 | ✅ 修正済み |
| 26 | infra-terraform | `README.md`: 「各各種」の重複タイポを修正 | ✅ 修正済み |
