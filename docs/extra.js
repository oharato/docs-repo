// Mermaid ダイアグラムのクリック全画面拡大機能 (イベントデリゲーション方式)
(function () {
  document.addEventListener("click", function (e) {
    // 既存モーダルの削除処理
    const existingOverlay = document.querySelector(".mermaid-modal-overlay");
    if (existingOverlay) {
      existingOverlay.remove();
      return;
    }

    // .mermaid 要素またはその内部要素 (SVG/path/text/g 等) がクリックされたか判定
    const mermaidEl = e.target.closest(".mermaid");
    if (!mermaidEl) return;

    const svg = mermaidEl.querySelector("svg");
    if (!svg) return;

    // モーダル背景の生成
    const overlay = document.createElement("div");
    overlay.className = "mermaid-modal-overlay";

    // SVG クローンの作成
    const svgClone = svg.cloneNode(true);
    svgClone.removeAttribute("style");
    svgClone.removeAttribute("width");
    svgClone.removeAttribute("height");
    svgClone.style.maxWidth = "95vw";
    svgClone.style.maxHeight = "95vh";
    svgClone.style.width = "auto";
    svgClone.style.height = "auto";

    overlay.appendChild(svgClone);

    // クリックで閉じる
    overlay.addEventListener("click", function () {
      overlay.remove();
    });

    document.body.appendChild(overlay);
  });
})();
