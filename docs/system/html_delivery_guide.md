# 生 HTML ドキュメント配置 & 自動目次生成ガイド

本ドキュメントは、Markdown 形式以外にも生の HTML ファイル（独立した Web レポート、データ分析ダッシュボード、自作ツールの画面等）を `docs-repo` 内で安全・簡単に配信し、目次インデックスを全自動生成・更新するための構成仕様と運用手順についてまとめたものです。

---

## 1. ディレクトリ構造仕様

生の HTML ファイルは **`docs/html/`** 配下に自由に配置・サブフォルダ構成を掘って格納します。

```text
docs-repo/
├── docs/
│   ├── index.md
│   ├── system/                  # システムドキュメント群
│   └── html/                    # 生 HTML 配置ディレクトリ (新規)
│       ├── index.md             # 自動生成される目次インデックス
│       ├── sample_report.html   # HTMLファイル例 1
│       └── analytics/
│           └── dashboard.html   # HTMLファイル例 2 (サブフォルダ可)
├── scripts/
│   └── generate_html_index.py  # 自動目次生成スクリプト
└── mkdocs.yml
```

---

## 2. 自動目次 & 左メニューツリー生成の仕組み (`scripts/generate_html_index.py`)

`docs/html/` 配下のすべての `.html` ファイルを再帰的に走査し、各ファイル内の `<title>` または `<h1>` の見出しを自動抽出して、以下の 2 つを全自動作成・更新します：

1. **目次インデックスページ (`docs/html/index.md`)**: 全 HTML リンク付き一覧 Markdown。
2. **左サイドバーツリー (`mkdocs.yml`)**: 左メニューの `HTMLコンテンツ (Raw HTML)` の配下にサブツリーとして各 HTML ページをタイトル付きで直接展開。

### 実行タイミング
- **ローカル開発時**: `python3 scripts/generate_html_index.py` を実行。
- **CI/CD 自動連携**: GitHub Actions (`deploy.yml`) の `mkdocs build` 直前に自動実行されるため、**HTML ファイルを追加して `git push` するだけで、左サイドバーメニューおよび目次ページが全自動で更新・配信**されます。

---

## 3. アクセス URL & 閲覧の仕組み

- **目次インデックスページ**:
  `https://docs.ohchans.com/html/`
- **各 HTML ファイル直アクセス**:
  - `https://docs.ohchans.com/html/sample_report.html`
  - `https://docs.ohchans.com/html/analytics/dashboard.html`

※ MkDocs は `.html` ファイルを処理せずそのまま成果物 (`site/html/...`) へPass-throughコピーするため、HTML ファイル独自の `<style>`, `<script>`, 外部ライブラリが 100% 崩れずに動作します。
