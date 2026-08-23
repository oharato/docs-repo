# 📘 NuxtHub × Cloudflare チュートリアル & 開発ガイド

このチュートリアルでは、**Nuxt 4 + NuxtHub + TypeScript × Cloudflare Workers** 環境で Ruby on Rails のような「設定不要・オールインワン・型安全」な開発体験を実践し、**Pulumi (TypeScript)** を使ったインフラ構築とデプロイまでの全工程を解説します。

---

## 📑 目次

1. [NuxtHub のセットアップと設定](#1-nuxthub-のセットアップと設定)
2. [LAN からの接続設定 (0.0.0.0 リッスン)](#2-lan-からの接続設定-0000-リッスン)
3. [データベース (D1 + Drizzle ORM) を使う](#3-データベース-d1--drizzle-orm-を使う)
4. [KV (Key-Value Store) を使う](#4-kv-key-value-store-を使う)
5. [Blob (R2 オブジェクトストレージ) を使う](#5-blob-r2-オブジェクトストレージ-を使う)
6. [エッジキャッシュ (Cached Handler) を使う](#6-エッジキャッシュ-cached-handler-を使う)
7. [リアルタイム Server-Sent Events (SSE) を使う](#7-リアルタイム-server-sent-events-sse-を使う)
8. [日本語 PDF 領収書生成 (pdf-lib) を使う](#8-日本語-pdf-領収書生成-pdf-lib-を使う)
9. [Nuxt DevTools (NuxtHub GUI) の活用](#9-nuxt-devtools-nuxthub-gui-の活用)
10. [Pulumi によるインフラ構築と本番デプロイ](#10-pulumi-によるインフラ構築と本番デプロイ)

---

## 1. NuxtHub のセットアップと設定

NuxtHub の各機能は `nuxt.config.ts` で有効化するだけで、Cloudflare 側のバインディングやローカルエミュレータ（workerd / SQLite）が自動設定されます。

```ts
// nuxt.config.ts
export default defineNuxtConfig({
  modules: ["@nuxthub/core", "nuxt-auth-utils"],
  hub: {
    db: "sqlite", // D1 (SQLite)
    kv: true, // Workers KV
    blob: true, // R2 Storage
    cache: true, // Edge Nitro Cache
  },
});
```

---

## 2. LAN からの接続設定 (0.0.0.0 リッスン)

別PCやスマートフォンなどの同一LAN内の端末からアクセスできるように、`devServer` を設定しています。

```ts
// nuxt.config.ts
export default defineNuxtConfig({
  devServer: {
    host: "0.0.0.0",
    port: 3000,
  },
});
```

---

## 3. データベース (D1 + Drizzle ORM) を使う

Rails の `ActiveRecord` に相当する機能です。TypeScript でスキーマを定義し、型安全にクエリを実行します。

### ① スキーマの定義 (`server/db/schema.sqlite.ts`)

```ts
import { sqliteTable, text, integer } from "drizzle-orm/sqlite-core";

export const products = sqliteTable("products", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  name: text("name").notNull(),
  slug: text("slug").notNull().unique(),
  price: integer("price").notNull(),
  stockQuantity: integer("stock_quantity").notNull().default(0),
  createdAt: integer("created_at", { mode: "timestamp" })
    .notNull()
    .$defaultFn(() => new Date()),
});
```

### ② ヘルパー関数の作成 (`server/utils/drizzle.ts`)

```ts
import { db, schema } from "hub:db";

export { sql, eq, and, or, desc, asc } from "drizzle-orm";
export const tables = schema;

export function useDrizzle() {
  return db;
}
```

### ③ マイグレーションの管理

```bash
# スキーマ変更からマイグレーション SQL を自動生成
pnpm db:generate

# 本番 Cloudflare D1 へのマイグレーション適用 (Wrangler 自動管理)
pnpm db:migrate:prod
```

---

## 4. KV (Key-Value Store) を使う

Rails の `Rails.cache` や `Solid Cache` のように、低レイテンシでグローバルに伝播する Key-Value データを扱えます。

```ts
import { kv } from "hub:kv";

// ショッピングカートの保存 (TTL: 7日間)
await kv.set(`cart:guest_${guestId}`, cartData, { ttl: 60 * 60 * 24 * 7 });

// 取得
const cart = await kv.get(`cart:guest_${guestId}`);

// 削除
await kv.del(`cart:guest_${guestId}`);
```

---

## 5. Blob (R2 オブジェクトストレージ) を使う

Rails の `ActiveStorage` に相当する機能です。S3互換の Cloudflare R2 ストレージへファイルのアップロードや配信を行います。

```ts
import { blob } from "hub:blob";

// アップロード
await blob.put(`products/${productId}/image.svg`, svgContent, {
  contentType: "image/svg+xml",
});

// ファイルの直接配信 (server/api/blob/[pathname].get.ts)
export default defineEventHandler(async (event) => {
  const pathname = getRouterParam(event, "pathname");
  setHeader(event, "Cache-Control", "public, max-age=31536000, immutable");
  return blob.serve(event, decodeURIComponent(pathname!));
});
```

---

## 6. エッジキャッシュ (Cached Handler) を使う

関数のレスポンスを Cloudflare エッジネットワーク上にキャッシュし、超高速な応答と DB 負荷ゼロを実現します。

```ts
// server/api/products/index.get.ts
export default defineCachedEventHandler(
  async () => {
    const db = useDrizzle();
    return await db.select().from(tables.products);
  },
  {
    maxAge: 60, // 60秒間エッジキャッシュ
    name: "products-list",
  },
);
```

---

## 7. リアルタイム Server-Sent Events (SSE) を使う

Cloudflare Workers エッジ環境に完全対応した Web Standard `TransformStream` によるリアルタイムイベント配信です。

```ts
// server/api/realtime/inventory.get.ts
export default defineEventHandler((event) => {
  const { readable, writable } = new TransformStream();
  const writer = writable.getWriter();
  const encoder = new TextEncoder();

  // 初期接続イベント
  writer.write(encoder.encode(`data: ${JSON.stringify({ type: "connected" })}\n\n`));

  const unsubscribe = subscribeInventory((data) => {
    writer.write(encoder.encode(`data: ${JSON.stringify(data)}\n\n`));
  });

  return new Response(readable, {
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    },
  });
});
```

---

## 8. 日本語 PDF 領収書生成 (pdf-lib) を使う

Cloudflare Workers 上で Google Noto Sans JP を完全埋め込みし、文字化けのない美しい A4 領収書 PDF をバイナリ生成して R2 に自動保管します。

```ts
// server/utils/pdf.ts
import { PDFDocument } from "pdf-lib";
import fontkit from "@pdf-lib/fontkit";

export async function generateOrderReceiptPdf(orderData: OrderReceiptData): Promise<Uint8Array> {
  const pdfDoc = await PDFDocument.create();
  pdfDoc.registerFontkit(fontkit);

  const fontBytes = await useStorage("assets:server").getItemRaw("fonts/NotoSansJP.ttf");
  const customFont = await pdfDoc.embedFont(fontBytes);

  const page = pdfDoc.addPage([595.28, 841.89]);
  // 日本語テキストの描画
  return await pdfDoc.save();
}
```

---

## 9. Nuxt DevTools (NuxtHub GUI) の活用

NuxtHub の管理 GUI は **Nuxt DevTools** に統合されています。

1. ブラウザで [http://localhost:3000](http://localhost:3000) を開きます。
2. ショートカット `Shift + Alt + D` を押します。
3. サイドメニューの **「Hub」** タブから、D1 データベース、KV ストア、Blob ストレージを直接閲覧・編集できます。

---

## 10. Pulumi によるインフラ構築と本番デプロイ

### ① Pulumi で Cloudflare インフラを作成

```bash
# 事前確認
pnpm infra:preview

# 作成・適用
pnpm infra:apply
```

### ② `wrangler.toml` の設定

```toml
name = "try-nuxthub"
compatibility_date = "2025-03-01"
pages_build_output_dir = "dist"

[[d1_databases]]
binding = "DB"
database_name = "nuxthub-cloudflare-infra-prod-d1"
database_id = "<d1DatabaseId>"
migrations_dir = "server/db/migrations/sqlite"

[[kv_namespaces]]
binding = "KV"
id = "<kvNamespaceId>"

[[r2_buckets]]
binding = "BLOB"
bucket_name = "<r2BucketName>"
```

### ③ 本番 D1 データベースへのマイグレーション適用

```bash
pnpm db:migrate:prod
```

### ④ アプリケーションのデプロイ

```bash
pnpm deploy:cf
```

GitHub リポジトリにプッシュすると、`.github/workflows/deploy.yml` により自動でマイグレーション適用・ビルド・デプロイが実行されます！
