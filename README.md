# Docs Repository (Markdownコンテンツ・GitHub Pages自動デプロイ)

本リポジトリは、ドキュメントのソースコード (Markdown) と MkDocs 設定、および GitHub Pages への自動デプロイ用 GitHub Actions ワークフローを管理します。

---

## 📁 ディレクトリ構造

```text
docs-repo/
├── .github/
│   └── workflows/
│       └── deploy.yml          # GitHub Pages 自動デプロイ CI/CD ワークフロー
├── docs/                        # Markdownドキュメント群
│   ├── index.md                # メインページ
│   ├── architecture.md         # システム構成解説
│   ├── extra.css               # カスタムスタイル
│   └── extra.js                # カスタムスクリプト
├── mkdocs.yml                  # MkDocs (Material theme) 設定
└── README.md                   # 本ドキュメント
```

---

## 💻 開発・ローカルプレビュー手順

### 1. 前提条件
Python 3.10 以上がインストールされていることを確認します。

### 2. パッケージのインストールとコミット前検証フックの有効化
```bash
# `uv.lock` に固定された依存関係をインストール
uv sync --frozen

# 別PC/初回クローン時にローカルコミット前検証フックを有効化
git config core.hooksPath .githooks
```

### 3. ローカルサーバーの起動
```bash
uv run mkdocs serve
```
起動後、ブラウザで [http://127.0.0.1:8000](http://127.0.0.1:8000) にアクセスしてプレビューを確認します。ファイル更新時はリアルタイムで自動リロードされます。

---

## 🚀 GitHub Pages 設定・デプロイ仕様

1. **GitHub リポジトリ設定**:
   - リポジトリの **Settings > Pages** を開きます。
   - **Build and deployment > Source** で `GitHub Actions` を選択します。
2. **自動デプロイ**:
   - `main` ブランチへのコミット Push 時にワークフロー (`.github/workflows/deploy.yml`) が自動実行されます。
   - `uv.lock` による依存関係インストール、生 HTML インデックス自動抽出 (`scripts/generate_html_index.py`)、`mkdocs build --strict` を実行後、`actions/deploy-pages` 経由で GitHub Pages へ公開されます。
