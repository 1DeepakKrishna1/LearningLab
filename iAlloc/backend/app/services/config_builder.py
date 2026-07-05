"""Builds and validates a System.config JSON from the stage catalog + domain template."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "config_templates"


@lru_cache
def load_catalog() -> dict:
    return json.loads((_TEMPLATE_DIR / "catalog.json").read_text(encoding="utf-8"))


@lru_cache
def load_domains() -> dict:
    return json.loads((_TEMPLATE_DIR / "domains.json").read_text(encoding="utf-8"))


def list_domains() -> list[dict]:
    domains = load_domains()
    return [
        {"domain": key, "name_suggestion": tpl.get("name_suggestion", key)}
        for key, tpl in domains.items()
    ]


def _catalog_by_type() -> dict[str, dict]:
    return {s["type"]: s for s in load_catalog()["stage_catalog"]}


def build_config(domain: str) -> dict:
    """Materialize a full System.config from a domain template."""
    domains = load_domains()
    if domain not in domains:
        domain = "generic"
    tpl = domains[domain]
    cat = _catalog_by_type()

    stages: list[dict] = []
    seen: dict[str, int] = {}
    for order, st in enumerate(tpl["stages"], start=1):
        stype = st["type"]
        meta = cat.get(stype, {})
        # Unique key per stage (a domain may use a type twice, e.g. two evaluations).
        seen[stype] = seen.get(stype, 0) + 1
        key = stype if seen[stype] == 1 else f"{stype}_{seen[stype]}"
        stages.append(
            {
                "key": key,
                "type": stype,
                "name": st.get("name_override") or meta.get("name", stype.title()),
                "order": order,
                "enabled": st.get("enabled", True),
                "roles": st.get("roles", meta.get("default_roles", [])),
                "ai": {
                    "enabled": st.get("ai_enabled", False),
                    "task": st.get("ai_task")
                    or (meta.get("ai_tasks") or [""])[0],
                    "model": st.get("ai_model"),
                    "instructions": st.get("ai_instructions", ""),
                },
                "available_ai_tasks": meta.get("ai_tasks", []),
            }
        )

    return {
        "domain": domain,
        "stages": stages,
        "form_fields": tpl.get("form_fields", []),
        "ranking": tpl.get("ranking", {"strategy": "score_desc", "tie_breakers": []}),
        "allocation": tpl.get("allocation", {"strategy": "merit_preference", "rounds": 1}),
    }


def default_options(domain: str) -> list[dict]:
    return load_domains().get(domain, {}).get("options", [])


def stage_by_key(config: dict, stage_key: str) -> dict | None:
    for s in config.get("stages", []):
        if s["key"] == stage_key:
            return s
    return None


def ordered_enabled_stages(config: dict) -> list[dict]:
    return sorted(
        [s for s in config.get("stages", []) if s.get("enabled", True)],
        key=lambda s: s.get("order", 0),
    )
