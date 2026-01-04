# SPEC_D_001: Micro-Analyst OSINT Intelligence System

**A deterministic OSINT enrichment engine with LLM-based synthesis, suitable for competitor intelligence, deal sourcing, and internal decision support.**

---

## System Overview

Micro-Analyst is a **production-grade autonomous OSINT analyst** that transforms public web surfaces into actionable intelligence reports. Unlike sales demos, this system is built for **recurring revenue generation** with:

- **Real AI synthesis** via Google Gemini LLM
- **Non-blocking execution** for responsive UX
- **Failure-resilient data pipelines** that propagate partial results
- **API key authentication** for access control
- **SQLite persistence** for report storage and retrieval
- **PDF export** for client deliverables
- **Usage metering** for billing integration

---

## Key Capabilities

### Intelligence Collection
- **Multi-surface web scraping** with user agent rotation
- **SEO diagnostics** (metadata, heading structure)
- **Tech stack fingerprinting** (frameworks, analytics, CMS, CDN)
- **Reviews analysis** (sentiment, complaints, praises)
- **Social footprint** detection (Instagram, Twitter, TikTok, YouTube)
- **Hiring signals** (open roles, org focus inference)
- **Ads presence** (paid media platforms, messaging themes)

### AI-Powered Synthesis
- **Contextual planning**: LLM decides which MCPs to activate based on target and focus
- **Multi-voice reports**: Standard, red-team, narrative, investor, founder modes
- **Structured insights**: SWOT-style analysis, prioritization, strategic recommendations
- **Fallback behavior**: Deterministic synthesis when LLM unavailable

### Production Features
- **Async job execution**: Immediate API response with job ID, poll for status
- **Partial failure handling**: One failed MCP doesn't abort entire analysis
- **Report persistence**: SQLite database with full audit trail
- **PDF export**: Client-ready deliverables with professional formatting
- **API key auth**: Simple but effective access control
- **Usage tracking**: Per-key daily report counts for billing

---

## Installation

### Prerequisites
- Python 3.9+
- Google Cloud API key with Gemini API enabled

### Setup

```bash
cd micro_analyst_full_with_scripts

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and set:
#   USE_GEMINI_LLM=1
#   GOOGLE_API_KEY=your_actual_key
#   ENABLE_AUTH=1  (optional, for production)
#   VALID_API_KEYS=key1,key2,key3
```

---

## Running the System

### Start All MCP Services

```bash
# Use the helper script:
./run_all.sh

# Or manually start each MCP:
uvicorn mcp_web_scrape.server:app --port 8001
uvicorn mcp_seo_probe.server:app --port 8002
uvicorn mcp_tech_stack.server:app --port 8003
uvicorn mcp_reviews_snapshot.server:app --port 8004
uvicorn mcp_social_snapshot.server:app --port 8005
uvicorn mcp_careers_intel.server:app --port 8006
uvicorn mcp_ads_snapshot.server:app --port 8007
```

### Start Main Agent

```bash
uvicorn agent.micro_analyst:app --port 8000 --reload
```

---

## API Usage

### 1. Submit Analysis Job

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -H "X-API-Key: demo_key_abc123" \
  -d '{
    "company_url": "https://example.com",
    "company_name": "Example Corp",
    "focus": "competitor intelligence"
  }'

# Response:
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "queued",
  "message": "Analysis started. Poll /jobs/{job_id} for status."
}
```

### 2. Poll Job Status

```bash
curl http://localhost:8000/jobs/a1b2c3d4-e5f6-7890-abcd-ef1234567890

# Response (complete):
{
  "status": "complete",
  "progress": 100,
  "result": {
    "profile": { ... },
    "report_markdown": "# OSINT Intelligence Report: Example Corp\n\n..."
  }
}
```

### 3. Export PDF

```bash
curl -H "X-API-Key: demo_key_abc123" \
  http://localhost:8000/reports/a1b2c3d4-e5f6-7890-abcd-ef1234567890/pdf \
  --output report.pdf
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_GEMINI_LLM` | `1` | Enable real LLM (set to `0` for deterministic fallback) |
| `GOOGLE_API_KEY` | - | **Required** for LLM functionality |
| `GEMINI_PLANNING_MODEL` | `gemini-2.0-flash-lite` | Model for MCP planning |
| `GEMINI_SYNTHESIS_MODEL` | `gemini-2.0-flash-lite` | Model for report synthesis |
| `ENABLE_AUTH` | `0` | Require API key authentication |
| `VALID_API_KEYS` | - | Comma-separated list of valid keys |
| `REPORTS_DB_PATH` | `./reports.db` | SQLite database location |

### Cost Estimation

With `gemini-2.0-flash-lite`:
- **Per report**: $0.01 - $0.05 USD
- **1000 reports/month**: ~$10 - $50 USD

---

## Failure Resilience

### User Agent Rotation
- 5 common browser signatures
- Random selection per request
- Reduces bot detection

### Partial Data Propagation
- Each MCP call wrapped in try/except
- Failed MCPs log warnings but don't abort
- Report generated with available data

### LLM Fallback
- Network/API errors → deterministic planning
- **System never fails due to LLM unavailability**

---

## Report Modes

- **Standard**: Neutral consultant voice
- **Red Team** (`focus: "red team"`): Adversarial OPFOR analysis
- **Narrative** (`focus: "narrative"`): Long-form prose
- **Investor** (`focus: "investor"`): Metrics-driven PE perspective
- **Founder** (`focus: "founder"`): YC partner-style playbook

---

## Productization Checklist

- [x] Real LLM integration (Gemini)
- [x] Non-blocking execution (FastAPI BackgroundTasks)
- [x] Job state tracking with progress updates
- [x] User agent rotation (5 signatures)
- [x] Partial failure propagation
- [x] API key authentication
- [x] SQLite report persistence
- [x] PDF export endpoint
- [x] Usage metering

---

## Deployment

### Single-Server (Recommended)

Use systemd or supervisor to manage processes. Example systemd service:

```ini
[Unit]
Description=Micro-Analyst Agent
After=network.target

[Service]
Type=simple
User=analyst
WorkingDirectory=/opt/micro_analyst
ExecStart=/opt/micro_analyst/.venv/bin/uvicorn agent.micro_analyst:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

### Backup Strategy

```bash
# Daily SQLite backup
0 2 * * * cp /path/to/reports.db /backups/reports_$(date +\%Y\%m\%d).db
```

---

## Limitations (By Design)

- **Single-server only**: No horizontal scaling
- **In-memory job state**: Restart loses pending jobs
- **No JavaScript rendering**: Static HTML scraping only
- **No proxy rotation**: Single IP per deployment
- **Manual invoicing**: No automated payment processing

These are **intentional scope boundaries** to minimize complexity for a chargeable MVP.

---

**Built for recurring low-interference income, not engineering prestige.**
