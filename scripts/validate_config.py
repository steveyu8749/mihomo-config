from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml


PLACEHOLDER_UUID = "00000000-0000-4000-8000-000000000000"
BUILTIN_TARGETS = {"DIRECT", "REJECT", "REJECT-DROP", "PASS", "COMPATIBLE"}
FAKE_IP_RESULTS = {"real-ip", "fake-ip"}


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "config.example.yaml")
    errors: list[str] = []

    if not path.is_file():
        print(f"ERROR: config not found: {path}")
        return 2

    raw = path.read_text(encoding="utf-8")

    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        print(f"ERROR: YAML parse failed: {exc}")
        return 1

    if not isinstance(data, dict):
        print("ERROR: YAML root must be a mapping")
        return 1

    proxies = data.get("proxies") or []
    groups = data.get("proxy-groups") or []
    providers = data.get("rule-providers") or {}
    rules = data.get("rules") or []

    proxy_names = {
        item.get("name")
        for item in proxies
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    group_names = {
        item.get("name")
        for item in groups
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    provider_names = set(providers) if isinstance(providers, dict) else set()
    valid_targets = proxy_names | group_names | BUILTIN_TARGETS

    # Proxy-group members must resolve to another group, a local proxy, or a builtin target.
    for group in groups:
        if not isinstance(group, dict):
            fail(errors, f"proxy-group entry is not a mapping: {group!r}")
            continue
        name = group.get("name", "<unnamed>")
        for member in group.get("proxies") or []:
            if member not in valid_targets:
                fail(errors, f"proxy-group {name!r} references missing member {member!r}")

    # Rule targets and RULE-SET provider references must exist.
    for index, rule in enumerate(rules, start=1):
        if not isinstance(rule, str):
            fail(errors, f"rule #{index} is not a string: {rule!r}")
            continue
        parts = [part.strip() for part in rule.split(",")]
        if not parts:
            continue
        kind = parts[0]
        if kind == "MATCH":
            if len(parts) < 2:
                fail(errors, f"rule #{index} MATCH has no target")
                continue
            target = parts[1]
        else:
            if len(parts) < 3:
                fail(errors, f"rule #{index} {kind} is incomplete: {rule}")
                continue
            if kind == "RULE-SET" and parts[1] not in provider_names:
                fail(errors, f"rule #{index} references missing rule-provider {parts[1]!r}")
            target = parts[2]

        if target not in valid_targets:
            fail(errors, f"rule #{index} references missing target {target!r}")

    # DNS fake-ip-filter can also reference rule providers.
    fake_filter = ((data.get("dns") or {}).get("fake-ip-filter") or [])
    for index, item in enumerate(fake_filter, start=1):
        if not isinstance(item, str):
            continue
        parts = [part.strip() for part in item.split(",")]
        if parts and parts[0] == "RULE-SET":
            if len(parts) < 3:
                fail(errors, f"fake-ip-filter #{index} RULE-SET is incomplete: {item}")
                continue
            if parts[1] not in provider_names:
                fail(errors, f"fake-ip-filter #{index} references missing rule-provider {parts[1]!r}")
            if parts[2] not in FAKE_IP_RESULTS:
                fail(errors, f"fake-ip-filter #{index} has invalid result {parts[2]!r}")

    # Public template safety: subscription providers must visibly use placeholders.
    proxy_providers = data.get("proxy-providers") or {}
    if isinstance(proxy_providers, dict):
        for name, provider in proxy_providers.items():
            if not isinstance(provider, dict):
                continue
            url = str(provider.get("url", ""))
            if url and "example.com" not in url and "YOUR_" not in url:
                fail(errors, f"proxy-provider {name!r} URL looks live instead of sanitized")

    # Public template safety: manually defined remote nodes must use placeholder endpoints/UUIDs.
    for proxy in proxies:
        if not isinstance(proxy, dict) or proxy.get("type") == "direct":
            continue
        name = proxy.get("name", "<unnamed>")
        server = str(proxy.get("server", ""))
        uuid = str(proxy.get("uuid", ""))
        if server and not (server.endswith(".example.com") or server.startswith("YOUR_")):
            fail(errors, f"proxy {name!r} server looks live instead of sanitized")
        if uuid and uuid != PLACEHOLDER_UUID and "YOUR_" not in uuid:
            fail(errors, f"proxy {name!r} UUID looks live instead of sanitized")

    # Catch common secrets even if they appear outside the expected YAML fields.
    for match in re.finditer(r"(?i)(?:token|auth|api[_-]?key|secret)=([A-Za-z0-9_.-]{12,})", raw):
        value = match.group(1)
        if not value.upper().startswith("YOUR_"):
            fail(errors, "found a query-string credential that does not look like a placeholder")

    for value in re.findall(
        r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
        raw,
    ):
        if value.lower() != PLACEHOLDER_UUID:
            fail(errors, "found a UUID that does not match the public placeholder UUID")

    if errors:
        print("Validation failed:")
        for item in errors:
            print(f"  - {item}")
        return 1

    print("Validation passed")
    print(f"  proxy-providers: {len(proxy_providers)}")
    print(f"  proxies:         {len(proxies)}")
    print(f"  proxy-groups:    {len(groups)}")
    print(f"  rules:           {len(rules)}")
    print(f"  rule-providers:  {len(providers)}")
    print("  secret scan:     passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
