// ============================================================
// APP — tabs, initialization
// ============================================================

// ---- TAB SLIDING UNDERLINE (B) ----
function updateTabUnderline(){
  const nav = document.querySelector("nav.tabs");
  if(!nav) return;
  const u = nav.querySelector(".tab-underline");
  const activeBtn = nav.querySelector("button.active");
  if(!u || !activeBtn) return;

  const navRect = nav.getBoundingClientRect();
  const btnRect = activeBtn.getBoundingClientRect();

  u.style.left  = (btnRect.left - navRect.left) + "px";
  u.style.width = btnRect.width + "px";

  // Scroll tab into view σε μικρές οθόνες
  activeBtn.scrollIntoView({
    behavior: "smooth",
    inline: "center",
    block: "nearest"
  });
}

// ---- STAGGER FADE-IN (A) ----
function applyStaggerIndexes(){
  const groups = [
    ".view tbody tr",
    ".view .dash-grid .stat-card",
    ".view .team-page-stats .team-stat-card",
    ".view .team-upcoming .team-upcoming-row",
    ".view .bracket .bracket-match",
    ".view .playin-grid .playin-match"
  ];
  groups.forEach(sel => {
    document.querySelectorAll(sel).forEach((el, i) => {
      // Cap delay στα ~180ms max (12ms × 15 = 180ms)
      el.style.setProperty("--i", Math.min(i, 15));
    });
  });
  // Headers → πάντα index 0
  document.querySelectorAll(".view .team-page-header, .view .h2h-header").forEach(el => {
    el.style.setProperty("--i", 0);
  });
}

function triggerStagger(viewEl){
  if(!viewEl) return;
  viewEl.classList.remove("stagger-play");
  void viewEl.offsetWidth;   // force reflow → restart animation
  viewEl.classList.add("stagger-play");
}

// ---- INIT ----
function initTabs(){
  document.querySelectorAll("nav.tabs button").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("nav.tabs button").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
      btn.classList.add("active");

      const viewEl = document.getElementById("view-" + btn.dataset.view);
      viewEl.classList.add("active");

      // Reset toolbar height
      if(typeof updateToolbarHeight === "function") updateToolbarHeight();

      // Tab underline slide
      updateTabUnderline();

      // Stagger fade-in
      applyStaggerIndexes();
      triggerStagger(viewEl);
    });
  });
}

function init(){
  initTheme();
  initTabs();
  renderAll();

  // Init stagger + underline μετά το πρώτο render
  applyStaggerIndexes();
  updateTabUnderline();
  triggerStagger(document.querySelector(".view.active"));
}

init();

// Resize → re-measure toolbar + reposition underline
window.addEventListener("resize", () => {
  if(typeof updateToolbarHeight === "function") updateToolbarHeight();
  updateTabUnderline();
});