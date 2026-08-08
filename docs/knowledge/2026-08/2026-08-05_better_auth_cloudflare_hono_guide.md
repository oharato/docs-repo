# TypeScript 認証ライブラリ選定 & Cloudflare + Hono + Better Auth 実装ガイド

**調査日**: 2026年8月5日  
**概要**: TypeScript環境における認証ライブラリのトレンド分析、Better Auth の選定理由、および Cloudflare Workers / D1 / Hono アーキテクチャでの具体的な実装手順。

---

## 1. 認証ライブラリ選定比較 (2026年時点)

自前データベース（セルフホスト）でユーザー情報やセッションを管理する TypeScript プロジェクトにおいて、現在最も推奨される認証ライブラリは **Better Auth** です。

| ライブラリ / サービス | 方式 | 型安全性 | フレームワーク非依存 | 評価・使い分けの目安 |
| :--- | :--- | :--- | :--- | :--- |
| **Better Auth** *(推奨)* | OSS / セルフホスト | ⭐⭐⭐ | ◯ (Next/Nuxt/Hono等) | **2026年の最推奨選択肢**。TypeScriptファースト、プラグイン機能（Passkey, 2FA, 組織等）が豊富。 |
| **Auth.js (NextAuth.js)** | OSS / セルフホスト | ⭐⭐ | △ (Next.js中心) | 巨体なコミュニティと圧倒的実績。Next.js標準エコシステム重視の場合に選ばれる。 |
| **Clerk** | Managed SaaS | ⭐⭐⭐ | ◯ | ログインUIも含めて即時構築したいスタートアップ向け（運用コスト・ベンダーロックインに注意）。 |
| **Lucia Auth** | *(非推薦)* | - | - | 2024年にライブラリとしての更新を停止。学習リソース・設計パターン集に移行したため新規採用は非推奨。 |

---

## 2. Better Auth の主な特徴・選定メリット

1. **完全な TypeScript ファースト**: サーバー/クライアント間の型推論が完璧で、プラグイン追加時も型が自動追従。
2. **ランタイム & DB 非依存**: Node.js だけでなく Cloudflare Workers (Edge), Deno, Bun でも動作。D1, Prisma, Drizzle, Kysely 等に対応。
3. **強力なプラグイン機能**: Passkeys (WebAuthn), 2FA, Multi-tenancy (組織・チーム管理), RBAC などが数行で有効化可能。
4. **脱ベンダーロックイン**: すべてのデータを自前DBに保存。

---

## 3. Cloudflare Workers + Hono + D1 + Better Auth 実装仕様

### 3.1 D1 データベースのバインド (`wrangler.json`)

```json
{
  "name": "my-hono-app",
  "main": "src/index.ts",
  "compatibility_date": "2024-09-23",
  "d1_databases": [
    {
      "binding": "DB",
      "database_name": "my-auth-db",
      "database_id": "YOUR_D1_DATABASE_ID"
    }
  ]
}
```

---

### 3.2 サーバー側実装

#### ① 認証の設定 (`src/auth.ts`)

```typescript
import { betterAuth } from "better-auth";
import { d1Adapter } from "better-auth/adapters/d1";

export type Env = {
  Bindings: {
    DB: D1Database;
    BETTER_AUTH_SECRET: string;
    GITHUB_CLIENT_ID: string;
    GITHUB_CLIENT_SECRET: string;
  };
};

export const getAuth = (env: Env["Bindings"]) => {
  return betterAuth({
    database: d1Adapter(env.DB, {
      provider: "sqlite",
    }),
    secret: env.BETTER_AUTH_SECRET,
    baseURL: "https://your-domain.workers.dev",
    emailAndPassword: {
      enabled: true,
    },
    socialProviders: {
      github: {
        clientId: env.GITHUB_CLIENT_ID,
        clientSecret: env.GITHUB_CLIENT_SECRET,
      },
    },
  });
};
```

#### ② Hono API ルート定義 (`src/index.ts`)

```typescript
import { Hono } from "hono";
import { cors } from "hono/cors";
import { getAuth, type Env } from "./auth";

const app = new Hono<Env>();

// CORSミドルウェア（フロントエンド分離時に必須）
app.use(
  "/api/auth/*",
  cors({
    origin: ["http://localhost:5173", "https://your-frontend.pages.dev"],
    allowHeaders: ["Content-Type", "Authorization"],
    allowMethods: ["POST", "GET", "OPTIONS"],
    credentials: true,
  })
);

// Better Auth ハンドラーのエンドポイントマウント
app.on(["POST", "GET"], "/api/auth/*", (c) => {
  const auth = getAuth(c.env);
  return auth.handler(c.req.raw);
});

// 認証済み保護ルートの例
app.get("/api/me", async (c) => {
  const auth = getAuth(c.env);
  const session = await auth.api.getSession({
    headers: c.req.raw.headers,
  });

  if (!session) {
    return c.json({ error: "Unauthorized" }, 401);
  }

  return c.json({ user: session.user });
});

export default app;
```

---

### 3.3 D1 データベースのマイグレーション

Better Auth CLI を使用して D1 用の SQL を自動生成し適用します。

```bash
# 1. マイグレーションSQLの生成
npx @better-auth/cli generate --config ./src/auth.ts

# 2. ローカル環境への適用
npx wrangler d1 execute my-auth-db --local --file=./better-auth_migrations/0000_xxx.sql

# 3. 本番環境への適用
npx wrangler d1 execute my-auth-db --remote --file=./better-auth_migrations/0000_xxx.sql
```

---

### 3.4 クライアント側実装 (`src/auth-client.ts`)

```typescript
import { createAuthClient } from "better-auth/client";

export const authClient = createAuthClient({
  baseURL: "https://your-domain.workers.dev",
});

// メールサインイン
export async function login(email: string, password: string) {
  const { data, error } = await authClient.signIn.email({
    email,
    password,
  });
  return { data, error };
}

// セッション状態の確認
export async function getSession() {
  return await authClient.getSession();
}
```
