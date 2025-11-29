const API_BASE = "http://localhost:8000"; // FastAPI agent

const companyNameInput = document.getElementById("companyName");
const companyUrlInput = document.getElementById("companyUrl");
const focusInput = document.getElementById("focus");
const analyzeBtn = document.getElementById("analyzeBtn");
const statusEl = document.getElementById("status");
const reportEl = document.getElementById("report");
const rawJsonEl = document.getElementById("rawJson");
const toggleJsonBtn = document.getElementById("toggleJsonBtn");

let lastProfile = null;

function setStatus(text) {
  statusEl.textContent = text || "";
}

function setReport(markdown) {
  if (!markdown) {
    reportEl.innerHTML = '<p class="placeholder">No report generated.</p>';
    return;
  }
  // Spec says we can render markdown as plain text; we'll just dump it.
  reportEl.textContent = markdown;
}

function setRawJson(profile) {
  if (!profile) {
    rawJsonEl.textContent = "";
    return;
  }
  rawJsonEl.textContent = JSON.stringify(profile, null, 2);
}

async function runAnalysis() {
  const name = companyNameInput.value.trim() || null;
  const url = companyUrlInput.value.trim();
  const focus = focusInput.value.trim() || null;

  if (!url) {
    alert("Please enter a company URL.");
    return;
  }

  setStatus("Analyzing...");
  analyzeBtn.disabled = true;
  setReport("");
  setRawJson(null);

  try {
    const payload = {
      company_name: name,
      company_url: url,
      focus: focus,
    };

    const resp = await fetch(`${API_BASE}/analyze`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}`);
    }

    const data = await resp.json();
    lastProfile = data.profile || null;

    setReport(data.report_markdown || "");
    setRawJson(lastProfile);
    setStatus("Done.");
  } catch (err) {
    console.error(err);
    setStatus("Error. See console.");
    reportEl.innerHTML =
      '<p class="placeholder">Error during analysis. Check console logs.</p>';
  } finally {
    analyzeBtn.disabled = false;
  }
}

analyzeBtn.addEventListener("click", () => {
  runAnalysis();
});

toggleJsonBtn.addEventListener("click", () => {
  if (rawJsonEl.classList.contains("hidden")) {
    rawJsonEl.classList.remove("hidden");
  } else {
    rawJsonEl.classList.add("hidden");
  }
});
