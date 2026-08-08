from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import yaml

PLACEHOLDER_UUID = "00000000-0000-4000-8000-000000000000"
DEFAULT_PROXY = "🚀 默认代理"
HARD_DIRECT = "直连"
REQUIRED_FAKEIP_COMPAT = {
    "dns.msftncsi.com",
    "+.push.apple.com",
    "+.market.xiaomi.com",
}
REQUIRED_RULES = {
    "RULE-SET,private_domain,直连",
    "RULE-SET,cn_domain,直连",
    "RULE-SET,cn_ip,直连",
}
RULE_ORDER = [
    ("RULE-SET,geolocation-!cn,", "RULE-SET,cn_domain,", "geolocation-!cn must appear before cn_domain"),
    ("RULE-SET,onedrive_domain,", "RULE-SET,microsoft_domain,", "onedrive_domain must appear before microsoft_domain"),
    ("RULE-SET,github_domain,", "RULE-SET,microsoft_domain,", "github_domain must appear before microsoft_domain"),
    ("RULE-SET,youtube_domain,", "RULE-SET,google_domain,", "youtube_domain must appear before google_domain"),
]
GEODATA_KEYS = {
    "geodata-mode",
    "geodata-loader",
    "geo-auto-update",
    "geo-update-interval",
    "geox-url",
}


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def require_mapping(value: Any, name: str, errors: list[str]) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    fail(errors, f"{name} must be a mapping")
    return {}


def require_list(value: Any, name: str, errors: list[str]) -> list[Any]:
    if isinstance(value, list):
        return value
    fail(errors, f"{name} must be a list")
    return []


def is_placeholder_url(url: str) -> bool:
    normalized = url.strip().upper()
    return (
        "YOUR_" in normalized
        or "EXAMPLE.COM" in normalized
        or normalized in {"订阅URL", "SUBSCRIPTION_URL", "SUBSCRIPTION URL"}
    )


def find_rule(rules: list[Any], prefix: str) -> int | None:
    for index, rule in enumerate(rules):
        if isinstance(rule, str) and rule.startswith(prefix):
            return index
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Check repository-specific policy for the public Mihomo template. "
            "Mihomo itself is the authoritative syntax and semantic validator."
        )
    )
    parser.add_argument("config", nargs="?", default="config.example.yaml")
    args = parser.parse_args()

    path = Path(args.config)
    if not path.is_file():
        print(f"ERROR: config not found: {path}")
        return 2

    raw = path.read_text(encoding="utf-8")
    try:
        loaded = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        print(f"ERROR: YAML parse failed: {exc}")
        return 1
    if not isinstance(loaded, dict):
        print("ERROR: YAML root must be a mapping")
        return 1

    data: dict[str, Any] = loaded
    errors: list[str] = []

    proxies = require_list(data.get("proxies") or [], "proxies", errors)
    groups = require_list(data.get("proxy-groups") or [], "proxy-groups", errors)
    providers = require_mapping(data.get("rule-providers") or {}, "rule-providers", errors)
    proxy_providers = require_mapping(data.get("proxy-providers") or {}, "proxy-providers", errors)
    rules = require_list(data.get("rules") or [], "rules", errors)
    dns = require_mapping(data.get("dns") or {}, "dns", errors)
    sniffer = require_mapping(data.get("sniffer") or {}, "sniffer", errors)

    # Repository invariant: the default proxy group must never silently become DIRECT.
    groups_by_name = {
        item.get("name"): item
        for item in groups
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    default_group = groups_by_name.get(DEFAULT_PROXY)
    if not isinstance(default_group, dict):
        fail(errors, f"missing {DEFAULT_PROXY} group")
    else:
        if default_group.get("type") != "select":
            fail(errors, f"{DEFAULT_PROXY} must remain a select group")
        if default_group.get("include-all") is not True:
            fail(errors, f"{DEFAULT_PROXY} must use include-all: true")
        excluded = {
            item.strip()
            for item in str(default_group.get("exclude-type", "")).lower().split("|")
            if item.strip()
        }
        if "direct" not in excluded:
            fail(errors, f"{DEFAULT_PROXY} must exclude direct-type nodes")
        if HARD_DIRECT in (default_group.get("proxies") or []):
            fail(errors, f"{DEFAULT_PROXY} must not expose hard DIRECT")

    # Project convention only; core syntax/semantics are checked later by real Mihomo.
    for group in groups:
        if not isinstance(group, dict):
            continue
        if group.get("type") in {"fallback", "url-test"}:
            fail(errors, f"proxy-group {group.get('name')!r} reintroduces removed automatic selection")
        if group.get("name") == "🌐 全部节点":
            fail(errors, "shared '🌐 全部节点' group was intentionally removed")

    rule_strings = {item for item in rules if isinstance(item, str)}
    for rule in sorted(REQUIRED_RULES - rule_strings):
        fail(errors, f"missing required routing rule: {rule}")

    if not rules or not isinstance(rules[-1], str) or not rules[-1].startswith("MATCH,"):
        fail(errors, "routing rules must end with MATCH")

    for first, second, message in RULE_ORDER:
        first_index = find_rule(rules, first)
        second_index = find_rule(rules, second)
        if first_index is not None and second_index is not None and first_index > second_index:
            fail(errors, message)

    apns_index = find_rule(rules, "DOMAIN-SUFFIX,push.apple.com,🍎 Apple")
    apple_index = find_rule(rules, "RULE-SET,apple_domain,🍎 Apple")
    if apple_index is not None and apns_index is None:
        fail(errors, "Apple APNs must have an explicit push.apple.com rule")
    elif apns_index is not None and apple_index is not None and apns_index > apple_index:
        fail(errors, "Apple APNs rule must appear before apple_domain")

    # Fake-IP policy belongs to this repository rather than to Mihomo syntax.
    fake_filter = dns.get("fake-ip-filter") or []
    if dns.get("fake-ip-filter-mode") == "rule":
        if not isinstance(fake_filter, list):
            fail(errors, "dns.fake-ip-filter must be a list")
            fake_filter = []
        required_real_ip = {
            "RULE-SET,private_domain,real-ip",
            "RULE-SET,fakeip_compat,real-ip",
        }
        present = {item for item in fake_filter if isinstance(item, str)}
        for rule in sorted(required_real_ip - present):
            fail(errors, f"missing required Real-IP compatibility rule: {rule}")
        if not fake_filter or fake_filter[-1] != "MATCH,fake-ip":
            fail(errors, "fake-ip-filter in rule mode must end with MATCH,fake-ip")

    if dns.get("respect-rules") is True:
        fail(errors, "respect-rules must remain disabled for the direct domestic DoH design")

    compat = providers.get("fakeip_compat")
    if not isinstance(compat, dict):
        fail(errors, "missing inline fakeip_compat rule-provider")
    else:
        if compat.get("type") != "inline" or compat.get("behavior") != "domain":
            fail(errors, "fakeip_compat must remain type:inline with behavior:domain")
        payload = {item for item in (compat.get("payload") or []) if isinstance(item, str)}
        for item in sorted(REQUIRED_FAKEIP_COMPAT - payload):
            fail(errors, f"fakeip_compat missing required domain pattern: {item}")

    if sniffer.get("enable") is not True:
        fail(errors, "sniffer must remain enabled")
    if sniffer.get("override-destination") is not False:
        fail(errors, "sniffer override-destination must remain false")

    if data.get("allow-lan") is True:
        fail(errors, "allow-lan must not be enabled in the local-only public template")
    for key in sorted(GEODATA_KEYS):
        if key in data:
            fail(errors, f"{key} should not be configured in the MRS-only template")

    # Public-template hygiene: reject actual subscription/node credentials.
    for name, provider in proxy_providers.items():
        if not isinstance(provider, dict):
            continue
        url = str(provider.get("url", ""))
        if url and not is_placeholder_url(url):
            fail(errors, f"proxy-provider {name!r} URL looks live instead of sanitized")

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

    for match in re.finditer(r"(?i)(?:token|auth|api[_-]?key|secret)=([A-Za-z0-9_.-]{12,})", raw):
        value = match.group(1)
        if not value.upper().startswith("YOUR_"):
            fail(errors, "found a query-string credential that does not look like a placeholder")

    for value in re.findall(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b", raw):
        if value.lower() != PLACEHOLDER_UUID:
            fail(errors, "found a UUID that does not match the public placeholder UUID")

    if errors:
        print("Repository policy validation failed:")
        for item in errors:
            print(f"  - {item}")
        return 1

    print("Repository policy validation passed")
    print("  YAML:             parsed")
    print("  routing intent:   preserved")
    print("  DNS/sniffer:      policy passed")
    print("  public secrets:   sanitized")
    print("  core semantics:   delegated to mihomo -t")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
