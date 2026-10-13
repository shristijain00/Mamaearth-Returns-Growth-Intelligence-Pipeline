import re
import time
import calendar
import json
import os
import sys
from pathlib import Path

# The Google imports live inside the LLM function, so a machine without
# google-genai installed can still run the offline fallback.

BASE_DIR = Path(__file__).resolve().parent.parent
FINDINGS_PATH = BASE_DIR / "narrator" / "findings.json"
SAMPLE_PATH = BASE_DIR / "narrator" / "sample_output.txt"

# Check Google's current docs / client.models.list() for valid model names; they change over time.
MODEL_NAME = "gemini-3.5-flash-lite"

SYSTEM_PROMPT = (
    "You are a senior data analyst writing for Mamaearth's regional ops and finance heads. "
    "Write a short narrative with exactly three labeled sections, in this order: "
    "'Situation' (the neutral facts and context), "
    "'Complication' (the problem or risk the data reveals), and "
    "'Resolution' (what ops and finance should do about it). "
    "Strict number rules: every number you write must come from the findings supplied "
    "by the user and must appear with exactly the same value (no rounding, no re-expressing, "
    "no unit changes). Do not compute new figures such as percentage changes, ratios, or "
    "multiples unless that exact figure is in the findings. If something is not in the "
    "findings, do not state it. "
    "Style rules: write in natural, flowing business prose. Never repeat field names or "
    "labels from the findings. Put revenue amounts in rupees, for example 'INR 97358.3', "
    "and write return rates with a percent sign, for example '44.4%'. Adding a unit or "
    "sign is fine, but the digits must stay identical. "
    "Name the true peak month in words (for example 'March'), not only as a YYYY-MM code. "
    "Recommendations must follow directly from the findings. Do not propose specific "
    "tools, processes, or systems that the findings do not support, and do not make "
    "claims about profitability or fulfillment impact beyond what the numbers show."
    "Never state differences, totals, ratios or any other figure that is not listed in the "
    "findings. Never comment on what you can or cannot state and never describe your own "
    "reasoning; if a figure is absent, leave it out silently."
)


def month_name_of(period: str) -> str:
    """'2026-03' -> 'March'"""
    return calendar.month_name[int(period.split("-")[1])]


def build_user_prompt(findings: dict) -> str:
    rr = findings["return_rate_by_payment"]
    seg = findings["highest_risk_segment"]
    peak = findings["true_peak_month"]
    infl = findings["outlier_inflated_month"]

    return (
        "Write the Situation / Complication / Resolution narrative using ONLY these findings.\n\n"
        f"Cleaned total revenue (INR): {findings['cleaned_total_revenue_inr']}\n"
        f"Raw total revenue (INR): {findings['raw_total_revenue_inr']}\n"
        f"Revenue removed by deduplication (INR): {findings['duplicate_reconciliation_delta_inr']}\n"
        f"Return rate by payment method (%): COD {rr['COD']}, CARD {rr['CARD']}, UPI {rr['UPI']}\n"
        f"Highest-risk segment: {seg['payment_method']} in Tier-{seg['city_tier']} cities "
        f"at {seg['return_rate_pct']}% return rate\n"
        f"True peak month: {month_name_of(peak['month'])} ({peak['month']}) "
        f"at {peak['revenue_inr']} INR\n"
        f"Outlier-inflated month: {infl['month']} appeared as {infl['apparent_revenue_inr']} INR "
        f"but is {infl['corrected_revenue_inr']} INR after excluding bulk-order outliers\n\n"
        "Full findings as JSON, for reference:\n"
        f"{json.dumps(findings, indent=2)}"
    )


def generate_scr_narrative_llm(findings: dict) -> dict:
    """Gemini path. Always returns a dict; never raises."""
    try:
        # Imported here so a missing library is caught as an API-path failure.
        from google import genai
        from google.genai import types

        client = genai.Client()  # reads GEMINI_API_KEY from the environment
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=build_user_prompt(findings),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                # temperature 0.0: this is a factual business report where every number
                # must match the findings, so we want deterministic output, not creativity.
                temperature=0.0,
                max_output_tokens=4096,
                http_options=types.HttpOptions(timeout=90000),  # milliseconds = 30 s
            ),
        )

        # These checks run only after a successful call, so `response` always exists here.
        finish = response.candidates[0].finish_reason if response.candidates else None
        if finish is not None and "MAX_TOKENS" in str(finish):
            raise ValueError("Narrative was cut off at max_output_tokens; raise the limit.")
        if not response.text:
            raise ValueError("Model returned no text (possibly truncated or blocked).")

        return {
            "status": "success",
            "narrative": response.text,
            "tokens": response.usage_metadata.total_token_count,
        }
    except Exception as err:
        # Nothing in this block may touch `response`; it may not exist.
        return {"status": "error", "narrative": None, "message": str(err)}


def generate_scr_narrative_offline(findings: dict) -> dict:
    """Deterministic template path: no network, no API key, same return shape."""
    rr = findings["return_rate_by_payment"]
    seg = findings["highest_risk_segment"]
    peak = findings["true_peak_month"]
    infl = findings["outlier_inflated_month"]
    peak_label = f"{month_name_of(peak['month'])} ({peak['month']})"

    narrative = (
        "Situation\n"
        f"Raw total revenue was INR {findings['raw_total_revenue_inr']}. Deduplication removed "
        f"INR {findings['duplicate_reconciliation_delta_inr']}, leaving a cleaned total of "
        f"INR {findings['cleaned_total_revenue_inr']}. The true peak month is {peak_label} "
        f"at INR {peak['revenue_inr']}.\n\n"
        "Complication\n"
        f"{infl['month']} appeared to be the strongest month at INR {infl['apparent_revenue_inr']}, "
        f"but excluding bulk-order outliers it is INR {infl['corrected_revenue_inr']}. "
        f"Return rates differ by payment method: COD {rr['COD']}%, UPI {rr['UPI']}%, "
        f"CARD {rr['CARD']}%. The highest-risk segment is {seg['payment_method']} in "
        f"Tier-{seg['city_tier']} cities at {seg['return_rate_pct']}%.\n\n"
        "Resolution\n"
        f"Finance should plan against the cleaned total of INR {findings['cleaned_total_revenue_inr']} "
        f"and treat {peak_label} at INR {peak['revenue_inr']} as the true peak, not "    
        f"{infl['month']}. Operations should focus return-reduction effort on "
        f"{seg['payment_method']} orders in Tier-{seg['city_tier']} cities, where the return "
        f"rate reaches {seg['return_rate_pct']}%."
    )
    return {"status": "success", "narrative": narrative, "tokens": 0}


def generate_scr_narrative(findings: dict) -> dict:
    """Entry point: try Gemini if a key exists; otherwise (or on error) use the offline template."""
    has_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if has_key:
        result = generate_scr_narrative_llm(findings)
        if result["status"] == "success":
            return result
        print(f"[fallback] API path failed: {result['message']}")
    else:
        print("[fallback] No API key configured.")
    return generate_scr_narrative_offline(findings)

def _numbers_in(text: str) -> set:
    return {float(n) for n in re.findall(r"\d+(?:\.\d+)?", text.replace(",", ""))}


def check_no_invented_numbers(narrative: str, findings: dict, verbose: bool = True) -> bool:
    """Every number in the narrative must appear somewhere in findings."""
    extra = sorted(_numbers_in(narrative) - _numbers_in(json.dumps(findings)))
    if verbose:
        print(f"[{'PASS' if not extra else 'FAIL'}] no invented numbers"
              + (f": unexpected {extra}" if extra else ""))
    return not extra


def check_narrative(narrative: str, findings: dict, verbose: bool = True) -> bool:
    """PASS/FAIL per required figure, plus the no-invented-numbers check."""
    text = narrative.replace(",", "")
    peak = findings["true_peak_month"]
    checks = [
        ("cleaned total revenue", str(findings["cleaned_total_revenue_inr"])),
        ("COD return rate", str(findings["return_rate_by_payment"]["COD"])),
        ("highest-risk segment rate", str(findings["highest_risk_segment"]["return_rate_pct"])),
        ("duplicate delta", str(findings["duplicate_reconciliation_delta_inr"])),
        ("peak month name", month_name_of(peak["month"])),
        ("peak month revenue", str(peak["revenue_inr"])),
    ]
    all_ok = True
    for label, needle in checks:
        ok = needle in text
        if verbose:
            print(f"[{'PASS' if ok else 'FAIL'}] {label}: {needle}")
        all_ok = all_ok and ok
    return check_no_invented_numbers(narrative, findings, verbose) and all_ok


def save_llm_sample(findings: dict, attempts: int = 3, wait_seconds: int = 20) -> None:
    """Save a real Gemini narrative to sample_output.txt (never the offline text)."""
    for attempt in range(1, attempts + 1):
        result = generate_scr_narrative_llm(findings)
        if result["status"] == "success":
            SAMPLE_PATH.write_text(result["narrative"], encoding="utf-8")
            print(f"Saved {SAMPLE_PATH.relative_to(BASE_DIR)}")
            return
        print(f"Attempt {attempt}/{attempts} failed: {result['message']}")
        if attempt < attempts:
            time.sleep(wait_seconds)
    print("All attempts failed; sample not saved.")


if __name__ == "__main__":
    with open(FINDINGS_PATH) as f:
        findings = json.load(f)

    if "--save-sample" in sys.argv:
        save_llm_sample(findings)

    result = generate_scr_narrative(findings)
    print(result["narrative"])
    print(f"\n[tokens used: {result['tokens']}]")

    print("\n--- Checker: offline path (hard pass/fail) ---")
    offline = generate_scr_narrative_offline(findings)
    assert check_narrative(offline["narrative"], findings), "Offline narrative is missing a figure"

    if SAMPLE_PATH.exists():
        print("\n--- Checker: saved Gemini sample ---")
        check_narrative(SAMPLE_PATH.read_text(encoding="utf-8"), findings)