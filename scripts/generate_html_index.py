#!/usr/bin/env python3
import os
import re
from pathlib import Path

HTML_DIR = Path("docs/html")
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
    """mkdocs.yml 内の HTML セクションを直接 HTML ファイルのみの木構造形式で動的更新"""
    if not MKDOCS_YML.exists():
        return

    content = MKDOCS_YML.read_text(encoding="utf-8")
    
    tree = build_tree_structure(html_files)
    
    nav_lines = ["  - HTMLコンテンツ (Raw HTML):"]
    
    yaml_tree_lines = render_tree_to_yaml(tree, indent_level=6)
    if yaml_tree_lines:
        nav_lines.extend(yaml_tree_lines)
    else:
        nav_lines.append("      - (なし): index.md")

    new_section = "\n".join(nav_lines)

    #  "  - HTMLコンテンツ (Raw HTML): ..." セクションを全置換
    pattern = r"  \- HTMLコンテンツ \(Raw HTML\):.*?(?=\n  \- |\Z)"
    if re.search(pattern, content, re.DOTALL):
        updated_content = re.sub(pattern, new_section, content, flags=re.DOTALL)
        MKDOCS_YML.write_text(updated_content, encoding="utf-8")
        print("✅ mkdocs.yml の左ナビゲーションツリー（純粋HTMLのみ）を更新しました。")

def main():
    if not HTML_DIR.exists():
        print(f"Directory {HTML_DIR} does not exist. Creating...")
        HTML_DIR.mkdir(parents=True, exist_ok=True)

    # index.md ファイルが存在すれば削除する
    index_md = HTML_DIR / "index.md"
    if index_md.exists():
        index_md.unlink()
        print(f"🗑️ 不要な目次インデックスファイルを削除しました: {index_md}")

    html_files = sorted(HTML_DIR.glob("**/*.html"))

    update_mkdocs_nav(html_files)

if __name__ == "__main__":
    main()
