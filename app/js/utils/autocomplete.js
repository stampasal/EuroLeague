// ============================================================
// AUTOCOMPLETE — dropdown with team suggestions
// ============================================================

function attachAutocomplete(input){
  if(!input) return;
  if(input.dataset.acInit === "1") return;
  input.dataset.acInit = "1";

  // Wrap input σε .ac-wrapper αν δεν υπάρχει ήδη
  let wrapper = input.parentNode;
  const needsWrap =
    !wrapper ||
    !wrapper.classList ||
    !wrapper.classList.contains("ac-wrapper");

  if(needsWrap){
    wrapper = document.createElement("div");
    wrapper.className = "ac-wrapper";
    input.parentNode.insertBefore(wrapper, input);
    wrapper.appendChild(input);
  }

  const dropdown = document.createElement("div");
  dropdown.className = "ac-dropdown";
  dropdown.style.display = "none";
  wrapper.appendChild(dropdown);

  let activeIndex    = -1;
  let currentMatches = [];

  function escapeRegex(s){
    return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  function highlight(team, q){
    const safe = escapeHtml(team);
    if(!q) return safe;
    const re = new RegExp("(" + escapeRegex(q) + ")", "i");
    return safe.replace(re, "<mark>$1</mark>");
  }

  function render(matches, q){
    currentMatches = matches;

    if(!matches.length){
      dropdown.style.display = "none";
      dropdown.innerHTML = "";
      activeIndex = -1;
      return;
    }

    dropdown.innerHTML = matches.map((team, i) => `
      <div class="ac-item" data-team="${escapeHtml(team)}" data-index="${i}">
        <span class="ac-logo">${logoHTML(team)}</span>
        <span class="ac-name">${highlight(team, q)}</span>
      </div>
    `).join("");

    dropdown.style.display = "block";
    activeIndex = -1;

    dropdown.querySelectorAll(".ac-item").forEach(item => {
      item.addEventListener("mousedown", e => {
        e.preventDefault();   // να μην χαθεί το focus πριν το click
        select(item.dataset.team);
      });
    });
  }

  function select(team){
    input.value = team;
    dropdown.style.display = "none";
    activeIndex = -1;
    // Ειδοποιούμε τους listeners (π.χ. renderGames) για την αλλαγή
    input.dispatchEvent(new Event("input", { bubbles: true }));
  }

  function filter(){
    const q = input.value.trim().toUpperCase();
    if(!q){
      render([], "");
      return;
    }
    const matches = TEAMS.filter(t => t.includes(q)).slice(0, 8);
    render(matches, q);
  }

  function updateActive(items){
    items.forEach((it, i) => it.classList.toggle("ac-active", i === activeIndex));
    if(items[activeIndex]){
      items[activeIndex].scrollIntoView({ block: "nearest" });
    }
  }

  input.addEventListener("input", filter);
  input.addEventListener("focus", filter);

  input.addEventListener("keydown", e => {
    const items = dropdown.querySelectorAll(".ac-item");
    if(!items.length){
      if(e.key === "Escape") dropdown.style.display = "none";
      return;
    }

    if(e.key === "ArrowDown"){
      e.preventDefault();
      activeIndex = (activeIndex + 1) % items.length;
      updateActive(items);
    } else if(e.key === "ArrowUp"){
      e.preventDefault();
      activeIndex = activeIndex <= 0 ? items.length - 1 : activeIndex - 1;
      updateActive(items);
    } else if(e.key === "Enter"){
      if(activeIndex >= 0 && items[activeIndex]){
        e.preventDefault();
        select(items[activeIndex].dataset.team);
      }
    } else if(e.key === "Escape"){
      dropdown.style.display = "none";
      activeIndex = -1;
    }
  });

  input.addEventListener("blur", () => {
    setTimeout(() => {
      dropdown.style.display = "none";
      activeIndex = -1;
    }, 150);
  });
}