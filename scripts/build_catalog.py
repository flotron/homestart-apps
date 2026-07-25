#!/usr/bin/env python3
import argparse
import json
import re
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
PLACEHOLDER = re.compile(r"\{\{([a-z][a-z0-9_]*)\}\}")
RESERVED = {"homestart_data", "server_timezone"}
ALLOWED_INPUT_TYPES = {"text", "port", "path", "select", "timezone"}


def fail(message):
    raise ValueError(message)


def placeholders(value):
    if isinstance(value, dict):
        result = set()
        for key, item in value.items():
            result.update(placeholders(key))
            result.update(placeholders(item))
        return result
    if isinstance(value, list):
        result = set()
        for item in value:
            result.update(placeholders(item))
        return result
    return set(PLACEHOLDER.findall(value)) if isinstance(value, str) else set()


def validate_app(app):
    app_id = str(app.get("id", ""))
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", app_id):
        fail(f"Invalid app id: {app_id!r}")
    for field in ("name", "description", "category", "page_url"):
        if not isinstance(app.get(field), str) or not app[field].strip():
            fail(f"{app_id}: {field} is required")
    inputs = app.get("inputs")
    if not isinstance(inputs, list):
        fail(f"{app_id}: inputs must be a list")
    input_ids = set()
    for item in inputs:
        input_id = str(item.get("id", ""))
        if not re.fullmatch(r"[a-z][a-z0-9_]*", input_id) or input_id in input_ids:
            fail(f"{app_id}: invalid or duplicate input {input_id!r}")
        if item.get("type") not in ALLOWED_INPUT_TYPES:
            fail(f"{app_id}: invalid input type for {input_id}")
        if not isinstance(item.get("label"), str) or "default" not in item:
            fail(f"{app_id}: input {input_id} needs label and default")
        if placeholders(item["default"]) - RESERVED:
            fail(f"{app_id}: input {input_id} default may only use reserved placeholders")
        if item.get("type") == "select" and not item.get("options"):
            fail(f"{app_id}: select input {input_id} needs options")
        input_ids.add(input_id)
    compose = app.get("compose")
    if not isinstance(compose, dict) or not isinstance(compose.get("services"), dict) or not compose["services"]:
        fail(f"{app_id}: compose.services is required")
    unknown = placeholders(compose) - input_ids - RESERVED
    if unknown:
        fail(f"{app_id}: undeclared placeholders: {', '.join(sorted(unknown))}")
    for service_name, service in compose["services"].items():
        if not re.fullmatch(r"[a-zA-Z0-9_.-]+", str(service_name)) or not isinstance(service, dict):
            fail(f"{app_id}: invalid service")
        if not isinstance(service.get("image"), str) or not service["image"].strip():
            fail(f"{app_id}: every service needs an image")


def build():
    index = yaml.safe_load((ROOT / "catalog.yaml").read_text(encoding="utf-8"))
    if index.get("schema_version") != 1:
        fail("Only schema_version 1 is supported")
    result = {
        "schema_version": 1,
        "catalog_version": str(index.get("catalog_version", "")),
        "name": str(index.get("name", "HomeStart Apps")),
        "apps": [],
    }
    seen = set()
    for app_id in index.get("apps", []):
        directory = ROOT / "apps" / str(app_id)
        manifest = yaml.safe_load((directory / "manifest.yaml").read_text(encoding="utf-8"))
        compose_file = directory / manifest.pop("compose_file", "compose.yaml")
        manifest["compose"] = yaml.safe_load(compose_file.read_text(encoding="utf-8"))
        validate_app(manifest)
        if manifest["id"] in seen:
            fail(f"Duplicate app id: {manifest['id']}")
        seen.add(manifest["id"])
        result["apps"].append(manifest)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="verify dist/catalog.json is current")
    args = parser.parse_args()
    payload = json.dumps(build(), ensure_ascii=False, indent=2) + "\n"
    target = ROOT / "dist" / "catalog.json"
    if args.check:
        if not target.exists() or target.read_text(encoding="utf-8") != payload:
            print("dist/catalog.json is not current; run scripts/build_catalog.py", file=sys.stderr)
            return 1
        print(f"Catalog valid: {len(json.loads(payload)['apps'])} apps")
        return 0
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(payload, encoding="utf-8")
    print(target)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, yaml.YAMLError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
