// ============================================================
// GAMES VIEW — renderGames, renderRoundNav, scroll spy, LIVE
// ============================================================

let scrollSpyScheduled = false;
let liveIntervalId = null;

// ---- GR TIME (UTC/CET + 1h → Ελλάδα) ----
// ---- GR TIME (UTC + offset Ελλάδας με DST) ----
// Το data.js [3] = LOCAL, [4] = GMT/UTC
// Δέχεται "HH:MM" (GMT) + "YYYY-MM-DD" (date για DST)
function toGRTime(gmtStr, dateStr){
  if(!gmtStr) return "—";
  const [hh, mm] = gmtStr.split(":").map(Number);
  const offset = grOffsetHours(dateStr);
  const grHour = (hh + offset + 24) % 24;
  return String(grHour).padStart(2, "0") + ":" + String(mm).padStart(2, "0");
}

// Επιστρέφει 2 (χειμώνας) ή 3 (καλοκαίρι) — Ελληνική DST
function grOffsetHours(dateStr){
  if(!dateStr) return 2; // default χειμώνας
  const d = new Date(dateStr + "T12:00:00Z");
  const year = d.getUTCFullYear();

  // Τελευταία Κυριακή Μαρτίου (03:00 UTC = DST start)
  const dstStart = lastSundayOfMonth(year, 2); // 2 = March
  // Τελευταία Κυριακή Οκτωβρίου (04:00 UTC = DST end)
  const dstEnd = lastSundayOfMonth(year, 9);   // 9 = October

  if (d >= dstStart && d < dstEnd) {
    return 3; // καλοκαίρι
  }
  return 2;   // χειμώνας
}

// Επιστρέφει Date object για την τελευταία Κυριακή του μήνα (μήνας 0-11)
function lastSundayOfMonth(year, monthIdx){
  const lastDay = new Date(Date.UTC(year, monthIdx + 1, 0));
  const day = lastDay.getUTCDay(); // 0=Κυρ, 1=Δευτ, ...
  const offset = day; // Πόσες μέρες πίσω για Κυριακή
  const sunday = new Date(Date.UTC(year, monthIdx + 1, 0 - offset));
  return sunday;
}

// ---- SHORT DATE (2026-09-29 → 29 Sep) ----
function toShortDate(isoDate){
  if(!isoDate) return "—";
  const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  const [y,m,d] = isoDate.split("-");
  return `${parseInt(d,10)} ${MONTHS[parseInt(m,10)-1]}`;
}

// ---- LIVE STATUS ----
function isGameLive(date, utcStr){
  if(!date || !utcStr) return false;
  // Το utc field = ώρα Κεντρικής Ευρώπης
  // Θεωρούμε CEST (+02:00) για τη σεζόν (Σεπ-Απρ, εκτός DST χειμώνα)
  // Για απλότητα: -2h offset → UTC timestamp
  try{
    const start = new Date(`${date}T${utcStr}:00Z`).getTime();
    const end   = start + 2 * 60 * 60 * 1000;
    const now   = Date.now();
    return now >= start && now <= end;
  }catch(e){
    return false;
  }
}

function liveBadgeHTML(date, utcStr, hs, aw){
  if(isGameLive(date, utcStr)){
    return `<span class="live-badge">LIVE</span>`;
  }
  return `<span class="live-badge off">—</span>`;
}

// ---- AUTO-REFRESH LIVE (μόνο τα badges, χωρίς full render) ----
function startLiveRefresh(){
  stopLiveRefresh();
  liveIntervalId = setInterval(() => {
    const cells = document.querySelectorAll("#view-games .live-cell");
    if(!cells.length) return;
    cells.forEach(cell => {
      const date = cell.dataset.date;
      const utc  = cell.dataset.utc;
      cell.innerHTML = liveBadgeHTML(date, utc);
    });
  }, 60000); // κάθε 60 sec
}

function stopLiveRefresh(){
  if(liveIntervalId){
    clearInterval(liveIntervalId);
    liveIntervalId = null;
  }
}

// ---- SCROLL SPY ----
function initScrollSpy(){
  const mainEl = document.querySelector("main");
  if(!mainEl) return;
  if(mainEl.dataset.spyInit === "1") return;
  mainEl.dataset.spyInit = "1";

  mainEl.addEventListener("scroll", () => {
    if(scrollSpyScheduled) return;
    scrollSpyScheduled = true;
    requestAnimationFrame(() => {
      scrollSpyScheduled = false;
      updateCurrentRoundFromScroll();
    });
  });
}

function setActiveRound(r){
  if(r === activeRound) return;
  activeRound = r;

  const nav = document.getElementById("roundNav");
  if(!nav) return;

  nav.querySelectorAll("button").forEach(x =>
    x.classList.toggle("active", +x.dataset.round === r)
  );

  const activeBtn = nav.querySelector("button.active");
  if(activeBtn){
    nav.scrollTo({
      left: activeBtn.offsetLeft - nav.clientWidth / 2 + activeBtn.clientWidth / 2,
      behavior: "smooth"
    });
  }
}

function updateCurrentRoundFromScroll(){
  const mainEl = document.querySelector("main");
  const roundRows = document.querySelectorAll("tr[data-round-start]");
  if(!roundRows.length) return;

  const isAtBottom =
    mainEl.scrollTop + mainEl.clientHeight >= mainEl.scrollHeight - 8;
  if(isAtBottom){
    const lastRound = +roundRows[roundRows.length - 1].dataset.roundStart;
    setActiveRound(lastRound);
    return;
  }

  const mainRect = mainEl.getBoundingClientRect();
  const toolbarH = parseFloat(
    getComputedStyle(document.documentElement).getPropertyValue("--toolbar-h")
  ) || 0;

  const checkLine = mainRect.top + toolbarH + 30;

  let currentRound = activeRound;
  roundRows.forEach(row => {
    const rect = row.getBoundingClientRect();
    if(rect.top <= checkLine){
      currentRound = +row.dataset.roundStart;
    }
  });

  setActiveRound(currentRound);
}

function renderRoundNav(){
  const rounds = [...new Set(games.map(g => g[0]))].sort((a,b)=>a-b);
  const nav = document.getElementById("roundNav");
  if(!nav) return;
  nav.innerHTML = rounds.map(r =>
    `<button data-round="${r}" class="${r === activeRound ? 'active' : ''}">R${r}</button>`
  ).join("");
  nav.querySelectorAll("button").forEach(b => {
    b.addEventListener("click", () => {
      const r = +b.dataset.round;
      activeRound = r;
      const target = document.querySelector(`tr[data-round-start="${r}"]`);
      if(target){
        const mainEl = document.querySelector("main");
        const navHeight = nav.offsetHeight;
        const offset = target.offsetTop - navHeight - 8;
        mainEl.scrollTo({ top: offset, behavior: "smooth" });
      }
      nav.querySelectorAll("button").forEach(x =>
        x.classList.toggle("active", +x.dataset.round === r));
    });
  });
  const activeBtn = nav.querySelector("button.active");
  if(activeBtn){
    nav.scrollTo({
      left: activeBtn.offsetLeft - nav.clientWidth / 2 + activeBtn.clientWidth / 2,
      behavior: "instant"
    });
  }
}

// ---- GO TO H2H (VS link) ----
function goToH2H(home, away){
  h2hView.team1 = home;
  h2hView.team2 = away;

  document.querySelectorAll("nav.tabs button").forEach(b => b.classList.remove("active"));
  document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));

  const h2hBtn = document.querySelector('nav.tabs button[data-view="h2h"]');
  if(h2hBtn) h2hBtn.classList.add("active");

  const h2hViewEl = document.getElementById("view-h2h");
  if(h2hViewEl) h2hViewEl.classList.add("active");

  if(typeof updateTabUnderline === "function") updateTabUnderline();
  if(typeof applyStaggerIndexes === "function") applyStaggerIndexes();
  if(typeof updateToolbarHeight === "function") updateToolbarHeight();

  renderH2H();
}

// ---- MAIN RENDER ----
function renderGames(){
  const el = document.getElementById("view-games");

  let html = `<div class="sticky-toolbar">
    <div class="h2h-search">
      <input type="text" class="h2h-input" id="h2hTeam1"
             placeholder="🔍 Team 1..." value="${gamesFilter.team1}"
             autocomplete="off">
      <span class="h2h-vs">VS</span>
      <input type="text" class="h2h-input" id="h2hTeam2"
             placeholder="🔍 Team 2..." value="${gamesFilter.team2}"
             autocomplete="off">
      <button class="h2h-clear" id="h2hClear" title="Καθαρισμός">✕</button>
    </div>
    <div class="round-nav" id="roundNav"></div>
  </div>
  <div class="h2h-info" id="h2hInfo"></div>`;

  html += `<table><thead><tr>
    <th class="num">R</th>
    <th>Date</th>
    <th class="center">GR Time</th>
    <th class="center">Live</th>
    <th>Home Team</th>
    <th class="center">Score</th>
    <th class="center">VS</th>
    <th class="center">Score</th>
    <th>Away Team</th>
    <th>Winner</th>
  </tr></thead><tbody>`;

  const t1 = gamesFilter.team1.trim().toUpperCase();
  const t2 = gamesFilter.team2.trim().toUpperCase();

  let filteredCount = 0;
  let lastRound = null;
  let h2hStats = { t1Name: null, t2Name: null, t1Wins: 0, t2Wins: 0, games: 0 };

  games.sort((a, b) => {
    if (a[0] !== b[0]) return a[0] - b[0];
    if (a[2] !== b[2]) return a[2].localeCompare(b[2]);
    return a[4].localeCompare(b[4]);
  });
  games.forEach((g, idx) => {
    const [round, day, date, local, utc, home, away, hs, aw] = g;

    const homeMatch1 = matchTeam(home, t1);
    const awayMatch1 = matchTeam(away, t1);
    const homeMatch2 = matchTeam(home, t2);
    const awayMatch2 = matchTeam(away, t2);

    let include = false;
    if(t1 && !t2){
      include = homeMatch1 || awayMatch1;
    } else if(!t1 && t2){
      include = homeMatch2 || awayMatch2;
    } else if(t1 && t2){
      include = (homeMatch1 && awayMatch2) || (awayMatch1 && homeMatch2);
    } else {
      include = true;
    }

    if(!include) return;
    filteredCount++;

    if(t1 && t2 && hs !== null && aw !== null){
      if(!h2hStats.t1Name){
        h2hStats.t1Name = homeMatch1 ? home : away;
        h2hStats.t2Name = homeMatch2 ? home : away;
      }
      h2hStats.games++;
      const winner = hs > aw ? home : away;
      if(matchTeam(winner, t1)) h2hStats.t1Wins++;
      else if(matchTeam(winner, t2)) h2hStats.t2Wins++;
    }

    if(round !== lastRound){
      html += `<tr class="round-sep" data-round-start="${round}"><td colspan="10">Round ${round}</td></tr>`;
      lastRound = round;
    }

    const homeWin = hs !== null && aw !== null && hs > aw;
    const awayWin = hs !== null && aw !== null && aw > hs;
    const winner = homeWin ? home : awayWin ? away : "";
    const homeClass = homeWin ? "winner-home" : "";
    const awayClass = awayWin ? "winner-away" : "";
    const disabled = CONFIG.scoreInputEnabled ? "" : "readonly";

    const grTime  = toGRTime(utc, date);
    const liveHTML = liveBadgeHTML(date, utc, hs, aw);

    html += `<tr data-idx="${idx}" class="${homeClass} ${awayClass}">
      <td class="num">${round}</td>
      <td style="white-space:nowrap">${toShortDate(date)}</td>
      <td class="center">${grTime}</td>
      <td class="center live-cell" data-date="${date}" data-utc="${utc}">${liveHTML}</td>
      <td class="home-col"><div class="team-cell">${logoHTML(home)}<span>${home}</span></div></td>
      <td class="center"><input type="number" class="score" data-idx="${idx}" data-side="h" value="${hs ?? ""}" min="0" ${disabled}></td>
      <td class="center">
        <a class="vs-link" data-home="${escapeHtml(home)}" data-away="${escapeHtml(away)}" title="Head-to-Head: ${escapeHtml(home)} vs ${escapeHtml(away)}">VS</a>
      </td>
      <td class="center"><input type="number" class="score" data-idx="${idx}" data-side="a" value="${aw ?? ""}" min="0" ${disabled}></td>
      <td class="away-col"><div class="team-cell">${logoHTML(away)}<span>${away}</span></div></td>
      <td class="winner-cell">${winner ? logoHTML(winner) + winner : "<span style='color:var(--muted2)'>—</span>"}</td>
    </tr>`;
  });

  if(filteredCount === 0){
    html += `<tr><td colspan="10" style="text-align:center;padding:40px;color:var(--muted)">
      Δεν βρέθηκαν παιχνίδια με αυτά τα φίλτρα.
    </td></tr>`;
  }

  html += `</tbody></table>`;
  el.innerHTML = html;

  // --- H2H INFO BAR ---
  const infoEl = document.getElementById("h2hInfo");
  if(infoEl){
    if(t1 && t2 && h2hStats.games > 0){
      const t1Name = h2hStats.t1Name || gamesFilter.team1;
      const t2Name = h2hStats.t2Name || gamesFilter.team2;
      const leader = h2hStats.t1Wins > h2hStats.t2Wins ? t1Name
                    : h2hStats.t2Wins > h2hStats.t1Wins ? t2Name : null;
      infoEl.innerHTML = `
        <div class="h2h-badge">
          <span class="h2h-team">${logoHTML(t1Name)} ${t1Name}</span>
          <span class="h2h-score-badge">${h2hStats.t1Wins} - ${h2hStats.t2Wins}</span>
          <span class="h2h-team">${t2Name} ${logoHTML(t2Name)}</span>
        </div>
        ${leader ? `<span class="h2h-leader">Προηγείται: <b>${leader}</b></span>` : `<span class="h2h-leader">Ισοπαλία</span>`}
        <span class="h2h-count">${h2hStats.games} παιχνίδια</span>
      `;
    } else if(t1 || t2){
      infoEl.innerHTML = `<span class="h2h-count">${filteredCount} παιχνίδια</span>`;
    } else {
      infoEl.innerHTML = `<span class="h2h-count">${games.length} παιχνίδια συνολικά</span>`;
    }
  }

  renderRoundNav();

  // --- AUTOCOMPLETE ---
  attachAutocomplete(document.getElementById("h2hTeam1"));
  attachAutocomplete(document.getElementById("h2hTeam2"));

  const in1 = document.getElementById("h2hTeam1");
  const in2 = document.getElementById("h2hTeam2");
  const clearBtn = document.getElementById("h2hClear");

  if(in1){
    in1.addEventListener("input", e => {
      gamesFilter.team1 = e.target.value;
      const pos = e.target.selectionStart;
      renderGames();
      const ni = document.getElementById("h2hTeam1");
      if(ni){ ni.focus(); ni.setSelectionRange(pos, pos); }
    });
  }
  if(in2){
    in2.addEventListener("input", e => {
      gamesFilter.team2 = e.target.value;
      const pos = e.target.selectionStart;
      renderGames();
      const ni = document.getElementById("h2hTeam2");
      if(ni){ ni.focus(); ni.setSelectionRange(pos, pos); }
    });
  }
  if(clearBtn){
    clearBtn.addEventListener("click", () => {
      gamesFilter = { team1: "", team2: "" };
      renderGames();
    });
  }

  // --- SCORE INPUTS ---
  if(CONFIG.scoreInputEnabled){
    el.querySelectorAll("input.score").forEach(inp => {
      inp.addEventListener("change", e => {
        const idx = +e.target.dataset.idx;
        const side = e.target.dataset.side;
        const val = e.target.value.trim();
        const scoreIdx = side === "h" ? 7 : 8;
        games[idx][scoreIdx] = val === "" ? null : Math.max(0, parseInt(val, 10));
        saveGames();
        renderGames();
        renderStandings();
        renderDashboard();
        renderHeader();
      });
      inp.addEventListener("keydown", e => {
        if(e.key === "Enter") e.target.blur();
      });
    });
  }

  // --- VS LINKS ---
  el.querySelectorAll(".vs-link").forEach(link => {
    link.addEventListener("click", e => {
      e.preventDefault();
      const home = link.dataset.home;
      const away = link.dataset.away;
      if(home && away) goToH2H(home, away);
    });
  });

  setTimeout(updateToolbarHeight, 0);
  initScrollSpy();
  startLiveRefresh();
}