// ============================================================
// TEAM HELPERS — colors, logos, escaping
// ============================================================

const TEAM_COLORS = {
  "ANADOLU EFES ISTANBUL":         "#0033a0",
  "ARMANI OLIMPIA MILAN":          "#e2001a",
  "BASKONIA VITORIA-GASTEIZ":      "#009ee0",
  "BESIKTAS ISTANBUL":             "#1c1c1c",
  "CRVENA ZVEZDA BELGRADE":        "#c8102e",
  "DUBAI BASKETBALL":              "#c9a227",
  "FC BARCELONA":                  "#a50044",
  "FC BAYERN MUNICH":              "#dc052d",
  "FENERBAHCE ISTANBUL":           "#005f9e",
  "HAPOEL IBI TEL AVIV":           "#e30613",
  "LDLC ASVEL VILLEURBANNE":       "#2c2c2c",
  "MACCABI RAPYD TEL AVIV":        "#d4af37",
  "OLYMPIACOS PIRAEUS":            "#e60000",
  "PANATHINAIKOS AKTOR ATHENS":    "#00843d",
  "PARIS BASKETBALL":              "#0a1e3f",
  "PARTIZAN MOZZART BELGRADE":     "#0a0a0a",
  "REAL MADRID":                   "#00529f",
  "VALENCIA BASKET":               "#ff6600",
  "VIRTUS BOLOGNA":                "#404040",
  "ZALGIRIS KAUNAS":               "#007a33"
};

function teamColor(team){
  return TEAM_COLORS[team] || "#64748b";
}

function escapeHtml(str){
  if(str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function initials(team){
  if(!team) return "?";
  const words = String(team).trim().split(/\s+/);
  if(words.length >= 2){
    return (words[0][0] + words[1][0]).toUpperCase();
  }
  return team.slice(0, 2).toUpperCase();
}

function logoHTML(team){
  if(!team) return "";
  const src   = (typeof LOGOS !== "undefined") ? LOGOS[team] : null;
  const color = teamColor(team);
  const ini   = initials(team);

  if(src){
    const onerr =
      `this.onerror=null;` +
      `this.parentNode.classList.add('fallback');` +
      `this.parentNode.style.background='${color}';` +
      `this.parentNode.textContent='${ini}';`;
    return `<span class="logo"><img src="${escapeHtml(src)}" alt="${escapeHtml(team)}" onerror="${onerr}"></span>`;
  }
  return `<span class="logo fallback" style="background:${color}">${ini}</span>`;
}