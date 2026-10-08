// ============================================================
// BRACKET VIEW
// ============================================================

function renderBracket(){
  const el = document.getElementById("view-bracket");
  if(!el) return;

  const hasRealPlayoffs = typeof PLAYOFF_GAMES !== "undefined" && PLAYOFF_GAMES.length > 0;

  if(hasRealPlayoffs){
    renderRealBracket(el);
  } else {
    renderProjectionBracket(el);
  }
}

function renderProjectionBracket(el){
  const rows = computeStandings();
  const playedRows = rows.filter(r => r.GP > 0);

  if(playedRows.length < 8){
    el.innerHTML = `<div class="empty">
      <span class="icon">🏆</span>
      <p>Δεν υπάρχουν αρκετά δεδομένα ακόμα.</p>
      <p style="margin-top:8px;font-size:12px;color:var(--muted2)">
        Χρειάζονται τουλάχιστον 8 ομάδες με παιχνίδια
      </p>
    </div>`;
    return;
  }

  const t1 = playedRows[0], t2 = playedRows[1], t3 = playedRows[2], t4 = playedRows[3];
  const t5 = playedRows[4], t6 = playedRows[5], t7 = playedRows[6], t8 = playedRows[7];
  const t9 = playedRows[8] || null;
  const t10 = playedRows[9] || null;

  el.innerHTML = `
    <div class="bracket-header">
      <h2>🏆 Playoff Projection</h2>
      <p>Αν η σεζόν τελείωνε σήμερα · <span style="color:var(--accent);font-weight:700">Projection mode</span></p>
    </div>

    <div class="bracket">
      <div class="bracket-round">
        <div class="bracket-round-title">Quarterfinals</div>
        ${bracketMatch(t1, t8)}
        ${bracketMatch(t4, t5)}
      </div>

      <div class="bracket-round bracket-semis">
        <div class="bracket-round-title">Semifinal 1</div>
        <div class="bracket-slot">
          <div class="bracket-slot-label">Winner QF1</div>
          <div class="bracket-slot-vs">VS</div>
          <div class="bracket-slot-label">Winner QF2</div>
        </div>
      </div>

      <div class="bracket-round bracket-final">
        <div class="bracket-round-title">🏆 Final</div>
        <div class="bracket-slot bracket-slot-final">
          <div class="bracket-slot-label">Winner SF1</div>
          <div class="bracket-slot-vs">VS</div>
          <div class="bracket-slot-label">Winner SF2</div>
        </div>
      </div>

      <div class="bracket-round bracket-semis">
        <div class="bracket-round-title">Semifinal 2</div>
        <div class="bracket-slot">
          <div class="bracket-slot-label">Winner QF3</div>
          <div class="bracket-slot-vs">VS</div>
          <div class="bracket-slot-label">Winner QF4</div>
        </div>
      </div>

      <div class="bracket-round">
        <div class="bracket-round-title">Quarterfinals</div>
        ${bracketMatch(t2, t7)}
        ${bracketMatch(t3, t6)}
      </div>
    </div>

    <div class="playin-section">
      <div class="bracket-round-title">🎯 Play-In Tournament (7–10)</div>
      <div class="playin-grid">
        <div class="playin-match">
          <div class="playin-match-label">Game A · Winner → Playoffs (#7)</div>
          ${playinTeam(t7, 7)}
          ${playinTeam(t8, 8)}
        </div>
        <div class="playin-match">
          <div class="playin-match-label">Game B · Winner → vs Loser Game A</div>
          ${playinTeam(t9, 9)}
          ${playinTeam(t10, 10)}
        </div>
      </div>
    </div>

    <div class="bracket-note">
      💡 <b>Projection mode:</b> Δεν έχουν καταχωρηθεί playoff games ακόμα. Όταν προστεθούν στο <code>PLAYOFF_GAMES</code>, αυτό το tab θα δείχνει πραγματικά αποτελέσματα.
    </div>
  `;
}

function renderRealBracket(el){
  const byRound = {};
  PLAYOFF_GAMES.forEach(g => {
    const r = g[0];
    if(!byRound[r]) byRound[r] = [];
    byRound[r].push(g);
  });

  const playinGames = [...(byRound[1] || []), ...(byRound[2] || [])];
  const qfGames = byRound[3] || [];
  const sfGames = byRound[4] || [];
  const finalGames = byRound[5] || [];

  el.innerHTML = `
    <div class="bracket-header">
      <h2>🏆 Playoffs · Live Bracket</h2>
      <p><span style="color:#10b981;font-weight:700">● Real mode</span> — Δείχνει πραγματικά αποτελέσματα</p>
    </div>

    ${playinGames.length ? `
      <div class="playin-section">
        <div class="bracket-round-title">🎯 Play-In Tournament</div>
        <div class="playin-grid">
          ${playinGames.map(g => realGameCard(g)).join("")}
        </div>
      </div>
    ` : ""}

    <div class="bracket">
      ${renderRealRound("Quarterfinals (QF1)", qfGames.filter((_,i) => i % 2 === 0))}
      ${renderRealRound("Semifinal 1", sfGames.filter((_,i) => i === 0))}
      ${renderRealRound("🏆 Final", finalGames)}
      ${renderRealRound("Semifinal 2", sfGames.filter((_,i) => i === 1))}
      ${renderRealRound("Quarterfinals (QF2)", qfGames.filter((_,i) => i % 2 === 1))}
    </div>
  `;
}

function renderRealRound(title, games){
  if(!games.length){
    return `<div class="bracket-round">
      <div class="bracket-round-title">${title}</div>
      <div class="bracket-slot">
        <div class="bracket-slot-label">Αναμένεται</div>
      </div>
    </div>`;
  }
  return `<div class="bracket-round">
    <div class="bracket-round-title">${title}</div>
    ${games.map(g => realGameCard(g)).join("")}
  </div>`;
}

function realGameCard(g){
  const [round, day, date, utc, local, home, away, hs, aw] = g;
  const isPlayed = hs !== null && aw !== null;
  const homeWin = isPlayed && hs > aw;
  const awayWin = isPlayed && aw > hs;

  return `<div class="bracket-match">
    <div class="bracket-team ${homeWin ? "winner" : ""}">
      <span class="bracket-logo">${logoHTML(home)}</span>
      <span class="bracket-name">${home}</span>
      <span class="bracket-score">${isPlayed ? hs : "—"}</span>
    </div>
    <div class="bracket-team ${awayWin ? "winner" : ""}">
      <span class="bracket-logo">${logoHTML(away)}</span>
      <span class="bracket-name">${away}</span>
      <span class="bracket-score">${isPlayed ? aw : "—"}</span>
    </div>
    <div class="bracket-game-date">${date} · ${utc}</div>
  </div>`;
}

function bracketMatch(teamA, teamB){
  return `<div class="bracket-match">
    ${bracketTeam(teamA)}
    ${bracketTeam(teamB)}
  </div>`;
}

function bracketTeam(t){
  if(!t) return `<div class="bracket-team empty">—</div>`;
  const rank = computeStandings().findIndex(x => x.team === t.team) + 1;
  return `<div class="bracket-team">
    <span class="bracket-rank">${rank}</span>
    <span class="bracket-logo">${logoHTML(t.team)}</span>
    <span class="bracket-name">${t.team}</span>
    <span class="bracket-record">${t.W}-${t.L}</span>
  </div>`;
}

function playinTeam(t, seed){
  if(!t) return `<div class="playin-team empty">—</div>`;
  return `<div class="playin-team">
    <span class="bracket-rank">${seed}</span>
    <span class="bracket-logo">${logoHTML(t.team)}</span>
    <span class="bracket-name">${t.team}</span>
    <span class="bracket-record">${t.W}-${t.L}</span>
  </div>`;
}