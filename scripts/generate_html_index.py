#!/usr/bin/env python3
import os
import re
from pathlib import Path

HTML_DIR = Path("docs/html")
INDEX_FILE = HTML_DIR / "index.md"
MKDOCS_YML = Path("mkdocs.yml")

def extract_title(html_path: Path) -> str:
    """HTMLファイルから <title> または <h1> のテキストを抽出"""
    try:
        content = html_path.read_text(encoding="utf-8", errors="ignore")
        title_match = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE | re.DOTALL)
        if title_match and title_match.group(1).strip():
            return title_match.group(1).strip()
        h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', content, re.IGNORECASE | re.DOTALL)
        if h1_match and h1_match.group(1).strip():
            return re.sub(r'<[^>]+>', '', h1_match.group(1)).strip()
    except Exception as e:
        print(f"Warning: Could not read {html_path}: {e}")
    
    return html_path.name

def build_tree_structure(html_files):
    """ファイルパス群から再帰的な辞書ツリーを構築"""
    tree = {"_files": []}

    for html_file in html_files:
        rel_path = html_file.relative_to(HTML_DIR)
        parts = rel_path.parts
        
        current = tree
        for part in parts[:-1]: # ディレクトリ部分
            if part not in current:
                current[part] = {"_files": []}
            current = current[part]
        
        # 最深部のファイル
        title = extract_title(html_file)
        full_rel_path = html_file.relative_to(Path("docs"))
        current["_files"].append((title, str(full_rel_path)))

    return tree

def render_tree_to_yaml(tree, indent_level=2):
    """辞書ツリーを MkDocs nav YAML のネスト文字列に変換"""
    lines = []
    indent = " " * indent_level

    # 直下のファイルを配置
    for title, path in tree.get("_files", []):
        lines.append(f"{indent}- {title}: {path}")

    # サブディレクトリを順に処理
    for key in sorted(tree.keys()):
        if key == "_files":
            continue
        lines.append(f"{indent}- {key}:")
        subtree_lines = render_tree_to_yaml(tree[key], indent_level + 4)
        lines.extend(subtree_lines)

    return lines

def update_mkdocs_nav(html_files):
    """mkdocs.yml 内の HTML セクションをサブディレクトリ階層化ツリー形式で動的更新"""
    if not MKDOCS_YML.exists():
        return

    content = MKDOCS_YML.read_text(encoding="utf-8")
    
    tree = build_tree_structure(html_files)
    
    nav_lines = [
        "  - HTMLコンテンツ (Raw HTML):",
        "      - 目次インデックス: html/index.md"
    ]
    
    yaml_tree_lines = render_tree_to_yaml(tree, indent_level=6)
    nav_lines.extend(yaml_tree_lines)

    new_section = "\n".join(nav_lines)

    #  "  - HTMLコンテンツ (Raw HTML): ..." セクションを全置換
    pattern = r"  \- HTMLコンテンツ \(Raw HTML\):.*?(?=\n  \- |\Z)"
    if re.search(pattern, content, re.DOTALL):
        updated_content = re.sub(pattern, new_section, content, flags=re.DOTALL)
        MKDOCS_YML.write_text(updated_content, encoding="utf-8")
        print("✅ mkdocs.yml の左ナビゲーションツリーを階層化更新しました。")

def main():
    if not HTML_DIR.exists():
        print(f"Directory {HTML_DIR} does not exist. Creating...")
        HTML_DIR.mkdir(parents=True, exist_ok=True)

    html_files = sorted(HTML_DIR.glob("**/*.html"))

    lines = [
        "# 📁 HTMLドキュメント・レポート一覧",
        "",
        "本セクションでは、`docs/html/` 配下に配置された生の HTML ドキュメント・レポート・各種ダッシュボードの一覧を自動集約しています。",
        ""
    ]

    if not html_files:
        lines.append("_現在配置されている HTML ドキュメントはありません。_")
    else:
        for html_file in html_files:
            rel_path = html_file.relative_to(HTML_DIR)
            title = extract_title(html_file)
            lines.append(f"- [{title}]({rel_path}) `({rel_path})`")

    INDEX_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"✅ HTML 目次ページを自動更新しました: {INDEX_FILE} (検出ファイル数: {len(html_files)})")

    update_mkdocs_nav(html_files)

if __name__ == "__main__":
    main()
