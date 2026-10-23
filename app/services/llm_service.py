"""
LLM service: generates QA test cases from document node text.

Design decisions:
  - Provider: Groq (free tier) with llama-3.3-70b-versatile.
    Fallback: if GROQ_API_KEY is absent, a structured mock response is returned
    so the API stays testable without credentials.
  - Structured output: the LLM is prompted to return JSON matching the
    TestCaseList schema.  We validate with Pydantic.  If the response is
    malformed we attempt two things in order:
      1. Regex-extract any JSON array from the raw text.
      2. If that also fails, we return a PARTIAL_ERROR result with the raw
         text and a descriptive error — never silently swallow the failure.
  - Prompt design: the prompt explicitly requires numbered test cases with
    fields: id, title, preconditions, steps, expected_result, requirement_ref.
    The requirement_ref field anchors each test case to the source node heading
    — this is the traceability link.
  - Retry strategy: one automatic retry on HTTP 429 / 503 (rate limit / server
    error) with 2-second backoff.  We do NOT retry on schema validation failures
    because that usually signals a prompt issue, not a transient error.

Limits of approach:
  - A one-word wording change (e.g., "300 mmHg" → "320 mmHg") triggers the
    same staleness flag as a structural rewrite.  We surface both; the user
    must decide if the change is significant for their test case.
  - The LLM may produce test cases that don't map to specific requirements when
    the input text is very short.  We include the source node heading in each
    test case's requirement_ref to mitigate this.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Optional

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

# ─── Output schema ────────────────────────────────────────────────────────────

class TestCase(BaseModel):
    id:               str
    title:            str
    preconditions:    str
    steps:            list[str]
    expected_result:  str
    requirement_ref:  str   # heading of the source node


class TestCaseList(BaseModel):
    test_cases: list[TestCase]


class GenerationResult(BaseModel):
    status:          str            # "ok" | "partial_error" | "mock"
    test_cases:      list[TestCase]
    raw_llm_output:  Optional[str] = None
    error_detail:    Optional[str] = None


# ─── Prompt ───────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are a QA engineer specialising in regulated medical devices (ISO 13485, IEC 62304).
Your task is to generate concrete, executable QA test case ideas from a section of a
medical device user manual.

Rules:
- Generate between 3 and 5 test cases.
- Each test case must be traceable to a specific part of the supplied text.
- Steps must be concrete enough that a technician with no prior context could execute them.
- Do NOT invent requirements not present in the supplied text.
- Output ONLY valid JSON — no preamble, no markdown fences, no trailing text.

JSON schema (return exactly this structure):
{
  "test_cases": [
    {
      "id": "TC-001",
      "title": "Short descriptive title",
      "preconditions": "What must be true before the test",
      "steps": ["Step 1", "Step 2", "Step 3"],
      "expected_result": "Observable, measurable pass criterion",
      "requirement_ref": "Exact heading from the source document"
    }
  ]
}
"""

def _build_user_prompt(section_texts: list[tuple[str, str]]) -> str:
    """
    section_texts: list of (heading, body_text) tuples.
    """
    parts = []
    for heading, body in section_texts:
        parts.append(f"## {heading}\n\n{body}")
    combined = "\n\n---\n\n".join(parts)
    return (
        "Generate QA test cases for the following document section(s):\n\n"
        + combined
    )


# ─── JSON extraction helpers ──────────────────────────────────────────────────

def _try_parse_json(text: str) -> Optional[dict]:
    """Try to parse raw text as JSON, stripping markdown fences if present."""
    # Strip ```json ... ``` wrappers
    clean = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    clean = re.sub(r"```\s*$", "", clean.strip(), flags=re.MULTILINE)
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        pass

    # Try extracting first {...} blob
    m = re.search(r"\{.*\}", clean, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass
    return None


# ─── Mock fallback ────────────────────────────────────────────────────────────

def _mock_result(section_texts: list[tuple[str, str]]) -> GenerationResult:
    heading = section_texts[0][0] if section_texts else "Unknown Section"
    return GenerationResult(
        status="mock",
        test_cases=[
            TestCase(
                id="TC-001",
                title="[MOCK] Verify normal operation",
                preconditions="Device is powered on with fresh batteries.",
                steps=["Perform action 1", "Observe result"],
                expected_result="Device behaves as described in the manual.",
                requirement_ref=heading,
            ),
            TestCase(
                id="TC-002",
                title="[MOCK] Verify error condition",
                preconditions="Device is in error state.",
                steps=["Trigger error condition", "Observe display"],
                expected_result="Correct error code is displayed.",
                requirement_ref=heading,
            ),
            TestCase(
                id="TC-003",
                title="[MOCK] Verify recovery",
                preconditions="Error condition has been triggered.",
                steps=["Follow recovery steps", "Attempt normal operation"],
                expected_result="Device recovers and resumes normal operation.",
                requirement_ref=heading,
            ),
        ],
        raw_llm_output=None,
        error_detail="GROQ_API_KEY not set; returning mock output.",
    )


# ─── Main generation function ─────────────────────────────────────────────────

def generate_test_cases(
    section_texts: list[tuple[str, str]],
    max_retries: int = 2,
) -> GenerationResult:
    """
    Call the LLM and return structured test cases.

    Args:
        section_texts: list of (heading, body_text) tuples from pinned nodes.
        max_retries:   number of retry attempts on transient LLM errors.

    Returns:
        GenerationResult with status "ok", "partial_error", or "mock".
    """
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        logger.warning("GROQ_API_KEY not set; returning mock output.")
        return _mock_result(section_texts)

    try:
        from groq import Groq, RateLimitError, APIStatusError
    except ImportError:
        logger.error("groq package not installed.")
        return _mock_result(section_texts)

    client = Groq(api_key=api_key)
    user_prompt = _build_user_prompt(section_texts)
    last_error: Optional[str] = None

    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user",   "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=2048,
            )
            raw = response.choices[0].message.content or ""
            logger.debug("LLM raw response (attempt %d): %s", attempt, raw[:200])

            parsed = _try_parse_json(raw)
            if parsed is None:
                last_error = f"Could not parse JSON from LLM response (attempt {attempt})."
                logger.warning(last_error)
                continue   # retry

            try:
                tc_list = TestCaseList.model_validate(parsed)
                return GenerationResult(
                    status="ok",
                    test_cases=tc_list.test_cases,
                    raw_llm_output=raw,
                )
            except ValidationError as ve:
                last_error = f"Schema validation failed: {ve}"
                logger.warning(last_error)
                # Do NOT retry on schema failures — return partial_error immediately
                return GenerationResult(
                    status="partial_error",
                    test_cases=[],
                    raw_llm_output=raw,
                    error_detail=last_error,
                )

        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "503" in err_str or "rate" in err_str.lower():
                last_error = f"Transient LLM error (attempt {attempt}): {err_str}"
                logger.warning(last_error)
                time.sleep(2 ** attempt)   # exponential backoff
                continue
            else:
                last_error = f"LLM call failed: {err_str}"
                logger.error(last_error)
                break

    # All retries exhausted
    return GenerationResult(
        status="partial_error",
        test_cases=[],
        raw_llm_output=None,
        error_detail=last_error or "Unknown LLM error after retries.",
    )
