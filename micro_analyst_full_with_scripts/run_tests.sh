#!/usr/bin/env bash

set -e

CMD="$1"

if [ -z "$CMD" ]; then
  echo "Usage: $0 [tier1|tier2|tier3|all]"
  echo
  echo "  tier1  - Run Tier 1 tests (agent orchestration)"
  echo "  tier2  - Run Tier 2 tests (pure logic: SEO, tech stack, utils, LLM client)"
  echo "  tier3  - Run Tier 3 tests (MCP API tests)"
  echo "  all    - Run full test suite (same as 'pytest -v')"
  exit 1
fi

if [ "$CMD" = "tier1" ]; then
  echo "Running Tier 1 tests (agent orchestration)..."
  pytest tests/test_agent_analyze.py -v
  exit $?
fi

if [ "$CMD" = "tier2" ]; then
  echo "Running Tier 2 tests (SEO/tech/utils/LLM)..."
  pytest \
    tests/test_seo_logic.py \
    tests/test_tech_stack_logic.py \
    tests/test_text_utils.py \
    tests/test_llm_client.py -v
  exit $?
fi

if [ "$CMD" = "tier3" ]; then
  echo "Running Tier 3 tests (MCP API tests)..."
  pytest tests/mcp_* -v
  exit $?
fi

if [ "$CMD" = "all" ]; then
  echo "Running full test suite..."
  pytest -v
  exit $?
fi

echo "Unknown command: $CMD"
echo "Usage: $0 [tier1|tier2|tier3|all]"
exit 1
