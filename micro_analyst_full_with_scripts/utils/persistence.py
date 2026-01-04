"""
Report persistence and export utilities.

Provides SQLite-based storage and PDF export for OSINT reports.
"""

import json
import os
import sqlite3
from datetime import datetime
from typing import Dict, Any, Optional

from loguru import logger

# Optional dependency - requires system libraries (pango, cairo, etc.)
try:
    import markdown
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError) as e:
    logger.warning(f"WeasyPrint not available (PDF export disabled): {e}")
    WEASYPRINT_AVAILABLE = False
    HTML = None  # type: ignore
    markdown = None  # type: ignore


DB_PATH = os.getenv("REPORTS_DB_PATH", "./reports.db")


def init_db() -> None:
    """Initialize SQLite database with required tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Reports table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            company_name TEXT,
            company_url TEXT,
            focus TEXT,
            profile_json TEXT,
            report_markdown TEXT,
            api_key TEXT
        )
    """)
    
    # Usage metering table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usage (
            api_key TEXT,
            date DATE,
            report_count INTEGER DEFAULT 0,
            PRIMARY KEY (api_key, date)
        )
    """)
    
    # Jobs table (for restart survival)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL DEFAULT 'queued',
            progress INTEGER DEFAULT 0,
            company_url TEXT,
            company_name TEXT,
            focus TEXT,
            api_key TEXT,
            result_json TEXT,
            error TEXT
        )
    """)
    
    # Cohorts table (for SaaS cohort mode)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cohorts (
            cohort_id TEXT PRIMARY KEY,
            anchor_url TEXT NOT NULL,
            category_hint TEXT,
            status TEXT DEFAULT 'proposed',
            created_at REAL,
            updated_at REAL,
            candidates_json TEXT,
            confirmed_urls_json TEXT,
            job_ids_json TEXT,
            matrix_json TEXT,
            report_md TEXT,
            api_key TEXT
        )
    """)
    
    conn.commit()
    conn.close()
    logger.info(f"Database initialized at {DB_PATH}")


def save_report(
    job_id: str,
    company_name: Optional[str],
    company_url: str,
    focus: Optional[str],
    profile: Dict[str, Any],
    report_markdown: str,
    api_key: str
) -> None:
    """Save a completed report to the database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            """
            INSERT INTO reports (id, created_at, company_name, company_url, focus, profile_json, report_markdown, api_key)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                datetime.utcnow(),
                company_name,
                company_url,
                focus,
                json.dumps(profile),
                report_markdown,
                api_key
            )
        )
        
        conn.commit()
        conn.close()
        logger.info(f"Report {job_id} saved to database")
    except Exception as e:
        logger.error(f"Failed to save report {job_id}: {e}")


def get_report(job_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a report from the database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM reports WHERE id = ?",
            (job_id,)
        )
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "id": row["id"],
                "created_at": row["created_at"],
                "company_name": row["company_name"],
                "company_url": row["company_url"],
                "focus": row["focus"],
                "profile": json.loads(row["profile_json"]),
                "report_markdown": row["report_markdown"],
                "api_key": row["api_key"]
            }
        return None
    except Exception as e:
        logger.error(f"Failed to retrieve report {job_id}: {e}")
        return None


def increment_usage(api_key: str) -> None:
    """Increment usage counter for an API key."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        today = datetime.utcnow().date()
        
        cursor.execute(
            """
            INSERT INTO usage (api_key, date, report_count)
            VALUES (?, ?, 1)
            ON CONFLICT(api_key, date) DO UPDATE SET report_count = report_count + 1
            """,
            (api_key, today)
        )
        
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to increment usage for {api_key}: {e}")


# ---------------------------------------------------------------------------
# Quota Enforcement
# ---------------------------------------------------------------------------
DAILY_QUOTA_PER_KEY = int(os.getenv("DAILY_QUOTA_PER_KEY", "100"))


def get_usage_today(api_key: str) -> int:
    """Get the number of reports generated today for an API key."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        today = datetime.utcnow().date()
        
        cursor.execute(
            "SELECT report_count FROM usage WHERE api_key = ? AND date = ?",
            (api_key, today)
        )
        
        row = cursor.fetchone()
        conn.close()
        
        return row[0] if row else 0
    except Exception as e:
        logger.error(f"Failed to get usage for {api_key}: {e}")
        return 0


def check_quota(api_key: str) -> tuple[bool, int]:
    """
    Check if API key is under daily quota.
    Returns (is_allowed, remaining_quota).
    """
    used = get_usage_today(api_key)
    remaining = max(0, DAILY_QUOTA_PER_KEY - used)
    return (used < DAILY_QUOTA_PER_KEY, remaining)


# ---------------------------------------------------------------------------
# Job Persistence (for restart survival)
# ---------------------------------------------------------------------------
def save_job(
    job_id: str,
    status: str,
    progress: int,
    company_url: str,
    company_name: Optional[str],
    focus: Optional[str],
    api_key: str,
    result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None
) -> None:
    """Save or update a job in the database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            """
            INSERT INTO jobs (id, status, progress, company_url, company_name, focus, api_key, result_json, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET 
                status = excluded.status,
                progress = excluded.progress,
                result_json = excluded.result_json,
                error = excluded.error
            """,
            (
                job_id,
                status,
                progress,
                company_url,
                company_name,
                focus,
                api_key,
                json.dumps(result) if result else None,
                error
            )
        )
        
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to save job {job_id}: {e}")


def get_job_db(job_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a job from the database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            result_json = row["result_json"]
            return {
                "id": row["id"],
                "status": row["status"],
                "progress": row["progress"],
                "company_url": row["company_url"],
                "company_name": row["company_name"],
                "focus": row["focus"],
                "api_key": row["api_key"],
                "result": json.loads(result_json) if result_json else None,
                "error": row["error"],
                "created_at": row["created_at"]
            }
        return None
    except Exception as e:
        logger.error(f"Failed to retrieve job {job_id}: {e}")
        return None


def load_pending_jobs() -> Dict[str, Dict[str, Any]]:
    """Load all non-complete jobs from database (for restart recovery)."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM jobs WHERE status NOT IN ('complete', 'failed')"
        )
        
        rows = cursor.fetchall()
        conn.close()
        
        pending = {}
        for row in rows:
            result_json = row["result_json"]
            pending[row["id"]] = {
                "status": row["status"],
                "progress": row["progress"],
                "company_url": row["company_url"],
                "company_name": row["company_name"],
                "focus": row["focus"],
                "api_key": row["api_key"],
                "result": json.loads(result_json) if result_json else None,
                "error": row["error"],
            }
        
        logger.info(f"Loaded {len(pending)} pending jobs from database")
        return pending
    except Exception as e:
        logger.error(f"Failed to load pending jobs: {e}")
        return {}


def delete_job(job_id: str) -> None:
    """Delete a job from the database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to delete job {job_id}: {e}")


# ---------------------------------------------------------------------------
# Cohort Persistence (for SaaS cohort mode)
# ---------------------------------------------------------------------------

def save_cohort(
    cohort_id: str,
    anchor_url: str,
    category_hint: Optional[str],
    status: str,
    candidates: Optional[list] = None,
    confirmed_urls: Optional[list] = None,
    job_ids: Optional[list] = None,
    matrix: Optional[Dict[str, Any]] = None,
    report_md: Optional[str] = None,
    api_key: Optional[str] = None
) -> None:
    """Save or update a cohort in the database."""
    try:
        import time
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        now = time.time()
        
        cursor.execute(
            """
            INSERT INTO cohorts (cohort_id, anchor_url, category_hint, status, created_at, updated_at,
                                candidates_json, confirmed_urls_json, job_ids_json, matrix_json, report_md, api_key)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(cohort_id) DO UPDATE SET
                status = excluded.status,
                updated_at = excluded.updated_at,
                candidates_json = COALESCE(excluded.candidates_json, cohorts.candidates_json),
                confirmed_urls_json = COALESCE(excluded.confirmed_urls_json, cohorts.confirmed_urls_json),
                job_ids_json = COALESCE(excluded.job_ids_json, cohorts.job_ids_json),
                matrix_json = COALESCE(excluded.matrix_json, cohorts.matrix_json),
                report_md = COALESCE(excluded.report_md, cohorts.report_md)
            """,
            (
                cohort_id,
                anchor_url,
                category_hint,
                status,
                now,
                now,
                json.dumps(candidates) if candidates else None,
                json.dumps(confirmed_urls) if confirmed_urls else None,
                json.dumps(job_ids) if job_ids else None,
                json.dumps(matrix) if matrix else None,
                report_md,
                api_key
            )
        )
        
        conn.commit()
        conn.close()
        logger.info(f"Cohort {cohort_id} saved to database (status={status})")
    except Exception as e:
        logger.error(f"Failed to save cohort {cohort_id}: {e}")


def get_cohort(cohort_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a cohort from the database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM cohorts WHERE cohort_id = ?", (cohort_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "cohort_id": row["cohort_id"],
                "anchor_url": row["anchor_url"],
                "category_hint": row["category_hint"],
                "status": row["status"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "candidates": json.loads(row["candidates_json"]) if row["candidates_json"] else [],
                "confirmed_urls": json.loads(row["confirmed_urls_json"]) if row["confirmed_urls_json"] else [],
                "job_ids": json.loads(row["job_ids_json"]) if row["job_ids_json"] else [],
                "matrix": json.loads(row["matrix_json"]) if row["matrix_json"] else None,
                "report_md": row["report_md"],
                "api_key": row["api_key"],
            }
        return None
    except Exception as e:
        logger.error(f"Failed to retrieve cohort {cohort_id}: {e}")
        return None


def update_cohort_status(cohort_id: str, status: str) -> None:
    """Update only the status of a cohort."""
    try:
        import time
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE cohorts SET status = ?, updated_at = ? WHERE cohort_id = ?",
            (status, time.time(), cohort_id)
        )
        
        conn.commit()
        conn.close()
        logger.info(f"Cohort {cohort_id} status updated to {status}")
    except Exception as e:
        logger.error(f"Failed to update cohort status {cohort_id}: {e}")


def markdown_to_pdf(markdown_text: str, company_name: str = "Company") -> bytes:
    """Convert Markdown report to PDF bytes."""
    if not WEASYPRINT_AVAILABLE:
        raise RuntimeError(
            "PDF export requires weasyprint and system dependencies (pango, cairo). "
            "Install with: brew install pango cairo && pip install weasyprint"
        )
    
    try:
        # Convert markdown to HTML
        html_content = markdown.markdown(
            markdown_text,
            extensions=['extra', 'codehilite', 'tables']
        )
        
        # Wrap in styled HTML document
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>OSINT Report - {company_name}</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                h1 {{
                    color: #1a1a1a;
                    border-bottom: 3px solid #0066cc;
                    padding-bottom: 10px;
                }}
                h2 {{
                    color: #0066cc;
                    margin-top: 30px;
                }}
                h3 {{
                    color: #555;
                }}
                code {{
                    background-color: #f4f4f4;
                    padding: 2px 6px;
                    border-radius: 3px;
                    font-family: 'Courier New', monospace;
                }}
                pre {{
                    background-color: #f4f4f4;
                    padding: 15px;
                    border-radius: 5px;
                    overflow-x: auto;
                }}
                ul, ol {{
                    margin-left: 20px;
                }}
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin: 20px 0;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 12px;
                    text-align: left;
                }}
                th {{
                    background-color: #0066cc;
                    color: white;
                }}
                .footer {{
                    margin-top: 50px;
                    padding-top: 20px;
                    border-top: 1px solid #ddd;
                    font-size: 0.9em;
                    color: #666;
                    text-align: center;
                }}
            </style>
        </head>
        <body>
            {html_content}
            <div class="footer">
                Generated by Micro-Analyst OSINT System | {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
            </div>
        </body>
        </html>
        """
        
        # Convert HTML to PDF
        pdf_bytes = HTML(string=full_html).write_pdf()
        return pdf_bytes
        
    except Exception as e:
        logger.error(f"Failed to generate PDF: {e}")
        raise
