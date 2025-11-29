# **Micro-Analyst OSINT Agent**

### **A deterministic, multi-MCP intelligence system for real-time organizational analysis**




---

## **1. Overview — What This Agent Does**

Micro-Analyst is a **self-directed autonomous OSINT analyst** built for the **Verisense | Sense Space** hackathon.
It uses a chain-of-thought planning stage, modular MCP microservices, and deterministic heuristics to produce **consultant-grade intelligence reports** on any company’s public surface:

* Website structure & messaging
* SEO posture
* Tech stack fingerprinting
* Reviews, social signals, hiring behavior
* Ads presence (if available)
* Unified Pydantic model: `CompanyOSINTProfile`
* Fully deterministic fallback behaviors

This project implements the **full machine spec** of the hackathon prompt and the refined technical constraints in the project state file.

---

## **2. Why This Agent Matters (Hackathon-Focused Pitch)**

Judges are looking for:

### **✔ Autonomous behavior**

Micro-Analyst performs a **planning step** using an LLM abstraction (`plan_tools`) to decide which MCP tools to activate based on company type, URL, and domain-specific keywords. When planning fails, it automatically falls back to a safe deterministic plan.

### **✔ Modular MCP architecture**

Each OSINT function is a **standalone FastAPI microservice**—independent, stateless, and robust.
All MCPs conform to the hackathon’s `/run` JSON contract.

### **✔ Determinism + Reliability**

The entire system is designed for **zero nondeterminism**, no external network calls (beyond fetching HTML), no randomness, stable Pydantic v2 schemas, and test-enforced invariants.

### **✔ Real-world value**

Micro-Analyst models how a modern A2A-style agent can **sense, interpret, and act** on public-facing organizational data—precisely the kind of agent the hackathon wants.

### **✔ Human-readable output**

Every run ends with a structured Markdown intelligence report synthesizing all MCP outputs.

---

## **3. Architecture**

```
project_root/
    core/
    mcp_web_scrape/
    mcp_seo_probe/
    mcp_tech_stack/
    mcp_reviews_snapshot/
    mcp_social_snapshot/
    mcp_careers_intel/
    agent/
    miniapp/
    utils/
    demo_data/
```

This structure follows the exact required directory layout in the hackathon specification.

Each MCP is a **FastAPI service** implementing:

* `POST /run`
* deterministic heuristics
* strict Pydantic I/O schemas
* safe error handling
* no LLM calls inside MCPs

---

## **4. Intelligence Pipeline**

### **Step 1 — Planning**

`llm_client.plan_tools()` inspects:

* `company_url`
* `focus`
* semantic keyword cues (reviews, hiring, ads, etc.)

Output: a JSON plan activating specific MCPs.

### **Step 2 — MCP Execution**

Ordered execution (required by spec):

1. Web Scrape
2. (If success) SEO + Tech
3. Optional: Reviews, Social, Careers, Ads

### **Step 3 — Profile Merge**

All MCP outputs are merged into a unified `CompanyOSINTProfile`.

### **Step 4 — Report Synthesis**

`llm_client.synthesize_report()` produces modular Markdown sections:

* Web
* SEO
* Tech
* Reviews
* Social
* Hiring
* Ads
* Recommendations

If synthesis fails → required fallback text is returned.

---

## **5. Deterministic LLM Abstraction**

The LLM abstraction **does not call external APIs** in this version.
It provides:

* deterministic planning rules
* deterministic synthesized Markdown

This satisfies the hackathon rule: *LLM usage optional; dummy implementation acceptable*.

---

## **6. Mini-App Frontend**

A minimal browser interface allows:

* entering a company URL
* toggling demo mode
* viewing Markdown intelligence reports

The demo mode loads cached profiles from `demo_data/`.

---

## **7. Key Technical Guarantees**

### **✔ Zero randomness**

### **✔ No time-based behavior**

### **✔ All failures degrade gracefully**

### **✔ All MCPs are stateless and sandbox-safe**

### **✔ All Pydantic schemas match the machine spec exactly**

### **✔ Entire system passes test suite and meta-tests**

Everything aligns with the hackathon’s stability > cleverness philosophy.

---

## **8. How to Run**

### **MCP Microservices**

```bash
uvicorn mcp_web_scrape.server:app --port 9101
uvicorn mcp_seo_probe.server:app --port 9102
uvicorn mcp_tech_stack.server:app --port 9103
uvicorn mcp_reviews_snapshot.server:app --port 9104
uvicorn mcp_social_snapshot.server:app --port 9105
uvicorn mcp_careers_intel.server:app --port 9106
# ads MCP optional
```

### **Micro-Analyst Agent**

```bash
uvicorn agent.micro_analyst:app --port 8000
```

### **Web UI**

Open:

```
miniapp/index.html
```

---

## **9. Demo Mode**

Run:

```bash
# Example:
python agent/micro_analyst.py
```

Then activate Demo Mode in the UI to load:

* `blue_bottle.json`
* `sweetgreen.json`
* `glossier.json`

All demo files load cleanly into `CompanyOSINTProfile`.

---

## **10. Hackathon Criteria Checklist**

| Requirement                      | Status |
| -------------------------------- | ------ |
| Modular A2A-style agent          | ✔      |
| Uses MCP microservices           | ✔      |
| Autonomous planning stage        | ✔      |
| Fully deterministic execution    | ✔      |
| Real-time actionable data        | ✔      |
| Frontend for demonstration       | ✔      |
| Demo data for offline mode       | ✔      |
| Robust error handling            | ✔      |
| Stateless MCPs                   | ✔      |
| Clear deliverable for 2-min demo | ✔      |

---

## **11. Key Features**

This project is built exactly according to the hackathon’s **machine spec**, emphasizing:

* reliability
* deterministic reasoning
* agent autonomy
* modular design
* clear UX

It demonstrates a **full-stack autonomous intelligence system**: planning → sensing → reasoning → reporting.


# Analyst Workspace

This workspace contains the `micro_analyst_full_with_scripts` project.

To run the development server using uvicorn:

```bash
cd micro_analyst_full_with_scripts
uvicorn agent.micro_analyst:app --reload --port 8000
```# signal_analyst

