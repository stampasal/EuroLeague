// ============================================================
// DASHBOARD VIEW — Top 3 leaders
// ============================================================

function renderDashboard(){
  const rows = computeStandings();
  const playedRows = rows.filter(r => r.GP > 0);

  if(!playedRows.length){
    document.getElementById("view-dashboard").innerHTML =
      `<div class="empty"><span class="icon">🏀</span>No games played yet.</div>`;
    return;
  }

  function top3(metricFn, order = "desc"){
    return playedRows
      .map(t => ({ team: t.team, value: metricFn(t) }))
      .filter(x => x.value !== null && x.value !== undefined && !isNaN(x.value))
      .sort((a, b) => order === "desc"
        ? b.value - a.value
        : a.value - b.value)
      .slice(0, 3);
  }

  function fmt(value, type){
    if(value === null || value === undefined) return "—";
    if(type === "pct")  return (value * 100).toFixed(1) + "%";
    if(type === "pct2") return (value * 100).toFixed(2) + "%";
    if(type === "diff") return (value > 0 ? "+" : "") + value;
    if(type === "1dec") return Number(value).toFixed(1);
    if(type === "2dec") return Number(value).toFixed(2);
    return value;
  }

  function adv(team, key){
    const advData = TEAM_ADVANCED?.[team];
    if(!advData) return null;
    const data = advData[statsMode] || advData.perGame || advData;
    return data?.[key] ?? null;
  }

  const cards = [
    // ═══ Row 1: Overall ═══
    { icon:"🏆", title:"League Leader",
      get: t => t.W,
      fmt: v => v + "W",
      sub: t => `${t.W}-${t.L}`
    },
    { icon:"⚡", title:"Best PIR",
      get: t => adv(t.team, "PIR"),
      fmt: v => v.toFixed(1),
      sub: t => `PIR avg`
    },
    { icon:"💯", title:"Most Points Scored",
      get: t => t.PF,
      fmt: v => v.toLocaleString() + " pts",
      sub: t => `in ${t.GP} GP`
    },

    // ═══ Row 2: Team Identity ═══
    { icon:"🔥", title:"Best Offense",
      get: t => t.GP ? t.PF / t.GP : 0,
      fmt: v => v.toFixed(1) + " PPG",
      sub: t => `${t.PF} pts`
    },
    { icon:"🛡️", title:"Best Defense",
      get: t => t.GP ? t.PA / t.GP : 0,
      order:"asc",
      fmt: v => v.toFixed(1) + " PAPG",
      sub: t => `${t.PA} allowed`
    },
    { icon:"📈", title:"Best Differential",
      get: t => t.diff,
      fmt: v => (v > 0 ? "+" : "") + v,
      sub: t => `${t.GP} GP`
    },

    // ═══ Row 3: Shooting Percentages ═══
    { icon:"🎯", title:"Best True Shooting",
      get: t => adv(t.team, "TS"),
      fmt: v => v.toFixed(1) + "%",
      sub: t => `TS%`
    },
    { icon:"🎯", title:"Best eFG%",
      get: t => adv(t.team, "eFG"),
      fmt: v => v.toFixed(1) + "%",
      sub: t => `eFG%`
    },
    { icon:"🎯", title:"Best 3P%",
      get: t => adv(t.team, "3P%"),
      fmt: v => v.toFixed(1) + "%",
      sub: t => `three-pointers`
    },
    { icon:"🎯", title:"Best 2P%",
      get: t => adv(t.team, "2P%"),
      fmt: v => v.toFixed(1) + "%",
      sub: t => `two-pointers`
    },
    { icon:"🎯", title:"Best FT%",
      get: t => adv(t.team, "FT%"),
      fmt: v => v.toFixed(1) + "%",
      sub: t => `free throws`
    },

    // ═══ Row 4: Defense & Rebounds ═══
    { icon:"💪", title:"Most Rebounds",
      get: t => adv(t.team, "REB"),
      fmt: v => v.toFixed(1) + " RPG",
      sub: t => `rebounds`
    },
    { icon:"✋", title:"Most Steals",
      get: t => adv(t.team, "STL"),
      fmt: v => v.toFixed(1) + " SPG",
      sub: t => `steals`
    },
    { icon:"🚫", title:"Most Blocks",
      get: t => adv(t.team, "BLK"),
      fmt: v => v.toFixed(1) + " BPG",
      sub: t => `blocks`
    },

    // ═══ Row 5: Playmaking & Turnovers ═══
    { icon:"🎁", title:"Most Assists",
      get: t => adv(t.team, "AST"),
      fmt: v => v.toFixed(1) + " APG",
      sub: t => `assists`
    },
    { icon:"📉", title:"Fewest Turnovers",
      get: t => adv(t.team, "TOV"),
      order:"asc",
      fmt: v => v.toFixed(1) + " TOV",
      sub: t => `per game`
    },
    { icon:"🤝", title:"Best AST/TO",
      get: t => adv(t.team, "AST/TO"),
      fmt: v => v.toFixed(2),
      sub: t => `ratio`
    },

    // ═══ Row 6: Splits & Form ═══
    { icon:"🏠", title:"Best Home",
      get: t => (t.hW + t.hL) ? t.hW / (t.hW + t.hL) : 0,
      fmt: v => (v * 100).toFixed(0) + "%",
      sub: t => `${t.hW}-${t.hL}`
    },
    { icon:"✈️", title:"Best Away",
      get: t => (t.aW + t.aL) ? t.aW / (t.aW + t.aL) : 0,
      fmt: v => (v * 100).toFixed(0) + "%",
      sub: t => `${t.aW}-${t.aL}`
    },
    { icon:"🎯", title:"Best L10",
      get: t => t.last10.split("").filter(c => c === "W").length,
      fmt: v => v + "W / 10",
      sub: t => t.last10 || "—"
    }
  ];

  const cardRows = [
    cards.slice(0, 3),
    cards.slice(3, 6),
    cards.slice(6, 11),
    cards.slice(11, 14),
    cards.slice(14, 17),
    cards.slice(17, 20),
  ];

  function renderCard(card){
    const top = top3(card.get, card.order || "desc");

    let cardHTML = `
      <div class="leader-card">
        <div class="leader-card-title">
          <span class="leader-card-icon">${card.icon}</span>
          <span class="leader-card-name">${card.title}</span>
        </div>
        <div class="leader-card-list">
    `;

    if(!top.length){
      cardHTML += `<div class="leader-row empty">Δεν υπάρχουν δεδομένα</div>`;
    } else {
      const medals = ["🥇", "🥈", "🥉"];
      top.forEach((entry, i) => {
        cardHTML += `
          <div class="leader-row rank-${i + 1} clickable-row" data-team="${escapeHtml(entry.team)}">
            <span class="leader-medal">${medals[i]}</span>
            <span class="leader-logo">${logoHTML(entry.team)}</span>
            <span class="leader-team">${entry.team}</span>
            <span class="leader-value">${card.fmt(entry.value)}</span>
          </div>
        `;
      });
    }

    cardHTML += `
        </div>
      </div>
    `;
    return cardHTML;
  }

  let html = `
    <div class="dashboard-header">
      <h2>📊 League Dashboard</h2>
      <p>Top 3 leaders σε κάθε κατηγορία</p>
    </div>
  `;

  cardRows.forEach(row => {
    if(!row.length) return;
    const colCount = row.length;
    html += `<div class="dash-row" style="grid-template-columns:repeat(${colCount}, 1fr)">`;
    row.forEach(card => {
      html += renderCard(card);
    });
    html += `</div>`;
  });

  html += `
    <div class="dash-footer-stats">
      <div class="mini-footer-stat">
        <span class="lbl">Games Played</span>
        <span class="val">${games.filter(g => g[7] !== null && g[8] !== null).length} / ${games.length}</span>
      </div>
      <div class="mini-footer-stat">
        <span class="lbl">Total Points</span>
        <span class="val">${playedRows.reduce((s,t) => s + t.PF, 0).toLocaleString()}</span>
      </div>
      <div class="mini-footer-stat">
        <span class="lbl">Teams</span>
        <span class="val">${playedRows.length}</span>
      </div>
    </div>
  `;

  document.getElementById("view-dashboard").innerHTML = html;

  document.querySelectorAll("#view-dashboard .clickable-row").forEach(row => {
    row.addEventListener("click", () => {
      const team = row.dataset.team;
      if(!team) return;
      teamPage.team = team;
      document.querySelectorAll("nav.tabs button").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
      document.querySelector('nav.tabs button[data-view="team"]').classList.add("active");
      document.getElementById("view-team").classList.add("active");
	  if(typeof updateTabUnderline === "function") updateTabUnderline();
      if(typeof applyStaggerIndexes === "function") applyStaggerIndexes();
      if(typeof updateToolbarHeight === "function") updateToolbarHeight();
      renderTeamPage();
    });
  });
}