// ============================================================
// TEAM PAGE VIEW
// ============================================================

function renderTeamPage(){
  const el = document.getElementById("view-team");
  if(!el) return;

  let html = `<div class="team-page-selector">
    <label for="teamPageSearch">Διάλεξε ομάδα:</label>
    <input type="text" class="h2h-input" id="teamPageSearch"
           value="${teamPage.team}"
           placeholder="🔍 Search team..."
           autocomplete="off">
  </div>`;

  const rows = computeStandings();
  const t = findTeamFromQuery(teamPage.team, rows);
  if(!t){
    el.innerHTML = html + `<div class="empty">
      <span class="icon">🏀</span>
      <p>Δεν βρέθηκε η ομάδα: <b>${teamPage.team || "(κενό)"}</b></p>
      <p style="margin-top:8px;font-size:12px;color:var(--muted2)">
        Δοκίμασε π.χ. <code>oly</code>, <code>pao</code>, <code>real</code>
      </p>
    </div>`;

    const inp = document.getElementById("teamPageSearch");
    if(inp){
      attachAutocomplete(inp);
      inp.addEventListener("input", e => {
        teamPage.team = e.target.value;
        const pos = e.target.selectionStart;
        renderTeamPage();
        const ni = document.getElementById("teamPageSearch");
        if(ni){ ni.focus(); ni.setSelectionRange(pos, pos); }
      });
    }
    return;
  }
  const rank = rows.findIndex(r => r.team === t.team) + 1;
  const rankClass = rank <= CONFIG.playoffTeams ? "qual"
                  : rank <= CONFIG.playInTeams ? "playin" : "zone-out";

  const teamGames = games
    .map((g, idx) => ({ ...arrayToGame(g), idx }))
    .filter(g => g.home === t.team || g.away === t.team)
    .sort((a,b) => {
      if(a.date !== b.date) return a.date < b.date ? -1 : 1;
      return (a.utc||"").localeCompare(b.utc||"");
    });

  const playedGames = teamGames.filter(g => g.hs !== null && g.aw !== null);
  const upcomingGames = teamGames.filter(g => g.hs === null || g.aw === null);

  const streakClass = t.streakType === "W" ? "streak-w" : t.streakType === "L" ? "streak-l" : "";
  const streakText = t.streak > 0 ? `${t.streakType}${t.streak}` : "—";

  // --- Basic Stats: 2 cards που αλλάζουν ανά mode ---
  let basicCard1Label, basicCard1Value;
  let basicCard2Label, basicCard2Value;
  if(statsMode === "totals"){
    basicCard1Label = "PF";
    basicCard1Value = t.PF;
    basicCard2Label = "PA";
    basicCard2Value = t.PA;
  } else {
    basicCard1Label = "PPG";
    basicCard1Value = t.GP ? (t.PF / t.GP).toFixed(1) : "0.0";
    basicCard2Label = "PAPG";
    basicCard2Value = t.GP ? (t.PA / t.GP).toFixed(1) : "0.0";
  }

  html += `
    <div class="team-page-header team-page-hero" style="--team-color:${teamColor(t.team)}">
      <div class="team-page-logo">${logoHTML(t.team)}</div>
      <div class="team-page-info">
        <h1 class="team-page-name">${t.team}</h1>
        <div class="team-page-meta">
          <span class="team-page-rank ${rankClass}">#${rank}</span>
          <span class="team-page-record">${t.W}W – ${t.L}L</span>
          <span class="team-page-pct">${(t.winPct*100).toFixed(1)}%</span>
        </div>
      </div>
    </div>

    <div class="stats-mode-toggle">
      <button class="stats-mode-btn ${statsMode === "perGame" ? "active" : ""}"
              data-mode="perGame">Per Game</button>
      <button class="stats-mode-btn ${statsMode === "totals" ? "active" : ""}"
              data-mode="totals">Total</button>
    </div>

    <h3 class="team-section-title">📊 Basic Stats</h3>
    <div class="team-page-stats">
      <div class="team-stat-card">
        <div class="team-stat-label">GP</div>
        <div class="team-stat-value">${t.GP}</div>
      </div>
      <div class="team-stat-card">
        <div class="team-stat-label">${basicCard1Label}</div>
        <div class="team-stat-value">${basicCard1Value}</div>
      </div>
      <div class="team-stat-card">
        <div class="team-stat-label">${basicCard2Label}</div>
        <div class="team-stat-value">${basicCard2Value}</div>
      </div>
      <div class="team-stat-card">
        <div class="team-stat-label">DIFF</div>
        <div class="team-stat-value ${t.diff > 0 ? 'positive' : t.diff < 0 ? 'negative' : ''}">${t.diff > 0 ? "+" : ""}${t.diff}</div>
      </div>
      <div class="team-stat-card">
        <div class="team-stat-label">HOME</div>
        <div class="team-stat-value">${t.hW}-${t.hL}</div>
      </div>
      <div class="team-stat-card">
        <div class="team-stat-label">AWAY</div>
        <div class="team-stat-value">${t.aW}-${t.aL}</div>
      </div>
      <div class="team-stat-card">
        <div class="team-stat-label">STREAK</div>
        <div class="team-stat-value">
          <span class="streak ${streakClass}">${streakText}</span>
        </div>
      </div>
      <div class="team-stat-card">
        <div class="team-stat-label">L10</div>
        <div class="team-stat-value">
          <span class="l10">${t.last10.split("").map(c => `<span class="${c}">${c}</span>`).join("") || "—"}</span>
        </div>
      </div>
    </div>

    ${(() => {
      const adv = (typeof TEAM_ADVANCED !== "undefined" && TEAM_ADVANCED[t.team]) 
        ? TEAM_ADVANCED[t.team] 
        : null;
      
      if(!adv){
        return `
          <h3 class="team-section-title">⚡ Advanced Stats</h3>
          <div class="team-empty">Δεν υπάρχουν advanced stats.</div>
        `;
      }
      
      let data = adv[statsMode] || adv.perGame || adv;
      
      // Fallback για totals αν λείπουν αθροιστικά keys
      if(statsMode === "totals" && data && t.GP > 0){
        const pg = adv.perGame || {};
        const totalKeys = ["REB", "AST", "STL", "BLK", "TOV"];
        const needsFallback = totalKeys.some(k => data[k] === null || data[k] === undefined);
        
        if(needsFallback){
          data = { ...data };
          totalKeys.forEach(k => {
            if((data[k] === null || data[k] === undefined) && pg[k] != null){
              data[k] = Math.round(pg[k] * t.GP);
            }
          });
        }
      }
      
      const f1 = v => (v !== undefined && v !== null) ? Number(v).toFixed(1) : "—";
      const f2 = v => (v !== undefined && v !== null) ? Number(v).toFixed(2) : "—";
      const fP = v => (v !== undefined && v !== null) ? Number(v).toFixed(1) + "%" : "—";
      
      const card = (label, value) => `
        <div class="team-stat-card team-stat-advanced">
          <div class="team-stat-label">${label}</div>
          <div class="team-stat-value">${value}</div>
        </div>
      `;
      
      // Σειρά 1: αθροιστικά μεγέθη + PIR (πάντα ορατά, 6 cards)
      const row1 = `
        ${card("REB",    f1(data.REB))}
        ${card("AST",    f1(data.AST))}
        ${card("STL",    f1(data.STL))}
        ${card("BLK",    f1(data.BLK))}
        ${card("TOV",    f1(data.TOV))}
        ${card("PIR",    f1(data.PIR))}
      `;
      
      // Σειρά 2: ποσοστά + AST/TO (μόνο Per Game, 6 cards)
      const row2 = statsMode === "perGame" ? `
        ${card("TS%",    fP(data.TS))}
        ${card("eFG%",   fP(data.eFG))}
        ${card("3P%",    fP(data["3P%"]))}
        ${card("2P%",    fP(data["2P%"]))}
        ${card("FT%",    fP(data["FT%"]))}
        ${card("AST/TO", f2(data["AST/TO"]))}
      ` : "";
      
      return `
        <h3 class="team-section-title">⚡ Advanced Stats</h3>
        <div class="team-stats-grid-6">${row1}</div>
        ${row2 ? `<div class="team-stats-grid-6" style="margin-top:12px">${row2}</div>` : ""}
      `;
    })()}

    <h3 class="team-section-title">📅 Επόμενα παιχνίδια (${upcomingGames.length})</h3>`;

  if(upcomingGames.length === 0){
    html += `<div class="team-empty">Δεν υπάρχουν επόμενα παιχνίδια.</div>`;
  } else {
    html += `<div class="team-upcoming">`;
    upcomingGames.slice(0, 5).forEach(g => {
      const isHome = g.home === t.team;
      const opponent = isHome ? g.away : g.home;
      html += `
        <div class="team-upcoming-row">
          <span class="team-upcoming-round">R${g.round}</span>
          <span class="team-upcoming-date">${toShortDate(g.date)}</span>
          <span class="team-upcoming-time">${g.utc}</span>
          <span class="team-upcoming-vs ${isHome ? 'home' : 'away'}">${isHome ? '🏠' : '✈️'}</span>
          <span class="team-upcoming-team">${logoHTML(opponent)} ${opponent}</span>
        </div>
      `;
    });
    if(upcomingGames.length > 5){
      html += `<div class="team-upcoming-more">+${upcomingGames.length - 5} ακόμα...</div>`;
    }
    html += `</div>`;
  }

  html += `<h3 class="team-section-title">📋 Όλα τα παιχνίδια (${teamGames.length})</h3>`;
  html += `<table class="team-page-table"><thead><tr>
    <th class="num">R</th>
    <th>Date</th>
    <th>Home</th>
    <th class="center">Score</th>
    <th class="center">VS</th>
    <th class="center">Score</th>
    <th>Away</th>
    <th>Winner</th>
  </tr></thead><tbody>`;

  teamGames.forEach(g => {
    const isPlayed = g.hs !== null && g.aw !== null;
    const homeWin = isPlayed && g.hs > g.aw;
    const awayWin = isPlayed && g.aw > g.hs;
    const winner = homeWin ? g.home : awayWin ? g.away : "";
    const homeClass = homeWin ? "winner-home" : "";
    const awayClass = awayWin ? "winner-away" : "";
    const rowHighlight = !isPlayed ? "team-future-row" : "";

    html += `<tr class="${homeClass} ${awayClass} ${rowHighlight}">
      <td class="num">${g.round}</td>
      <td>${toShortDate(g.date)}</td>
      <td class="home-col"><div class="team-cell">${logoHTML(g.home)}<span>${g.home}</span></div></td>
      <td class="center"><b>${isPlayed ? g.hs : "—"}</b></td>
      <td class="center">
        <button class="vs-row-btn ${isPlayed ? '' : 'disabled'}"
                data-home="${escapeHtml(g.home)}"
                data-away="${escapeHtml(g.away)}"
                ${isPlayed ? '' : 'disabled'}
                title="Head-to-Head: ${escapeHtml(g.home)} vs ${escapeHtml(g.away)}">VS</button>
      </td>
      <td class="center"><b>${isPlayed ? g.aw : "—"}</b></td>
      <td class="away-col"><div class="team-cell">${logoHTML(g.away)}<span>${g.away}</span></div></td>
      <td class="winner-cell">${winner ? logoHTML(winner) + winner : "<span style='color:var(--muted2)'>Αναμένεται</span>"}</td>
    </tr>`;
  });

  html += `</tbody></table>`;
  el.innerHTML = html;
  
  document.querySelectorAll(".stats-mode-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const mode = btn.dataset.mode;
      if(mode === statsMode) return;
      statsMode = mode;
      renderTeamPage();
    });
  });

  // VS buttons → H2H
  el.querySelectorAll(".vs-row-btn").forEach(btn => {
    btn.addEventListener("click", e => {
      e.preventDefault();
      e.stopPropagation();
      if(btn.classList.contains("disabled")) return;
      const home = btn.dataset.home;
      const away = btn.dataset.away;
      if(home && away) goToH2H(home, away);
    });
  });

  const searchInput = document.getElementById("teamPageSearch");
  if(searchInput){
    attachAutocomplete(searchInput);
    searchInput.addEventListener("input", e => {
      teamPage.team = e.target.value;
      const pos = e.target.selectionStart;
      renderTeamPage();
      const ni = document.getElementById("teamPageSearch");
      if(ni){ ni.focus(); ni.setSelectionRange(pos, pos); }
    });
  }

  try{ localStorage.setItem("euroleague-team-page", teamPage.team); }catch(e){}
}

function findTeamFromQuery(query, rows){
  if(!query) return null;
  const q = query.toUpperCase().trim();
  let t = rows.find(r => r.team.toUpperCase() === q);
  if(t) return t;
  t = rows.find(r => r.team.toUpperCase().startsWith(q));
  if(t) return t;
  t = rows.find(r => r.team.toUpperCase().includes(q));
  return t || null;
}

function arrayToGame(g){
  return {
    round: g[0],
    day: g[1],
    date: g[2],
    utc: g[3],
    local: g[4],
    home: g[5],
    away: g[6],
    hs: g[7],
    aw: g[8]
  };
}