# 陥りやすいミスと設定の工夫・ハマりポイント集

本ドキュメントは、`docs-repo` および `infra-terraform` の構築・運用・CI/CD 化の過程で得られた過去のコミット履歴、トラブルシューティング事例、セキュリティ強化策、および各種パフォーマンス設定の工夫を体系的にまとめたノウハウ集です。

---

## 1. 🛡️ インフラ & GCP セキュリティ (Terraform)

### 1.1 GCP Project レベル IAM バインドの制約 (`roles/iap.webServiceAdmin`)
- **事象**: WIF Service Account に対して `roles/iap.webServiceAdmin`（IAP Web サービス管理者）をプロジェクト全体 (`google_project_iam_member`) に付与しようとすると `googleapi: Error 400: Role is not supported for this resource` が発生する。
- **原因**: `roles/iap.webServiceAdmin` は特定のバックエンドサービス個体 (`iap_web/compute/services/...`) にのみ付与可能なリソースレベル専用ロールであり、プロジェクト全域レベルの IAM Policy にはバインドできない。
- **対策**: プロジェクト全域レベルでの操作権限には `roles/iap.admin` を使用する。

### 1.2 IAP (Identity-Aware Proxy) のバイパスリスクと完全遮断
- **事象**: HTTP (ポート 80) 通信が直接バックエンドに転送されていると、IAP 認証を経由せずに Cloud Run にアクセスできる脆弱性が生じる。
- **対策**:
  1. **HTTP → HTTPS リダイレクト**: HTTP フォワーディングルールには直接バックエンドを紐付けず、専用の HTTP リダイレクト URL Map (`google_compute_url_map.http_redirect`) を適用して全アクセスを HTTPS へ強制リダイレクト。
  2. **Cloud Run の IAM 制限**: `member = "allUsers"` への `roles/run.invoker` 権限を削除し、IAP システムサービスアカウント (`service-<project_number>@gcp-sa-iap.iam.gserviceaccount.com`) のみに限定してアクセスをバインド。

### 1.3 Workload Identity Federation (WIF) SA の最小権限化 (Least Privilege)
- **事象**: CI/CD 用 Service Account に `roles/owner` や `roles/editor` などの広範な特権をバインドすると、リポジトリ侵害時に重大なセキュリティリスクとなる。
- **対策**: `roles/owner` / `editor` を完全に削除し、インフラ更新に必要な 11 個の最小権限のみに特定・制限。
  ```hcl
  for_each = toset([
    "roles/iam.workloadIdentityPoolAdmin",
    "roles/resourcemanager.projectIamAdmin",
    "roles/run.admin",
    "roles/compute.networkAdmin",
    "roles/compute.loadBalancerAdmin",
    "roles/compute.securityAdmin",
    "roles/storage.admin",
    "roles/artifactregistry.admin",
    "roles/iam.serviceAccountAdmin",
    "roles/iam.serviceAccountUser",
    "roles/iap.admin",
  ])
  ```

### 1.4 `terraform fmt -check` と動的生成 `terraform.tfvars` の競合
- **事象**: CI 上で `secrets.TFVARS_FILE` から一時的に動的生成される `terraform.tfvars` のフォーマット崩れにより、`terraform fmt -check` が Code 3 で失敗する。
- **対策**: ソースコードである `.tf` ファイルのみを対象とし、`terraform fmt -check *.tf` またはディレクトリ指定で検証を行う。

### 1.5 静的コンテンツ配信におけるコンテナのシンプル設計
- **事象**: MkDocs 等の静的ドキュメント配信で独自 Dockerfile やコンテナビルドを行うと、パイプラインが複雑化し不要な管理コストが発生する。
- **対策**: Cloud Run にはパブリック公式イメージ **`nginx:1.27-alpine`** を指定し、静的ファイルは GCS Volume Mount 経由で給仕させる。コンテンツ更新は `docs-repo` 側の GCS 同期 (`gcloud storage rsync`) のみで完結させる。

---

## 2. 🌐 Web アプリケーション & Nginx セキュリティ

### 2.1 Content-Security-Policy (CSP) の設定と厳格度の調整
- **事象**: Nginx に `Content-Security-Policy "default-src 'self';"` を適用すると、MkDocs Material の初期化 JavaScript (`__md_get is not defined`)、Google Fonts、外部 CDN (Mermaid.js)、インライン SVG スタイルがすべてブラウザにブロックされ、画面描画が崩れて Mermaid ダイアグラムが表示されなくなる。
- **対策**: MkDocs Material および Mermaid.js が必要とするドメインとインライン実行権限を精査して CSP に追加。
  ```nginx
  add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://unpkg.com https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; font-src 'self' https://fonts.gstatic.com data:; img-src 'self' data: blob:;" always;
  ```

### 2.2 Mermaid.js の二重読み込み競合
- **事象**: `mkdocs.yml` の `markdown_extensions` (`pymdownx.superfences`) で mermaid を有効にしている状態で `extra_javascript` に外部 Mermaid CDN を指定すると、ライブラリの二重読み込み・二重初期化が発生し、レンダリングの不具合やダークモード切替エラーの原因となる。
- **対策**: MkDocs Material ネイティブの Mermaid サポートに一本化し、`extra_javascript` から外部 CDN 読み込み行を削除。

---

## 3. 🚀 CI/CD パイプライン高速化 (GitHub Actions)

### 3.1 `gcloud storage rsync` の構文位置と引数
- **事象**: `gcloud storage rsync --recursive site/ gs://bucket` のようにフラグを先に記述したり、`--gzip-in-flight` フラグを単体で渡すと `argument DESTINATION: Must be specified` や `expected one argument` エラーが発生する。
- **対策**:
  - `SOURCE` と `DESTINATION` 引数をオプショナルフラグの前に記述する。
  - 全ファイルを自動インフライト圧縮する場合は `--gzip-in-flight-all` (`-J`) を使用する。
  ```bash
  gcloud storage rsync site/ gs://${{ secrets.GCS_BUCKET }} --recursive --delete-unmatched-destination-objects --gzip-in-flight-all
  ```

### 3.2 GitHub Actions の高速化テクニック
1. **`uv` (`astral-sh/setup-uv@v9.0.0`) による超高速パッケージ管理 & キャッシュ**:
   従来の `pip` の代わりに Rust 製の超高速パッケージインパクター `uv` を導入。`enable-cache: true` を有効にすることで、ホイールキャッシュ・コンパイル結果を高度に自動復元し、依存関係取得をサブセコンド化。
2. **`actions/checkout@v7` や `google-github-actions/auth@v3` などの最新アクションの利用**:
   バージョン警告を解消しセキュリティと安定性を確保。
