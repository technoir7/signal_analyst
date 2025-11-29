from fastapi import FastAPI
from loguru import logger

from .schemas import SocialSnapshotInput, SocialSnapshotOutput

app = FastAPI(title="MCP Social Snapshot", version="1.0.0")


@app.post("/run", response_model=SocialSnapshotOutput)
def run_social_snapshot(payload: SocialSnapshotInput) -> SocialSnapshotOutput:
    """Minimal, deterministic stub for social snapshot."""
    try:
        logger.info(
            "mcp_social_snapshot: received request for name={}, url={}",
            payload.company_name,
            payload.company_url,
        )

        return SocialSnapshotOutput(
            success=True,
            instagram=None,
            youtube=None,
            twitter=None,
            error="Social discovery not implemented in this prototype.",
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("mcp_social_snapshot: unhandled error")
        return SocialSnapshotOutput(
            success=False,
            instagram=None,
            youtube=None,
            twitter=None,
            error=f"Unexpected error during social snapshot: {exc}",
        )
