"""Dashboard templates (templates/*.json) and dashboard provisioning from files.

A template binds each of its roles to a source: `{{role}}` becomes the source slug and
`{{role.name}}` the column the source maps to OTel role `name`. Tiles of unbound roles are dropped.
Provisioning upserts by slug, as HyperDX packages/api/src/tasks/provisionDashboards/index.ts does by name.
"""

import copy
import json
import re
from pathlib import Path
from typing import Dict, List

from django.db import transaction

from telescope.models import Dashboard, Source
from telescope.rbac import permissions
from telescope.rbac.manager import RBACManager
from telescope.serializers.dashboard import (
    DASHBOARD_DATA_VERSION,
    NewDashboardSerializer,
    dashboard_raw_queries,
    dashboard_sources,
)

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
PLACEHOLDER_RE = re.compile(r"\{\{([a-z_]+)(?:\.([a-z_]+))?\}\}")
SLUG_RE = re.compile(r"^[-a-zA-Z0-9_]{1,262}$")
# duration_precision -> number format unit and the divisor that turns a duration into ms.
DURATION_UNITS = {9: "duration_ns", 6: "duration_us", 3: "duration_ms", 0: "duration_s"}
MS_DIVISORS = {9: "1000000", 6: "1000", 3: "1", 0: "0.001"}

rbac_manager = RBACManager()


class TemplateError(ValueError):
    pass


def load_templates() -> Dict[str, dict]:
    templates = {}
    for path in sorted(TEMPLATES_DIR.glob("*.json")):
        template = json.loads(path.read_text())
        templates[template["slug"]] = template
    return templates


def get_template(slug: str) -> dict:
    template = load_templates().get(slug)
    if template is None:
        raise TemplateError(f"template {slug} not found")
    return template


def placeholder_roles(value) -> set:
    return {m.group(1) for m in PLACEHOLDER_RE.finditer(json.dumps(value))}


def source_matches(source: Source, spec: dict) -> bool:
    data = source.data or {}
    if "signal" in spec:
        return (data.get("otel") or {}).get("signal") == spec["signal"]
    database, table = spec["table"].split(".", 1)
    return (
        source.kind == "clickhouse"
        and data.get("database") == database
        and data.get("table") == table
    )


def role_values(source: Source) -> Dict[str, str]:
    roles = ((source.data or {}).get("otel") or {}).get("roles") or {}
    values = {k: v for k, v in roles.items() if isinstance(v, str) and v}
    precision = roles.get("duration_precision", 9)
    values["duration_unit"] = DURATION_UNITS.get(precision, "duration_ns")
    values["ms_divisor"] = MS_DIVISORS.get(precision, "1000000")
    return values


def instantiate(template: dict, sources: Dict[str, Source]) -> dict:
    """Dashboard data of `template` with each role bound to the source in `sources`."""
    roles = template["roles"]
    unknown = sorted(set(sources) - set(roles))
    if unknown:
        raise TemplateError(f"unknown role {unknown[0]}")
    for name, spec in roles.items():
        if name not in sources:
            if not spec.get("optional"):
                raise TemplateError(f"pick a source for {spec['label']}")
        elif not source_matches(sources[name], spec):
            raise TemplateError(
                f"source {sources[name].slug} does not fit {spec['label']}"
            )
    values = {name: role_values(source) for name, source in sources.items()}

    def resolve(match):
        role, key = match.group(1), match.group(2)
        if key is None:
            return sources[role].slug
        if key not in values[role]:
            raise TemplateError(f"source {sources[role].slug} has no {key} column")
        return values[role][key]

    def fill(value):
        if isinstance(value, str):
            return PLACEHOLDER_RE.sub(resolve, value)
        if isinstance(value, list):
            return [fill(v) for v in value]
        if isinstance(value, dict):
            return {k: fill(v) for k, v in value.items()}
        return value

    bound = set(sources)
    dashboard = copy.deepcopy(template["dashboard"])
    tiles = [t for t in dashboard["tiles"] if placeholder_roles(t) <= bound]
    if not any(t["chart"]["display"] != "text" for t in tiles):
        raise TemplateError("pick a source for at least one role")
    used = {t.get("section") for t in tiles}
    dashboard["tiles"] = tiles
    dashboard["sections"] = [
        s for s in dashboard.get("sections", []) if s["id"] in used
    ]
    dashboard["variables"] = [
        v for v in dashboard.get("variables", []) if placeholder_roles(v) <= bound
    ]
    return {"version": DASHBOARD_DATA_VERSION, **fill(dashboard)}


def role_candidates(user, template: dict) -> List[dict]:
    """Roles of `template`, each with the sources `user` can use for it and a default pick."""
    usable = sorted(
        rbac_manager.get_sources(
            user, required_permissions=[permissions.Source.USE.value]
        ),
        key=lambda s: s.slug,
    )
    result, picked = [], []
    for name, spec in template["roles"].items():
        matching = [s for s in usable if source_matches(s, spec)]
        # Prefer the source an earlier pick links to, e.g. the logs of the chosen traces.
        linked = [
            ((p.data.get("otel") or {}).get("links") or {}).get(spec.get("signal"))
            for p in picked
        ]
        default = next((s for s in matching if s.slug in linked), None) or (
            matching[0] if matching else None
        )
        if default:
            picked.append(default)
        result.append(
            {
                "name": name,
                **spec,
                "optional": bool(spec.get("optional")),
                "candidates": [{"slug": s.slug, "name": s.name} for s in matching],
                "default": default.slug if default else None,
            }
        )
    return result


def template_summary(template: dict) -> dict:
    return {
        "slug": template["slug"],
        "name": template["name"],
        "description": template.get("description", ""),
        "tags": template.get("tags", []),
        "tiles": len(template["dashboard"]["tiles"]),
    }


def provision_data(item: dict, user) -> dict:
    """The dashboard data of one provisioning file: `data`, or `template` plus `sources`."""
    if "template" not in item:
        return item.get("data")
    sources = {}
    for role, slug in (item.get("sources") or {}).items():
        try:
            sources[role] = rbac_manager.get_source(
                user, slug, [permissions.Source.USE.value]
            )
        except Source.DoesNotExist:
            raise TemplateError(f"source {slug} not found")
    return instantiate(get_template(item["template"]), sources)


def provision_file(path: Path, user) -> tuple:
    """Upserts the dashboard in `path` by slug; returns (slug, "created" | "updated" | "unchanged")."""
    item = json.loads(path.read_text())
    if not isinstance(item, dict):
        raise TemplateError("file is not a JSON object")
    slug = item.get("slug") or path.stem
    if not SLUG_RE.match(slug):
        raise TemplateError(f"invalid slug {slug}")
    template = get_template(item["template"]) if "template" in item else {}
    payload = {
        "name": item.get("name") or template.get("name"),
        "description": item.get("description", template.get("description", "")),
        "shared": item.get("shared", True),
        "data": provision_data(item, user),
    }
    with transaction.atomic():
        existing = Dashboard.objects.select_for_update().filter(slug=slug).first()
        serializer = NewDashboardSerializer(
            data=payload,
            context={
                "user": user,
                "old_sources": dashboard_sources(existing.data) if existing else set(),
                "old_raw_queries": (
                    dashboard_raw_queries(existing.data) if existing else set()
                ),
            },
        )
        if not serializer.is_valid():
            raise TemplateError(json.dumps(serializer.errors))
        fields = dict(serializer.validated_data)
        if existing is None:
            Dashboard.objects.create(slug=slug, owner=user, updated_by=user, **fields)
            return slug, "created"
        if all(getattr(existing, k) == v for k, v in fields.items()):
            return slug, "unchanged"
        for key, value in fields.items():
            setattr(existing, key, value)
        existing.version += 1
        existing.updated_by = user
        existing.save()
        return slug, "updated"


def provision(paths: List[str], user) -> List[tuple]:
    """(path, slug or None, action or error text) for every .json file in `paths` (files or dirs)."""
    files = []
    for value in paths:
        path = Path(value)
        files += sorted(path.glob("*.json")) if path.is_dir() else [path]
    results = []
    for path in files:
        try:
            slug, action = provision_file(path, user)
            results.append((str(path), slug, action))
        except (OSError, ValueError, KeyError, TypeError) as err:
            results.append((str(path), None, f"error: {err}"))
    return results
