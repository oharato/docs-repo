#!/usr/bin/env python3
import os
import re
from pathlib import Path

HTML_DIR = Path("docs/html")
INDEX_FILE = HTML_DIR / "index.md"

def extract_title(html_path: Path) -> str:
    """HTMLファイルから <title> または <h1> のテキストを抽出"""
    try:
        content = html_path.read_text(encoding="utf-8", errors="ignore")
        # <title> の抽出
        title_match = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE | re.DOTALL)
        if title_match and title_match.group(1).strip():
            return title_match.group(1).strip()
        # <h1> の抽出
        h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', content, re.IGNORECASE | re.DOTALL)
        if h1_match and h1_match.group(1).strip():
            return re.sub(r'<[^>]+>', '', h1_match.group(1)).strip()
    except Exception as e:
        print(f"Warning: Could not read {html_path}: {e}")
    
    return html_path.name

def main():
    if not HTML_DIR.exists():
        print(f"Directory {HTML_DIR} does not exist. Creating...")
        HTML_DIR.mkdir(parents=True, exist_ok=True)

    # docs/html/ 配下のすべての .html ファイルを取得（再帰的）
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

if __name__ == "__main__":
    main()
