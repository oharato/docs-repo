// Mermaid ダイアグラムのクリック全画面拡大機能
document.addEventListener("DOMContentLoaded", function () {
  function initMermaidZoom() {
    document.querySelectorAll(".mermaid").forEach(function (el) {
      el.addEventListener("click", function () {
        const svg = el.querySelector("svg");
        if (!svg) return;

        // モーダル背景の生成
        const overlay = document.createElement("div");
        overlay.className = "mermaid-modal-overlay";

        // SVG のクローンを作成して高画質表示
        const svgClone = svg.cloneNode(true);
        svgClone.removeAttribute("style");
        overlay.appendChild(svgClone);

        // クリックで閉じる
        overlay.addEventListener("click", function () {
          document.body.removeChild(overlay);
        });

        document.body.appendChild(overlay);
      });
    });
  }

  // MkDocs のページ遷移に対応
  initMermaidZoom();
  if (typeof location$ !== "undefined") {
    location$.subscribe(function () {
      setTimeout(initMermaidZoom, 500);
    });
  }
});
