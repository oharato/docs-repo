# Mermaid ダイアグラムの自動検証・リンター導入ガイド

本ドキュメントは、Markdown 内の Mermaid.js ダイアグラムにおける構文エラー（特殊文字のエスケープ漏れや構文不備など）を自動検出し、ローカル開発および CI/CD パイプライン上で事前に防ぐための主要ツールと設定手順についてまとめたものです。

---

## 1. 主要な Mermaid リンター・検証ツール

### 1.1 `@mermaid-js/mermaid-cli` (公式 CLI)
Mermaid 公式が提供する CLI ツール（`mmdc`）です。ダイアグラムの構文解析や SVG/PNG 生成を行います。

- **コマンド例**:
  ```bash
  npx @mermaid-js/mermaid-cli -i diagram.mmd -o output.svg
  ```
  ※ 構文エラーがある場合、エラー詳細を出力してステータスコード `1` で異常終了するため、スクリプトや CI で検知できます。

### 1.2 `markdownlint` + `markdownlint-rule-mermaid` (推奨)
Markdown 全般の標準リンター `markdownlint` に Mermaid 構文検証ルールを追加するプラグインです。

- **特徴**:
  - Markdown ファイル内の ` ```mermaid ` ブロックを自動検出・抽出し、全図の文法チェックを一括実行します。
- **インストール手順**:
  ```bash
  npm install -D markdownlint-cli markdownlint-rule-mermaid
  ```
- **実行手順**:
  ```bash
  npx markdownlint --rules markdownlint-rule-mermaid "docs/**/*.md"
  ```

### 1.3 `mermaid-linter` (CLI)
Markdown ファイル内の Mermaid ブロック検証に特化した軽量 CLI です。

- **実行例**:
  ```bash
  npx mermaid-linter "docs/**/*.md"
  ```

---

## 2. ローカル開発環境 (VS Code 拡張機能)

リアルタイムに編集中のエラーを検知するために、以下のエディタ拡張の導入を推奨します。

- **[Mermaid Preview](https://marketplace.visualstudio.com/items?itemName=vsciot-vscode.vscode-mermaid-preview)**
  - サイドバーまたは分割タブでプレビューを即座に描画し、文法エラー時に赤波線とログを表示。
- **[Mermaid Chart](https://marketplace.visualstudio.com/items?itemName=MermaidChart.vscode-mermaid-chart)**
  - 公式のリアルタイム・バリデーション & 編集支援プラグイン。

---

## 3. 陥りやすい構文エラーの注意点

1. **特殊文字のダブルクォート囲み漏れ**:
   - ノードテキスト内にコロン (`:`), スラッシュ (`/`), アンパサンド (`&`), 括弧 (`()`), プラス (`+`) が含まれる場合、ダブルクォートで囲まないと構文エラーになります。
   - ❌ 誤り: `A[開発者: Git Push] --> B[GitHub / GitLab]`
   - ⭕ 修正: `A["開発者: Git Push"] --> B["GitHub / GitLab"]`

2. **外部 CDN との二重読み込み**:
   - MkDocs Material などのテーマで `pymdownx.superfences` が有効な場合、外部 JS を追加ロードすると二重初期化が発生します。

---

## 4. GitHub Actions (CI/CD) への組み込み例

`docs-repo/.github/workflows/deploy.yml` の MkDocs ビルド前に Mermaid 検証ステップを追加することで、壊れた図のデプロイを自動的に未然防止できます。

```yaml
      - name: Validate Mermaid Diagrams
        run: |
          npx -y mermaid-linter "docs/**/*.md"
```
