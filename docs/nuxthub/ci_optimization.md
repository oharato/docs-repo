# CI/CD & デプロイ高速化ガイド (Nuxt 4 × Cloudflare Pages)

本プロジェクト（`try-nuxthub`）における GitHub Actions CI/CD パイプライン、ビルド、テスト、および Cloudflare Pages デプロイの高速化に関する検証経緯と適用した最適化手法のまとめです。

---

## 📊 最適化の成果とベンチマーク比較

| パイプライン構成                              | 実行時間                             | 特徴・所要時間の内訳                                                   |
| :-------------------------------------------- | :----------------------------------- | :--------------------------------------------------------------------- |
| **初期状態 (直列)**                           | **約 2分30秒**                       | `pnpm check` 内での重複ビルド、キャッシュ未設定                        |
| **Actions 最新化 + キャッシュ導入**           | **1分33秒**                          | `setup-node (cache: pnpm)` + Nuxt/Vite ビルドキャッシュ                |
| **マルチジョブ構成 (Check / Build / Deploy)** | **1分12秒**                          | 2台の VM でテストとビルドを並行実行 (ただしジョブ間オーバーヘッドあり) |
| **ubuntu-slim 検証**                          | **1分35秒**                          | 1 vCPU コンテナのため並列コンパイル処理で速度低下                      |
| **🏆 最終構成 (最適化 1ジョブ統合)**          | **【1分12秒 (実質ステップ約60秒)】** | Corepack、Vitest forks最適化、sourcemap off、単一VM完結                |

---

## 🛠 適用した最適化一覧

### 1. ランナー & CI パイプライン層 (GitHub Actions)

- **Corepack による pnpm 有効化 (16秒 ➔ 5秒)**:
  - `pnpm/action-setup` アクションのダウンロードを廃止し、Node.js 24 組み込みの `corepack enable` を利用して **0.1 秒** で pnpm を有効化。
- **pnpm ストアの自動キャッシュ**:
  - `actions/setup-node` の `cache: 'pnpm'` を利用し、グローバルストアをキャッシュ。
- **Nuxt & Vite ビルドキャッシュ**:
  - `actions/cache` により `node_modules/.cache` および `.nuxt/cache` を保存・復元。
- **不要な CI 実行のスキップ (`paths-ignore`)**:
  - `README.md`, `docs/**`, `.gitignore` などコードに関係ないドキュメント変更時は自動スキップ。
- **古い実行の自動キャンセル (`concurrency`)**:
  - 同一ブランチに連続 push された場合、古いパイプラインを自動キャンセルしてリソースと時間を節約。

```yaml
# .github/workflows/deploy.yml 抜粋
on:
  push:
    branches: [main]
    paths-ignore:
      - "README.md"
      - "docs/**"
      - ".gitignore"

concurrency:
  group: deploy-${{ github.ref }}
  cancel-in-progress: true
```

---

### 2. テスト & 品質チェック層 (Vitest / TypeScript / Oxlint)

- **3タスクのシェル並行実行**:
  - `pnpm lint` (Oxlint, 0.5s)、`pnpm typecheck` (vue-tsc, 6s)、`pnpm test` (Vitest, 19s) をバックグラウンド（`&`）で同時に走らせ、最長タスクの時間のみに集約。
- **Vitest 4 の `pool: 'forks'` & `isolate: false` 最適化**:
  - デフォルトの `threads` ワーカーオーバーヘッドを排除し、CI 環境の 2 コアに合わせた `maxForks: 2` とワーカー再利用 `isolate: false` を設定。
- **TypeScript の増分コンパイル (`incremental: true`)**:
  - `tsconfig.json` に `"incremental": true` を追加し、型チェックを高速化。

```typescript
// vitest.config.ts
export default defineVitestConfig({
  test: {
    pool: "forks",
    maxForks: process.env.CI ? 2 : undefined,
    isolate: false,
    environmentOptions: {
      nuxt: { domEnvironment: "happy-dom" },
    },
  },
});
```

---

### 3. ビルド層 (Nuxt 4 / Nitro)

- **重複ビルドの完全排除**:
  - `pnpm check` 内に含まれていた不要な `nuxt build` を削除し、デプロイ直前の `pnpm build:cf`（`NITRO_PRESET=cloudflare_pages nuxt build`）の 1 回のみに集約。
- **Sourcemap 生成 & テレメトリの無効化**:
  - CI / 本番デプロイ用に `sourcemap: { server: false, client: false }` と `telemetry: false` を設定し、ディスク I/O とコンパイル時間を削減。

```typescript
// nuxt.config.ts
export default defineNuxtConfig({
  telemetry: false,
  sourcemap: {
    server: false,
    client: false,
  },
  // ...
});
```

---

### 4. デプロイ層 (Cloudflare Pages / Wrangler)

- **ローカル Wrangler の直接実行**:
  - 毎回 npm からダウンロードが走る `npx wrangler` をやめ、`node_modules` 内のインストール済み wrangler を `pnpm deploy:cf` 経由で **0.1 秒** で直接起動。
- **Git コミットスキャンのスキップ (`--commit-dirty=true`)**:
  - CI 上での不要なコミット差分スキャン処理をスキップし、アップロードを即時開始。

```json
// package.json
{
  "scripts": {
    "build:cf": "NITRO_PRESET=cloudflare_pages nuxt build",
    "deploy:cf": "wrangler pages deploy dist --project-name=try-nuxthub --branch=main --commit-dirty=true"
  }
}
```

---

## 💡 アーキテクチャ選定の経緯（知見まとめ）

1. **なぜマルチジョブではなく 1 ジョブ構成を採用したか？**
   - 複数ジョブ（VM 分離）に分けると、ジョブ間の VM 起動待ち時間や Artifact（`dist`）のアップロード／ダウンロードで **約 25 秒のオーバーヘッド** が発生します。
   - 1 台の VM でセットアップからチェック・ビルド・デプロイまで一気に実行する方が、全体の待ち時間を最小化できます。
2. **なぜ `ubuntu-slim` は不向きだったか？**
   - `ubuntu-slim` は 1 vCPU のため、Vite ビルドや Vitest、TypeScript のようなマルチスレッド処理で計算時間が 2 倍近くに伸びてしまいます。CPU 集約型のビルドジョブには標準の `ubuntu-latest`（2 vCPU）が最適です。
