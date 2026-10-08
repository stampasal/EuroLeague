// ============================================================
// VIEWS — μόνο renderAll
// Όλα τα views είναι σε ξεχωριστά files στο js/views/
// ============================================================

function renderAll(){
  renderGames();
  renderStandings();
  renderDashboard();
  renderHeader();
  renderH2H();
  renderBracket();
  renderTeamPage();
  renderCharts();
  renderFantasy();
  if(typeof renderCoaches === "function") renderCoaches();
  if(typeof renderFantasyTeam === "function") renderFantasyTeam();
  if(typeof checkSeasonComplete === "function") checkSeasonComplete();
}