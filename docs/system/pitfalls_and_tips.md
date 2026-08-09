# 陥りやすいミスと設定の工夫・ハマりポイント集

本ドキュメントは、`docs-repo` および `infra-terraform` の構築・運用・CI/CD 化の過程で得られた過去のコミット履歴、トラブルシューティング事例、セキュリティ強化策、および各種パフォーマンス設定の工夫を体系的にまとめたノウハウ集です。

---

## 1. 🛡️ インフラ & GCP セキュリティ (Terraform)

### 1.1 GCP Provider v6 破壊的変更への対応
- **事象**: Google Provider を `v6.0.0` 以上（例: `v6.50.0`）へアップグレードした際、`google_compute_backend_service` リソースの IAP 設定でエラーが発生。
- **原因**: Provider v6 では、IAP ブロックを定義する場合に `enabled = true` の明示指定が必須化されました。
- **対策**:
  ```hcl
  iap {
    enabled              = true  # v6 では必須
    oauth2_client_id     = var.iap_client_id
    oauth2_client_secret = var.iap_client_secret
  }
  ```

### 1.2 IAP (Identity-Aware Proxy) のバイパスリスクと完全遮断
- **事象**: HTTP (ポート 80) 通信が直接バックエンドに転送されていると、IAP 認証を経由せずに Cloud Run にアクセスできる脆弱性が生じる。
- **対策**:
  1. **HTTP → HTTPS リダイレクト**: HTTP フォワーディングルールには直接バックエンドを紐付けず、専用の HTTP リダイレクト URL Map (`google_compute_url_map.http_redirect`) を適用して全アクセスを HTTPS へ強制リダイレクト。
  2. **Cloud Run の IAM 制限**: `member = "allUsers"` への `roles/run.invoker` 権限を削除し、IAP システムサービスアカウント (`service-<project_number>@gcp-sa-iap.iam.gserviceaccount.com`) のみに限定してアクセスをバインド。

### 1.3 Workload Identity Federation (WIF) の最小権限原則
- **事象**: CI/CD 用サービスアカウントに `roles/owner` や `role### 1.3 Workload Identity Federation (WIF) SA の最小権限化 (Least Privilege)
- **事象**: CI/CD 用 Service Account に `roles/owner` や `roles/editor` などの広範な特権をバインドすると、リポジトリ侵害時に重大なセキュリティリスクとなる。
- **対策**: `roles/owner` / `editor` を完全に削除し、インフラ更新に必要な 9 つの最小権限のみに特定・制限。
  ```hcl
  for_each = toset([
    "roles/iam.workloadIdentityPoolAdmin",
    "roles/resourcemanager.projectIamAdmin",
    "roles/run.admin",
    "roles/compute.admin",
    "roles/compute.securityAdmin",
    "roles/storage.admin",
    "roles/artifactregistry.admin",
    "roles/iam.serviceAccountAdmin",
    "roles/iam.serviceAccountUser",
    "roles/iap.admin",
    "roles/iap.webServiceAdmin",
  ])
  ```

### 1.4 Artifact Registry のイミュータブルタグ (`immutable_tags = true`)
- **事象**: `immutable_tags = true` を設定すると、`:latest` タグのイメージ上書きプッシュが `error from registry: cannot update tag latest` で拒否される。
- **対策**: セキュリティ・再現性の観点から `:latest` の運用を止め、ビルドごとに意図したセマンティックバージョンタグ（例: `v1.0.1`, `v1.0.2`）を付与してプッシュ・デプロイを行う。

### 1.5 `.gitignore` における設定の落とし穴
- **事象**: ローカルの `*.tfvars` を除外する目的で `.gitignore` に `*.tfvars` と記述すると、サンプルファイル `terraform.tfvars.example` も除外され Git 管理から外れる。
- **対策**: 例外除外ルール `!terraform.tfvars.example` を明示的に追加。

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

### 2.3 Mermaid ズーム機能の安定実装
- **事象**: クリック時のモーダルズーム表示を SVG の DOM 複製方式で実装すると、SVG ID の重複やスクリプトエラーを引き起こす。
- **対策**: DOM を複製せず、親要素へのクラス切替 (`is-zoomed`) と CSS ガラスモフィズムモーダルスタイルによるオーバーレイ方式を採用。

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
1. **Runner プリインストール `gcloud` の活用**: `ubuntu-latest` Runner には `gcloud` CLI が標準搭載されているため、`google-github-actions/setup-gcloud` ステップをスキップすることでインストール時間（15〜20 秒）を削減。
2. **`uv` (`astral-sh/setup-uv`) による超高速パッケージ管理 & キャッシュ**:
   従来の `pip` の代わりに Rust 製の超高速パッケージインパクター `uv` を導入。`enable-cache: true` を有効にすることで、ホイールキャッシュ・コンパイル結果を高度に自動復元し、依存関係取得をサブセコンド化。
3. **浅い Git クローン**: `actions/checkout` で `fetch-depth: 1` を指定してコミット履歴取得を最小化。

### 3.4 Git Pre-commit Hook によるコミット前の事前自動検証 (マルチ PC 対応)
- **目的**: 壊れたリンクや構成不備を含んだままコミット・Push されるのをローカル段階で 100% 阻止する。
- **マルチ PC 共有設計**:
  通常 `.git/hooks/` は追跡不可ですが、本リポジトリではコミット共有可能な `.githooks/` ディレクトリにフックを配置・一元管理しています。
- **設定方法 (別 PC / 新環境クローン時)**:
  `git config core.hooksPath .githooks`
- **挙動**:
  `git commit` 時に自動で `mkdocs build --strict` がローカル実行され、警告やエラーがあればコミットを中断し、修正を促します。
