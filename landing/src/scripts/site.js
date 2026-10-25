const status = document.querySelector("#site-status");

function announce(message) {
  if (status) status.textContent = message;
}

document.querySelectorAll("[data-todo]").forEach((link) => {
  link.addEventListener("click", (event) => {
    event.preventDefault();
    const type = link.dataset.todo;
    const configName = type === "support" ? "SUPPORT_URL" : type === "dashboard" ? "DASHBOARD_URL" : "INVITE_URL";
    announce(configName + " is not configured yet. Set it in src/config.ts before launch.");
  });
});

const navToggle = document.querySelector(".nav-toggle");
const primaryNav = document.querySelector("#primary-nav");
if (navToggle && primaryNav) {
  navToggle.addEventListener("click", () => {
    const open = navToggle.getAttribute("aria-expanded") === "true";
    navToggle.setAttribute("aria-expanded", String(!open));
    primaryNav.classList.toggle("is-open", !open);
  });
  primaryNav.addEventListener("click", (event) => {
    if (event.target instanceof HTMLAnchorElement) {
      primaryNav.classList.remove("is-open");
      navToggle.setAttribute("aria-expanded", "false");
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      primaryNav.classList.remove("is-open");
      navToggle.setAttribute("aria-expanded", "false");
      navToggle.focus();
    }
  });
}

document.querySelectorAll("[data-command-catalog]").forEach((catalog) => {
  const rows = [...catalog.querySelectorAll("[data-command-row]")];
  const search = catalog.querySelector("[data-command-search]");
  const tier = catalog.querySelector("[data-tier-filter]");
  const tabs = [...catalog.querySelectorAll("[data-category]")];
  const count = catalog.querySelector("[data-command-count]");
  const empty = catalog.querySelector("[data-empty-results]");
  let selectedCategory = "all";
  const visibleReferenceRows = rows.filter((row) => row.dataset.tier !== "Bot owner");

  function update() {
    const query = search?.value.trim().toLowerCase() || "";
    const selectedTier = tier?.value || "all";
    let visibleCount = 0;
    for (const row of rows) {
      const categoriesMatch = selectedCategory === "all" || row.dataset.category === selectedCategory;
      const tierText = row.dataset.tier || "";
      const tierMatches = selectedTier === "all" || tierText.split("/").some((part) => part.trim().toLowerCase() === selectedTier.toLowerCase());
      const searchMatches = !query || row.dataset.search.includes(query);
      const show = row.dataset.tier !== "Bot owner" && categoriesMatch && tierMatches && searchMatches;
      row.hidden = !show;
      if (show) visibleCount += 1;
    }
    if (count) count.textContent = "Showing " + visibleCount + " of " + visibleReferenceRows.length + " documented commands";
    if (empty) empty.hidden = visibleCount !== 0;
  }

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      selectedCategory = tab.dataset.category || "all";
      tabs.forEach((other) => {
        const selected = other === tab;
        other.classList.toggle("is-selected", selected);
        other.setAttribute("aria-selected", String(selected));
      });
      update();
    });
  });
  search?.addEventListener("input", update);
  tier?.addEventListener("change", update);

  catalog.querySelectorAll("[data-copy-command]").forEach((button) => {
    button.addEventListener("click", async () => {
      const command = button.dataset.copyCommand || "";
      try {
        if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(command);
        else {
          const input = document.createElement("textarea");
          input.value = command;
          input.style.position = "fixed";
          input.style.opacity = "0";
          document.body.append(input);
          input.select();
          document.execCommand("copy");
          input.remove();
        }
        announce("Copied " + command);
        const label = button.querySelector("span");
        if (label) {
          const previous = label.textContent;
          label.textContent = "Copied";
          window.setTimeout(() => { label.textContent = previous; }, 1400);
        }
      } catch {
        announce("Could not copy. Select the command text to copy it manually.");
      }
    });
  });
  update();

  const slashInput = catalog.querySelector("[data-command-search]");
  document.addEventListener("keydown", (event) => {
    if (event.key === "/" && !event.ctrlKey && !event.metaKey && !event.altKey) {
      const target = event.target;
      if (target instanceof HTMLElement && /INPUT|TEXTAREA|SELECT/.test(target.tagName)) return;
      event.preventDefault();
      slashInput?.focus();
    }
  });
});

const hero = document.querySelector("#hero");
const mobileCta = document.querySelector(".mobile-cta");
if (hero && mobileCta) {
  mobileCta.querySelector("a")?.setAttribute("tabindex", "-1");
}
if (hero && mobileCta && "IntersectionObserver" in window) {
  const observer = new IntersectionObserver(([entry]) => {
    mobileCta.classList.toggle("is-visible", !entry.isIntersecting);
    mobileCta.setAttribute("aria-hidden", String(entry.isIntersecting));
    if (entry.isIntersecting) mobileCta.querySelector("a")?.setAttribute("tabindex", "-1");
    else mobileCta.querySelector("a")?.removeAttribute("tabindex");
  }, { threshold: 0.05 });
  observer.observe(hero);
}

const revealTargets = document.querySelectorAll(".reveal");
if ("IntersectionObserver" in window && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
  const revealObserver = new IntersectionObserver((entries, observer) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-revealed");
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12 });
  revealTargets.forEach((element) => revealObserver.observe(element));
} else {
  revealTargets.forEach((element) => element.classList.add("is-revealed"));
}
