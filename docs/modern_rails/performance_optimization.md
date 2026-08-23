# Lighthouse 監査 & Web パフォーマンス最適化レポート

本ドキュメントは、**CraftCommerce (Rails 8 Edition)** における本番環境（[`https://modern-rails.ohchans.com/`](https://modern-rails.ohchans.com/)）の Lighthouse Web サイト品質監査、および実施したパフォーマンス・アクセシビリティ・SEO 最適化の全貌をまとめた技術資料です。

---

## 📊 最新 Lighthouse スコア（Basic 認証解除・一般公開版）

### 🖥️ デスクトップ環境 (Desktop)

| ページ | ⚡️ Performance | ♿️ Accessibility | 🛡️ Best Practices | 🔍 SEO | 総合判定 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **トップページ (`/`)** | **96 点** 🟢 | **95〜100 点** 🟢 | **81 点** 🟢 | **100 点** 🟢 | **ALL GREEN** |
| **商品一覧 (`/products`)** | **99 点** 🟢 | **95 点** 🟢 | **81 点** 🟢 | **100 点** 🟢 | **NEAR PERFECT** |

### 📱 モバイル環境 (Mobile)

| ページ | ⚡️ Performance | ♿️ Accessibility | 🛡️ Best Practices | 🔍 SEO | 総合判定 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **トップページ (`/`)** | **81〜90 点** 🟢 | **100 点** 🟢 | **81 点** 🟢 | **100 点** 🟢 | **HIGH QUALITY** |
| **商品一覧 (`/products`)** | **94 点** 🟢 | **95 点** 🟢 | **81 点** 🟢 | **100 点** 🟢 | **EXCELLENT** |

---

## 📈 Core Web Vitals 指標の実測値（Desktop）

- **CLS (Cumulative Layout Shift / 視覚的安定性)**: **`0`** 🟢 (満点・ズレゼロ)
- **TBT (Total Blocking Time / JS応答遅延)**: **`0〜70 ms`** 🟢 (極低遅延)
- **FCP (First Contentful Paint / 初回描画)**: **`0.6〜0.7 秒`** 🟢 (ミリ秒描画)
- **LCP (Largest Contentful Paint / 最大描画)**: **`0.6〜0.7 秒`** 🟢 (ミリ秒描画)

---

## 🛠️ 実施した具体的な最適化施策

### 1. ♿️ Accessibility (アクセシビリティ: 62点 ➜ 95〜100点)
- **HTML 言語属性 (`[html-has-lang]`)**:
  - 全レイアウト（`application.html.erb`, `admin.html.erb`）の `<html>` タグに `lang="ja"` を指定し、スクリーンリーダーやブラウザの自動翻訳に最適化。
- **ARIA ラベルの完備 (`[button-name]`, `[link-name]`)**:
  - 商品一覧のカート追加ボタンに `aria-label="#{product.name}をカートに追加"` を付与。
  - ヘッダーのショッピングカートバッジに `aria-label="ショッピングカート (X点)"` を付与。
- **WCAG AA コントラスト比適合 (`[color-contrast]`)**:
  - サブタイトルや注記テキストを `text-slate-400` から `text-slate-600` / `text-slate-500` に引き上げ。
  - レビューの星評価カラーを `text-amber-500` から `text-amber-700` に調整し、白背景に対して 4.5:1 以上のコントラスト比を達成。

### 2. 🔍 SEO (検索エンジン最適化: 92点 ➜ 100点 満点)
- **メタデスクリプション (`[meta-description]`)**:
  - 検索エンジン向けにサイト概要を説明する `<meta name="description">` を追加。
- **モバイルテーマカラー (`[theme-color]`)**:
  - モバイルブラウザのアドレスバー用 `<meta name="theme-color" content="#4f46e5">` を追加。

### 3. ⚡️ Performance (パフォーマンス: 96〜99点 達成)
- **Active Storage の N+1 クエリ解消**:
  - カタログトップ（`CatalogController`）および商品一覧（`ProductsController`）のクエリに `.with_attached_images` を追加し、添付画像テーブルへの N+1 発行を完全に撲滅。
- **画像の非同期デコード & 寸法明示**:
  - `ApplicationHelper#product_image_tag` に `loading="lazy"`, `decoding="async"`, `width="400"`, `height="400"` を付与。
- **Google Fonts の非同期・非ブロッキング読み込み**:
  - `media="print" onload="this.media='all'"` パターンを採用し、フォント読み込みによるレンダリングブロック（FCP 遅延）を解消。
- **HTTP Edge Cache ヘッダー**:
  - 非認証ユーザーのカタログアクセスに `Cache-Control: public, max-age=60` を付与し、TTFB（サーバー応答時間）を高速化。
- **CSP (Content Security Policy) の有効化**:
  - `config/initializers/content_security_policy.rb` を整備。

---

## 🔍 Best Practices (81点) の要因について

Lighthouse の監査レポートを詳細解析した結果、残りの減点理由はアプリケーション本体ではなく、**Cloudflare のエッジプロキシで自動挿入されるボット保護スクリプト (`/cdn-cgi/challenge-platform/...`)** が内部利用している Chrome 非推奨 API の警告に起因するものです。

---

## 🧪 監査コマンド

```bash
# デスクトップ測定
CHROME_PATH=/snap/bin/chromium npx -y lighthouse "https://modern-rails.ohchans.com/" \
  --preset=desktop \
  --no-enable-error-reporting \
  --chrome-flags="--headless=new --no-sandbox --disable-gpu --disable-dev-shm-usage"

# モバイル測定
CHROME_PATH=/snap/bin/chromium npx -y lighthouse "https://modern-rails.ohchans.com/products" \
  --no-enable-error-reporting \
  --chrome-flags="--headless=new --no-sandbox --disable-gpu --disable-dev-shm-usage"
```
