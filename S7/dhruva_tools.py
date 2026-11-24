"""Dhruva's four tools for the ADK agents. The type hints and docstrings ARE the job cards the model reads.

The scoring reads cached assessments (dhruva_core/fixtures), so the numbers are the same on every run.
Only the agent's own model calls vary.
"""
import json
import logging

from dhruva_core import config, guard, loader, score

log = logging.getLogger(__name__)
_CANNED = json.loads((config.HERE / "fixtures" / "llm_responses.json").read_text())
_OPEN = {}  # app_id -> ticket


def _err(code, message):
    return {"ok": False, "error": {"code": code, "message": message}}


def _find(app_id):
    key = app_id.strip().lower()
    return next((a for a in loader.load() if a["id"].lower() == key or a["name"].lower() == key), None)


def list_applications() -> dict:
    """List every application as id and name, e.g. A03 FactoryDesk. Use this when the user asks about all applications or a shortlist. Read only."""
    return {"ok": True, "applications": [{"id": a["id"], "name": a["name"]} for a in loader.load()]}


def get_application(app_id: str) -> dict:
    """Fetch one startup application (form fields and deck text) by id, e.g. 'A03', or by startup name, e.g. 'FactoryDesk'. Use it to read what a founder submitted. Do not use it to judge fit: use score_application for that.

    Failures: NOT_FOUND (do not retry; tell the user the id is unknown).
    """
    a = _find(app_id)
    return {"ok": True, **a} if a else _err("NOT_FOUND", f"no application with id {app_id}")


def score_application(app_id: str) -> dict:
    """Score one application, given its id (e.g. 'A03') or startup name (e.g. 'FactoryDesk'), against the Dhruva thesis. Returns fit (0 to 10), the recommendation, and the criteria that could not be established. Use it when asked whether to take a call or pass. Read only.

    Failures: NOT_FOUND (do not retry; tell the user the id is unknown).
    """
    a = _find(app_id)
    if not a:
        return _err("NOT_FOUND", f"no application with id {app_id}")
    verdicts = _CANNED[a["id"]]["criteria"]
    fit = round(score.raw_score(verdicts) / len(config.CRITERIA) * 10, 1)
    gaps = score.missing(verdicts)
    rec = score.recommend(fit, len(gaps), guard.anti_thesis(a))
    log.info("score_application %s fit=%s rec=%s", a["id"], fit, rec)
    return {"ok": True, "id": a["id"], "name": a["name"], "fit": fit, "recommendation": rec,
            "could_not_establish": gaps}


def escalate_to_analyst(app_id: str, reason: str) -> dict:
    """Hand one application, given by id or startup name, to a human analyst, with a reason. Use it when evidence is missing or the user asks for a person. Changes something: it opens a ticket. Safe to call twice for the same id: the second call returns the same ticket with already_open true.

    Failures: NOT_FOUND (do not retry).
    """
    a = _find(app_id)
    if not a:
        return _err("NOT_FOUND", f"no application with id {app_id}")
    if a["id"] in _OPEN:
        return {"ok": True, "ticket": _OPEN[a["id"]], "already_open": True}
    _OPEN[a["id"]] = f"T-{len(_OPEN) + 1:03d}"
    return {"ok": True, "ticket": _OPEN[a["id"]], "already_open": False}
