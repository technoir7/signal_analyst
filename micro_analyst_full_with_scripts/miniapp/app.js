// Signal-Analyst – Frontend Logic

const API_URL = "http://localhost:8000/analyze";

const form = document.getElementById("analyze-form");
const companyNameInput = document.getElementById("company_name");
const companyUrlInput = document.getElementById("company_url");
const focusInput = document.getElementById("focus");
const reportStyleSelect = document.getElementById("report_style");
const demoModeCheckbox = document.getElementById("demo_mode");
const demoDatasetSelect = document.getElementById("demo_dataset");
const analyzeButton = document.getElementById("analyze-button");

const statusText = document.getElementById("status-text");
const statusDot = document.querySelector(".dot");
const cardStatusBadge = document.getElementById("card-status-badge");
const planSummaryBadge = document.getElementById("plan-summary-badge");
const surfaceBadge = document.getElementById("surface-badge");
const cotStatusBadge = document.getElementById("cot-status-badge");

const planGrid = document.getElementById("plan-grid");
const reportMarkdownEl = document.getElementById("report-markdown");

const metaCompanyName = document.getElementById("meta-company-name");
const metaCompanyUrl = document.getElementById("meta-company-url");
const metaInference = document.getElementById("meta-inference");

const metricMetaIssues = document.getElementById("metric-meta-issues");
const metricKeywords = document.getElementById("metric-keywords");
const metricFrameworks = document.getElementById("metric-frameworks");
const metricHiring = document.getElementById("metric-hiring");

const latencyValue = document.getElementById("latency-value");
const modeValue = document.getElementById("mode-value");

const mcpWeb = document.getElementById("mcp-web");
const mcpSeo = document.getElementById("mcp-seo");
const mcpTech = document.getElementById("mcp-tech");
const mcpReviews = document.getElementById("mcp-reviews");
const mcpSocial = document.getElementById("mcp-social");
const mcpCareers = document.getElementById("mcp-careers");
const mcpAds = document.getElementById("mcp-ads");

const cotStream = document.getElementById("cot-stream");

// Command palette elements
const cmdkBackdrop = document.getElementById("cmdk-backdrop");
const cmdkInput = document.getElementById("cmdk-input");

// ---------- Status helpers ----------

function setStatus(state, message) {
  statusText.textContent = message;

  statusDot.classList.remove("dot--idle", "dot--running", "dot--error");
  cardStatusBadge.classList.remove(
    "badge-status--neutral",
    "badge-status--active",
    "badge-status--error"
  );

  switch (state) {
    case "running":
      statusDot.classList.add("dot--running");
      cardStatusBadge.classList.add("badge-status--active");
      cardStatusBadge.textContent = "RUNNING";
      break;
    case "error":
      statusDot.classList.add("dot--error");
      cardStatusBadge.classList.add("badge-status--error");
      cardStatusBadge.textContent = "ERROR";
      break;
    default:
      statusDot.classList.add("dot--idle");
      cardStatusBadge.classList.add("badge-status--neutral");
      cardStatusBadge.textContent = "IDLE";
      break;
  }
}

function setLoadingState(isLoading) {
  analyzeButton.disabled = isLoading;
  analyzeButton.textContent = isLoading ? "Running…" : "Run Analysis";
}

function setModeLabel(label) {
  modeValue.textContent = label;
}

// ---------- Inline demo payloads ----------

const INLINE_DEMOS = {
  blue_bottle: {
    profile: {
      company: {
        name: "Blue Bottle Coffee",
        url: "https://bluebottlecoffee.com",
      },
      web: {
        url: "https://bluebottlecoffee.com",
        snapshot_summary:
          "Modern, high-quality coffee roaster and cafe brand with emphasis on origin, brewing, and subscription.",
      },
      seo: {
        meta_issues: [
          "Missing meta description on several product detail pages.",
          "Duplicate title tags on archive/collection pages.",
        ],
        heading_issues: ["Multiple H1s on homepage hero + featured story block."],
        keyword_summary: [
          "single origin",
          "coffee subscription",
          "pour over",
          "espresso",
        ],
      },
      tech_stack: {
        frameworks: ["Next.js", "React"],
        analytics: ["Google Analytics", "Segment"],
      },
      reviews: {
        summary:
          "Strong fan base with praise for coffee quality and design; complaints center around price and wait times.",
        sources: ["Google Maps", "Yelp"],
      },
      social: {
        platforms: ["Instagram", "Twitter", "Facebook"],
      },
      careers: {
        open_roles: [
          "Senior Product Manager, E-commerce",
          "Brand Marketing Manager",
          "Café Manager - Bay Area",
        ],
      },
      ads: {
        platforms: ["Meta", "Google", "TikTok"],
      },
    },
    report_markdown: `# Business Intelligence Report: Blue Bottle Coffee

## 1. Company Overview

Blue Bottle is a third-wave coffee company operating a hybrid of retail cafes,
wholesale distribution, and a global e-commerce subscription business.

## 2. Web / SEO Surface

- Meta issues concentrated on long-tail product pages (missing descriptions).
- Core marketing pages are clean and structured; titles are coherent.

## 3. Tech Stack & Instrumentation

- Next.js + React front-end with Segment + Google Analytics instrumentation.

## 4. Customer Voice & Reviews

- Positive: quality, ambiance, consistency.
- Negative: price sensitivity and perceived elitism.

## 5. Org & Hiring Signals

- Emphasis on e-commerce product management and brand.

## 6. Growth & Ads Read

- Visible activity on Meta, Google, and TikTok.

## 7. Strategic Notes

- High brand equity; main risk is macro price sensitivity in premium coffee.`,
  },
};

// ---------- CoT helpers ----------

function appendCotLine(kind, text) {
  const li = document.createElement("li");
  li.className = `cot-line cot-line--${kind}`;
  li.textContent = text;
  cotStream.appendChild(li);
  cotStream.scrollTop = cotStream.scrollHeight;
}

function resetCot() {
  cotStream.innerHTML = "";
}

function setCotStatus(state) {
  cotStatusBadge.classList.remove(
    "badge-status--neutral",
    "badge-status--active",
    "badge-status--error"
  );

  switch (state) {
    case "running":
      cotStatusBadge.classList.add("badge-status--active");
      cotStatusBadge.textContent = "SESSION LIVE";
      break;
    case "error":
      cotStatusBadge.classList.add("badge-status--error");
      cotStatusBadge.textContent = "SESSION ERROR";
      break;
    default:
      cotStatusBadge.classList.add("badge-status--neutral");
      cotStatusBadge.textContent = "AWAITING INPUT";
      break;
  }
}

// ---------- Plan preview ----------

function createPlanPreview({ hasUrl, focus, forceFullPlan }) {
  if (!hasUrl && !forceFullPlan) {
    return {
      use_web_scrape: false,
      use_seo_probe: false,
      use_tech_stack: false,
      use_reviews_snapshot: false,
      use_social_snapshot: false,
      use_careers_intel: false,
      use_ads_snapshot: false,
    };
  }

  const plan = {
    use_web_scrape: true,
    use_seo_probe: true,
    use_tech_stack: true,
    use_reviews_snapshot: false,
    use_social_snapshot: false,
    use_careers_intel: false,
    use_ads_snapshot: false,
  };

  const lowerFocus = (focus || "").toLowerCase();

  const containsAny = (text, phrases) => phrases.some((p) => text.includes(p));

  if (containsAny(lowerFocus, ["review", "reputation", "rating", "trustpilot"])) {
    plan.use_reviews_snapshot = true;
  }

  if (
    containsAny(lowerFocus, [
      "social",
      "twitter",
      "instagram",
      "tiktok",
      "brand",
      "community",
    ])
  ) {
    plan.use_social_snapshot = true;
  }

  if (containsAny(lowerFocus, ["hiring", "talent", "org", "team", "recruit"])) {
    plan.use_careers_intel = true;
  }

  if (containsAny(lowerFocus, ["ads", "advertising", "campaign", "paid", "growth", "marketing"])) {
    plan.use_ads_snapshot = true;
  }

  return plan;
}

function renderPlanGrid(plan) {
  const items = [
    ["WEB SCRAPE", "use_web_scrape"],
    ["SEO PROBE", "use_seo_probe"],
    ["TECH STACK", "use_tech_stack"],
    ["REVIEWS", "use_reviews_snapshot"],
    ["SOCIAL", "use_social_snapshot"],
    ["HIRING", "use_careers_intel"],
    ["ADS", "use_ads_snapshot"],
  ];

  planGrid.innerHTML = "";
  items.forEach(([label, key]) => {
    const active = !!plan[key];
    const div = document.createElement("div");
    div.className = "plan-item" + (active ? " plan-item--active" : "");
    div.innerHTML = `
      <span class="plan-dot ${active ? "plan-dot--active" : ""}"></span>
      <span class="plan-label">${label}</span>
    `;
    planGrid.appendChild(div);
  });
}

// ---------- MCP status ----------

function resetSurfaceBadges() {
  surfaceBadge.textContent = "Running…";
  surfaceBadge.classList.remove("badge-status--neutral", "badge-status--error");
  surfaceBadge.classList.add("badge-status--active");

  [mcpWeb, mcpSeo, mcpTech, mcpReviews, mcpSocial, mcpCareers, mcpAds].forEach((el) => {
    el.classList.remove("pill--on", "pill--error");
    el.classList.add("pill--off");
  });
}

function setMcpStatus(el, state) {
  el.classList.remove("pill--off", "pill--on", "pill--error");
  if (state === "on") el.classList.add("pill--on");
  else if (state === "error") el.classList.add("pill--error");
  else el.classList.add("pill--off");
}

// ---------- Demo loading ----------

function loadDemoProfile(key) {
  const data = INLINE_DEMOS[key] || INLINE_DEMOS.blue_bottle;
  return Promise.resolve(data);
}

// ---------- Markdown rendering ----------

function renderMarkdown(text) {
  if (!text) {
    reportMarkdownEl.innerHTML =
      '<p class="placeholder">No report content returned.</p>';
    return;
  }

  const lines = text.split("\n");
  const html = [];
  let inList = false;

  for (const line of lines) {
    if (line.startsWith("## ")) {
      if (inList) {
        html.push("</ul>");
        inList = false;
      }
      const content = line.replace(/^##\s+/, "");
      html.push(`<h2>${content}</h2>`);
    } else if (line.startsWith("# ")) {
      if (inList) {
        html.push("</ul>");
        inList = false;
      }
      const content = line.replace(/^#\s+/, "");
      html.push(`<h1>${content}</h1>`);
    } else if (line.startsWith("- ")) {
      if (!inList) {
        html.push("<ul>");
        inList = true;
      }
      const content = line.replace(/^-+\s+/, "");
      html.push(`<li>${content}</li>`);
    } else if (line.trim() === "") {
      if (inList) {
        html.push("</ul>");
        inList = false;
      }
      html.push("<p></p>");
    } else {
      html.push(`<p>${line}</p>`);
    }
  }

  if (inList) {
    html.push("</ul>");
  }

  reportMarkdownEl.innerHTML = html.join("\n");
}

// ---------- CoT runner ----------

function runCotSequence(plan, modeLabel) {
  resetCot();
  setModeLabel(modeLabel.toUpperCase());

  setTimeout(() => {
    appendCotLine("system", "Session reset. Awaiting new target surface…");
  }, 50);

  setTimeout(() => {
    appendCotLine("plan", "Mode: " + modeLabel + ". Deriving tool plan from surface…");
  }, 350);

  setTimeout(() => {
    appendCotLine(
      "plan",
      "Enabled tools → " +
        Object.keys(plan)
          .filter((k) => plan[k])
          .map((k) => {
            switch (k) {
              case "use_web_scrape":
                return "WEB SCRAPE";
              case "use_seo_probe":
                return "SEO PROBE";
              case "use_tech_stack":
                return "TECH STACK";
              case "use_reviews_snapshot":
                return "REVIEWS";
              case "use_social_snapshot":
                return "SOCIAL";
              case "use_careers_intel":
                return "HIRING";
              case "use_ads_snapshot":
                return "ADS";
              default:
                return "";
            }
          })
          .filter(Boolean)
          .join(" · ")
    );
  }, 700);

  setTimeout(() => {
    appendCotLine(
      "mcp",
      "Dispatching mcp_web_scrape → primary domain (navigation, content density)."
    );
  }, 900);
}

// ---------- Render profile + report ----------

function renderProfileAndReport(profile, reportMarkdown) {
  if (!profile || typeof profile !== "object") {
    surfaceBadge.textContent = "No profile";
    surfaceBadge.classList.add("badge-status--error");
    return;
  }

  renderMarkdown(reportMarkdown || "");
  reportMarkdownEl.classList.remove("report-output--empty");

  const company = profile.company || {};
  metaCompanyName.textContent = company.name || "—";
  metaCompanyUrl.textContent = company.url || "—";

  const seo = profile.seo || {};
  const metaIssues = (seo.meta_issues || []).length;
  const headingIssues = (seo.heading_issues || []).length;
  metricMetaIssues.textContent = metaIssues + headingIssues;

  const keywordSummary = seo.keyword_summary || [];
  metricKeywords.textContent = keywordSummary.length || "0";

  const tech = profile.tech_stack || {};
  const frameworks = tech.frameworks || [];
  const analytics = tech.analytics || [];
  metricFrameworks.textContent = frameworks.length + analytics.length;

  const careers = profile.careers || {};
  const openRoles = careers.open_roles || [];
  metricHiring.textContent = openRoles.length.toString();

  surfaceBadge.textContent = "Surface updated";
  surfaceBadge.classList.remove("badge-status--neutral", "badge-status--error");
  surfaceBadge.classList.add("badge-status--active");

  if (profile.web) setMcpStatus(mcpWeb, "on");
  if (profile.seo) setMcpStatus(mcpSeo, "on");
  if (profile.tech_stack) setMcpStatus(mcpTech, "on");
  if (profile.reviews) setMcpStatus(mcpReviews, "on");
  if (profile.social) setMcpStatus(mcpSocial, "on");
  if (profile.careers) setMcpStatus(mcpCareers, "on");
  if (profile.ads) setMcpStatus(mcpAds, "on");

  const companySummary = [
    company.name || "Unknown company",
    company.url || "",
    profile.web && profile.web.snapshot_summary
      ? profile.web.snapshot_summary
      : "",
  ]
    .filter(Boolean)
    .join(" · ");

  metaInference.textContent =
    companySummary ||
    "Surface read unavailable. Try re-running with a valid URL and/or focus.";
}

// ---------- Command palette ----------

function openCmdK() {
  cmdkBackdrop.classList.add("cmdk-backdrop--visible");
  cmdkInput.value = "";
  cmdkInput.focus();
}

function closeCmdK() {
  cmdkBackdrop.classList.remove("cmdk-backdrop--visible");
}

function handleCommandSelection(cmd) {
  switch (cmd) {
    case "load_blue_bottle":
      demoModeCheckbox.checked = true;
      demoDatasetSelect.value = "blue_bottle";
      autoRunDemo();
      closeCmdK();
      break;
    case "toggle_demo":
      demoModeCheckbox.checked = !demoModeCheckbox.checked;
      closeCmdK();
      break;
    case "focus_growth":
      focusInput.value = "growth marketing & paid ads risk";
      closeCmdK();
      break;
    default:
      closeCmdK();
  }
}

function autoRunDemo() {
  companyNameInput.value = "";
  companyUrlInput.value = "";
  focusInput.value = "";
  const ev = new Event("submit", { cancelable: true });
  form.dispatchEvent(ev);
}

// ---------- Main submit handler ----------

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  resetSurfaceBadges();

  const companyName = companyNameInput.value.trim();
  const companyUrl = companyUrlInput.value.trim();
  const focus = focusInput.value.trim();
  const reportStyle =
    reportStyleSelect && reportStyleSelect.value
      ? reportStyleSelect.value
      : "standard";
  const demoMode = demoModeCheckbox.checked;
  const demoKey = demoDatasetSelect.value;

  const plan = createPlanPreview({
    hasUrl: !!companyUrl,
    focus,
    forceFullPlan: demoMode,
  });
  renderPlanGrid(plan);

  const modeLabel = demoMode ? "DEMO" : "LIVE";

  resetCot();
  runCotSequence(plan, modeLabel.toLowerCase());

  setStatus(
    "running",
    demoMode ? "Loading demo profile…" : "Dispatching agent API…"
  );
  setCotStatus("running");
  setLoadingState(true);

  const startTime = performance.now();

  try {
    let data;

    if (demoMode) {
      data = await loadDemoProfile(demoKey);
    } else {
      const resp = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          company_name: companyName || null,
          company_url: companyUrl || null,
          focus: focus || null,
          report_style: reportStyle,
        }),
      });
      if (!resp.ok) {
        throw new Error(`Agent API returned ${resp.status}`);
      }
      data = await resp.json();
      appendCotLine("synth", "Agent returned OSINT profile and markdown report.");
    }

    const elapsed = Math.round(performance.now() - startTime);
    latencyValue.textContent = `${elapsed} ms`;

    renderProfileAndReport(data.profile, data.report_markdown);
    setStatus("idle", "Analysis complete. You can refine focus or change target.");
    setCotStatus("idle");
    appendCotLine("synth", "Synthesis complete. Report ready for review.");
  } catch (err) {
    console.error(err);
    setStatus(
      "error",
      "Failure during analysis: " +
        (err && err.message ? err.message : "Unknown error")
    );
    setCotStatus("error");
    appendCotLine(
      "error",
      "Failure during analysis. Check console logs for more detail."
    );
  } finally {
    setLoadingState(false);
  }
});

// ---------- Keyboard shortcuts ----------

document.addEventListener("keydown", (event) => {
  if (event.key === "k" && (event.metaKey || event.ctrlKey)) {
    event.preventDefault();
    openCmdK();
  } else if (event.key === "Escape") {
    closeCmdK();
  }
});

cmdkBackdrop.addEventListener("click", (event) => {
  if (event.target === cmdkBackdrop) {
    closeCmdK();
  }
});

cmdkInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    const value = (cmdkInput.value || "").trim();
    if (!value) {
      closeCmdK();
      return;
    }
    handleCommandSelection(value.toLowerCase());
  } else if (event.key === "Escape") {
    closeCmdK();
  }
});

// ---------- Initial UI ----------

(function init() {
  demoModeCheckbox.checked = true;

  const initialPlan = createPlanPreview({
    hasUrl: false,
    focus: "",
    forceFullPlan: true,
  });
  renderPlanGrid(initialPlan);

  latencyValue.textContent = "– ms";
})();
