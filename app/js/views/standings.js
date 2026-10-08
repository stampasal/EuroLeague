// ============================================================
// STANDINGS VIEW
// ============================================================

function renderStandings(){
  const rows = computeStandings();
  const rankChanges = computeRankChanges();
  const el = document.getElementById("view-standings");

  let html = `<div class="toolbar">
    <input type="text" class="search-input" id="searchStandings" placeholder="🔍 Search team..." value="${standingsFilter}">
    <div class="legend">
      <span><span class="swatch" style="background:#10b981"></span>Top ${CONFIG.playoffTeams}</span>
      <span><span class="swatch" style="background:#f59e0b"></span>Play-In ${CONFIG.playoffTeams+1}–${CONFIG.playInTeams}</span>
    </div>
  </div>`;

  html += `<table><thead><tr>
    <th class="center">#</th>
    <th>Club</th>
    <th class="center">STRK</th>
    <th class="num">GP</th><th class="num">W</th><th class="num">L</th>
    <th class="num">Win%</th>
    <th class="num">PTS+</th><th class="num">PTS-</th><th class="num">+/-</th>
    <th class="center">H</th><th class="center">A</th>
    <th class="num">OT</th>
    ${CONFIG.showL10 ? "<th>L10</th>" : ""}
    <th class="num">TW</th><th class="num">TD</th><th class="num">TPF</th>
  </tr></thead><tbody>`;

  const filter = standingsFilter.trim().toUpperCase();
  rows.forEach((t, i) => {
    if(filter && !t.team.includes(filter)) return;
    const rank = i + 1;
    const rankClass = rank <= CONFIG.playoffTeams ? "qual"
                    : rank <= CONFIG.playInTeams ? "playin" : "";
    const zoneClass = rank <= CONFIG.playoffTeams ? "zone-top"
                    : rank <= CONFIG.playInTeams ? "zone-playin" : "zone-out";
    const l10 = t.last10.split("").map(c => `<span class="${c}">${c}</span>`).join("");
    const streakClass = t.streakType === "W" ? "streak-w" : t.streakType === "L" ? "streak-l" : "";
    const streakText = t.streak > 0 ? `${t.streakType}${t.streak}` : "—";
    const change = rankChanges[t.team] || 0;
    let arrowHTML = '<span class="rank-arrow"></span>';
    if(change > 0)      arrowHTML = '<span class="rank-arrow up">▲</span>';
    else if(change < 0) arrowHTML = '<span class="rank-arrow down">▼</span>';
    html += `<tr class="standings-row ${zoneClass} clickable-row" data-team="${escapeHtml(t.team)}" style="--team-color:${teamColor(t.team)}">
    <td class="center rank ${rankClass}"><span class="rank-cell">${arrowHTML}<span class="rank-num">${rank}</span></span></td>
      <td><div class="team-cell">${logoHTML(t.team)}<span>${t.team}</span></div></td>
      <td class="center"><span class="streak ${streakClass}">${streakText}</span></td>
      <td class="num">${t.GP}</td>
      <td class="num"><b>${t.W}</b></td>
      <td class="num">${t.L}</td>
      <td class="num">${(t.winPct*100).toFixed(1)}%</td>
      <td class="num">${t.PF}</td><td class="num">${t.PA}</td>
      <td class="num">${t.diff > 0 ? "+" : ""}${t.diff}</td>
      <td class="center">${t.hW}-${t.hL}</td>
      <td class="center">${t.aW}-${t.aL}</td>
      <td class="num">0</td>
      ${CONFIG.showL10 ? `<td class="l10">${l10 || "<span style='color:var(--muted2)'>—</span>"}</td>` : ""}
      <td class="num">${t.tieWins}</td>
      <td class="num">${t.tieDiff}</td>
      <td class="num">${t.tiePF}</td>
    </tr>`;
  });
  html += `</tbody></table>`;
  el.innerHTML = html;

  el.querySelectorAll("tr.clickable-row").forEach(row => {
    row.addEventListener("click", () => {
      const team = row.dataset.team;
      if(team){
        teamPage.team = team;
        document.querySelectorAll("nav.tabs button").forEach(b => b.classList.remove("active"));
        document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
        document.querySelector('nav.tabs button[data-view="team"]').classList.add("active");
        document.getElementById("view-team").classList.add("active");
	  if(typeof updateTabUnderline === "function") updateTabUnderline();
      if(typeof applyStaggerIndexes === "function") applyStaggerIndexes();
      if(typeof updateToolbarHeight === "function") updateToolbarHeight();
        renderTeamPage();
      }
    });
  });

  const inp = document.getElementById("searchStandings");
  if(inp){
    inp.addEventListener("input", e => {
      standingsFilter = e.target.value;
      const pos = e.target.selectionStart;
      renderStandings();
      const ni = document.getElementById("searchStandings");
      ni.focus(); ni.setSelectionRange(pos, pos);
    });
    attachAutocomplete(inp);
  }
}