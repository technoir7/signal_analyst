import json
from pathlib import Path


def _print_check_line(check_id: str, status: str, message: dict) -> None:
    print(f"CHECK {check_id} {status} {json.dumps(message, separators=(',', ':'))}")


def check_cors_middleware_present():
    """
    LM_04_CORS_MIDDLEWARE_PRESENT

    Static check that agent/micro_analyst.py configures CORSMiddleware.
    This is a proxy for 'frontend <-> API interaction will be less fragile'.
    """
    check_id = "LM_04_CORS_MIDDLEWARE_PRESENT"
    agent_path = Path("agent") / "micro_analyst.py"

    if not agent_path.exists():
        status = "SKIP"
        msg = {
            "detail": "agent/micro_analyst.py not found; skipping CORS check.",
            "hint": "Ensure FastAPI agent lives at agent/micro_analyst.py per spec.",
        }
        _print_check_line(check_id, status, msg)
        return {"id": check_id, "status": status, "detail": msg["detail"], "data": msg}

    text = agent_path.read_text(encoding="utf-8")
    has_import = "CORSMiddleware" in text
    has_add = "app.add_middleware(" in text and "CORSMiddleware" in text

    status = "PASS" if (has_import and has_add) else "FAIL"
    msg = {
        "detail": "CORSMiddleware "
        + ("appears to be configured" if status == "PASS" else "not detected"),
    }
    if status == "FAIL":
        msg["hint"] = (
            "Add permissive CORSMiddleware to the FastAPI app, e.g.:\n"
            "from fastapi.middleware.cors import CORSMiddleware\n"
            "app.add_middleware(CORSMiddleware, allow_origins=['*'], "
            "allow_credentials=True, allow_methods=['*'], allow_headers=['*'])"
        )

    _print_check_line(check_id, status, msg)
    return {"id": check_id, "status": status, "detail": msg["detail"], "data": msg}


# pytest integration ---------------------------------------------------------


def test_cors_middleware_present():
    result = check_cors_middleware_present()
    if result["status"] == "FAIL":
        raise AssertionError(result["detail"])
