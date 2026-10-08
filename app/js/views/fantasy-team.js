// ============================================================
// FANTASY TEAM OPTIMIZER — v5 (καθαρή έκδοση)
// Input: Court (5 starters) + 6TH (1) + BENCH (4) + COACH
// Output: top-3 λύσεις (#1/#2/#3) με official-style UI
// ============================================================

(function(){
  "use strict";

  // ----------------------------------------------------------
  // TEAM COLORS + SHORT CODES
  // ----------------------------------------------------------
  const TEAM_FULL_TO_SHORT = {
    "ANADOLU EFES ISTANBUL":      "ULK",
    "ARMANI OLIMPIA MILAN":       "MIL",
    "BASKONIA VITORIA-GASTEIZ":   "BAS",
    "BESIKTAS ISTANBUL":          "BES",
    "CRVENA ZVEZDA BELGRADE":     "RED",
    "DUBAI BASKETBALL":           "DUB",
    "FC BARCELONA":               "BAR",
    "FC BAYERN MUNICH":           "MUN",
    "FENERBAHCE ISTANBUL":        "IST",
    "HAPOEL IBI TEL AVIV":        "HTA",
    "LDLC ASVEL VILLEURBANNE":    "ASV",
    "MACCABI RAPYD TEL AVIV":     "TEL",
    "OLYMPIACOS PIRAEUS":         "OLY",
    "PANATHINAIKOS AKTOR ATHENS": "PAN",
    "PARIS BASKETBALL":           "PRS",
    "PARTIZAN MOZZART BELGRADE":  "PAR",
    "REAL MADRID":                "MAD",
    "VALENCIA BASKET":            "PAM",
    "VIRTUS BOLOGNA":             "VIR",
    "ZALGIRIS KAUNAS":            "ZAL",
  };

  const TEAM_COLORS = {
    PAN: { primary: "#008a3c", secondary: "#ffffff" },
    OLY: { primary: "#e60000", secondary: "#ffffff" },
    BAR: { primary: "#a50044", secondary: "#004d98" },
    MAD: { primary: "#ffffff", secondary: "#00529f" },
    IST: { primary: "#ffcc00", secondary: "#003366" },
    MIL: { primary: "#e60000", secondary: "#000000" },
    ZAL: { primary: "#008a3c", secondary: "#ffffff" },
    BAS: { primary: "#003d7a", secondary: "#e60000" },
    PAM: { primary: "#ff6b00", secondary: "#000000" },
    DUB: { primary: "#003d7a", secondary: "#ffffff" },
    PAR: { primary: "#000000", secondary: "#ffffff" },
    HTA: { primary: "#e60000", secondary: "#ffffff" },
    BES: { primary: "#000000", secondary: "#ffffff" },
    ULK: { primary: "#003d7a", secondary: "#ffffff" },
    ASV: { primary: "#e60000", secondary: "#000000" },
    RED: { primary: "#e60000", secondary: "#ffffff" },
    TEL: { primary: "#ffcc00", secondary: "#003d7a" },
    PRS: { primary: "#003d7a", secondary: "#ffffff" },
    VIR: { primary: "#000000", secondary: "#ffffff" },
    MUN: { primary: "#dc052d", secondary: "#ffffff" },
  };

  const FORMATIONS = {
    "1-2-2": { G: 1, F: 2, C: 2 },
    "1-3-1": { G: 1, F: 3, C: 1 },
    "2-1-2": { G: 2, F: 1, C: 2 },
    "2-2-1": { G: 2, F: 2, C: 1 },
    "3-1-1": { G: 3, F: 1, C: 1 },
  };

  const TOTAL = { G: 4, F: 4, C: 2 };

  const REDUCED_INJURY_STATUSES = ["uncertain", "game_time", "doubtful"];

  // ----------------------------------------------------------
  // STATE
  // ----------------------------------------------------------
  const state = {
    formation: "2-1-2",
    starters: {
      G: [null, null, null, null],
      F: [null, null, null, null],
      C: [null, null],
    },
    sixth: null,
    bench: [null, null, null, null],
    coach: null,
    cash: 0,
    maxTransfers: 4,
    sidebarTab: "G",
    sidebarSearch: "",
    selectedSlot: null,
    results: [],
    activeRank: 0,
    loading: false,
    error: null,

    players: [],
    coaches: [],
    playersLoaded: false,
    coachesLoaded: false,
    _loadPromise: null,
    _cssLoaded: false,
  };

  const API_URL = "/api/optimize";
  const API_PLAYERS = "/api/players";
  const API_COACHES = "/api/coaches";

  // ----------------------------------------------------------
  // HELPERS
  // ----------------------------------------------------------
  function esc(s){
    return String(s == null ? "" : s)
      .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
      .replace(/"/g,"&quot;").replace(/'/g,"&#39;");
  }

  function loadCss(){
    if(state._cssLoaded) return;
    state._cssLoaded = true;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = "css/fantasy-team-v2.css";
    document.head.appendChild(link);
  }

  function jerseySvg(primary, secondary){
    const p = primary || "#888";
    const s = secondary || "#fff";
    return `
      <svg viewBox="0 0 60 70" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        <path d="M15,15 L5,22 L10,35 L15,32 L15,65 L45,65 L45,32 L50,35 L55,22 L45,15 L40,10 L20,10 Z"
              fill="${p}" stroke="${s}" stroke-width="1.5" stroke-linejoin="round"/>
        <path d="M20,10 Q30,18 40,10" fill="none" stroke="${s}" stroke-width="2"/>
        <rect x="15" y="40" width="30" height="3" fill="${s}" opacity="0.5"/>
      </svg>
    `;
  }

  function injBadgeHtml(status, small){
    if(!status) return "";
    const isOut = status === "out";
    const isReduced = REDUCED_INJURY_STATUSES.includes(status);
    if(!isOut && !isReduced) return "";
    const cls = isOut ? "out" : "reduced";
    const label = isOut ? "OUT" : "?";
    const sizeClass = small ? " ftv2-inj-badge-small" : "";
    return `<span class="ftv2-inj-badge ${cls}${sizeClass}">${label}</span>`;
  }

  // ----------------------------------------------------------
  // DATA LOADING
  // ----------------------------------------------------------
  async function loadData(){
    if(state.playersLoaded && state.coachesLoaded) return;
    if(state._loadPromise) return state._loadPromise;

    state._loadPromise = (async () => {
      try {
        const [pr, cr] = await Promise.all([
          fetch(API_PLAYERS).then(r => r.json()),
          fetch(API_COACHES).then(r => r.json()),
        ]);
        if(pr.ok){ state.players = pr.players || []; state.playersLoaded = true; }
        if(cr.ok){ state.coaches = cr.coaches || []; state.coachesLoaded = true; }
      } catch(err){
        console.error("loadData error:", err);
      } finally {
        state._loadPromise = null;
      }
    })();

    return state._loadPromise;
  }

  // ----------------------------------------------------------
  // GAMES_RAW HELPERS
  // ----------------------------------------------------------
  function getNextRound(){
    if(typeof GAMES_RAW === "undefined") return 4;
    let maxRound = 0;
    for(const g of GAMES_RAW){
      const r = g[0]; const hs = g[7];
      if(hs !== null && hs !== undefined && r > maxRound) maxRound = r;
    }
    return maxRound + 1;
  }

  function getTeamNextMatch(teamShort, targetRound){
    if(typeof GAMES_RAW === "undefined") return null;
    for(const g of GAMES_RAW){
      if(g[0] !== targetRound) continue;
      const homeShort = TEAM_FULL_TO_SHORT[g[5]];
      const awayShort = TEAM_FULL_TO_SHORT[g[6]];
      if(homeShort === teamShort) return { opp: awayShort, home: true, day: g[1] };
      if(awayShort === teamShort) return { opp: homeShort, home: false, day: g[1] };
    }
    return null;
  }

  function getRoundDaysOrder(targetRound){
    if(typeof GAMES_RAW === "undefined") return [];
    const ORDER = { "Mon":1, "Tue":2, "Wed":3, "Thu":4, "Fri":5, "Sat":6, "Sun":7 };
    const days = new Set();
    for(const g of GAMES_RAW){
      if(g[0] === targetRound) days.add(g[1]);
    }
    return Array.from(days).sort((a,b) => (ORDER[a]||99) - (ORDER[b]||99));
  }

  function getTurnLabel(day, targetRound){
    const order = getRoundDaysOrder(targetRound);
    const idx = order.indexOf(day);
    if(idx === -1) return "T?";
    return "T" + (idx + 1);
  }

  function getPlayerMatchInfo(playerName){
    if(typeof PLAYER_STATS_2026 === "undefined") return null;
    const s = PLAYER_STATS_2026[playerName];
    if(!s || !s.team) return null;
    const teamShort = s.team;
    const round = getNextRound();
    const match = getTeamNextMatch(teamShort, round);
    if(!match) return { teamShort, opp: null, home: null, turn: "T?" };
    return {
      teamShort,
      opp: match.opp,
      home: match.home,
      turn: getTurnLabel(match.day, round),
    };
  }

  // ----------------------------------------------------------
  // FORMATION + POSITION HELPERS
  // ----------------------------------------------------------
  function getFormationSlots(){
    return FORMATIONS[state.formation] || FORMATIONS["2-1-2"];
  }

  function getStarterCount(pos){
    return getFormationSlots()[pos] || 0;
  }

  function getRestNeeded(){
    const f = getFormationSlots();
    return {
      G: TOTAL.G - f.G,
      F: TOTAL.F - f.F,
      C: TOTAL.C - f.C,
    };
  }

  function getBenchLabels(){
    const rest = getRestNeeded();
    let benchCounts;
    if(!state.sixth){
      benchCounts = { ...rest };
      benchCounts.G = Math.max(0, benchCounts.G - 1);
    } else {
      benchCounts = { ...rest };
      benchCounts[state.sixth.pos] = Math.max(0, benchCounts[state.sixth.pos] - 1);
    }
    const labels = [];
    for(let i = 0; i < benchCounts.G; i++) labels.push("G");
    for(let i = 0; i < benchCounts.F; i++) labels.push("F");
    for(let i = 0; i < benchCounts.C; i++) labels.push("C");
    return labels;
  }

  function countPositionInRoster(pos){
    let n = 0;
    const f = getFormationSlots();
    for(let i = 0; i < f[pos]; i++){
      if(state.starters[pos][i]) n++;
    }
    if(state.sixth && state.sixth.pos === pos) n++;
    for(const b of state.bench){
      if(b && b.pos === pos) n++;
    }
    return n;
  }

  function canPlaceInSlot(p, section, pos, idx){
    const total = countPositionInRoster(p.pos);
    let existing = null;
    if(section === "starter") existing = state.starters[pos][idx];
    else if(section === "sixth") existing = state.sixth;
    else if(section === "bench") existing = state.bench[idx];
    const existingIsSame = existing && existing.id === p.id;

    if(section === "starter" && p.pos !== pos){
      return { ok: false, reason: `Ο παίκτης είναι ${p.pos}, αλλά το slot είναι ${pos}.` };
    }
    if(section === "bench"){
      const labels = getBenchLabels();
      const targetLabel = labels[idx];
      if(targetLabel && p.pos !== targetLabel){
        return { ok: false, reason: `Το bench slot #${idx+1} δέχεται μόνο ${targetLabel}.` };
      }
    }
    const limit = TOTAL[p.pos];
    if(!existingIsSame && total >= limit){
      return { ok: false, reason: `Δεν χωράει άλλος ${p.pos} (max ${limit}).` };
    }
    return { ok: true };
  }

  function getTotalFilledCount(){
    let n = 0;
    const f = getFormationSlots();
    for(const pos of ["G","F","C"]){
      for(let i = 0; i < f[pos]; i++){
        if(state.starters[pos][i]) n++;
      }
    }
    if(state.sixth) n++;
    for(const b of state.bench) if(b) n++;
    return n;
  }

  function getAllPlayerIds(){
    const ids = [];
    const f = getFormationSlots();
    for(const pos of ["G","F","C"]){
      for(let i = 0; i < f[pos]; i++){
        const p = state.starters[pos][i];
        if(p) ids.push(p.id);
      }
    }
    if(state.sixth) ids.push(state.sixth.id);
    for(const b of state.bench) if(b) ids.push(b.id);
    return ids;
  }

  function isPlayerInTeam(playerId){
    return getAllPlayerIds().includes(playerId);
  }

  function isSlotSelected(section, pos, idx){
    if(!state.selectedSlot) return false;
    if(state.selectedSlot.section !== section) return false;
    if(section === "bench" || section === "coach"){
      return state.selectedSlot.idx === idx;
    }
    return state.selectedSlot.pos === pos && state.selectedSlot.idx === idx;
  }

  // ----------------------------------------------------------
  // PLACEMENT
  // ----------------------------------------------------------
  function placePlayerInSlot(p, slot){
    const section = slot.section;
    const pos = slot.pos;
    const idx = slot.idx;

    const check = canPlaceInSlot(p, section, pos, idx);
    if(!check.ok){
      state.error = check.reason;
      return false;
    }

    if(section === "starter"){
      state.starters[pos][idx] = p;
    } else if(section === "sixth"){
      state.sixth = p;
      autoAdjustBench();
    } else if(section === "bench"){
      state.bench[idx] = p;
    } else if(section === "coach"){
      return false;
    }
    return true;
  }

  function autoAdjustBench(){
    const labels = getBenchLabels();
    const players = state.bench.filter(Boolean);
    state.bench = [null, null, null, null];
    for(const p of players){
      let placed = false;
      for(let i = 0; i < labels.length; i++){
        if(labels[i] === p.pos && !state.bench[i]){
          state.bench[i] = p;
          placed = true;
          break;
        }
      }
      if(!placed){
        state.error = `Ο ${p.name} (${p.pos}) δεν χωράει πια στο bench. Αφαιρέθηκε.`;
      }
    }
  }

  // ----------------------------------------------------------
  // RENDER: PLAYER CARD
  // ----------------------------------------------------------
  function renderPlayerCard(p, opts){
    opts = opts || {};
    const isCap = !!opts.isCaptain;
    const small = !!opts.small;
    const isNew = !!opts.isNew;
    const colors = TEAM_COLORS[p.team] || { primary:"#888", secondary:"#fff" };

    let matchText = "";
    const mi = getPlayerMatchInfo(p.name.replace(/\s*~$/, ""));
    if(mi && mi.opp){
      const venue = mi.home ? "vs" : "@";
      matchText = `<span>${mi.turn}</span> <span class="ftv2-venue">${venue}</span> <span>${esc(mi.opp)}</span>`;
    } else {
      matchText = `<span>—</span>`;
    }

    const sizeClass = small ? " ftv2-card-small" : "";
    const fbClass = p.is_fallback ? " ftv2-card-fallback" : "";
    const newClass = isNew ? " ftv2-card-new" : "";
    const injClass = (p.injury_status === "out") ? " ftv2-inj-out"
                   : (REDUCED_INJURY_STATUSES.includes(p.injury_status) ? " ftv2-inj-reduced" : "");
    const capBadge = isCap ? `<div class="ftv2-cap-badge">CAP</div>` : "";
    const cBadge = isCap ? `<div class="ftv2-c-badge">C</div>` : "";
    const injuryFlag = (p.injury_status === "out")
      ? `<div class="ftv2-inj-flag out">OUT</div>`
      : (REDUCED_INJURY_STATUSES.includes(p.injury_status)
          ? `<div class="ftv2-inj-flag reduced">?</div>`
          : "");

    return `
      <div class="ftv2-card${sizeClass}${fbClass}${newClass}${injClass}">
        ${capBadge}
        ${injuryFlag}
        <div class="ftv2-card-jersey">
          ${jerseySvg(colors.primary, colors.secondary)}
          <div class="ftv2-card-team-bar" style="background:${colors.primary};"></div>
          ${cBadge}
        </div>
        <div class="ftv2-card-name-bar">
          <span class="ftv2-card-pos-badge">${esc(p.pos)}</span>
          <span class="ftv2-card-name">${esc(p.name)}</span>
        </div>
        <div class="ftv2-card-match-bar">${matchText}</div>
      </div>
    `;
  }

  // ----------------------------------------------------------
  // RENDER: INPUT COURT
  // ----------------------------------------------------------
  function renderInputCourt(){
    const f = getFormationSlots();
    const rows = [];

    const cCards = [];
    for(let i = 0; i < f.C; i++){
      cCards.push(renderInputSlot("starter", "C", i, "normal"));
    }
    rows.push(`<div class="ftv2-input-court-row">${cCards.join("")}</div>`);

    const fCards = [];
    for(let i = 0; i < f.F; i++){
      fCards.push(renderInputSlot("starter", "F", i, "normal"));
    }
    rows.push(`<div class="ftv2-input-court-row">${fCards.join("")}</div>`);

    const gCards = [];
    for(let i = 0; i < f.G; i++){
      gCards.push(renderInputSlot("starter", "G", i, "normal"));
    }
    rows.push(`<div class="ftv2-input-court-row">${gCards.join("")}</div>`);

    return `
      <div class="ftv2-input-court">
        <div class="ftv2-input-court-inner">
          ${rows.join("")}
        </div>
      </div>
    `;
  }

  function renderInputSlot(section, pos, idx, size){
    let p;
    if(section === "starter") p = state.starters[pos][idx];
    else if(section === "sixth") p = state.sixth;
    else if(section === "bench") p = state.bench[idx];

    const selected = isSlotSelected(section, pos, idx);
    const selectedClass = selected ? " ftv2-slot-selected" : "";
    const sizeClass = size === "small" ? " ftv2-card-small" : "";

    let displayPos, slotLabel;
    if(section === "sixth"){
      displayPos = p ? p.pos : "6TH";
      slotLabel = "6TH";
    } else if(section === "bench"){
      const labels = getBenchLabels();
      const label = labels[idx];
      displayPos = p ? p.pos : (label || "?");
      slotLabel = "BENCH";
    } else {
      displayPos = pos;
      slotLabel = "STARTER";
    }

    if(!p){
      return `
        <div class="ftv2-empty-slot${selectedClass}"
             data-action="select-slot"
             data-section="${section}"
             data-pos="${pos || ""}"
             data-idx="${idx}">
          <div class="ftv2-empty-slot-pos">${displayPos}</div>
          <div class="ftv2-empty-slot-plus">+</div>
          <div class="ftv2-empty-slot-label">${slotLabel}</div>
        </div>
      `;
    }

    const colors = TEAM_COLORS[p.team] || { primary:"#888", secondary:"#fff" };
    const fbClass = p.is_fallback ? " ftv2-card-fallback" : "";
    const injClass = (p.injury_status === "out") ? " ftv2-inj-out"
                   : (REDUCED_INJURY_STATUSES.includes(p.injury_status) ? " ftv2-inj-reduced" : "");
    const injuryFlag = (p.injury_status === "out")
      ? `<div class="ftv2-inj-flag out">OUT</div>`
      : (REDUCED_INJURY_STATUSES.includes(p.injury_status)
          ? `<div class="ftv2-inj-flag reduced">?</div>`
          : "");

    return `
      <div class="ftv2-filled-slot" data-section="${section}" data-pos="${pos||""}" data-idx="${idx}">
        <div class="ftv2-remove"
             data-action="remove"
             data-section="${section}"
             data-pos="${pos || ""}"
             data-idx="${idx}">×</div>
        <div class="ftv2-card${sizeClass}${fbClass}${injClass}">
          ${injuryFlag}
          <div class="ftv2-card-jersey">
            ${jerseySvg(colors.primary, colors.secondary)}
            <div class="ftv2-card-team-bar" style="background:${colors.primary};"></div>
          </div>
          <div class="ftv2-card-name-bar">
            <span class="ftv2-card-pos-badge">${esc(p.pos)}</span>
            <span class="ftv2-card-name">${esc(p.name)}</span>
          </div>
          <div class="ftv2-card-match-bar"><span>${(p.credits||0).toFixed(1)} cr</span></div>
        </div>
      </div>
    `;
  }

  // ----------------------------------------------------------
  // RENDER: INPUT BOTTOM
  // ----------------------------------------------------------
  function renderInputBottom(){
    const sixthSlot = renderInputSlot("sixth", null, 0, "small");

    const benchSlots = [];
    for(let i = 0; i < 4; i++){
      benchSlots.push(renderInputSlot("bench", null, i, "small"));
    }

    const coachSlot = renderCoachSlot();

    return `
      <div class="ftv2-input-bottom">
        <div class="ftv2-input-group">
          <div class="ftv2-input-group-label">6TH (100% FPT)</div>
          ${sixthSlot}
        </div>
        <div class="ftv2-input-group">
          <div class="ftv2-input-group-label">BENCH (50% FPT)</div>
          <div class="ftv2-input-bench-cards">${benchSlots.join("")}</div>
        </div>
        <div class="ftv2-input-group">
          <div class="ftv2-input-group-label">COACH (100% FPT)</div>
          ${coachSlot}
        </div>
      </div>
    `;
  }

  function renderCoachSlot(){
    const selected = isSlotSelected("coach", null, 0);
    const selectedClass = selected ? " ftv2-slot-selected" : "";

    if(!state.coach){
      return `
        <div class="ftv2-input-coach-slot${selectedClass}"
             data-action="select-slot"
             data-section="coach"
             data-idx="0">
          <div class="ftv2-coach-icon">👔</div>
          <div class="ftv2-coach-name">+</div>
          <div class="ftv2-coach-meta">COACH</div>
        </div>
      `;
    }

    return `
      <div class="ftv2-input-coach-slot filled" data-section="coach" data-idx="0" style="position:relative;">
        <div class="ftv2-remove" style="position:absolute;top:-8px;right:-8px;width:22px;height:22px;background:#ff4444;color:#fff;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:0.85em;font-weight:800;cursor:pointer;box-shadow:0 2px 6px rgba(0,0,0,0.3);border:2px solid #fff;"
             data-action="remove" data-section="coach" data-idx="0">×</div>
        <div class="ftv2-coach-icon">👔</div>
        <div class="ftv2-coach-name">${esc(state.coach.name)}</div>
        <div class="ftv2-coach-meta">${(state.coach.credits||0).toFixed(1)} cr · ${(state.coach.avg_xp||0).toFixed(1)} xp</div>
      </div>
    `;
  }

  // ----------------------------------------------------------
  // RENDER: SIDEBAR
  // ----------------------------------------------------------
  function renderSidebar(){
    return `
      <div class="ftv2-sidebar">
        <div class="ftv2-sidebar-search">
          <input type="text" id="ftv2SideSearch"
                 placeholder="Find player..."
                 value="${esc(state.sidebarSearch)}">
        </div>
        <div class="ftv2-sidebar-tabs">
          <button class="ftv2-sidebar-tab ${state.sidebarTab==="G"?"active":""}" data-tab="G">G</button>
          <button class="ftv2-sidebar-tab ${state.sidebarTab==="F"?"active":""}" data-tab="F">F</button>
          <button class="ftv2-sidebar-tab ${state.sidebarTab==="C"?"active":""}" data-tab="C">C</button>
          <button class="ftv2-sidebar-tab ${state.sidebarTab==="HC"?"active":""}" data-tab="HC">HC</button>
        </div>
        <div class="ftv2-sidebar-list" id="ftv2SidebarList">
          ${renderSidebarItems()}
        </div>
      </div>
    `;
  }

  function renderSidebarItems(){
    const pos = state.sidebarTab;
    const q = state.sidebarSearch.trim().toLowerCase();

    let list;
    if(pos === "HC"){
      list = state.coaches.map(c => ({
        id: c.id, name: c.name, team: c.team, credits: c.credits,
        avg_xp: c.avg_xp, pos: "HC",
      }));
    } else {
      list = state.players.filter(p => p.pos === pos);
    }

    if(q){
      list = list.filter(p => p.name.toLowerCase().includes(q) || (p.team||"").toLowerCase().includes(q));
    }

    list = list.slice().sort((a,b) => {
      if(pos === "HC") return (b.avg_xp||0) - (a.avg_xp||0);
      return (b.xpdk||0) - (a.xpdk||0);
    });

    if(!list.length){
      return `<div style="padding:12px;opacity:0.5;text-align:center;">—</div>`;
    }

    return list.slice(0, 200).map(p => {
      const inTeam = pos === "HC"
        ? (state.coach && String(state.coach.id) === String(p.id))
        : isPlayerInTeam(p.id);
      const colors = TEAM_COLORS[p.team] || { primary:"#888", secondary:"#fff" };
      const mi = pos === "HC" ? null : getPlayerMatchInfo(p.name);
      const matchText = mi && mi.opp ? `${mi.home?"vs":"@"} ${mi.opp}` : (p.team||"—");
      const statText = pos === "HC"
        ? `avg ${(p.avg_xp||0).toFixed(1)}`
        : `xpdk ${(p.xpdk||0).toFixed(1)}`;

      const injBadge = pos === "HC" ? "" : injBadgeHtml(p.injury_status, true);

      const isOut = pos !== "HC" && p.injury_status === "out";
      const disabledClass = isOut ? " disabled" : "";

      return `
        <div class="ftv2-sidebar-item ${inTeam ? "in-team" : ""}${disabledClass}"
             data-action="pick"
             data-pos="${pos}"
             data-id="${esc(p.id)}">
          <div class="ftv2-si-jersey">${jerseySvg(colors.primary, colors.secondary)}</div>
          <div class="ftv2-si-info">
            <div class="ftv2-si-name">${esc(p.name)}${injBadge}</div>
            <div class="ftv2-si-meta">${esc(p.team||"")} · ${esc(matchText)} · ${statText}</div>
          </div>
          <div class="ftv2-si-credits">${(p.credits||0).toFixed(1)}</div>
        </div>
      `;
    }).join("");
  }

  // ----------------------------------------------------------
  // RENDER: INPUT FORM
  // ----------------------------------------------------------
  function renderInputForm(){
    const dataStatus = !state.playersLoaded
      ? `<div class="ftv2-info">⏳ Φόρτωση παικτών...</div>`
      : "";

    const formationOptions = Object.keys(FORMATIONS).map(f =>
      `<option value="${f}" ${state.formation === f ? "selected" : ""}>${f}</option>`
    ).join("");

    const total = getTotalFilledCount();

    return `
      <div class="ftv2-header">
        <h2>🏀 Fantasy Team Optimizer</h2>
        <p>Δώσε την τρέχουσα ομάδα σου. Ο optimizer θα προτείνει τις 3 καλύτερες αλλαγές.</p>
      </div>

      ${dataStatus}

      <div class="ftv2-input-layout">
        <div>
          <div class="ftv2-formation-bar">
            <label>Σύστημα:</label>
            <select id="ftv2Formation">${formationOptions}</select>
            <span class="ftv2-count">${total}/10 παίκτες</span>
          </div>

          ${renderInputCourt()}
          ${renderInputBottom()}
        </div>

        ${renderSidebar()}
      </div>

      <div class="ftv2-bottom-bar">
        <label>Cash:</label>
        <input type="number" id="ftv2CashInput" min="0" max="500" step="0.1" value="${state.cash}">
        <label>Max transfers:</label>
        <input type="number" id="ftv2MaxInput" min="0" max="4" step="1" value="${state.maxTransfers}">
        <button id="ftv2OptimizeBtn" class="ftv2-btn ftv2-btn-primary" style="margin-left:auto;">Optimize</button>
        <button id="ftv2ClearBtn" class="ftv2-btn ftv2-btn-secondary">Clear</button>
      </div>

      ${state.error ? `<div class="ftv2-error">${esc(state.error)}</div>` : ""}
      ${state.loading ? `<div class="ftv2-loading">⏳ Optimizing... (5-15 δευτ.)</div>` : ""}

      <div id="ftv2-results-container">
        ${renderResults()}
      </div>
    `;
  }

  // ----------------------------------------------------------
  // RENDER: RESULTS
  // ----------------------------------------------------------
  function renderResults(){
    if(!state.results.length){
      return `<div class="ftv2-empty">Δεν υπάρχουν αποτελέσματα ακόμα. Πάτα Optimize.</div>`;
    }

    const tabs = state.results.map((r, i) => `
      <button class="ftv2-tab ${i === state.activeRank ? 'active' : ''}" data-rank="${i}">
        #${r.rank} — ${r.score.toFixed(1)} pts
      </button>
    `).join("");

    const active = state.results[state.activeRank];
    if(!active) return `<div class="ftv2-empty">Κάτι πήγε λάθος.</div>`;

    const allPlayers = [...(active.starters||[]), active.sixth, ...(active.bench||[])].filter(Boolean);
    const fallbackCount = allPlayers.filter(p => p.is_fallback).length;
    const warn = fallbackCount >= 3
      ? `<div class="ftv2-warn">⚠️ ${fallbackCount} παίκτες χωρίς prediction (με ~). Το αποτέλεσμα μπορεί να είναι λιγότερο ακριβές.</div>`
      : "";

    return `
      <div class="ftv2-results">
        <div class="ftv2-tabs">${tabs}</div>
        ${warn}
        ${renderTeamPitch(active)}
        ${renderTransfersSummary(active)}
      </div>
    `;
  }

  function renderTeamPitch(r){
    const starterC = r.starters.filter(p => p.pos === "C");
    const starterFs = r.starters.filter(p => p.pos === "F");
    const starterGs = r.starters.filter(p => p.pos === "G");
    const capId = r.captain ? r.captain.id : null;

    const newIds = new Set((r.transfers_in || []).map(p => p.id));

    const card = (p) => renderPlayerCard(p, {
      isCaptain: p.id === capId,
      small: false,
      isNew: newIds.has(p.id),
    });

    const cardSmall = (p) => renderPlayerCard(p, {
      small: true,
      isNew: newIds.has(p.id),
    });

    return `
      <div class="ftv2-court">
        <div class="ftv2-court-inner">
          <div class="ftv2-court-row">${starterC.map(card).join("")}</div>
          <div class="ftv2-court-row">${starterFs.map(card).join("")}</div>
          <div class="ftv2-court-row">${starterGs.map(card).join("")}</div>
        </div>
      </div>

      <div class="ftv2-bench-section">
        <div class="ftv2-bench-group">
          <div class="ftv2-bench-label">6TH (100% FPT)</div>
          ${cardSmall(r.sixth)}
        </div>
        <div class="ftv2-bench-group">
          <div class="ftv2-bench-label">BENCH (50% FPT)</div>
          <div class="ftv2-bench-cards">
            ${r.bench.map(p => cardSmall(p)).join("")}
          </div>
        </div>
        <div class="ftv2-bench-group">
          <div class="ftv2-bench-label">COACH (100% FPT)</div>
          <div class="ftv2-coach-card${r.coach_changed ? ' ftv2-card-new' : ''}">
            <div class="ftv2-coach-card-title">Head Coach</div>
            <div class="ftv2-coach-card-icon">👔</div>
            <div class="ftv2-coach-card-name">${esc(r.coach.name)}</div>
            <div class="ftv2-coach-card-team">${esc(r.coach.team)}</div>
            <div class="ftv2-coach-card-stats">
              <span>${r.coach.credits.toFixed(1)} cr</span>
              <span>${r.coach.avg_xp.toFixed(1)} xp</span>
            </div>
          </div>
        </div>
      </div>

      <div class="ftv2-meta-row">
        <div class="ftv2-meta"><span class="ftv2-meta-label">Formation</span><span class="ftv2-meta-value">${esc(r.formation)}</span></div>
        <div class="ftv2-meta"><span class="ftv2-meta-label">Score</span><span class="ftv2-meta-value">${r.score.toFixed(2)}</span></div>
        <div class="ftv2-meta"><span class="ftv2-meta-label">Net cost</span><span class="ftv2-meta-value">${r.net_cost >= 0 ? "+" : ""}${r.net_cost.toFixed(1)} / ${state.cash}</span></div>
        <div class="ftv2-meta"><span class="ftv2-meta-label">Transfers</span><span class="ftv2-meta-value">${r.n_player_transfers}${r.coach_changed ? " + coach" : ""}</span></div>
      </div>
    `;
  }

  function renderTransfersSummary(r){
    if(!r.transfers_in || !r.transfers_in.length){
      return `<div class="ftv2-transfers"><em>Καμία αλλαγή — η ομάδα σου είναι ήδη βέλτιστη.</em></div>`;
    }
    const inList = r.transfers_in.map(p => {
      const fb = p.is_fallback ? " ~" : "";
      const inj = p.injury_status ? ` <span class="ftv2-inj-inline ${p.injury_status}">[${p.injury_status}]</span>` : "";
      return `<li><span class="ftv2-in">IN</span> ${esc(p.name)}${fb}${inj} <span class="ftv2-tiny">(${esc(p.team)}, ${p.credits.toFixed(1)} cr, ${p.xpdk.toFixed(1)} xp)</span></li>`;
    }).join("");
    const outList = r.transfers_out.map(p => {
      const fb = p.is_fallback ? " ~" : "";
      const inj = p.injury_status ? ` <span class="ftv2-inj-inline ${p.injury_status}">[${p.injury_status}]</span>` : "";
      return `<li><span class="ftv2-out">OUT</span> ${esc(p.name)}${fb}${inj} <span class="ftv2-tiny">(${esc(p.team)}, ${p.credits.toFixed(1)} cr, ${p.xpdk.toFixed(1)} xp)</span></li>`;
    }).join("");
    const coachLine = r.coach_changed
      ? `<li><span class="ftv2-out">COACH OUT</span> ${esc(r.coach_out.name)} <span class="ftv2-tiny">(${r.coach_out.credits.toFixed(1)} cr)</span></li>
         <li><span class="ftv2-in">COACH IN</span> ${esc(r.coach_in.name)} <span class="ftv2-tiny">(${r.coach_in.credits.toFixed(1)} cr, ${r.coach_in.avg_xp.toFixed(1)} xp)</span></li>`
      : "";

    return `
      <div class="ftv2-transfers">
        <h4>Transfers (${r.total_transfers})</h4>
        <ul>${inList}${coachLine}${outList}</ul>
      </div>
    `;
  }

  // ----------------------------------------------------------
  // EVENT BINDING
  // ----------------------------------------------------------
  function bindEvents(root){
    const formSel = root.querySelector("#ftv2Formation");
    if(formSel) formSel.addEventListener("change", e => {
      state.formation = e.target.value;
      state.selectedSlot = null;
      state.error = null;
      autoAdjustBench();
      renderView();
    });

    const searchIn = root.querySelector("#ftv2SideSearch");
    if(searchIn) searchIn.addEventListener("input", e => {
      state.sidebarSearch = e.target.value;
      const list = root.querySelector("#ftv2SidebarList");
      if(list) list.innerHTML = renderSidebarItems();
      bindSidebarPicks(root);
    });

    root.querySelectorAll(".ftv2-sidebar-tab").forEach(btn => {
      btn.addEventListener("click", () => {
        state.sidebarTab = btn.dataset.tab;
        state.sidebarSearch = "";
        renderView();
      });
    });

    root.querySelectorAll('[data-action="select-slot"]').forEach(el => {
      el.addEventListener("click", () => {
        const section = el.dataset.section;
        const pos = el.dataset.pos || null;
        const idx = Number(el.dataset.idx);
        const cur = state.selectedSlot;
        if(cur && cur.section === section && cur.pos === pos && cur.idx === idx){
          state.selectedSlot = null;
        } else {
          state.selectedSlot = { section, pos, idx };
        }
        renderView();
      });
    });

    root.querySelectorAll('[data-action="remove"]').forEach(btn => {
      btn.addEventListener("click", e => {
        e.stopPropagation();
        const section = btn.dataset.section;
        const pos = btn.dataset.pos || null;
        const idx = Number(btn.dataset.idx);
        if(section === "starter") state.starters[pos][idx] = null;
        else if(section === "sixth"){ state.sixth = null; autoAdjustBench(); }
        else if(section === "bench") state.bench[idx] = null;
        else if(section === "coach") state.coach = null;
        state.selectedSlot = null;
        state.error = null;
        renderView();
      });
    });

    bindSidebarPicks(root);

    const cashIn = root.querySelector("#ftv2CashInput");
    if(cashIn) cashIn.addEventListener("change", e => { state.cash = Number(e.target.value) || 0; });

    const maxIn = root.querySelector("#ftv2MaxInput");
    if(maxIn) maxIn.addEventListener("change", e => {
      state.maxTransfers = Math.max(0, Math.min(4, Number(e.target.value) || 4));
    });

    const optBtn = root.querySelector("#ftv2OptimizeBtn");
    if(optBtn) optBtn.addEventListener("click", runOptimizer);

    const clearBtn = root.querySelector("#ftv2ClearBtn");
    if(clearBtn) clearBtn.addEventListener("click", () => {
      state.starters = { G:[null,null,null,null], F:[null,null,null,null], C:[null,null] };
      state.sixth = null;
      state.bench = [null, null, null, null];
      state.coach = null;
      state.selectedSlot = null;
      state.results = [];
      state.error = null;
      renderView();
    });

    root.querySelectorAll(".ftv2-tab").forEach(btn => {
      btn.addEventListener("click", () => {
        state.activeRank = Number(btn.dataset.rank);
        renderView();
      });
    });
  }

  function bindSidebarPicks(root){
    root.querySelectorAll('[data-action="pick"]').forEach(el => {
      const fresh = el.cloneNode(true);
      el.parentNode.replaceChild(fresh, el);
      fresh.addEventListener("click", () => {
        if(fresh.classList.contains("in-team")) return;
        if(fresh.classList.contains("disabled")) return;
        const pos = fresh.dataset.pos;
        const id = fresh.dataset.id;

        if(pos === "HC"){
          const c = state.coaches.find(x => String(x.id) === String(id));
          if(c){
            state.coach = { id: c.id, name: c.name, credits: c.credits, avg_xp: c.avg_xp };
            state.selectedSlot = null;
            state.error = null;
            renderView();
          }
          return;
        }

        const p = state.players.find(x => String(x.id) === String(id));
        if(!p) return;

        const playerObj = {
          id: p.id, name: p.name, pos: p.pos, team: p.team,
          credits: p.credits, xpdk: p.xpdk, is_fallback: p.is_fallback,
        };

        let slot = state.selectedSlot;
        if(!slot){
          const f = getFormationSlots();
          let found = false;
          if(f[p.pos] !== undefined){
            for(let i = 0; i < f[p.pos]; i++){
              if(!state.starters[p.pos][i]){
                slot = { section:"starter", pos: p.pos, idx: i };
                found = true;
                break;
              }
            }
          }
          if(!found && !state.sixth){
            const check = canPlaceInSlot(playerObj, "sixth", null, 0);
            if(check.ok){
              slot = { section:"sixth", pos: null, idx: 0 };
              found = true;
            }
          }
          if(!found){
            const totalInRoster = countPositionInRoster(p.pos);
            if(totalInRoster >= TOTAL[p.pos]){
              state.error = `Δεν χωράει άλλος ${p.pos} (max ${TOTAL[p.pos]}).`;
              renderView();
              return;
            }
            const labels = getBenchLabels();
            for(let i = 0; i < 4; i++){
              if(!state.bench[i] && (labels[i] === null || labels[i] === p.pos)){
                slot = { section:"bench", pos: null, idx: i };
                found = true;
                break;
              }
            }
          }
          if(!found){
            state.error = `Δεν υπάρχει κενή θέση για ${p.pos}.`;
            renderView();
            return;
          }
        }

        const ok = placePlayerInSlot(playerObj, slot);
        if(ok){
          state.selectedSlot = null;
          state.error = null;
        }
        renderView();
      });
    });
  }

  // ----------------------------------------------------------
  // RUN OPTIMIZER
  // ----------------------------------------------------------
  async function runOptimizer(){
    if(!state.playersLoaded || !state.coachesLoaded){
      state.error = "Τα δεδομένα δεν έχουν φορτωθεί ακόμα.";
      renderView();
      return;
    }

    const allIds = getAllPlayerIds();
    if(allIds.length !== 10){
      state.error = `Συμπλήρωσε και τους 10 παίκτες (${allIds.length}/10).`;
      renderView();
      return;
    }
    if(!state.coach){
      state.error = "Διάλεξε προπονητή.";
      renderView();
      return;
    }
    if(new Set(allIds).size !== allIds.length){
      state.error = "Έχεις βάλει τον ίδιο παίκτη 2 φορές.";
      renderView();
      return;
    }

    const posCount = { G:0, F:0, C:0 };
    const allPlayers = [
      ...Object.values(state.starters).flat().filter(Boolean),
      state.sixth,
      ...state.bench,
    ].filter(Boolean);
    for(const p of allPlayers) posCount[p.pos]++;

    if(posCount.G !== 4 || posCount.F !== 4 || posCount.C !== 2){
      state.error = `Λάθος κατανομή: G=${posCount.G}/4, F=${posCount.F}/4, C=${posCount.C}/2`;
      renderView();
      return;
    }

    state.loading = true;
    state.error = null;
    state.results = [];
    renderView();

    try {
      const body = {
        player_ids: allIds,
        coach_id: state.coach.id,
        cash: state.cash,
        max_transfers: state.maxTransfers,
      };
      const resp = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await resp.json();

      if(!data.ok){
        state.error = data.error || "Σφάλμα από τον optimizer.";
      } else {
        state.results = data.results || [];
        state.activeRank = 0;
      }
    } catch(err){
      state.error = "Αδυναμία σύνδεσης με τον server.";
      console.error(err);
    } finally {
      state.loading = false;
      renderView();
    }
  }

  // ----------------------------------------------------------
  // RENDER VIEW
  // ----------------------------------------------------------
  function renderView(){
    const root = document.getElementById("view-fantasy-team");
    if(!root) return;
    root.innerHTML = `<div class="ftv2-wrapper">${renderInputForm()}</div>`;
    bindEvents(root);
  }

  async function renderViewAndLoad(){
    loadCss();
    await loadData();
    renderView();
  }

  window.renderFantasyTeam = function(){
    const root = document.getElementById("view-fantasy-team");
    if(!root) return;
    renderViewAndLoad();
  };

})();