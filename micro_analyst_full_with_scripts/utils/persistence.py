"""
Report persistence and export utilities.

Provides SQLite-based storage and PDF export for OSINT reports.
"""

import json
import os
import sqlite3
from datetime import datetime
from typing import Dict, Any, Optional

import markdown
from loguru import logger
from weasyprint import HTML


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


def markdown_to_pdf(markdown_text: str, company_name: str = "Company") -> bytes:
    """Convert Markdown report to PDF bytes."""
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
