"""VIZHI Intelligence Agent.

Generates Section-6-format intelligence briefs grounded in the predictive engine's
real output (risk scores, SHAP indicators, complaint IDs, transition flows). Works
fully offline via templates; if ANTHROPIC_API_KEY is set, free-text queries are
enriched by the Claude API using the same grounded context (never fabricated).

Every response is traceable to complaint IDs / data sources per the agent rules.
"""
from __future__ import annotations

from ..config import settings
from ..ml.pipeline import Pipeline

SYSTEM_PROMPT = """You are VIZHI Intelligence Agent, an AI assistant deployed by I4C
(Indian Cyber Crime Coordination Centre) under the Ministry of Home Affairs. Assist law
enforcement investigators analysing cybercrime complaints and predicted cash-withdrawal
hotspots. Never speculate beyond the data provided; say "data insufficient" when needed.
All outputs must be traceable to complaint IDs or data sources. Maintain a neutral,
professional law-enforcement tone."""

THREAT_BY_RISK = {"HIGH": "HIGH", "MEDIUM": "MEDIUM", "LOW": "LOW"}


def _threat_level(p_high: float, risk_level: str) -> str:
    """Map model confidence to an operational threat tier (incl. CRITICAL)."""
    if p_high >= 0.75:
        return "CRITICAL"
    if p_high >= 0.5 or risk_level == "HIGH":
        return "HIGH"
    if risk_level == "MEDIUM":
        return "MEDIUM"
    return "LOW"


def build_brief(pipeline: Pipeline, district: str) -> dict:
    """Produce a structured intelligence brief for a district, grounded in data."""
    detail = pipeline.explain_district(district)
    if detail is None:
        return {"error": f"data insufficient — no analytics available for '{district}'"}

    threat = _threat_level(detail["p_high"], detail["risk_level"])
    indicators = [
        f"{i['label']} {'elevated' if i['direction'] == 'raises' else 'moderate'} "
        f"(value {i['value']}, impact {i['impact']:+.2f})"
        for i in detail["key_indicators"]
    ]
    cashout = detail["likely_cashout_districts"]
    cashout_lines = [
        f"{c['withdrawal_district']} (p={c['probability']}, ~{c['median_lag_hrs']}h lag, "
        f"{c['count']} historical cash-outs)"
        for c in cashout
    ]
    lag = cashout[0]["median_lag_hrs"] if cashout else pipeline.transition.get("global_lag_hrs", 24)

    actions = []
    if threat in ("CRITICAL", "HIGH"):
        actions.append("Deploy surveillance to ATMs near transport hubs in predicted cash-out zones.")
        actions.append("Issue branch alerts to dominant banks; enable expedited fund-freeze.")
        actions.append("Pre-position a field team for the next {}h window.".format(int(lag)))
    else:
        actions.append("Maintain routine monitoring; re-evaluate on next weekly refresh.")

    time_window = f"next {int(lag)}-{int(lag) + 24}h"
    brief_text = _format_brief(
        threat, district, detail["state"], detail["p_high"],
        indicators, cashout_lines, actions, time_window
    )
    return {
        "threat_level": threat,
        "predicted_risk_zone": f"{district}, {detail['state']}",
        "time_window": time_window,
        "key_indicators": indicators,
        "likely_cashout_districts": cashout,
        "recommended_action": actions,
        "confidence_score": f"{int(round(detail['confidence'] * 100))}%",
        "risk_level": detail["risk_level"],
        "sources": {"district": district, "model_metrics": pipeline.metrics},
        "brief_text": brief_text,
    }


def _format_brief(
    threat, district, state, p_high, indicators, cashout_lines, actions, time_window
) -> str:
    ind = "\n".join(f"  - {i}" for i in indicators) or "  - data insufficient"
    co = "\n".join(f"  - {c}" for c in cashout_lines) or "  - no historical cash-out pattern"
    act = "\n".join(f"  - {a}" for a in actions)
    return (
        f"Threat Level: {threat}\n"
        f"Predicted Risk Zone: {district}, {state}\n"
        f"Time Window: {time_window}\n"
        f"Key Indicators:\n{ind}\n"
        f"Likely Cash-out Districts:\n{co}\n"
        f"Recommended Action:\n{act}\n"
        f"Confidence Score: {int(round(p_high * 100))}%"
    )


def _resolve_district(pipeline: Pipeline, query: str, district: str | None) -> str | None:
    if district:
        return district
    known = {p["district"].lower(): p["district"] for p in pipeline.get_predictions()["predictions"]}
    for word_district in known:
        if word_district in query.lower():
            return known[word_district]
    return None


def _grounded_context(
    pipeline: Pipeline,
    district: str | None,
    allowed_state: str | None = None,
    allowed_bank: str | None = None,
) -> str:
    top = pipeline.get_predictions(top_k=5)["predictions"]
    if allowed_state:
        top = [p for p in top if p["state"] == allowed_state]
    if allowed_bank:
        top = [p for p in top if allowed_bank in p.get("banks_involved", [])]
    lines = ["Top predicted high-risk districts (next window):"]
    for p in top:
        lines.append(
            f"- {p['district']}, {p['state']}: {p['risk_level']} (P(HIGH)={p['p_high']}, "
            f"conf={p['confidence']}); likely cash-out -> "
            + ", ".join(c["withdrawal_district"] for c in p["likely_cashout_districts"])
        )
    if district:
        d = pipeline.explain_district(district)
        if d:
            lines.append(f"\nFocus district {district}: risk={d['risk_level']}, P(HIGH)={d['p_high']}.")
            lines.append("Key indicators: " + "; ".join(i["label"] for i in d["key_indicators"]))
    return "\n".join(lines)


def _llm_answer(query: str, context: str) -> str | None:
    """Optional Claude API enrichment. Returns None if unavailable."""
    if not settings.anthropic_api_key:
        return None
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        msg = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=700,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": f"Grounded data context (do not go beyond it):\n{context}\n\n"
                           f"Investigator query: {query}",
            }],
        )
        return "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")
    except Exception:
        return None


def answer_query(
    pipeline: Pipeline,
    query: str,
    district: str | None = None,
    complaint_id: str | None = None,
    allowed_state: str | None = None,
    allowed_bank: str | None = None,
) -> dict:
    """Route an investigator NL query to a grounded, audit-traceable response."""
    resolved = _resolve_district(pipeline, query, district)
    context = _grounded_context(pipeline, resolved, allowed_state, allowed_bank)

    wants_brief = any(w in query.lower() for w in ("brief", "report", "intelligence", "summary"))
    brief = build_brief(pipeline, resolved) if (wants_brief and resolved) else None

    llm = _llm_answer(query, context)
    if llm:
        answer, mode = llm, "llm"
    elif brief and "error" not in brief:
        answer, mode = brief["brief_text"], "template-brief"
    else:
        answer = (
            "Based on the current predictive output:\n\n" + context +
            ("\n\nSpecify a district (e.g. 'generate a brief for Coimbatore') for a full "
             "intelligence brief." if not resolved else "")
        )
        mode = "template"

    return {
        "answer": answer,
        "mode": mode,
        "focus_district": resolved,
        "complaint_id": complaint_id,
        "brief": brief,
        "sources": {"context": context},
    }
