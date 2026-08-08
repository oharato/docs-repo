# システムアーキテクチャ

本システムの全体的なインフラ構成およびデプロイメントフローの解説です。

## 全体構成図

```mermaid
flowchart TD
    subgraph GitHub ["GitHub Repository (docs-repo)"]
        Markdown["Markdown Sources"]
        GHA["GitHub Actions Workflow"]
        Markdown -->|Push to main| GHA
    end

    subgraph GCP ["Google Cloud Platform"]
        subgraph Security ["Identity & Access Control"]
            WIF["Workload Identity Federation"]
            IAP["Identity-Aware Proxy (IAP)"]
            GoogleGroup["Allowed Google Workspace Group"]
            IAP --- GoogleGroup
        end

        subgraph Storage ["Storage Layer"]
            GCS["GCS Bucket (gs://<bucket_name>)"]
        end

        subgraph Networking ["Network Layer"]
            User(("User Browser"))
            HTTPSLB["Global External HTTPS Load Balancer"]
            NEG["Serverless NEG"]
            User -->|HTTPS Request| HTTPSLB
            HTTPSLB -->|Authentication| IAP
            IAP -->|Authorized| NEG
        end

        subgraph Compute ["Compute Layer"]
            CloudRun["Cloud Run Service (Nginx)"]
            NEG --> CloudRun
            CloudRun -->|GCS Volume Mount (gcsfuse)| GCS
        end

        subgraph Registry ["Container Registry"]
            AR["Artifact Registry"]
            AR -->|Nginx Container Image| CloudRun
        end
    end

    GHA -->|WIF Auth & gcloud storage rsync| GCS
```

---

## 各コンポーネントの役割

| コンポーネント | 技術・サービス | 説明 |
| :--- | :--- | :--- |
| **Docs CI/CD** | GitHub Actions + WIF | サービスアカウントキー非保持で GCP に安全に認証し、MkDocs ビルド成果物を GCS へ同期 |
| **Infra CI/CD** | GitHub Actions + Terraform | Pull Request 時に `terraform plan` の結果を自動コメント投稿し、`main` マージ時に `terraform apply` を自動適用 |
| **Storage** | Google Cloud Storage | パブリックアクセス不可の非公開バケットに HTML/CSS/JS 成果物を保存 |
| **Compute** | Cloud Run (Nginx) | GCS ダイレクトボリュームマウント機能を使用し、GCS 内の静的ファイルを Nginx 経由で返却 |
| **Auth / Proxy** | Identity-Aware Proxy (IAP) | 指定した Google アカウント (Gmail) および Google Workspace グループに基づくアクセス制御をロードバランサ層で提供 |
| **Routing** | Global External HTTPS Load Balancer | Serverless NEG 経由で Cloud Run へルーティング。SSL 証明書自動発行および IAP を統合 |
