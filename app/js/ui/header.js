// ============================================================
// HEADER — renderHeader + updateToolbarHeight
// ============================================================

function renderHeader(){
  const played = games.filter(g => g[7] !== null && g[8] !== null).length;
  const total = games.length;
  const pct = total ? (played / total * 100) : 0;
  document.getElementById("progressFill").style.width = pct + "%";
  document.getElementById("progressText").textContent =
    `${played} / ${total} games · ${pct.toFixed(1)}% complete`;

  const rows = computeStandings();
  const playedRows = rows.filter(r => r.GP > 0);
  const leader = playedRows[0];
  const bestOff = playedRows.slice().sort((a,b)=>b.PF - a.PF)[0];
  if(!leader){
    document.getElementById("headerMiniStats").innerHTML = "";
    return;
  }
  document.getElementById("headerMiniStats").innerHTML = `
    <div class="mini-stat">
      <span class="lbl">🏆 Leader</span>
      <span class="val">${logoHTML(leader.team)} ${leader.team.replace(/ .*$/,"")} <span class="dot"></span></span>
    </div>
    <div class="mini-stat">
      <span class="lbl">🔥 Best Offense</span>
      <span class="val">${logoHTML(bestOff.team)} ${bestOff.PF} pts</span>
    </div>
  `;
}

function updateToolbarHeight(){
  const activeView = document.querySelector(".view.active");
  const isGames = activeView && activeView.id === "view-games";

  if(isGames){
    const tb = document.querySelector("#view-games .sticky-toolbar");
    if(tb){
      document.documentElement.style.setProperty(
        "--toolbar-h",
        tb.offsetHeight + "px"
      );
      return;
    }
  }
  document.documentElement.style.setProperty("--toolbar-h", "0px");
}