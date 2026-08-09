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

def update_mkdocs_nav(html_files):
    """mkdocs.yml 内の HTML セクションをサブツリー形式で動的更新"""
    if not MKDOCS_YML.exists():
        return

    content = MKDOCS_YML.read_text(encoding="utf-8")
    
    nav_lines = ["  - HTMLコンテンツ (Raw HTML):", "      - 目次インデックス: html/index.md"]
    for html_file in html_files:
        rel_path = html_file.relative_to(Path("docs"))
        title = extract_title(html_file)
        nav_lines.append(f"      - {title}: {rel_path}")

    new_section = "\n".join(nav_lines)

    #  "  - HTMLコンテンツ (Raw HTML): ..." セクションを全置換
    pattern = r"  \- HTMLコンテンツ \(Raw HTML\):.*?(?=\n  \- |\Z)"
    if re.search(pattern, content, re.DOTALL):
        updated_content = re.sub(pattern, new_section, content, flags=re.DOTALL)
        MKDOCS_YML.write_text(updated_content, encoding="utf-8")
        print("✅ mkdocs.yml の左ナビゲーションツリーを自動更新しました。")

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
