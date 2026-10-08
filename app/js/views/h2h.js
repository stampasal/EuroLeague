// ============================================================
// H2H VIEW
// ============================================================

let h2hSelectedGame = null;

function winsLabel(n){
  if(n === 1) return "1 νίκη";
  return n + " νίκες";
}

function toShortDate(isoDate){
  if(!isoDate) return "—";
  const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  const parts = isoDate.split("-");
  if(parts.length < 3) return isoDate;
  return `${parseInt(parts[2],10)} ${MONTHS[parseInt(parts[1],10)-1]}`;
}

function renderH2H(){
  const el = document.getElementById("view-h2h");
  if(!el) return;

  let html = `<div class="h2h-search">
    <input type="text" class="h2h-input" id="h2hViewTeam1"
           placeholder="🔍 Team 1..." value="${h2hView.team1}"
           autocomplete="off">
    <span class="h2h-vs">VS</span>
    <input type="text" class="h2h-input" id="h2hViewTeam2"
           placeholder="🔍 Team 2..." value="${h2hView.team2}"
           autocomplete="off">
    <button class="h2h-clear" id="h2hViewClear" title="Καθαρισμός">✕</button>
  </div>`;

  const data = computeH2H(h2hView.team1, h2hView.team2);

  if(!data){
    html += `<div class="empty">
      <span class="icon">🏀</span>
      <p>Γράψε δύο ομάδες για να δεις το Head-to-Head.</p>
      <p style="margin-top:8px;font-size:12px;color:var(--muted2)">
        π.χ. <code>OLY</code> vs <code>REAL</code>
      </p>
    </div>`;
    el.innerHTML = html;
    bindH2HInputs();
    attachAutocomplete(document.getElementById("h2hViewTeam1"));
    attachAutocomplete(document.getElementById("h2hViewTeam2"));
    return;
  }

  const { team1, team2, games: h2hGames, played, t1Wins, t2Wins, t1Diff } = data;
  const totalPlayed = played || 0;
  const leader = t1Wins > t2Wins ? team1 : t2Wins > t1Wins ? team2 : null;

  const playedGames = h2hGames.filter(g => g.hs !== null && g.aw !== null);
  let activeGame = null;

  if(h2hSelectedGame){
    activeGame = playedGames.find(g =>
      g.date === h2hSelectedGame.date &&
      g.home === h2hSelectedGame.home &&
      g.away === h2hSelectedGame.away
    );
  }
  if(!activeGame && playedGames.length){
    activeGame = playedGames[playedGames.length - 1];
    h2hSelectedGame = { date: activeGame.date, home: activeGame.home, away: activeGame.away };
  }

  let t1Score = "—", t2Score = "—";
  if(activeGame){
    t1Score = (activeGame.home === team1) ? activeGame.hs : activeGame.aw;
    t2Score = (activeGame.home === team2) ? activeGame.hs : activeGame.aw;
  }

  let bs = null;
  if(activeGame){
    bs = findBoxscore(activeGame.date, activeGame.home, activeGame.away);
  }

  html += renderH2HMatchCard({
    team1, team2, t1Wins, t2Wins, totalPlayed, leader, t1Diff,
    t1Score, t2Score, bs, activeGame
  });

  html += `<h3 class="h2h-section-title">📅 Όλα τα μεταξύ τους παιχνίδια</h3>
    <table class="h2h-table"><thead><tr>
      <th class="num">R</th>
      <th>Date</th>
      <th>Home</th>
      <th class="center">Score</th>
      <th class="center"></th>
      <th class="center">Score</th>
      <th>Away</th>
      <th>Winner</th>
    </tr></thead><tbody>`;

  h2hGames.forEach(g => {
    const isPlayed = g.hs !== null && g.aw !== null;
    const homeWin = isPlayed && g.hs > g.aw;
    const awayWin = isPlayed && g.aw > g.hs;
    const winner = homeWin ? g.home : awayWin ? g.away : "";
    const homeClass = homeWin ? "winner-home" : "";
    const awayClass = awayWin ? "winner-away" : "";
    const rowClick = isPlayed ? "h2h-row-clickable" : "";
    const isActive = h2hSelectedGame &&
                     h2hSelectedGame.date === g.date &&
                     h2hSelectedGame.home === g.home &&
                     h2hSelectedGame.away === g.away;
    const activeClass = isActive ? "h2h-row-active" : "";

    const vsBtn = isPlayed
      ? `<button class="vs-row-btn" type="button">VS</button>`
      : `<button class="vs-row-btn disabled" type="button" disabled>VS</button>`;

    html += `<tr class="${homeClass} ${awayClass} ${rowClick} ${activeClass}"
                 ${isPlayed ? `data-date="${g.date}" data-home="${escapeHtml(g.home)}" data-away="${escapeHtml(g.away)}"` : ""}>
      <td class="num">${g.round}</td>
      <td>${toShortDate(g.date)}</td>
      <td class="home-col"><div class="team-cell">${logoHTML(g.home)}<span>${g.home}</span></div></td>
      <td class="center"><b>${isPlayed ? g.hs : "—"}</b></td>
      <td class="center">${vsBtn}</td>
      <td class="center"><b>${isPlayed ? g.aw : "—"}</b></td>
      <td class="away-col"><div class="team-cell">${logoHTML(g.away)}<span>${g.away}</span></div></td>
      <td class="winner-cell">${winner ? logoHTML(winner) + winner : "<span style='color:var(--muted2)'>Αναμένεται</span>"}</td>
    </tr>`;
  });

  html += `</tbody></table>`;
  el.innerHTML = html;

  // Click στο row → αλλάζει ενεργό game
  el.querySelectorAll("tr.h2h-row-clickable").forEach(tr => {
    tr.addEventListener("click", e => {
      if(e.target.closest(".vs-row-btn")) return;
      h2hSelectedGame = {
        date: tr.dataset.date,
        home: tr.dataset.home,
        away: tr.dataset.away
      };
      renderH2H();
    });
  });

  // Click στο VS row button → αλλάζει ενεργό game (ίδιο)
  el.querySelectorAll(".vs-row-btn:not(.disabled)").forEach(btn => {
    btn.addEventListener("click", e => {
      e.stopPropagation();
      const tr = btn.closest("tr");
      h2hSelectedGame = {
        date: tr.dataset.date,
        home: tr.dataset.home,
        away: tr.dataset.away
      };
      renderH2H();
    });
  });

  bindH2HInputs();
  attachAutocomplete(document.getElementById("h2hViewTeam1"));
  attachAutocomplete(document.getElementById("h2hViewTeam2"));
}

// ============================================================
// TEAM STATS PANEL
// ============================================================
function computeTeamGameStats(players, team){
  const teamPlayers = players.filter(p => p.team === team);
  const s = {
    pir: 0, pts: 0, reb: 0, rebD: 0, rebO: 0,
    ast: 0, stl: 0, blk: 0, to: 0, pf: 0,
    fgm2: 0, fga2: 0, fgm3: 0, fga3: 0, ftm: 0, fta: 0
  };
  teamPlayers.forEach(p => {
    s.pir  += p.pir  || 0;
    s.pts  += p.pts  || 0;
    s.reb  += p.reb  || 0;
    s.rebD += p.rebD || 0;
    s.rebO += p.rebO || 0;
    s.ast  += p.ast  || 0;
    s.stl  += p.stl  || 0;
    s.blk  += p.blk  || 0;
    s.to   += p.to   || 0;
    s.pf   += p.pf   || 0;
    s.fgm2 += p.fgm2 || 0;
    s.fga2 += p.fga2 || 0;
    s.fgm3 += p.fgm3 || 0;
    s.fga3 += p.fga3 || 0;
    s.ftm  += p.ftm  || 0;
    s.fta  += p.fta  || 0;
  });
  s.fg2Pct = s.fga2 > 0 ? (s.fgm2 / s.fga2 * 100) : 0;
  s.fg3Pct = s.fga3 > 0 ? (s.fgm3 / s.fga3 * 100) : 0;
  s.ftPct  = s.fta  > 0 ? (s.ftm  / s.fta  * 100) : 0;
  return s;
}

function statRow(label, homeVal, awayVal, opts = {}){
  const { higherBetter = true, suffix = "", dec = 0 } = opts;
  let homeClass = "", awayClass = "";
  if(typeof homeVal === "number" && typeof awayVal === "number" && homeVal !== awayVal){
    const homeWins = higherBetter ? homeVal > awayVal : homeVal < awayVal;
    if(homeWins) homeClass = "hs-win";
    else awayClass = "hs-win";
  }
  const hStr = typeof homeVal === "number" ? homeVal.toFixed(dec) : homeVal;
  const aStr = typeof awayVal === "number" ? awayVal.toFixed(dec) : awayVal;
  return `
    <div class="hs-row">
      <div class="hs-val hs-val-left ${homeClass}">${hStr}${suffix}</div>
      <div class="hs-label">${label}</div>
      <div class="hs-val hs-val-right ${awayClass}">${aStr}${suffix}</div>
    </div>
  `;
}

function statRowPair(label, h1, h2, a1, a2){
  const hStr = `${h1 || 0}/${h2 || 0}`;
  const aStr = `${a1 || 0}/${a2 || 0}`;
  let homeClass = "", awayClass = "";
  if(h2 > 0 && a2 > 0){
    const hPct = h1 / h2;
    const aPct = a1 / a2;
    if(hPct !== aPct){
      if(hPct > aPct) homeClass = "hs-win";
      else awayClass = "hs-win";
    }
  }
  return `
    <div class="hs-row">
      <div class="hs-val hs-val-left ${homeClass}">${hStr}</div>
      <div class="hs-label">${label}</div>
      <div class="hs-val hs-val-right ${awayClass}">${aStr}</div>
    </div>
  `;
}

function renderH2H(){
  const el = document.getElementById("view-h2h");
  if(!el) return;

  let html = `<div class="h2h-search">
    <input type="text" class="h2h-input" id="h2hViewTeam1"
           placeholder="🔍 Team 1..." value="${h2hView.team1}"
           autocomplete="off">
    <span class="h2h-vs">VS</span>
    <input type="text" class="h2h-input" id="h2hViewTeam2"
           placeholder="🔍 Team 2..." value="${h2hView.team2}"
           autocomplete="off">
    <button class="h2h-clear" id="h2hViewClear" title="Καθαρισμός">✕</button>
  </div>`;

  const data = computeH2H(h2hView.team1, h2hView.team2);

  if(!data){
    html += `<div class="empty">
      <span class="icon">🏀</span>
      <p>Γράψε δύο ομάδες για να δεις το Head-to-Head.</p>
      <p style="margin-top:8px;font-size:12px;color:var(--muted2)">
        π.χ. <code>OLY</code> vs <code>REAL</code>
      </p>
    </div>`;
    el.innerHTML = html;
    bindH2HInputs();
    attachAutocomplete(document.getElementById("h2hViewTeam1"));
    attachAutocomplete(document.getElementById("h2hViewTeam2"));
    return;
  }

  const { team1, team2, games: h2hGames, played, t1Wins, t2Wins, t1Diff } = data;
  const totalPlayed = played || 0;
  const leader = t1Wins > t2Wins ? team1 : t2Wins > t1Wins ? team2 : null;

  const playedGames = h2hGames.filter(g => g.hs !== null && g.aw !== null);
  let activeGame = null;

  if(h2hSelectedGame){
    activeGame = playedGames.find(g =>
      g.date === h2hSelectedGame.date &&
      g.home === h2hSelectedGame.home &&
      g.away === h2hSelectedGame.away
    );
  }
  if(!activeGame && playedGames.length){
    activeGame = playedGames[playedGames.length - 1];
    h2hSelectedGame = { date: activeGame.date, home: activeGame.home, away: activeGame.away };
  }

  let t1Score = "—", t2Score = "—";
  if(activeGame){
    t1Score = (activeGame.home === team1) ? activeGame.hs : activeGame.aw;
    t2Score = (activeGame.home === team2) ? activeGame.hs : activeGame.aw;
  }

  let bs = null;
  if(activeGame){
    bs = findBoxscore(activeGame.date, activeGame.home, activeGame.away);
  }

  html += renderH2HMatchCard({
    team1, team2, t1Wins, t2Wins, totalPlayed, leader, t1Diff,
    t1Score, t2Score, bs
  });

  html += `<h3 class="h2h-section-title">📅 Όλα τα μεταξύ τους παιχνίδια</h3>
    <table class="h2h-table"><thead><tr>
      <th class="num">R</th>
      <th>Date</th>
      <th>Home</th>
      <th class="center">Score</th>
      <th class="center"></th>
      <th class="center">Score</th>
      <th>Away</th>
      <th>Winner</th>
    </tr></thead><tbody>`;

  h2hGames.forEach(g => {
    const isPlayed = g.hs !== null && g.aw !== null;
    const homeWin = isPlayed && g.hs > g.aw;
    const awayWin = isPlayed && g.aw > g.hs;
    const winner = homeWin ? g.home : awayWin ? g.away : "";
    const homeClass = homeWin ? "winner-home" : "";
    const awayClass = awayWin ? "winner-away" : "";
    const rowClick = isPlayed ? "h2h-row-clickable" : "";
    const isActive = h2hSelectedGame &&
                     h2hSelectedGame.date === g.date &&
                     h2hSelectedGame.home === g.home &&
                     h2hSelectedGame.away === g.away;
    const activeClass = isActive ? "h2h-row-active" : "";
    const vsBtn = isPlayed
      ? `<button class="vs-row-btn" type="button">VS</button>`
      : `<button class="vs-row-btn disabled" type="button" disabled>VS</button>`;

    html += `<tr class="${homeClass} ${awayClass} ${rowClick} ${activeClass}"
                 ${isPlayed ? `data-date="${g.date}" data-home="${escapeHtml(g.home)}" data-away="${escapeHtml(g.away)}"` : ""}>
      <td class="num">${g.round}</td>
      <td>${toShortDate(g.date)}</td>
      <td class="home-col"><div class="team-cell">${logoHTML(g.home)}<span>${g.home}</span></div></td>
      <td class="center"><b>${isPlayed ? g.hs : "—"}</b></td>
      <td class="center">${vsBtn}</td>
      <td class="center"><b>${isPlayed ? g.aw : "—"}</b></td>
      <td class="away-col"><div class="team-cell">${logoHTML(g.away)}<span>${g.away}</span></div></td>
      <td class="winner-cell">${winner ? logoHTML(winner) + winner : "<span style='color:var(--muted2)'>Αναμένεται</span>"}</td>
    </tr>`;
  });

  html += `</tbody></table>`;
  el.innerHTML = html;

  el.querySelectorAll("tr.h2h-row-clickable").forEach(tr => {
    tr.addEventListener("click", e => {
      if(e.target.closest(".h2h-stats-btn")) return;
      h2hSelectedGame = {
        date: tr.dataset.date,
        home: tr.dataset.home,
        away: tr.dataset.away
      };
      renderH2H();
    });
  });

  el.querySelectorAll(".h2h-stats-btn").forEach(btn => {
    btn.addEventListener("click", e => {
      e.stopPropagation();
      const tr = btn.closest("tr");
      openBoxscoreModal(tr.dataset.date, tr.dataset.home, tr.dataset.away);
    });
  });

  // VS row button
  el.querySelectorAll(".vs-row-btn:not(.disabled)").forEach(btn => {
    btn.addEventListener("click", e => {
      e.stopPropagation();
      const tr = btn.closest("tr");
      h2hSelectedGame = {
        date: tr.dataset.date,
        home: tr.dataset.home,
        away: tr.dataset.away
      };
      renderH2H();
    });
  });

  // Box to Box button
  const boxBtn = document.getElementById("hmBoxBtn");
  if(boxBtn && activeGame){
    boxBtn.addEventListener("click", () => {
      openBoxscoreModal(activeGame.date, activeGame.home, activeGame.away);
    });
  }

  bindH2HInputs();
  attachAutocomplete(document.getElementById("h2hViewTeam1"));
  attachAutocomplete(document.getElementById("h2hViewTeam2"));
}

// ============================================================
// BIND INPUTS
// ============================================================
function bindH2HInputs(){
  const in1 = document.getElementById("h2hViewTeam1");
  const in2 = document.getElementById("h2hViewTeam2");
  const clearBtn = document.getElementById("h2hViewClear");

  if(in1){
    in1.addEventListener("input", e => {
      h2hView.team1 = e.target.value;
      const pos = e.target.selectionStart;
      renderH2H();
      const ni = document.getElementById("h2hViewTeam1");
      if(ni){ ni.focus(); ni.setSelectionRange(pos, pos); }
    });
  }
  if(in2){
    in2.addEventListener("input", e => {
      h2hView.team2 = e.target.value;
      const pos = e.target.selectionStart;
      renderH2H();
      const ni = document.getElementById("h2hViewTeam2");
      if(ni){ ni.focus(); ni.setSelectionRange(pos, pos); }
    });
  }
  if(clearBtn){
    clearBtn.addEventListener("click", () => {
      h2hView = { team1: "", team2: "" };
      h2hSelectedGame = null;
      renderH2H();
    });
  }
}

// ============================================================
// BOX SCORE MODAL (Modal 1)
// ============================================================
function findBoxscore(date, home, away){
  const all = window.GAME_BOXSCORES || {};
  for(const key in all){
    const bs = all[key];
    if(bs.date === date && bs.home === home && bs.away === away){
      return bs;
    }
  }
  return null;
}

function openBoxscoreModal(date, home, away){
  const bs = findBoxscore(date, home, away);
  if(!bs) return;

  const prevPl = document.getElementById("player-detail-modal");
  if(prevPl) prevPl.remove();
  const prev = document.getElementById("h2h-boxscore-modal");
  if(prev) prev.remove();

  const homePlayers = bs.players.filter(p => p.team === bs.home);
  const awayPlayers = bs.players.filter(p => p.team === bs.away);

  const bg = document.createElement("div");
  bg.id = "h2h-boxscore-modal";
  bg.className = "bs-modal-bg";

  bg.innerHTML = `
    <div class="bs-modal" role="dialog" aria-modal="true">
      <button class="bs-close" aria-label="Close">×</button>

      <div class="bs-header">
        <div class="bs-header-team">
          ${logoHTML(bs.home)}
          <span>${bs.home}</span>
        </div>
        <div class="bs-header-score">
          <span class="${bs.hs > bs.aw ? 'win' : ''}">${bs.hs}</span>
          <span class="bs-dash">–</span>
          <span class="${bs.aw > bs.hs ? 'win' : ''}">${bs.aw}</span>
        </div>
        <div class="bs-header-team bs-header-team-away">
          <span>${bs.away}</span>
          ${logoHTML(bs.away)}
        </div>
      </div>
      <div class="bs-subtitle">Round ${bs.round} · ${bs.date}</div>

      ${renderBoxscoreTable(bs.home, homePlayers)}
      ${renderBoxscoreTable(bs.away, awayPlayers)}
    </div>
  `;

  document.body.appendChild(bg);

  bg.querySelector(".bs-close").addEventListener("click", () => bg.remove());
  bg.addEventListener("click", e => { if(e.target === bg) bg.remove(); });
  document.addEventListener("keydown", function esc(e){
    if(e.key === "Escape"){ bg.remove(); document.removeEventListener("keydown", esc); }
  });

  bindBoxscoreRowClicks(bs);
}

function renderBoxscoreTable(teamName, players){
  if(!players.length){
    return `<div class="bs-empty">Δεν υπάρχουν παίκτες</div>`;
  }

  const sorted = players.slice().sort((a, b) => (b.pir || 0) - (a.pir || 0));

  const rows = sorted.map((p, idx) => {
    const starter = p.startFive ? " bs-starter" : "";
    const played  = p.played ? "" : " bs-dnp";
    const jersey  = p.jersey != null ? p.jersey : "—";

    return `<tr class="${starter}${played} bs-player-row" data-player-idx="${idx}" data-team="${escapeHtml(teamName)}">
      <td class="bs-pos">${p.pos || "—"}</td>
      <td class="bs-num">${jersey}</td>
      <td class="bs-name">${p.name || "—"}</td>
      <td class="bs-min">${p.min != null ? p.min : "—"}</td>
      <td class="bs-pir">${p.pir != null ? p.pir : "—"}</td>
      <td>${p.pts != null ? p.pts : "—"}</td>
      <td>${p.reb != null ? p.reb : "—"}</td>
      <td>${p.ast != null ? p.ast : "—"}</td>
      <td>${p.stl != null ? p.stl : "—"}</td>
      <td>${p.blk != null ? p.blk : "—"}</td>
      <td>${p.to != null ? p.to : "—"}</td>
      <td>${p.pf != null ? p.pf : "—"}</td>
    </tr>`;
  }).join("");

  return `
    <div class="bs-team-block">
      <div class="bs-team-title">${logoHTML(teamName)} ${teamName}</div>
      <table class="bs-table">
        <thead>
          <tr>
            <th class="bs-pos">POS</th>
            <th class="bs-num">#</th>
            <th class="bs-name">Player</th>
            <th class="bs-min">MIN</th>
            <th class="bs-pir">PIR</th>
            <th>PTS</th>
            <th>REB</th>
            <th>AST</th>
            <th>STL</th>
            <th>BLK</th>
            <th>TO</th>
            <th>PF</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
  `;
}

function bindBoxscoreRowClicks(bs){
  document.querySelectorAll("#h2h-boxscore-modal .bs-player-row").forEach(tr => {
    tr.addEventListener("click", (e) => {
      e.stopPropagation();
      const idx = +tr.dataset.playerIdx;
      const team = tr.dataset.team;
      const teamPlayers = bs.players.filter(x => x.team === team);
      const sorted = teamPlayers.slice().sort((a, b) => (b.pir || 0) - (a.pir || 0));
      const p = sorted[idx];
      if(p) openPlayerModal(p, {
        home: bs.home, away: bs.away,
        hs: bs.hs, aw: bs.aw,
        round: bs.round, date: bs.date,
        players: bs.players
      });
    });
  });
}

// ============================================================
// PLAYER DETAIL MODAL (Modal 2) — με flip stats
// ============================================================
let _statsMode = "absolute";

function computeTeamTotals(players){
  const totals = {
    sec: 0, min: 0, pir: 0, pts: 0,
    reb: 0, rebD: 0, rebO: 0, ast: 0, stl: 0, blk: 0,
    blkAgainst: 0, to: 0, pf: 0, fr: 0
  };
  players.forEach(p => {
    ["sec","min","pir","pts","reb","rebD","rebO","ast","stl","blk","blkAgainst","to","pf","fr"]
      .forEach(k => { totals[k] += (p[k] || 0); });
  });
  return totals;
}

function pct(value, total){
  if(!total || value == null) return "—";
  return ((value / total) * 100).toFixed(1) + "%";
}

function shootPct(made, att){
  if(att == null || att === 0) return "0%";
  return (((made || 0) / att) * 100).toFixed(1) + "%";
}

function buildGridItem(label, absVal, pctVal, cls, canPct){
  const isPct = _statsMode === "percent" && canPct;
  const shown = isPct ? pctVal : absVal;
  return `<div class="pl-grid-item ${cls || ""}" data-can-pct="${canPct ? '1' : '0'}" data-abs="${escapeHtml(String(absVal))}" data-pct="${escapeHtml(String(pctVal))}">
    <div class="pl-grid-label">${label}</div>
    <div class="pl-grid-value">${shown}</div>
  </div>`;
}

function flipAllCards(){
  const cards = document.querySelectorAll("#player-detail-modal .pl-grid-item");
  if(!cards.length) return;

  cards.forEach(el => el.classList.add("flipping"));

  setTimeout(() => {
    cards.forEach(el => {
      const canPct = el.dataset.canPct === "1";
      if(!canPct) return;
      const v = el.querySelector(".pl-grid-value");
      v.textContent = (_statsMode === "percent") ? el.dataset.pct : el.dataset.abs;
    });
  }, 180);

  setTimeout(() => {
    cards.forEach(el => el.classList.remove("flipping"));
  }, 200);
}

function toggleStatsMode(){
  _statsMode = (_statsMode === "absolute") ? "percent" : "absolute";
  flipAllCards();
}

function openPlayerModal(player, gameInfo){
  const prev = document.getElementById("player-detail-modal");
  if(prev) prev.remove();

  const p = player;
  const v = (x) => (x === null || x === undefined || x === "") ? "—" : x;

  const allPlayers = (gameInfo && gameInfo.players) ? gameInfo.players : [];
  const teamPlayers = allPlayers.filter(x => x.team === p.team);
  const T = computeTeamTotals(teamPlayers);

  const gi = (label, key, cls) => {
    const abs = v(p[key]);
    const pctVal = pct(p[key], T[key]);
    const canPct = (T[key] > 0 && p[key] != null);
    return buildGridItem(label, abs, pctVal, cls, canPct);
  };

  const bg = document.createElement("div");
  bg.id = "player-detail-modal";
  bg.className = "pl-modal-bg";

  bg.innerHTML = `
    <div class="pl-modal" role="dialog" aria-modal="true">
      <button class="pl-close" aria-label="Close">×</button>

      <div class="pl-header">
        <div class="pl-photo">
          ${p.photo
            ? `<img src="${p.photo}" alt="${escapeHtml(p.name)}" onerror="this.style.display='none';this.parentNode.textContent='${(p.name||'?').slice(0,2)}'">`
            : escapeHtml((p.name || "?").slice(0,2))}
        </div>
        <div class="pl-header-info">
          <h2 class="pl-name">${escapeHtml(p.name || "—")}</h2>
          <div class="pl-meta">
            <span class="pl-meta-item">${logoHTML(p.team)} ${escapeHtml(p.team)}</span>
            <span class="pl-meta-item">🎽 #${v(p.jersey)}</span>
            <span class="pl-meta-item">📍 ${v(p.pos)}</span>
            ${p.startFive ? `<span class="pl-meta-item pl-starter">⭐ Starter</span>` : ""}
            ${p.played ? "" : `<span class="pl-meta-item pl-dnp">DNP</span>`}
          </div>
          <div class="pl-bio">
            ${p.countryFull ? `<span>🌍 ${escapeHtml(p.countryFull)}</span>` : ""}
            ${p.height ? `<span>📏 ${p.height} cm</span>` : ""}
            ${p.weight ? `<span>⚖️ ${p.weight} kg</span>` : ""}
            ${p.birthDate ? `<span>🎂 ${p.birthDate}</span>` : ""}
          </div>
        </div>
      </div>

      <div class="pl-section">
        <div class="pl-section-title">📊 Basic</div>
        <div class="pl-grid">
          ${gi("MIN", "min")}
          ${gi("SEC", "sec")}
          ${gi("PIR", "pir", "accent")}
          ${gi("PTS", "pts")}
          <div class="pl-grid-item" data-can-pct="0">
            <div class="pl-grid-label">+/-</div>
            <div class="pl-grid-value">${v(p.plusMinus)}</div>
          </div>
        </div>
      </div>

      <div class="pl-section">
        <div class="pl-section-title">🏀 Rebounds & Defense</div>
        <div class="pl-grid">
          ${gi("REB", "reb")}
          ${gi("DEF REB", "rebD")}
          ${gi("OFF REB", "rebO")}
          ${gi("AST", "ast")}
          ${gi("STL", "stl")}
          ${gi("BLK", "blk")}
          ${gi("BLK AGN", "blkAgainst")}
          ${gi("TO", "to")}
          ${gi("PF", "pf")}
          ${gi("FR", "fr")}
        </div>
      </div>

      <div class="pl-section">
        <div class="pl-section-title">🎯 Shooting</div>
        <div class="pl-grid">
          ${buildGridItem("2P", `${v(p.fgm2)} / ${v(p.fga2)}`, shootPct(p.fgm2, p.fga2), "", true)}
          ${buildGridItem("3P", `${v(p.fgm3)} / ${v(p.fga3)}`, shootPct(p.fgm3, p.fga3), "", true)}
          ${buildGridItem("FG", `${v(p.fgm)} / ${v(p.fga)}`, shootPct(p.fgm, p.fga), "", true)}
          ${buildGridItem("FT", `${v(p.ftm)} / ${v(p.fta)}`, shootPct(p.ftm, p.fta), "", true)}
        </div>
      </div>

      ${gameInfo ? `
        <div class="pl-footer">
          ${logoHTML(gameInfo.home)} ${escapeHtml(gameInfo.home)} ${gameInfo.hs} – ${gameInfo.aw} ${escapeHtml(gameInfo.away)} ${logoHTML(gameInfo.away)}
          <span class="pl-footer-sub">R${gameInfo.round} · ${gameInfo.date}</span>
        </div>
      ` : ""}
    </div>
  `;

  document.body.appendChild(bg);

  bg.querySelectorAll(".pl-grid-item").forEach(card => {
    card.addEventListener("click", () => toggleStatsMode());
  });

  bg.querySelector(".pl-close").addEventListener("click", () => bg.remove());
  bg.addEventListener("click", e => { if(e.target === bg) bg.remove(); });
  document.addEventListener("keydown", function esc(e){
    if(e.key === "Escape"){ bg.remove(); document.removeEventListener("keydown", esc); }
  });
}

// ============================================================
// MATCH CARD — header + score + wins + stats (ίδιο grid)
// ============================================================
function renderH2HMatchCard({ team1, team2, t1Wins, t2Wins, totalPlayed, leader, t1Diff, t1Score, t2Score, bs, activeGame }){
  let statsHTML = "";
  if(bs){
    const H = computeTeamGameStats(bs.players, bs.home);
    const A = computeTeamGameStats(bs.players, bs.away);
    const isT1Home = bs.home === team1;
    const homeT = isT1Home ? H : A;
    const awayT = isT1Home ? A : H;

    statsHTML = `
      <div class="hm-sep"></div>
      ${hmStatRow("Performance Index Rating", homeT.pir,   awayT.pir)}
      ${hmStatRowPair("Free-throw",           homeT.ftm,  homeT.fta,  awayT.ftm,  awayT.fta)}
      ${hmStatRow("Free-throw %",             homeT.ftPct, awayT.ftPct, { suffix:"%", dec:1 })}
      ${hmStatRowPair("Two-point",            homeT.fgm2, homeT.fga2, awayT.fgm2, awayT.fga2)}
      ${hmStatRow("Two-point %",              homeT.fg2Pct,awayT.fg2Pct,{ suffix:"%", dec:1 })}
      ${hmStatRowPair("Three-point",          homeT.fgm3, homeT.fga3, awayT.fgm3, awayT.fga3)}
      ${hmStatRow("Three-point %",            homeT.fg3Pct,awayT.fg3Pct,{ suffix:"%", dec:1 })}
      ${hmStatRow("Offensive rebounds",       homeT.rebO,  awayT.rebO)}
      ${hmStatRow("Defensive rebounds",       homeT.rebD,  awayT.rebD)}
      ${hmStatRow("Total rebounds",           homeT.reb,   awayT.reb)}
      ${hmStatRow("Assists",                  homeT.ast,   awayT.ast)}
      ${hmStatRow("Steals",                   homeT.stl,   awayT.stl)}
      ${hmStatRow("Blocks",                   homeT.blk,   awayT.blk)}
      ${hmStatRow("Turnovers",                homeT.to,    awayT.to, { higherBetter:false })}
    `;
  }

  const boxBtn = bs
    ? `<button class="hm-box-btn" type="button" id="hmBoxBtn">Boxscore</button>`
    : "";

  return `
    <div class="hm-card">
      <div class="hm-grid">
        <div class="hm-cell hm-home hm-logo-cell">
          <div class="hm-big-logo">${logoHTML(team1)}</div>
          <div class="hm-team-name">${team1}</div>
        </div>
        <div class="hm-cell hm-center-cell">
          <div class="hm-vs-big">VS</div>
          <div class="hm-total-games">${totalPlayed} παιχνίδια</div>
          ${leader
            ? `<div class="hm-leader-big">🏆 ${leader}</div>`
            : totalPlayed > 0
              ? `<div class="hm-leader-big hm-draw">Ισοπαλία</div>`
              : `<div class="hm-leader-big hm-pending">Δεν έχουν παιχτεί ακόμα</div>`
          }
        </div>
        <div class="hm-cell hm-away hm-logo-cell">
          <div class="hm-big-logo">${logoHTML(team2)}</div>
          <div class="hm-team-name">${team2}</div>
        </div>

        <div class="hm-cell hm-home hm-score-cell">${t1Score}</div>
        <div class="hm-cell hm-center-cell hm-score-label">ΤΕΛΙΚΟ ΣΚΟΡ</div>
        <div class="hm-cell hm-away hm-score-cell">${t2Score}</div>

        <div class="hm-cell hm-home hm-wins-cell">${winsLabel(t1Wins)}</div>
        <div class="hm-cell hm-center-cell hm-box-cell">${boxBtn}</div>
        <div class="hm-cell hm-away hm-wins-cell">${winsLabel(t2Wins)}</div>

        ${statsHTML}
      </div>
    </div>
  `;
}

function hmStatRow(label, hVal, aVal, opts){
  opts = opts || {};
  const higherBetter = opts.higherBetter !== false;
  const suffix = opts.suffix || "";
  const dec = opts.dec || 0;
  let homeClass = "", awayClass = "";
  if(typeof hVal === "number" && typeof aVal === "number" && hVal !== aVal){
    const homeWins = higherBetter ? hVal > aVal : hVal < aVal;
    if(homeWins) homeClass = "hm-win";
    else awayClass = "hm-win";
  }
  const hStr = typeof hVal === "number" ? hVal.toFixed(dec) : hVal;
  const aStr = typeof aVal === "number" ? aVal.toFixed(dec) : aVal;
  return `
    <div class="hm-cell hm-home hm-stat-val ${homeClass}">${hStr}${suffix}</div>
    <div class="hm-cell hm-center-cell hm-stat-label">${label}</div>
    <div class="hm-cell hm-away hm-stat-val ${awayClass}">${aStr}${suffix}</div>
  `;
}

function hmStatRowPair(label, hM, hA, aM, aA){
  const hStr = `${hM || 0}/${hA || 0}`;
  const aStr = `${aM || 0}/${aA || 0}`;
  let homeClass = "", awayClass = "";
  if(hA > 0 && aA > 0){
    const hPct = hM / hA;
    const aPct = aM / aA;
    if(hPct !== aPct){
      if(hPct > aPct) homeClass = "hm-win";
      else awayClass = "hm-win";
    }
  }
  return `
    <div class="hm-cell hm-home hm-stat-val ${homeClass}">${hStr}</div>
    <div class="hm-cell hm-center-cell hm-stat-label">${label}</div>
    <div class="hm-cell hm-away hm-stat-val ${awayClass}">${aStr}</div>
  `;
}