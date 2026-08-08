// CSS クラス切替方式による安全な Mermaid 全画面ズーム
document.addEventListener("DOMContentLoaded", function () {
  document.addEventListener("click", function (e) {
    // クリックされた要素から .mermaid コンテナを探す
    const container = e.target.closest(".mermaid, div.mermaid, pre.mermaid");

    if (container) {
      // ズーム状態のトグル
      container.classList.toggle("is-zoomed");
      e.stopPropagation();
      return;
    }

    // モーダル外クリック時に既存のズーム状態を全解除
    document.querySelectorAll(".is-zoomed").forEach(function (el) {
      el.classList.remove("is-zoomed");
    });
  });
});
