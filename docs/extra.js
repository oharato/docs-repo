// Material for MkDocs の Mermaid 公式初期化 & 全画面拡大モーダル
document.addEventListener("DOMContentLoaded", function () {
  if (typeof mermaid !== "undefined") {
    mermaid.initialize({
      startOnLoad: true,
      theme: "default",
    });
  }

  // ドキュメント全体でのクリックイベント検知
  document.addEventListener("click", function (e) {
    const existingOverlay = document.querySelector(".mermaid-modal-overlay");
    if (existingOverlay) {
      existingOverlay.remove();
      return;
    }

    // クリック要素または親要素から SVG を検索
    const target = e.target;
    let svg = target.closest("svg");

    if (!svg) {
      const container = target.closest(".mermaid, pre.mermaid, div.mermaid");
      if (container) {
        svg = container.querySelector("svg");
      }
    }

    if (!svg) return;

    // 全画面モーダルの構築
    const overlay = document.createElement("div");
    overlay.className = "mermaid-modal-overlay";

    const svgClone = svg.cloneNode(true);
    svgClone.removeAttribute("style");
    svgClone.removeAttribute("width");
    svgClone.removeAttribute("height");
    svgClone.style.maxWidth = "95vw";
    svgClone.style.maxHeight = "95vh";
    svgClone.style.width = "auto";
    svgClone.style.height = "auto";

    overlay.appendChild(svgClone);

    overlay.addEventListener("click", function () {
      overlay.remove();
    });

    document.body.appendChild(overlay);
  });
});
