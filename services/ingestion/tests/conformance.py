"""Reads every response against the hand-written YAML. PROVIDED.

check_response(resp, method, template) fails when:
- the status code is not documented for that operation, or
- the JSON body does not match the documented schema.
template is the YAML path, e.g. "/api/v1/screenings/{screening_id}", not the real URL.
"""
from pathlib import Path

import jsonschema
import yaml

SPEC = yaml.safe_load(
    Path(__file__).parents[1].joinpath("specs/ingestion-openapi-v1.0.yaml")
    .read_text(encoding="utf-8"))
METHODS = ("get", "post", "put", "patch", "delete")


def _resolve(node: dict) -> dict:
    while "$ref" in node:                       # follow '#/components/...' pointers
        target = SPEC
        for part in node["$ref"][2:].split("/"):
            target = target[part]
        node = target
    return node


def spec_operations() -> dict:
    return {(m.upper(), path): op["operationId"]
            for path, item in SPEC["paths"].items()
            for m, op in item.items() if m in METHODS}


def app_operations(app) -> dict:
    return {(m.upper(), path): op.get("operationId")
            for path, item in app.openapi()["paths"].items()
            for m, op in item.items()}


def check_response(resp, method: str, template: str) -> None:
    op = SPEC["paths"][template][method.lower()]
    code = str(resp.status_code)
    assert code in op["responses"], (
        f"{method} {template} answered {code}, which the YAML does not document "
        f"(documented: {', '.join(sorted(op['responses']))}). Body: {resp.text[:300]}")
    content = _resolve(op["responses"][code]).get("content", {})
    if "application/json" not in content:      # 204 and images: the status code is enough
        return
    schema = {**content["application/json"]["schema"], "components": SPEC["components"]}
    try:
        jsonschema.validate(resp.json(), schema, format_checker=jsonschema.FormatChecker())
    except jsonschema.ValidationError as exc:
        raise AssertionError(
            f"{method} {template} {code}: the body breaks the YAML schema at "
            f"{'/'.join(map(str, exc.absolute_path)) or '(root)'}: {exc.message}") from None
