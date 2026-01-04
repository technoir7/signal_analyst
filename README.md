# SPEC_D_001: Micro-Analyst OSINT Intelligence System

**A deterministic OSINT enrichment engine with LLM-based synthesis, suitable for competitor intelligence, deal sourcing, and internal decision support.**

---

## Quick Start

```bash
cd micro_analyst_full_with_scripts

# Configure environment
cp .env.example .env
# Edit .env: set USE_OLLAMA_LLM=1 (local, free) or GOOGLE_API_KEY (cloud, paid)

# Install dependencies
pip install -r requirements.txt

# Start MCPs (optional for full scraping)
./run_all.sh

# Start agent
uvicorn agent.micro_analyst:app --port 8000
```

---

## API Usage

### Submit Analysis

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
  -d '{"company_url": "https://example.com", "focus": "competitor intelligence"}'

# Returns: {"job_id": "uuid", "status": "queued"}
```

### Poll Status

```bash
curl http://localhost:8000/jobs/{job_id} \
  -H "X-API-Key: your_api_key"

# Returns: {"status": "complete", "progress": 100, "result": {...}}
```

### Export PDF

```bash
curl http://localhost:8000/reports/{job_id}/pdf \
  -H "X-API-Key: your_api_key" --output report.pdf
```

---

## Features

| Feature | Status |
|---------|--------|
| Real LLM synthesis (Gemini or Ollama) | ✅ |
| Non-blocking execution | ✅ |
| Job progress tracking (0-100%) | ✅ |
| Partial failure propagation | ✅ |
| API key authentication | ✅ |
| SQLite report persistence | ✅ |
| PDF export | ✅ (requires system deps) |
| SSRF protection | ✅ |
| Cross-user data isolation | ✅ |

---

## Configuration

```bash
# Local LLM (FREE - recommended for development)
USE_OLLAMA_LLM=1
OLLAMA_MODEL=gemma3:27b

# Cloud LLM (PAID - ~$0.01-0.05/report)
USE_GEMINI_LLM=1
GOOGLE_API_KEY=your_key

# Authentication & Quotas
ENABLE_AUTH=1
VALID_API_KEYS=key1,key2,key3
DAILY_QUOTA_PER_KEY=100
MAX_REQUESTS_PER_MINUTE=10

# Resource Limits
JOB_TTL_SECONDS=3600
MAX_JOBS_IN_MEMORY=500
```

---

## Security & Commercial Features

### Implemented Protections

| Protection | Description |
|------------|-------------|
| **Rate Limiting** | Sliding window limit (default 10 req/min/key) |
| **Quota Enforcement** | Daily reporting limits (default 100/day/key) |
| **Job Persistence** | Jobs survive server restarts (SQLite backed) |
| **SSRF Prevention** | Blocks localhost, private IPs, AWS metadata, cloud endpoints |
| **API Key Auth** | Header-based authentication on all protected endpoints |
| **Ownership Validation** | Users can only access their own jobs and reports |
| **Input Validation** | Strict length limits on all inputs to prevent memory attacks |

### URL Validation

The following are **blocked**:
- `http://localhost:*`
- `http://127.0.0.1:*`
- `http://192.168.*.*` (private)
- `http://10.*.*.*` (private)
- `http://169.254.169.254` (AWS metadata)
- `file://` scheme

### Production Recommendations

- Enable `ENABLE_AUTH=1` in production
- Set `DAILY_QUOTA_PER_KEY` based on your subscription tiers
- Use HTTPS (reverse proxy with nginx/caddy)
- Rotate API keys regularly
- Set up database backups
- Monitor for unusual usage patterns

---

## Report Modes

| Mode | Focus String | Style |
|------|-------------|-------|
| Standard | (default) | Neutral consultant |
| Red Team | `"red team"` | Adversarial OPFOR |
| Narrative | `"narrative"` | Long-form prose |
| Investor | `"investor"` | Metrics-driven PE |
| Founder | `"founder"` | YC partner playbook |

---

## Architecture

```
Agent (port 8000)
├── /analyze      → Background job, returns job_id
├── /jobs/{id}    → Poll status (auth + ownership)
└── /reports/pdf  → Export (auth + ownership)
    │
    ▼
LLM Client (Ollama or Gemini)
├── plan_tools()      → Which MCPs to call
└── synthesize_report() → Generate insights
    │
    ▼
MCP Services (ports 8001-8007)
├── web_scrape    → HTML + metadata
├── seo_probe     → SEO analysis
├── tech_stack    → Framework detection
├── reviews       → Sentiment analysis
├── social        → Social presence
├── careers       → Hiring signals
└── ads           → Ad platform detection
    │
    ▼
SQLite (reports.db)
├── reports table → Full OSINT profiles
└── usage table   → Per-key daily counts
```

---

## Limitations (By Design)

- Single-server only (no horizontal scaling)
- In-memory job state (lost on restart)
- No JavaScript rendering (static HTML only)
- PDF requires system deps (`brew install pango cairo`)

---

## License

Proprietary. Not for redistribution.
