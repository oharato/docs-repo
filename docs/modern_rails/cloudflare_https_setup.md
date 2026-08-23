# Cloudflare CDN 導入 & HTTPS 化手順書 (Pulumi)

本ドキュメントでは、Pulumi を使用して **Cloudflare CDN（リバースプロキシ）** を適用し、**常時 HTTPS 化（SSL/TLS）** を実現するための完全な設計・実装・運用手順を解説します。

---

## 🏗️ アーキテクチャ

```text
[ブラウザ / クライアント]
      │
      │  HTTPS (Port 443 / TLS 1.2+)
      ▼
[Cloudflare Edge (CDN / WAF / SSL終端)]
      │  - 独自ドメイン (DNS Proxied: true)
      │  - Always Use HTTPS (自動リダイレクト)
      │  - キャッシュ & Brotli 圧縮
      │
      │  HTTP (Port 80) ※Flexible SSL モード
      ▼
[GCP Compute Engine (Static IP: 34.27.174.205)]
      │
      ▼
[Kamal-proxy]
      │
      ▼
[Rails 8 Web アプリケーション (Puma)]
```

### なぜ Cloudflare + Pulumi か？
1. **即時 HTTPS 化**: サーバー側の Let's Encrypt 設定や証明書更新管理が不要。
2. **CDN & DDoS 保護**: エッジサーバーでの静的アセットキャッシュとセキュリティ防御。
3. **IaC による一元管理**: GCP のインフラ（VM, 静的IP, Artifact Registry）と Cloudflare の DNS・SSL 設定を同じ Pulumi スタックで同期管理。

---

## 📋 事前準備

### 1. Cloudflare アカウント & ドメイン登録
1. [Cloudflare ダッシュボード](https://dash.cloudflare.com/) にログインし、管理対象のドメイン（例: `example.com`）が追加されていることを確認します。
2. ドメインの概要ページ右下から **Zone ID** をコピーして控えておきます。

### 2. Cloudflare API トークンの発行
1. Cloudflare ダッシュボードの [API Tokens ページ](https://dash.cloudflare.com/profile/api-tokens) にアクセスします。
2. **Create Token** をクリックし、**Edit zone DNS** テンプレートを使用するか、以下の権限を持つカスタムトークンを作成します:
   - `Zone - DNS - Edit`
   - `Zone - Zone Settings - Edit`
   - `Zone - Zone - Read`
3. 発行された **API Token** を安全に控えます。

---

## ⚙️ Pulumi によるインフラ設定手順

### STEP 1: `@pulumi/cloudflare` パッケージのインストール

```bash
cd infra
npm install @pulumi/cloudflare
```

### STEP 2: `.env` に設定値を記述 & 一括適用

設定値（Cloudflare API Token、Zone ID、ドメイン等）は、プロジェクトルートの [`.env`](file:///home/oharato/workspace/modern-rails/.env) に記載して一元管理できます。

#### 1. [`.env`](file:///home/oharato/workspace/modern-rails/.env) に設定を記述
```dotenv
# Cloudflare CDN & HTTPS 設定
CLOUDFLARE_API_TOKEN="cf_api_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
CLOUDFLARE_ZONE_ID="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
CLOUDFLARE_DOMAIN="@"      # Apexドメインなら "@"、サブドメインなら "app" など
DOMAIN="example.com"       # 本番FQDN
```

#### 2. 一括適用スクリプトを実行
プロジェクトルートで以下のコマンドを実行すると、`.env` の内容を読み込み、APIトークンをシークレット暗号化して Pulumi に一括セットします。

```bash
# スクリプトを実行して .env から Pulumi config に一括反映
./script/apply-infra-config.sh

# または infra ディレクトリから npm コマンドで実行
cd infra && npm run config:sync
```

> **💡 個別にコマンドで設定したい場合:**
> ```bash
> cd infra
> pulumi config set --secret cloudflare:apiToken "<YOUR_CLOUDFLARE_API_TOKEN>"
> pulumi config set modern-rails-infra:cloudflareZoneId "<YOUR_CLOUDFLARE_ZONE_ID>"
> pulumi config set modern-rails-infra:domain "@"
> ```

---

### STEP 3: `infra/index.ts` の定義

[`infra/index.ts`](file:///home/oharato/workspace/modern-rails/infra/index.ts) に Cloudflare プロバイダおよび DNS / SSL リソースを追加します。

```typescript
import * as pulumi from "@pulumi/pulumi";
import * as gcp from "@pulumi/gcp";
import * as cloudflare from "@pulumi/cloudflare";
import * as fs from "fs";
import * as path from "path";
import * as os from "os";

// Config
const config = new pulumi.Config();
const gcpConfig = new pulumi.Config("gcp");
const project = gcpConfig.require("project");
const region = gcpConfig.get("region") || "us-central1";
const zone = gcpConfig.get("zone") || "us-central1-a";
const machineType = config.get("machineType") || "e2-micro";

// Cloudflare Config
const cloudflareZoneId = config.get("cloudflareZoneId");
const domainName = config.get("domain") || "@";

// ... (既存の GCP リソース: staticIp, webFirewall, sshFirewall, artifactRepo, instance 等) ...

// =========================================================================
// 6. Cloudflare CDN & HTTPS Configuration
// =========================================================================
if (cloudflareZoneId) {
  // Aレコード作成 (proxied: true で CDN と Cloudflare SSL を有効化)
  const dnsRecord = new cloudflare.Record("modern-rails-dns", {
    zoneId: cloudflareZoneId,
    name: domainName,
    type: "A",
    content: staticIp.address,
    proxied: true, // オレンジクラウド (CDN, DDoS防御, エッジSSL)
    ttl: 1,        // proxied の場合は Auto (1)
    comment: "Managed by Pulumi - Modern Rails Web Server",
  });

  // SSL/TLS & HTTPS セキュリティ設定
  const zoneSettings = new cloudflare.ZoneSettingsOverride("modern-rails-zone-settings", {
    zoneId: cloudflareZoneId,
    settings: {
      ssl: "flexible",                 // Cloudflare ↔ オリジン間を HTTP(80) 通信
      alwaysUseHttps: "on",             // HTTP (80) へのアクセスを HTTPS (443) へ 301 リダイレクト
      automaticHttpsRewrites: "on",     // 混在コンテンツ (HTTP画像等) を自動で HTTPS に書き換え
      minTlsVersion: "1.2",             // TLS 1.2 以上を強制
      brotli: "on",                     // Brotli 圧縮を有効化
      http3: "on",                      // HTTP/3 (QUIC) を有効化
      securityHeader: {
        strictTransportSecurity: {
          enabled: true,
          maxAge: 31536000,             // HSTS: 1年間
          includeSubdomains: true,
          preload: true,
        },
      },
    },
  });

  // Outputs
  export const cfRecordHostname = dnsRecord.hostname;
  export const cfRecordFqdn = dnsRecord.hostname;
}
```

---

### STEP 4: Pulumi でインフラをデプロイ

```bash
cd infra
# 変更差分の確認
pulumi preview

# 反映
pulumi up --yes
```

---

## 🛠️ Rails & Kamal の設定調整

### 1. Rails アプリケーション設定 (`config/environments/production.rb`)

Cloudflare が付与する `X-Forwarded-Proto: https` ヘッダーを Rails に信頼させ、リダイレクトループを防ぎます。

```ruby
# config/environments/production.rb
Rails.application.configure do
  # ...
  # Cloudflare のプロキシ経由で HTTPS 通信として認識
  config.assume_ssl = true
  config.force_ssl = true
  # ...
end
```

### 2. Kamal デプロイ設定 (`config/deploy.yml`)

ホスト名に独自ドメインを設定します。

```yaml
# config/deploy.yml
proxy:
  ssl: false # Cloudflare Flexible SSL のためオリジン側での SSL 終端は不要
  host: <%= ENV["DOMAIN"] || "example.com" %>
  app_port: 80
```

---

## 🚀 反映とデプロイ

```bash
# 1. Kamal で再デプロイ（またはプロキシ設定反映）
kamal proxy reboot
kamal deploy
```

---

## 🔍 動作確認 & 検証

### 1. HTTP から HTTPS へのリダイレクト確認

```bash
curl -I http://example.com
```
**期待される結果:**
```http
HTTP/1.1 301 Moved Permanently
Location: https://example.com/
Server: cloudflare
```

### 2. HTTPS 接続と Cloudflare エッジヘッダーの確認

```bash
curl -I https://example.com
```
**期待される結果:**
```http
HTTP/2 200
cf-ray: xxxxxxxxxxxxxxxx-NRT
cf-cache-status: DYNAMIC (または HIT)
strict-transport-security: max-age=31536000; includeSubDomains; preload
server: cloudflare
```

---

## ❓ トラブルシューティング

| 事象 | 原因 | 解決策 |
| :--- | :--- | :--- |
| **リダイレクトループが発生する (ERR_TOO_MANY_REDIRECTS)** | Cloudflare SSL が `Flexible` の状態で、Rails の `force_ssl = true` 単体で動作しており `assume_ssl` が未設定 | `config/environments/production.rb` で `config.assume_ssl = true` を設定する |
| **521 Web Server Is Down** | オリジンサーバー (GCP VM) の Web サービス (Kamal-proxy) が停止している、またはファイアウォールでポート 80 が拒否されている | GCP ファイアウォールで `0.0.0.0/0:80` が許可されているか、`docker ps` で `kamal-proxy` が動作中か確認する |
| **525 / 526 SSL Handshake Failed** | Cloudflare SSL モードが `Full (strict)` になっており、オリジン側に有効な証明書が存在しない | Pulumi の `settings.ssl` を `"flexible"` に設定するか、オリジンに証明書を配置する |
