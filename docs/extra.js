/**
 * Interactive Mermaid Diagram Zoom Feature
 */
document.addEventListener("DOMContentLoaded", () => {
  document.addEventListener("click", (e) => {
    const mermaidContainer = e.target.closest(".mermaid");

    if (mermaidContainer) {
      mermaidContainer.classList.toggle("is-zoomed");
      e.stopPropagation();
      return;
    }

    // Dismiss active zoom modals on background click
    document.querySelectorAll(".mermaid.is-zoomed").forEach((el) => {
      el.classList.remove("is-zoomed");
    });
  });
});
