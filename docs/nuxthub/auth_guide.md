# 🔐 暗号化 Cookie (Sealed Session) によるエッジ認証ガイド

このドキュメントでは、**Nuxt 4 + Cloudflare Workers** 環境におけるモダンな認証アプローチである **「暗号化 Cookie（Sealed Session）」** の仕組み、従来の Redis / JWT 方式との違い、メリット・デメリット、および実装方法について詳しく解説します。

---

## 📑 目次

1. [暗号化 Cookie (Sealed Session) とは](#1-暗号化-cookie-sealed-session-とは)
2. [従来の方式 (Redis / JWT) との比較](#2-従来の方式-redis--jwt-との比較)
3. [なぜエッジ・サーバーレスで暗号化 Cookie が選ばれるのか](#3-なぜエッジサーバーレスで暗号化-cookie-が選ばれるのか)
4. [メリットとデメリット・注意点](#4-メリットとデメリット注意点)
5. [Nuxt 4 での実装 (`nuxt-auth-utils`)](#5-nuxt-4-での実装-nuxt-auth-utils)
6. [本番運用の設定 (`NUXT_SESSION_PASSWORD`)](#6-本番運用の設定-nuxt_session_password)

---

## 1. 暗号化 Cookie (Sealed Session) とは

暗号化 Cookie とは、**ユーザーのセッション情報（ユーザーID、ロール、メールアドレスなど）そのものをサーバーの秘密鍵で AES-256-GCM 等で暗号化し、ブラウザの `HttpOnly` Cookie に直接保存する** ステートレスなセッション管理方式です。

```text
【従来の Redis / DB 方式 (Stateful)】
ブラウザ ──[ session_id: "abc-123" ]──▶ サーバー ──▶ Redis/DB に問い合わせてユーザー情報を取得
                                                    (※毎リクエストでネットワーク通信が発生)

【暗号化 Cookie 方式 (Stateless)】
ブラウザ ──[ session: "密文:9f8a2c... (AES暗号化)" ]──▶ エッジサーバー (Cloudflare Workers)
                                                        (※サーバーの秘密鍵で復号するだけ。通信 0 回・0ms！)
```

### 🔒 セキュリティ特性

- **`HttpOnly`**: JavaScript からアクセス不可（XSS によるトークン奪取を防止）。
- **`Secure`**: HTTPS 通信時のみ送信。
- **`SameSite=Lax`**: 外部サイトからの CSRF 攻撃をブラウザレベルで自動防御。
- **AES 暗号化 & 署名**: クライアント側からは**中身の閲覧も改ざんも一切不可能**。

---

## 2. 従来の方式 (Redis / JWT) との比較

| 比較項目              | 従来の Redis セッション          | 一般的な JWT (LocalStorage)      | 🔐 暗号化 Cookie (Sealed Cookie)   |
| :-------------------- | :------------------------------- | :------------------------------- | :--------------------------------- |
| **整合性 / 判定速度** | 強整合性 (DB/Redis通信あり)      | 0 ms (署名検証のみ)              | **0 ms (エッジで復号のみ)**        |
| **中身の秘匿性**      | サーバー側のみ保持               | ❌ **誰でも読める** (Base64)     | ⭕ **完全に暗号化** (サーバーのみ) |
| **保存場所**          | サーバー側 (Redis)               | ブラウザの `localStorage`        | **`HttpOnly` Cookie**              |
| **XSS 耐性**          | ⭕ 高い                          | ❌ **極めて脆弱** (JSで盗まれる) | ⭕ **極めて高い** (JSアクセス不可) |
| **CSRF 耐性**         | 対策が必要                       | ⭕ Authorization ヘッダー        | ⭕ **`SameSite` 属性で自動防御**   |
| **インフラ運用**      | Redis サーバーの構築・監視が必要 | 不要 (ステートレス)              | **不要 (0 円・完全サーバーレス)**  |

---

## 3. なぜエッジ・サーバーレスで暗号化 Cookie が選ばれるのか

Cloudflare Workers やエッジコンピューティング環境において、暗号化 Cookie は以下の決定的な優位性を持ちます：

1. **世界 300 箇所以上のエッジでレイテンシ 0 ms**:
   遠くのオリジンサーバーや Redis に通信しに行くことなく、ユーザーの最寄りエッジで即座に復号・認証チェックが完了します。
2. **サーバーレス特有の「コネクション枯渇問題」を回避**:
   アクセスが急増して Workers インスタンスが 1 万個立ち上がっても、Redis の接続プールがパンクするリスクが構造上存在しません。
3. **Cloudflare KV の結果整合性遅延の影響を受けない**:
   KV のような分散伝播遅延（最大60秒）を待つ必要がなく、ログイン直後のリダイレクト先画面でも即座にログイン済みとして認識されます。

---

## 4. メリットとデメリット・注意点

### ⭕ メリット

- **高速性**: DB / Redis アクセス不要で即時認証。
- **ゼロ運用コスト**: セッション用インフラの費用・障害監視が不要。
- **高可用性 (SPOF なし)**: 単一障害点となる Redis が存在しないため、インフラ障害に強い。

### ❌ デメリットと対策

- **容量制限 (4 KB 制限)**:
  - Cookie には最大 4 KB までしか入りません。
  - **対策**: セッションには `{ id, email, role }` などの最小限の識別子のみを保存し、巨大なプロフィールデータなどは保存しない。
- **サーバー側からの即時強制ログアウトが難しい (最大の特徴)**:
  - クライアントが有効期限内の Cookie を持っている限りアクセスできてしまいます。
  - **対策 1 (トークンバージョン)**: ユーザーテーブル（D1）に `token_version` カラムを持たせ、パスワード変更時にカウントアップして Cookie 内のバージョンと突合する。
  - **対策 2 (KV ブラックリスト)**: ログアウトされたセッション ID のみを短期間（TTL付きで）Cloudflare KV に保存し、エッジで弾く。

---

## 5. Nuxt 4 での実装 (`nuxt-auth-utils`)

当リポジトリでは Nuxt 公式チーム推奨の **`nuxt-auth-utils`** を導入しています。

### ① ログイン API (`server/api/auth/login.post.ts`)

```ts
export default defineEventHandler(async (event) => {
  const body = await readBody(event);

  // 1. パスワード・ユーザーの検証 (D1 など)
  const user = await verifyUser(body.email, body.password);

  // 2. 暗号化 Cookie セッションを発行 (自動で AES 暗号化 & Set-Cookie)
  await setUserSession(event, {
    user: {
      id: user.id,
      name: user.name,
      email: user.email,
      role: user.role,
      loggedInAt: new Date().toISOString(),
    },
  });

  return { success: true, user };
});
```

### ② ログアウト API (`server/api/auth/logout.post.ts`)

```ts
export default defineEventHandler(async (event) => {
  await clearUserSession(event);
  return { success: true };
});
```

### ③ 保護された API (`server/api/auth/protected.get.ts`)

```ts
export default defineEventHandler(async (event) => {
  // エッジで Cookie を即座に復号 (0ms)
  const session = await getUserSession(event);

  if (!session.user) {
    throw createError({ statusCode: 401, statusMessage: "Unauthorized" });
  }

  return { data: "Secret Data for " + session.user.name };
});
```

### ④ フロントエンド Vue コンポーネント (`app/pages/index.vue`)

```vue
<script setup lang="ts">
// Composable によるリアクティブなセッション管理
const { loggedIn, user, clear, fetch } = useUserSession()

async function login() {
  await $fetch('/api/auth/login', { method: 'POST', body: { ... } })
  await fetch() // セッション状態を更新
}

async function logout() {
  await $fetch('/api/auth/logout', { method: 'POST' })
  await clear() // セッション状態をクリア
}
</script>
```

---

## 6. 本番運用の設定 (`NUXT_SESSION_PASSWORD`)

暗号化 Cookie の暗号鍵として、**32文字以上のセキュアなランダム文字列** を環境変数 `NUXT_SESSION_PASSWORD` に設定します。

```bash
# 暗号鍵の生成例 (ターミナルで実行)
openssl rand -hex 32
```

### Cloudflare Pages への環境変数設定

Cloudflare ダッシュボード（**「Workers & Pages」→ 対象プロジェクト →「Settings」→「Environment variables」**）にて、以下のシークレットを登録します：

- **Variable name**: `NUXT_SESSION_PASSWORD`
- **Value**: (生成した32文字以上のランダム文字列)
- **Type**: `Secret`
