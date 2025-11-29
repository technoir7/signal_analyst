// miniapp/app.js

const API_URL = "http://localhost:8000/analyze";

/* Convert style code -> full descriptive label */
function getStyleLabel(code) {
  switch (code) {
    case "A":
      return "A – Default consultant style";
    case "B":
      return "B – OSINT analyst / tactical intelligence";
    case "C":
      return "C – Founder-facing / product strategy";
    case "D":
      return "D – Cold operator, $10k client work";
    case "E":
      return "E – McKinsey/BCG-style management report";
    case "F":
      return "F – Concise, hard-edged 2-page brief";
    default:
      return "A – Default consultant style";
  }
}

async function analyzeCompany(event) {
  event.preventDefault();

  const status = document.getElementById("status");
  const reportEl = document.getElementById("report-markdown");
  const jsonEl = document.getElementById("json-output");

  const companyName = document.getElementById("company-name").value.trim();
  const companyUrl = document.getElementById("company-url").value.trim();
  const focusRaw = document.getElementById("focus").value.trim();
  const styleCode = document.getElementById("style-preset").value;

  if (!companyUrl) {
    status.textContent = "Please provide a company URL.";
    return;
  }

  const styleLabel = getStyleLabel(styleCode);

  // inject the style instruction into focus
  const combinedFocus = focusRaw
    ? `[STYLE: ${styleLabel}] ${focusRaw}`
    : `[STYLE: ${styleLabel}]`;

  const payload = {
    company_name: companyName || null,
    company_url: companyUrl,
    focus: combinedFocus
  };

  status.textContent = "Running analysis…";
  reportEl.textContent = "";
  jsonEl.textContent = "";

  try {
    const resp = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!resp.ok) {
      const text = await resp.text();
      status.textContent = `Error: ${resp.status}`;
      reportEl.textContent = text;
      return;
    }

    const data = await resp.json();

    // display raw markdown for now
    reportEl.textContent = data.report_markdown || "(no report)";
    jsonEl.textContent = JSON.stringify(data.profile, null, 2);

    status.textContent = "Analysis complete.";
  } catch (err) {
    console.error("Request failed", err);
    status.textContent = "Error contacting API.";
    reportEl.textContent = String(err);
  }
}

/* Toggle JSON container */
function setupJsonToggle() {
  const toggleBtn = document.getElementById("toggle-json");
  const jsonContainer = document.getElementById("json-container");

  toggleBtn.addEventListener("click", () => {
    const hidden = jsonContainer.classList.contains("hidden");
    if (hidden) {
      jsonContainer.classList.remove("hidden");
      toggleBtn.textContent = "Hide JSON Profile";
    } else {
      jsonContainer.classList.add("hidden");
      toggleBtn.textContent = "Show JSON Profile";
    }
  });
}

function main() {
  document
    .getElementById("analyze-form")
    .addEventListener("submit", analyzeCompany);

  setupJsonToggle();
}

document.addEventListener("DOMContentLoaded", main);
