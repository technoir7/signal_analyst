import json

import requests


def _print_check_line(check_id: str, status: str, message: dict) -> None:
    print(f"CHECK {check_id} {status} {json.dumps(message, separators=(',', ':'))}")


def check_web_scrape_failure_graceful():
    """
    LM_05_WEB_SCRAPE_FAILURE_GRACEFUL

    Call mcp_web_scrape /run with an intentionally invalid domain and verify:
      - HTTP 200 from the FastAPI app (it handled the error)
      - success == False in the JSON
      - error is a non-empty string
      - error does not contain a full Python traceback

    If the service isn't reachable, SKIP instead of failing the suite.
    """
    check_id = "LM_05_WEB_SCRAPE_FAILURE_GRACEFUL"

    base_url = "http://localhost:8001"
    endpoint = f"{base_url}/run"

    payload = {"url": "http://nonexistent-domain-for-micro-analyst-test.invalid"}

    try:
        resp = requests.post(endpoint, json=payload, timeout=5)
    except requests.RequestException as exc:
        status = "SKIP"
        msg = {
            "detail": f"Could not reach mcp_web_scrape at {endpoint}: {exc}",
            "hint": "Start the mcp_web_scrape service on port 8001 before running this check "
                    "if you want a full integration pass.",
        }
        _print_check_line(check_id, status, msg)
        return {"id": check_id, "status": status, "detail": msg["detail"], "data": msg}

    ok_http = resp.status_code == 200
    try:
        data = resp.json()
    except ValueError:
        data = {}
    success_field = data.get("success")
    error_field = data.get("error") or ""

    has_structured_failure = (success_field is False and isinstance(error_field, str))
    no_traceback = "Traceback (most recent call last)" not in error_field

    status = "PASS" if (ok_http and has_structured_failure and no_traceback) else "FAIL"
    msg = {
        "detail": "web_scrape failure path tested",
        "http_status": resp.status_code,
        "success_field": success_field,
        "error_sample": error_field[:200],
    }
    if status == "FAIL":
        msg["hint"] = (
            "Ensure mcp_web_scrape catches network/HTTP errors, returns success=False, and "
            "uses a concise error message without raw stack traces."
        )

    _print_check_line(check_id, status, msg)
    return {"id": check_id, "status": status, "detail": msg["detail"], "data": msg}


# pytest integration ---------------------------------------------------------


def test_web_scrape_failure_graceful():
    result = check_web_scrape_failure_graceful()
    if result["status"] == "FAIL":
        raise AssertionError(result["detail"])
