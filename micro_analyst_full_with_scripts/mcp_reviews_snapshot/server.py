from fastapi import FastAPI
from loguru import logger

from .schemas import ReviewsSnapshotInput, ReviewsSnapshotOutput

app = FastAPI(title="MCP Reviews Snapshot", version="1.0.0")


@app.post("/run", response_model=ReviewsSnapshotOutput)
def run_reviews_snapshot(payload: ReviewsSnapshotInput) -> ReviewsSnapshotOutput:
    """Minimal, deterministic stub for reviews snapshot."""
    try:
        logger.info(
            "mcp_reviews_snapshot: received request for name={}, url={}",
            payload.company_name,
            payload.company_url,
        )

        summary = (
            "No external review data was fetched in this prototype. "
            "This section is reserved for future integration with Yelp / Google "
            "and other review platforms."
        )

        return ReviewsSnapshotOutput(
            success=True,
            sources=[],
            summary=summary,
            top_complaints=[],
            top_praises=[],
            error=None,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("mcp_reviews_snapshot: unhandled error")
        return ReviewsSnapshotOutput(
            success=False,
            sources=[],
            summary=None,
            top_complaints=[],
            top_praises=[],
            error=f"Unexpected error during reviews snapshot: {exc}",
        )
