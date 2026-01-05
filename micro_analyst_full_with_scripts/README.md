<p align="center">
  <img src="https://dummyimage.com/1200x260/111827/ffffff&text=Micro-Analyst+OSINT+Suite" alt="Micro-Analyst OSINT Suite Banner">
</p>
## 🚀 Summary for Recruiters & Hiring Managers

**Micro-Analyst** is a fully working, modular OSINT platform built as a network of microservices with deterministic execution, schema-driven intelligence, and a fault-tolerant orchestration agent.

What this project demonstrates:

- **Systems Engineering:** Designed a distributed architecture with 7+ independent FastAPI microservices and a central orchestrator.
- **AI Engineering:** Implemented a deterministic LLM synthesis pipeline; integrated a sponsor LLM safely behind a feature flag.
- **Reliability & Observability:** Schema validation, safe fallbacks, clean data flows, structured logs, reproducible behavior.
- **Scalability & Modularity:** Each microservice can be reused independently by other agents or extended into new capabilities.
- **Real-World Agentic Design:** Built for Know-Your-Agent requirements and A2A interoperability; clean MCP interfaces.

In short:  
**This repository shows the ability to design, build, and ship a real distributed system—not just prompt an LLM.**


# **Micro-Analyst OSINT Suite**

### *A modular intelligence system for discovering how a company actually operates.*

---

## **1. Overview**

**Micro-Analyst** is a lightweight OSINT engine built around a simple idea:

> **Companies reveal themselves through the small traces they leave online.**

This project collects those signals—website structure, tech stack, SEO posture, social footprint, customer voice, hiring activity—and assembles them into a readable intelligence report.

Instead of relying on an LLM to "figure everything out," the system uses:

* **Small, specialized microservices** to gather structured data
* **A central orchestrator agent** to plan and run the pipeline
* **A unified Pydantic model** to normalize all intelligence
* **A deterministic LLM wrapper** to synthesize the final report

The architecture is intentionally modular, transparent, and easy to extend.

---

## **2. Why this project exists**

This was built for Sense Space’s emerging “agent sharing economy”—a world where AI agents and MCPs behave like **small economic units** that can be mixed, reused, swapped, and extended.

Micro-Analyst embodies that philosophy:

* Each MCP does *one thing* well
* Each produces **schema-defined, predictable output**
* Any service can be used by other agents without modification
* The orchestrator is just one example of how to combine them

The goal: build simple, composable units that other developers can rely on.

---

## **3. What the system actually does**

Given a company name and URL, Micro-Analyst:

1. **Scrapes the website** and extracts readable text
2. **Runs SEO heuristics** (deterministic, no external network calls)
3. **Fingerprints the tech stack** from the HTML
4. **Fetches reviews data** (stubbed but structured)
5. **Captures social presence** (stubbed but structured)
6. **Analyzes hiring signals** from careers pages
7. **Merges everything** into a `CompanyOSINTProfile`
8. **Generates a concise intelligence report** via deterministic LLM logic or sponsor LLM

The final output feels like what an analyst would write after a fast reconnaissance sweep.

---

## **4. Architecture**

### **A. Narrow tools > broad tools**

Each MCP microservice is independent, tightly scoped, and returns clean JSON.

### **B. Everything is composable**

The pipeline mirrors real intelligence work:

* gather
* clean
* normalize
* merge
* synthesize

### **C. LLM at the end, not the beginning**

All core intelligence is deterministic.
LLMs are only used to *interpret* already-structured data.

This makes the system reliable, debuggable, and easy to audit.

---

## **5. Sponsor Integration (Ambient)**

Micro-Analyst includes a **minimal, production-safe integration** with a sponsor LLM provider (Ambient).

It’s controlled entirely by `.env`:

```bash
USE_SPONSOR=ambient
AMBIENT_API_KEY=your_api_key
AMBIENT_API_BASE=https://api.ambient.llm
AMBIENT_MODEL=osint-report-1
```

If the flag is off, the agent falls back to a **fully deterministic synthetic report**.

If the sponsor fails, the system **auto-recovers** using local deterministic logic.

This preserves reproducibility while meeting the hackathon’s requirements.

---

## **6. Running the System**

### **Install dependencies**

```bash
pip install -r requirements.txt
```

### **Start individual services manually**

You can also start the agent directly with uvicorn:

```bash
uvicorn agent.micro_analyst:app --host 0.0.0.0 --port 8000
```

### **Start the full MCP + agent cluster (recommended)**

```bash
./run_all_tmux.sh
```

This launches:

| Service          | Port |
| ---------------- | ---- |
| Agent            | 8000 |
| Web Scraper      | 8001 |
| SEO Probe        | 8002 |
| Tech Stack       | 8003 |
| Reviews Snapshot | 8004 |
| Social Snapshot  | 8005 |
| Careers Intel    | 8006 |
| Ads Snapshot     | 8007 |

Attach to the tmux session:

```bash
tmux attach -t micro-analyst
```

Detach with `Ctrl-b d`.

Kill the cluster:

```bash
tmux kill-session -t micro-analyst
```

### **Frontend demo**

```bash
cd miniapp
python3 -m http.server 8080
```

Visit [http://localhost:8080](http://localhost:8080)

---

## **7. Local Development**

### **One-command environment + agent launcher**

```bash
./dev.sh
```

This script:

* Loads `.env`
* Sets up `.venv`
* Installs dependencies
* Runs tests
* Starts the agent on port **8000**

### **Run tests only**

```bash
./test.sh
```

---

## **8. Extending the system**

Because each MCP is isolated and schema-defined, extensions are straightforward:

* Competitive intelligence modules
* Pricing or product scrapers
* WHOIS/DNS/CDN/IP intelligence
* Social trend analysis
* Embeddings or clustering
* Fraud/abuse indicators
* Vertical-specific intelligence (healthcare, fintech, logistics)

Or use the MCPs in an entirely different agent.

---

## **9. Why this project matters (to engineers & hiring managers)**

Micro-Analyst demonstrates practical engineering capabilities:

### **A. Systems design**

* Distributed microservices
* Deterministic orchestration
* Typed schemas and data normalization
* Clear execution flow
* Fault tolerance and safe fallbacks

### **B. AI engineering without duct tape**

* LLM is used *correctly*: for synthesis, not raw data retrieval
* Local deterministic behavior guarantees reproducibility
* Sponsor LLM integration is optional, safe, and feature-flagged

### **C. Code that is meant to be extended**

The architecture encourages other developers to build upon it.

### **D. A foundation for real-world agent ecosystems**

It plays nicely with Know-Your-Agent requirements and A2A registries.

This is the kind of project that shows strong engineering judgment, not just API glue.

---

## **10. Closing note**

Micro-Analyst is a small but functional foundation for agentic intelligence.
It favors clarity over cleverness, determinism over magic, and composability over monoliths.

If agents are going to operate as reusable economic units, the ecosystem needs tools like these—small, sharp, predictable, and easy to integrate.

