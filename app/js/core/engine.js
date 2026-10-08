// ============================================================
// ENGINE — standings, H2H, evolution, tiebreakers
// ============================================================

// ---- CORE: υπολογισμός standings από ένα υποσύνολο games ----
function _computeStandingsFromGames(gamesList){
  const stats = {};
  TEAMS.forEach(t => {
    stats[t] = {
      team: t,
      GP: 0, W: 0, L: 0,
      PF: 0, PA: 0, diff: 0,
      hW: 0, hL: 0, aW: 0, aL: 0,
      results: []   // χρονολογική σειρά "W"/"L"
    };
  });

  gamesList.forEach(g => {
    const home = g[5], away = g[6], hs = g[7], aw = g[8];
    if(hs === null || aw === null) return;
    if(!stats[home] || !stats[away]) return;

    const H = stats[home], A = stats[away];

    H.GP++;  A.GP++;
    H.PF += hs; H.PA += aw;
    A.PF += aw; A.PA += hs;

    if(hs > aw){
      H.W++; A.L++;
      H.hW++; A.aL++;
      H.results.push("W");
      A.results.push("L");
    } else if(aw > hs){
      A.W++; H.L++;
      A.aW++; H.hL++;
      H.results.push("L");
      A.results.push("W");
    }
  });

  const rows = Object.values(stats).map(s => {
    s.diff     = s.PF - s.PA;
    s.winPct   = s.GP > 0 ? s.W / s.GP : 0;

    // Last 10 (τελευταία 10 αποτελέσματα)
    s.last10 = s.results.slice(-10).join("");

    // Streak (τρέχον σερί)
    let streak = 0, streakType = "";
    for(let i = s.results.length - 1; i >= 0; i--){
      if(streak === 0){
        streakType = s.results[i];
        streak = 1;
      } else if(s.results[i] === streakType){
        streak++;
      } else {
        break;
      }
    }
    s.streak     = streak;
    s.streakType = streakType;

    // Tiebreaker display columns
    s.tieWins = s.W;
    s.tieDiff = s.diff;
    s.tiePF   = s.PF;

    return s;
  });

  // ---- SORT: Win% → H2H → diff → PF ----
  rows.sort((a, b) => {
    if(b.winPct !== a.winPct) return b.winPct - a.winPct;

    const h2h = _headToHeadWins(a.team, b.team, gamesList);
    if(h2h !== 0) return h2h;

    if(b.diff !== a.diff) return b.diff - a.diff;
    if(b.PF   !== a.PF)   return b.PF   - a.PF;
    return a.team.localeCompare(b.team);
  });

  return rows;
}

function _headToHeadWins(teamA, teamB, gamesList){
  let aWins = 0, bWins = 0;
  gamesList.forEach(g => {
    const home = g[5], away = g[6], hs = g[7], aw = g[8];
    if(hs === null || aw === null) return;
    if(home === teamA && away === teamB){
      if(hs > aw) aWins++; else if(aw > hs) bWins++;
    } else if(home === teamB && away === teamA){
      if(hs > aw) bWins++; else if(aw > hs) aWins++;
    }
  });
  return bWins - aWins;   // αρνητικό = A κερδίζει tiebreaker
}

// ---- PUBLIC: standings ----
function computeStandings(){
  return _computeStandingsFromGames(games);
}

// ---- PUBLIC: rank changes (σύγκριση με πριν το τελευταίο round) ----
function computeRankChanges(){
  const current = computeStandings();
  const currentRanks = {};
  current.forEach((r, i) => currentRanks[r.team] = i + 1);

  let maxPlayedRound = 0;
  games.forEach(g => {
    if(g[7] !== null && g[8] !== null && g[0] > maxPlayedRound){
      maxPlayedRound = g[0];
    }
  });

  const changes = {};
  if(maxPlayedRound <= 0){
    TEAMS.forEach(t => changes[t] = 0);
    return changes;
  }

  // Αφαιρούμε τα games του τελευταίου round
  const prevGames = games.filter(g => {
    if(g[0] < maxPlayedRound) return true;
    if(g[7] === null || g[8] === null) return true;
    return false;
  });

  const prev = _computeStandingsFromGames(prevGames);
  const prevRanks = {};
  prev.forEach((r, i) => prevRanks[r.team] = i + 1);

  TEAMS.forEach(t => {
    const now    = currentRanks[t] || 20;
    const before = prevRanks[t]    || 20;
    changes[t]   = before - now;   // > 0 = ανέβηκε
  });

  return changes;
}

// ---- PUBLIC: evolution (rank ανά round) ----
function computeStandingsEvolution(){
  let lastRound = 0;
  games.forEach(g => {
    if(g[7] !== null && g[8] !== null && g[0] > lastRound){
      lastRound = g[0];
    }
  });

  const evolution = {};
  TEAMS.forEach(t => evolution[t] = []);

  for(let r = 1; r <= lastRound; r++){
    const gamesUpToR = games.filter(g => g[0] <= r);
    const rows = _computeStandingsFromGames(gamesUpToR);
    rows.forEach((row, i) => {
      if(row.GP > 0){
        evolution[row.team].push({ round: r, rank: i + 1 });
      }
    });
  }

  return { evolution, lastRound };
}

// ---- PUBLIC: H2H ----
function _findTeam(query, rows){
  if(!query) return null;
  const q = String(query).toUpperCase().trim();
  if(!q) return null;

  let t = rows.find(r => r.team.toUpperCase() === q);
  if(t) return t;
  t = rows.find(r => r.team.toUpperCase().startsWith(q));
  if(t) return t;
  t = rows.find(r => r.team.toUpperCase().includes(q));
  return t || null;
}

function computeH2H(q1, q2){
  if(!q1 || !q2) return null;

  const rows = computeStandings();
  const t1   = _findTeam(q1, rows);
  const t2   = _findTeam(q2, rows);

  if(!t1 || !t2 || t1.team === t2.team) return null;

  const h2hGames = games
    .filter(g => {
      const home = g[5], away = g[6];
      return (home === t1.team && away === t2.team) ||
             (home === t2.team && away === t1.team);
    })
    .map(g => ({
      round: g[0], day: g[1], date: g[2], utc: g[3], local: g[4],
      home:  g[5], away: g[6], hs:   g[7], aw:   g[8]
    }))
    .sort((a, b) => {
      if(a.date !== b.date) return a.date < b.date ? -1 : 1;
      return (a.utc || "").localeCompare(b.utc || "");
    });

  let t1Wins = 0, t2Wins = 0, played = 0;
  let t1PF   = 0, t2PF   = 0;

  h2hGames.forEach(g => {
    if(g.hs === null || g.aw === null) return;
    played++;
    const homeIsT1 = g.home === t1.team;
    const t1Score  = homeIsT1 ? g.hs : g.aw;
    const t2Score  = homeIsT1 ? g.aw : g.hs;
    t1PF += t1Score;
    t2PF += t2Score;
    if(t1Score > t2Score) t1Wins++;
    else if(t2Score > t1Score) t2Wins++;
  });

  return {
    team1: t1.team,
    team2: t2.team,
    games: h2hGames,
    played,
    t1Wins,
    t2Wins,
    t1PF,
    t2PF,
    t1Diff: t1PF - t2PF
  };
}

// ---- PUBLIC: match team name vs query ----
function matchTeam(name, query){
  if(!name || !query) return false;
  return name.toUpperCase().includes(query.toUpperCase());
}

// ---- PUBLIC: season complete check ----
function checkSeasonComplete(){
  if(!games.length) return;
  const allPlayed = games.every(g => g[7] !== null && g[8] !== null);
  if(!allPlayed) return;

  let already = false;
  try{ already = sessionStorage.getItem("euroleague-season-celebrated") === "1"; }catch(e){}
  if(already) return;

  try{ sessionStorage.setItem("euroleague-season-celebrated", "1"); }catch(e){}

  if(typeof fireConfetti === "function"){
    setTimeout(fireConfetti, 500);
  }
}