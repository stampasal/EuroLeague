// ============================================================
// CHARTS VIEW
// ============================================================

function renderCharts(){
  const el = document.getElementById("view-charts");
  if(!el) return;

  const rows = computeStandings();
  const playedRows = rows.filter(r => r.GP > 0);

  if(playedRows.length < 2){
    el.innerHTML = `<div class="empty">
      <span class="icon">📈</span>
      <p>Δεν υπάρχουν αρκετά δεδομένα για γραφήματα.</p>
    </div>`;
    return;
  }

  const evoData = computeStandingsEvolution();
  const evolutionSVG = buildEvolutionSVG(evoData, rows);

  const ppgData = playedRows
    .map(t => ({ team: t.team, ppg: t.PF / t.GP, rank: rows.indexOf(t) + 1 }))
    .sort((a,b) => b.ppg - a.ppg);
  const ppgSVG = buildPPGSVG(ppgData, rows);

  const diffData = playedRows
    .map(t => ({ team: t.team, diff: t.diff, rank: rows.indexOf(t) + 1 }))
    .sort((a,b) => b.diff - a.diff);
  const diffSVG = buildDiffSVG(diffData, rows);

  el.innerHTML = `
    <div class="charts-header">
      <h2>📊 Statistics Charts</h2>
      <p>Visual insights από τη σεζόν</p>
    </div>

    <div class="chart-card">
      <div class="chart-card-header">
        <div>
          <div class="chart-title">📈 Standings Evolution</div>
          <div class="chart-subtitle">Πώς άλλαξε η κατάταξη ανά round</div>
        </div>
        <div class="chart-zoom-controls">
          <button class="zoom-btn" data-zoom="out" title="Zoom out">−</button>
          <button class="zoom-btn" data-zoom="reset" title="Reset zoom">⟲</button>
          <button class="zoom-btn" data-zoom="in" title="Zoom in">+</button>
        </div>
      </div>
      <div class="chart-zoom-wrapper" id="evoZoomWrapper">
        ${evolutionSVG}
      </div>
      <div class="chart-legend">
        <span style="color:var(--muted)">💡 Το χρώμα κάθε γραμμής = χρώμα ομάδας · Hover για highlight · <b>#rank</b> πάνω από κάθε logo</span>
        <span><span class="legend-dot" style="background:#10b981"></span>Top 6</span>
        <span><span class="legend-dot" style="background:#f59e0b"></span>Play-In 7–10</span>
        <span><span class="legend-dot" style="background:#94a3b8"></span>Κάτω από 10</span>
      </div>
    </div>

    <div class="chart-card">
      <div class="chart-title">🔥 PPG (Points Per Game)</div>
      <div class="chart-subtitle">Μέσοι πόντοι ανά αγώνα</div>
      ${ppgSVG}
    </div>

    <div class="chart-card">
      <div class="chart-title">📊 Point Differential</div>
      <div class="chart-subtitle">Διαφορά πόντων (PTS+ μείον PTS-)</div>
      ${diffSVG}
    </div>
  `;

  const evoLines = el.querySelectorAll(".evo-line");
  const evoLogos = el.querySelectorAll(".evo-logo");

  evoLines.forEach(line => {
    line.addEventListener("mouseenter", () => highlightEvoTeam(line.dataset.team));
    line.addEventListener("mouseleave", () => unhighlightEvoTeam());
  });

  evoLogos.forEach(logo => {
    logo.addEventListener("mouseenter", () => highlightEvoTeam(logo.dataset.team));
    logo.addEventListener("mouseleave", () => unhighlightEvoTeam());
  });

  function highlightEvoTeam(team){
    const chart = el.querySelector(".evo-chart");
    if(!chart) return;
    chart.classList.add("has-highlight");
    chart.querySelectorAll(".evo-line, .evo-logo").forEach(node => {
      const isTarget = node.dataset.team === team;
      node.classList.toggle("highlighted", isTarget);
      node.classList.toggle("dimmed", !isTarget);
    });
  }

  function unhighlightEvoTeam(){
    const chart = el.querySelector(".evo-chart");
    if(!chart) return;
    chart.classList.remove("has-highlight");
    chart.querySelectorAll(".evo-line, .evo-logo").forEach(node => {
      node.classList.remove("highlighted", "dimmed");
    });
  }

  let zoomLevel = 1.3;
  const MIN_ZOOM = 0.6;
  const MAX_ZOOM = 10;
  const STEP = 0.2;

  const zoomWrapper = document.getElementById("evoZoomWrapper");

  function applyZoom(){
    if(!zoomWrapper) return;
    const svg = zoomWrapper.querySelector(".evo-chart");
    if(!svg) return;
    svg.style.width = (zoomLevel * 100) + "%";
    svg.style.height = "auto";
  }

  el.querySelectorAll(".zoom-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const action = btn.dataset.zoom;
      if(action === "in"){
        zoomLevel = Math.min(MAX_ZOOM, zoomLevel + STEP);
      } else if(action === "out"){
        zoomLevel = Math.max(MIN_ZOOM, zoomLevel - STEP);
      } else if(action === "reset"){
        zoomLevel = 1.3;
      }
      applyZoom();
    });
  });
}

function buildEvolutionSVG(evoData, currentRows){
  const { evolution, lastRound } = evoData;
  if(lastRound === 0) return `<div class="chart-empty">Δεν έχει παιχτεί κανένα παιχνίδι ακόμα</div>`;

  const W = 1100, H = 620;
  const pad = { top: 30, right: 130, bottom: 50, left: 55 };
  const innerW = W - pad.left - pad.right;
  const innerH = H - pad.top - pad.bottom;
  const maxRank = 20;

  const xFor = r => pad.left + ((r - 1) / Math.max(1, lastRound - 1)) * innerW;
  const yFor = rank => pad.top + ((rank - 1) / (maxRank - 1)) * innerH;

  const finalRanks = {};
  currentRows.forEach((t, idx) => finalRanks[t.team] = idx + 1);

  let yAxis = "";
  for(let r = 1; r <= maxRank; r++){
    if(r === 1 || r % 5 === 0 || r === maxRank){
      const y = yFor(r);
      yAxis += `<text x="${pad.left - 14}" y="${y + 4}" text-anchor="end" class="chart-axis-text">#${r}</text>`;
      yAxis += `<line x1="${pad.left}" y1="${y}" x2="${pad.left + innerW}" y2="${y}" class="chart-grid"/>`;
    }
  }

  let xAxis = "";
  const step = Math.max(1, Math.ceil(lastRound / 10));
  for(let r = 1; r <= lastRound; r++){
    if(r === 1 || r % step === 0 || r === lastRound){
      const x = xFor(r);
      xAxis += `<text x="${x}" y="${H - 15}" text-anchor="middle" class="chart-axis-text">R${r}</text>`;
    }
  }

  const teamsSorted = [...TEAMS].sort((a,b) => {
    const ra = finalRanks[a] || 99;
    const rb = finalRanks[b] || 99;
    return ra - rb;
  });

  const LOGO_SIZE = 28;
 
  let lines = "";
  let logos = "";

  teamsSorted.forEach(team => {
    const points = evolution[team];
    if(!points.length) return;
    const finalRank = finalRanks[team] || 20;
    const color = teamColor(team);

    const path = points.map((p, i) =>
      `${i === 0 ? "M" : "L"} ${xFor(p.round).toFixed(1)} ${yFor(p.rank).toFixed(1)}`
    ).join(" ");

    const strokeW = finalRank <= 6 ? 3 : finalRank <= 10 ? 2 : 1.5;
    const opacity = finalRank <= 6 ? 1 : finalRank <= 10 ? 0.85 : 0.5;

    lines += `<path d="${path}" stroke="${color}" fill="none" stroke-width="${strokeW}" stroke-opacity="${opacity}" stroke-linejoin="round" stroke-linecap="round" class="evo-line" data-team="${escapeHtml(team)}"/>`;

    const last = points[points.length - 1];
    const endX = xFor(last.round);
    const endY = yFor(last.rank);
    const logoX = endX + 14;
    const logoY = endY;

    lines += `<line x1="${endX}" y1="${endY}" x2="${logoX}" y2="${logoY}" stroke="${color}" stroke-width="1.5" opacity="0.5"/>`;

    const logoUrl = LOGOS[team];
    const logoCy = logoY;

    const RANK_W = 32;
    const RANK_H = 18;
    const RANK_GAP = 8;
    const rankX = logoX + LOGO_SIZE + RANK_GAP;
    const rankY = logoCy - RANK_H / 2;

    let logoShape = "";
    if(logoUrl){
      logoShape = `<image href="${logoUrl}" x="${logoX}" y="${logoY - LOGO_SIZE / 2}" width="${LOGO_SIZE}" height="${LOGO_SIZE}" preserveAspectRatio="xMidYMid meet"/>`;
    } else {
      const initials = team.split(/\s+/).slice(0,2).map(w=>w[0]).join("").toUpperCase();
      logoShape = `
        <circle cx="${logoX + LOGO_SIZE/2}" cy="${logoY}" r="${LOGO_SIZE/2}" fill="${color}"/>
        <text x="${logoX + LOGO_SIZE/2}" y="${logoY + 4}" text-anchor="middle" font-size="11" font-weight="800" fill="#fff">${initials}</text>
      `;
    }

    logos += `<g class="evo-logo" data-team="${escapeHtml(team)}">
      <title>${escapeHtml(team)} · #${finalRank}</title>
      ${logoShape}
      <rect x="${rankX}" y="${rankY}" width="${RANK_W}" height="${RANK_H}" rx="${RANK_H / 2}" fill="${color}" opacity="0.9"/>
      <text x="${rankX + RANK_W / 2}" y="${rankY + 13}" text-anchor="middle" font-size="10.5" font-weight="900" fill="#fff">#${finalRank}</text>
    </g>`;
  });

  return `<svg viewBox="0 0 ${W} ${H}" class="chart-svg evo-chart" preserveAspectRatio="xMidYMid meet">
    <g>${yAxis}${xAxis}${lines}${logos}</g>
  </svg>`;
}

function buildPPGSVG(ppgData, currentRows){
  const maxPPG = Math.max(...ppgData.map(d => d.ppg), 100);
  const rowH = 32;
  const W = 1000;
  const labelW = 240;
  const valueW = 70;
  const barMaxW = W - labelW - valueW - 40;
  const H = ppgData.length * rowH + 20;

  let bars = "";
  ppgData.forEach((d, i) => {
    const y = 10 + i * rowH;
    const barW = (d.ppg / maxPPG) * barMaxW;
    const color = teamColor(d.team);

    bars += `
      <g class="chart-bar-group">
        <text x="10" y="${y + 18}" class="chart-team-label">${d.team}</text>
        <rect x="${labelW}" y="${y + 4}" width="${barW}" height="${rowH - 12}" fill="${color}" opacity="0.85" rx="4"/>
        <text x="${labelW + barW + 8}" y="${y + 18}" class="chart-value-text">${d.ppg.toFixed(1)}</text>
      </g>
    `;
  });

  return `<svg viewBox="0 0 ${W} ${H}" class="chart-svg" preserveAspectRatio="xMidYMid meet">
    ${bars}
  </svg>`;
}

function buildDiffSVG(diffData, currentRows){
  const maxAbs = Math.max(...diffData.map(d => Math.abs(d.diff)), 10);
  const rowH = 32;
  const W = 1000;
  const labelW = 240;
  const valueW = 80;
  const barMaxW = (W - labelW - valueW - 40) / 2;
  const H = diffData.length * rowH + 20;
  const centerX = labelW + barMaxW;

  let bars = "";
  diffData.forEach((d, i) => {
    const y = 10 + i * rowH;
    const barW = (Math.abs(d.diff) / maxAbs) * barMaxW;
    const color = teamColor(d.team);

    const isPos = d.diff >= 0;
    const x = isPos ? centerX : centerX - barW;
    const valueX = isPos ? centerX + barW + 8 : centerX - barW - 8;
    const valueAnchor = isPos ? "start" : "end";

    bars += `
      <g class="chart-bar-group">
        <text x="10" y="${y + 18}" class="chart-team-label">${d.team}</text>
        <line x1="${centerX}" y1="${y}" x2="${centerX}" y2="${y + rowH - 4}" class="chart-axis-line"/>
        <rect x="${x}" y="${y + 4}" width="${barW}" height="${rowH - 12}" fill="${color}" opacity="0.85" rx="4"/>
        <text x="${valueX}" y="${y + 18}" text-anchor="${valueAnchor}" class="chart-value-text">${d.diff > 0 ? "+" : ""}${d.diff}</text>
      </g>
    `;
  });

  return `<svg viewBox="0 0 ${W} ${H}" class="chart-svg" preserveAspectRatio="xMidYMid meet">
    ${bars}
  </svg>`;
}