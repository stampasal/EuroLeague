// ============================================================
// STATE — global app state + persistence
// ============================================================

// ---- LOAD GAMES (merge localStorage με GAMES_RAW) ----
function loadGames(){
  const raw = GAMES_RAW.map(g => [...g]);
  try{
    const saved = localStorage.getItem(CONFIG.storageKey);
    if(saved){
      const parsed = JSON.parse(saved);
      if(Array.isArray(parsed) && parsed.length === raw.length){
        return raw.map((g, i) => {
          const s = parsed[i];
          if(Array.isArray(s) && s.length >= 9){
            // Το GAMES_RAW (από Python) ΚΕΡΔΙΖΕΙ αν έχει score.
            // Το localStorage χρησιμοποιείται ΜΟΝΟ αν το raw είναι null.
            const hs = g[7] !== null ? g[7] : s[7];
            const aw = g[8] !== null ? g[8] : s[8];
            return [g[0], g[1], g[2], g[3], g[4], g[5], g[6], hs, aw];
          }
          return g;
        });
      }
    }
  }catch(e){ console.warn("loadGames:", e); }
  return raw;
}

// ---- GLOBAL STATE ----
let games           = loadGames();
let gamesFilter     = { team1: "", team2: "" };
let h2hView         = { team1: "", team2: "" };
let teamPage        = { team: "" };
let standingsFilter = "";
let activeRound     = CONFIG.defaultRound || 1;
let statsMode       = "perGame";   // "perGame" | "totals"

// ---- PERSIST ----
function saveGames(){
  try{
    localStorage.setItem(CONFIG.storageKey, JSON.stringify(games));
  }catch(e){ console.warn("saveGames:", e); }
}

// ---- THEME ----
function initTheme(){
  let saved = "light";
  try{ saved = localStorage.getItem(CONFIG.themeKey) || "light"; }catch(e){}
  document.documentElement.setAttribute("data-theme", saved);

  const btn = document.getElementById("btnTheme");
  if(btn){
    btn.textContent = saved === "dark" ? "☀️" : "🌙";
    btn.addEventListener("click", () => {
      const current = document.documentElement.getAttribute("data-theme");
      const next    = current === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      btn.textContent = next === "dark" ? "☀️" : "🌙";
      try{ localStorage.setItem(CONFIG.themeKey, next); }catch(e){}
    });
  }
}

// ---- RESTORE TEAM PAGE SELECTION ----
try{
  const savedTeam = localStorage.getItem("euroleague-team-page");
  if(savedTeam) teamPage.team = savedTeam;
}catch(e){}