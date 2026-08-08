from __future__ import annotations

import argparse
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import yaml

PLACEHOLDER_UUID = "00000000-0000-4000-8000-000000000000"
BUILTIN_TARGETS = {
    "DIRECT",
    "REJECT",
    "REJECT-DROP",
    "PASS",
    "PASS-RULE",
    "COMPATIBLE",
    "GLOBAL",
}
FAKE_IP_RESULTS = {"real-ip", "fake-ip"}
RULE_PROVIDER_TYPES = {"http", "file", "inline"}
RULE_PROVIDER_BEHAVIORS = {"domain", "ipcidr", "classical"}
RULE_PROVIDER_FORMATS = {"yaml", "text", "mrs"}
DEFAULT_PROXY_GROUP = "🚀 默认代理"
HARD_DIRECT = "直连"
RECOMMENDED_PROVIDER_INTERVAL = 86400
REQUIRED_FAKEIP_COMPAT = {
    "dns.msftncsi.com",
    "+.push.apple.com",
    "+.market.xiaomi.com",
}
EXPECTED_PROVIDER_TARGETS = {
    "private_domain": HARD_DIRECT,
    "openai_domain": "🤖 ChatGPT",
    "cn_domain": HARD_DIRECT,
    "cn_ip": HARD_DIRECT,
}
ORDER_PAIRS = [
    ("geolocation-!cn", "cn_domain", "geolocation-!cn must appear before cn_domain"),
    ("onedrive_domain", "microsoft_domain", "onedrive_domain must appear before microsoft_domain"),
    ("github_domain", "microsoft_domain", "github_domain must appear before microsoft_domain"),
    ("youtube_domain", "google_domain", "youtube_domain must appear before google_domain"),
]
AUTOMATIC_GROUP_TYPES = {"fallback", "url-test"}
GEODATA_KEYS = {
    "geodata-mode",
    "geodata-loader",
    "geo-auto-update",
    "geo-update-interval",
    "geox-url",
}


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def warn(warnings: list[str], message: str) -> None:
    warnings.append(message)


def is_placeholder_url(url: str) -> bool:
    upper = url.upper()
    return "YOUR_" in upper or "EXAMPLE.COM" in upper


def check_url(url: str, timeout: float = 15.0) -> tuple[bool, str]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "mihomo-config-validator/2.0", "Range": "bytes=0-0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            code = getattr(response, "status", 200)
            return (200 <= code < 400, str(code) if 200 <= code < 400 else f"HTTP {code}")
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except urllib.error.URLError as exc:
        return False, str(exc.reason)
    except TimeoutError:
        return False, "timeout"


def ensure_mapping(value: Any, name: str, errors: list[str]) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    fail(errors, f"{name} must be a mapping")
    return {}


def ensure_list(value: Any, name: str, errors: list[str]) -> list[Any]:
    if isinstance(value, list):
        return value
    fail(errors, f"{name} must be a list")
    return []


def named_entries(entries: list[Any], section: str, errors: list[str]) -> tuple[dict[str, dict[str, Any]], set[str]]:
    by_name: dict[str, dict[str, Any]] = {}
    duplicates: set[str] = set()
    for index, item in enumerate(entries, start=1):
        if not isinstance(item, dict):
            fail(errors, f"{section} entry #{index} is not a mapping: {item!r}")
            continue
        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            fail(errors, f"{section} entry #{index} has no valid name")
            continue
        if name in by_name:
            duplicates.add(name)
        else:
            by_name[name] = item
    for name in sorted(duplicates):
        fail(errors, f"duplicate {section} name {name!r}")
    return by_name, set(by_name)


def rule_parts(rule: str) -> list[str]:
    return [part.strip() for part in rule.split(",")]


def rule_index(rules: list[Any], provider_name: str) -> int | None:
    prefix = f"RULE-SET,{provider_name},"
    for index, rule in enumerate(rules):
        if isinstance(rule, str) and rule.startswith(prefix):
            return index
    return None


def rule_target_for_provider(rules: list[Any], provider_name: str) -> str | None:
    prefix = f"RULE-SET,{provider_name},"
    for rule in rules:
        if not isinstance(rule, str) or not rule.startswith(prefix):
            continue
        parts = rule_parts(rule)
        if len(parts) >= 3:
            return parts[2]
    return None


def exclude_types(group: dict[str, Any]) -> set[str]:
    value = group.get("exclude-type")
    if not isinstance(value, str):
        return set()
    return {part.strip().lower() for part in value.split("|") if part.strip()}


def url_hostname(url: str) -> str:
    try:
        return (urllib.parse.urlparse(url).hostname or "").lower()
    except ValueError:
        return ""


def validate_rule_provider(
    name: str,
    provider: Any,
    valid_targets: set[str],
    errors: list[str],
    warnings: list[str],
) -> None:
    if not isinstance(provider, dict):
        fail(errors, f"rule-provider {name!r} must be a mapping")
        return

    provider_type = provider.get("type")
    if provider_type not in RULE_PROVIDER_TYPES:
        fail(errors, f"rule-provider {name!r} has invalid type {provider_type!r}")
        return

    behavior = provider.get("behavior")
    if behavior not in RULE_PROVIDER_BEHAVIORS:
        fail(errors, f"rule-provider {name!r} has invalid behavior {behavior!r}")

    format_value = provider.get("format", "yaml")
    if format_value not in RULE_PROVIDER_FORMATS:
        fail(errors, f"rule-provider {name!r} has invalid format {format_value!r}")
    if format_value == "mrs" and behavior not in {"domain", "ipcidr"}:
        fail(errors, f"rule-provider {name!r} uses MRS with unsupported behavior {behavior!r}")

    if provider_type == "http":
        url = provider.get("url")
        if not isinstance(url, str) or not url.startswith(("https://", "http://")):
            fail(errors, f"rule-provider {name!r} type:http requires an HTTP(S) url")
        interval = provider.get("interval")
        if not isinstance(interval, int) or interval <= 0:
            fail(errors, f"rule-provider {name!r} type:http requires a positive interval")
        elif interval != RECOMMENDED_PROVIDER_INTERVAL:
            warn(
                warnings,
                f"rule-provider {name!r} interval is {interval}s; repository convention is {RECOMMENDED_PROVIDER_INTERVAL}s",
            )

        if behavior in {"domain", "ipcidr"} and format_value != "mrs":
            fail(errors, f"rule-provider {name!r} must use MRS for domain/ipcidr data in this template")

        proxy = provider.get("proxy")
        if proxy is not None:
            if not isinstance(proxy, str) or proxy not in valid_targets:
                fail(errors, f"rule-provider {name!r} references missing download proxy {proxy!r}")
        elif isinstance(url, str) and url_hostname(url) == "raw.githubusercontent.com":
            fail(errors, f"rule-provider {name!r} from raw.githubusercontent.com must set proxy: {DEFAULT_PROXY_GROUP}")

        if isinstance(url, str) and url_hostname(url) == "raw.githubusercontent.com" and proxy != DEFAULT_PROXY_GROUP:
            fail(errors, f"rule-provider {name!r} from raw.githubusercontent.com must download through {DEFAULT_PROXY_GROUP!r}")

    elif provider_type == "file":
        path = provider.get("path")
        if not isinstance(path, str) or not path:
            fail(errors, f"rule-provider {name!r} type:file requires path")

    elif provider_type == "inline":
        payload = provider.get("payload")
        if not isinstance(payload, list):
            fail(errors, f"rule-provider {name!r} type:inline requires a payload list")


def validate_proxy_provider(
    name: str,
    provider: Any,
    valid_targets: set[str],
    errors: list[str],
    warnings: list[str],
) -> None:
    if not isinstance(provider, dict):
        fail(errors, f"proxy-provider {name!r} must be a mapping")
        return

    provider_type = provider.get("type")
    if provider_type not in RULE_PROVIDER_TYPES:
        fail(errors, f"proxy-provider {name!r} has invalid type {provider_type!r}")
        return

    if provider_type == "http":
        url = provider.get("url")
        if not isinstance(url, str) or not url.startswith(("https://", "http://")):
            fail(errors, f"proxy-provider {name!r} type:http requires an HTTP(S) url")
        elif not is_placeholder_url(url):
            fail(errors, f"proxy-provider {name!r} URL looks live instead of sanitized")
        interval = provider.get("interval")
        if not isinstance(interval, int) or interval <= 0:
            fail(errors, f"proxy-provider {name!r} type:http requires a positive interval")

    elif provider_type == "file":
        path = provider.get("path")
        if not isinstance(path, str) or not path:
            fail(errors, f"proxy-provider {name!r} type:file requires path")

    elif provider_type == "inline" and not isinstance(provider.get("payload"), list):
        fail(errors, f"proxy-provider {name!r} type:inline requires a payload list")

    proxy = provider.get("proxy")
    if proxy is not None and (not isinstance(proxy, str) or proxy not in valid_targets):
        fail(errors, f"proxy-provider {name!r} references missing download proxy {proxy!r}")

    health = provider.get("health-check")
    if not isinstance(health, dict) or health.get("enable") is not True:
        warn(warnings, f"proxy-provider {name!r} has health-check disabled or missing")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the public Mihomo template")
    parser.add_argument("config", nargs="?", default="config.example.yaml")
    parser.add_argument(
        "--check-network",
        action="store_true",
        help="also check non-placeholder HTTP rule-provider URLs; disabled by default to keep CI deterministic",
    )
    parser.add_argument("--skip-network", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    check_network = args.check_network and not args.skip_network

    path = Path(args.config)
    errors: list[str] = []
    warnings: list[str] = []
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

    proxies = ensure_list(data.get("proxies") or [], "proxies", errors)
    groups = ensure_list(data.get("proxy-groups") or [], "proxy-groups", errors)
    providers = ensure_mapping(data.get("rule-providers") or {}, "rule-providers", errors)
    rules = ensure_list(data.get("rules") or [], "rules", errors)
    proxy_providers = ensure_mapping(data.get("proxy-providers") or {}, "proxy-providers", errors)

    proxies_by_name, proxy_names = named_entries(proxies, "proxy", errors)
    groups_by_name, group_names = named_entries(groups, "proxy-group", errors)
    provider_names = set(providers)
    proxy_provider_names = set(proxy_providers)

    for name in sorted(proxy_names & group_names):
        fail(errors, f"name {name!r} is used by both a proxy and a proxy-group")

    valid_targets = proxy_names | group_names | BUILTIN_TARGETS

    for name, group in groups_by_name.items():
        group_type = group.get("type")
        if not isinstance(group_type, str) or not group_type:
            fail(errors, f"proxy-group {name!r} has no valid type")
        elif group_type in AUTOMATIC_GROUP_TYPES:
            warn(warnings, f"proxy-group {name!r} uses automatic type {group_type!r}; current template convention is manual select")

        members = group.get("proxies") or []
        if not isinstance(members, list):
            fail(errors, f"proxy-group {name!r} proxies must be a list")
            members = []
        for member in members:
            if not isinstance(member, str):
                fail(errors, f"proxy-group {name!r} contains a non-string member {member!r}")
            elif member not in valid_targets:
                fail(errors, f"proxy-group {name!r} references missing member {member!r}")

        uses = group.get("use") or []
        if not isinstance(uses, list):
            fail(errors, f"proxy-group {name!r} use must be a list")
            uses = []
        for provider_name in uses:
            if not isinstance(provider_name, str) or provider_name not in proxy_provider_names:
                fail(errors, f"proxy-group {name!r} references missing proxy-provider {provider_name!r}")

        if group.get("include-all") is True and HARD_DIRECT in members and "direct" not in exclude_types(group):
            fail(
                errors,
                f"proxy-group {name!r} explicitly exposes {HARD_DIRECT!r} while include-all is enabled; add exclude-type: direct",
            )

    default_group = groups_by_name.get(DEFAULT_PROXY_GROUP)
    if not isinstance(default_group, dict):
        fail(errors, f"missing {DEFAULT_PROXY_GROUP} group")
    else:
        if default_group.get("type") != "select":
            fail(errors, f"{DEFAULT_PROXY_GROUP} must remain a select group")
        if default_group.get("include-all") is not True:
            fail(errors, f"{DEFAULT_PROXY_GROUP} must use include-all: true")
        if "direct" not in exclude_types(default_group):
            fail(errors, f"{DEFAULT_PROXY_GROUP} must exclude direct-type nodes")
        if HARD_DIRECT in (default_group.get("proxies") or []):
            fail(errors, f"{DEFAULT_PROXY_GROUP} must not expose hard DIRECT")

    for index, rule in enumerate(rules, start=1):
        if not isinstance(rule, str):
            fail(errors, f"rule #{index} is not a string: {rule!r}")
            continue
        parts = rule_parts(rule)
        if not parts or not parts[0]:
            fail(errors, f"rule #{index} is empty")
            continue
        kind = parts[0]

        if kind in {"GEOSITE", "GEOIP"}:
            fail(errors, f"rule #{index} uses {kind}; this repository intentionally uses Rule Providers instead of GeoData")

        if kind == "MATCH":
            if len(parts) < 2 or not parts[1]:
                fail(errors, f"rule #{index} MATCH has no target")
                continue
            target = parts[1]
        elif kind == "RULE-SET":
            if len(parts) < 3:
                fail(errors, f"rule #{index} RULE-SET is incomplete: {rule}")
                continue
            provider_name = parts[1]
            if provider_name not in provider_names:
                fail(errors, f"rule #{index} references missing rule-provider {provider_name!r}")
            target = parts[2]
        elif kind in {"SUB-RULE", "AND", "OR", "NOT"}:
            # These rule syntaxes can contain nested commas; PyYAML has already validated
            # the scalar itself, so avoid pretending a naive split can validate the target.
            continue
        else:
            if len(parts) < 3:
                fail(errors, f"rule #{index} {kind} is incomplete: {rule}")
                continue
            target = parts[2]

        if target not in valid_targets:
            fail(errors, f"rule #{index} references missing target {target!r}")

    if not rules or not isinstance(rules[-1], str) or not rules[-1].startswith("MATCH,"):
        fail(errors, "routing rules must end with MATCH")

    for first, second, message in ORDER_PAIRS:
        first_index = rule_index(rules, first)
        second_index = rule_index(rules, second)
        if first_index is not None and second_index is not None and first_index > second_index:
            fail(errors, message)

    for provider_name, expected_target in EXPECTED_PROVIDER_TARGETS.items():
        if provider_name not in provider_names:
            continue
        actual_target = rule_target_for_provider(rules, provider_name)
        if actual_target is None:
            fail(errors, f"rule-provider {provider_name!r} is present but has no routing rule")
        elif actual_target != expected_target:
            fail(
                errors,
                f"rule-provider {provider_name!r} must route to {expected_target!r}, got {actual_target!r}",
            )

    apns_prefix = "DOMAIN-SUFFIX,push.apple.com,🍎 Apple"
    apns_index = next(
        (index for index, rule in enumerate(rules) if isinstance(rule, str) and rule.startswith(apns_prefix)),
        None,
    )
    apple_index = rule_index(rules, "apple_domain")
    if "apple_domain" in provider_names and "🍎 Apple" in group_names:
        if apns_index is None:
            fail(errors, "Apple APNs must have an explicit push.apple.com rule")
        elif apple_index is not None and apns_index > apple_index:
            fail(errors, "Apple APNs rule must appear before apple_domain")

    dns = ensure_mapping(data.get("dns") or {}, "dns", errors)
    fake_filter = dns.get("fake-ip-filter") or []
    if not isinstance(fake_filter, list):
        fail(errors, "dns.fake-ip-filter must be a list")
        fake_filter = []

    if dns.get("fake-ip-filter-mode") == "rule":
        for index, item in enumerate(fake_filter, start=1):
            if not isinstance(item, str):
                fail(errors, f"fake-ip-filter #{index} is not a string: {item!r}")
                continue
            parts = rule_parts(item)
            if not parts:
                fail(errors, f"fake-ip-filter #{index} is empty")
                continue
            if parts[0] == "RULE-SET":
                if len(parts) < 3:
                    fail(errors, f"fake-ip-filter #{index} RULE-SET is incomplete: {item}")
                    continue
                provider_name = parts[1]
                if provider_name not in provider_names:
                    fail(errors, f"fake-ip-filter #{index} references missing rule-provider {provider_name!r}")
                else:
                    behavior = providers.get(provider_name, {}).get("behavior") if isinstance(providers.get(provider_name), dict) else None
                    if behavior not in {"domain", "classical"}:
                        fail(
                            errors,
                            f"fake-ip-filter #{index} uses rule-provider {provider_name!r} with unsupported behavior {behavior!r}",
                        )
                result = parts[2]
            elif parts[0] == "MATCH":
                if len(parts) < 2:
                    fail(errors, f"fake-ip-filter #{index} MATCH has no result")
                    continue
                result = parts[1]
            else:
                if len(parts) < 3:
                    fail(errors, f"fake-ip-filter #{index} is incomplete: {item}")
                    continue
                result = parts[-1]
            if result not in FAKE_IP_RESULTS:
                fail(errors, f"fake-ip-filter #{index} has invalid result {result!r}")

        if not fake_filter or fake_filter[-1] != "MATCH,fake-ip":
            fail(errors, "fake-ip-filter in rule mode must end with MATCH,fake-ip")

        for provider_name in ("private_domain", "fakeip_compat"):
            if provider_name not in provider_names:
                continue
            required = f"RULE-SET,{provider_name},real-ip"
            if required not in {item for item in fake_filter if isinstance(item, str)}:
                fail(errors, f"missing required Real-IP compatibility rule: {required}")

    if dns.get("respect-rules") is True:
        fail(errors, "respect-rules must remain disabled for the current direct domestic DoH design")

    sniffer = ensure_mapping(data.get("sniffer") or {}, "sniffer", errors)
    if sniffer.get("enable") is not True:
        fail(errors, "sniffer must remain enabled as a domain-identification fallback")
    if sniffer.get("override-destination") is not False:
        fail(errors, "sniffer override-destination must be false")
    for protocol, config in (sniffer.get("sniff") or {}).items():
        if isinstance(config, dict) and config.get("override-destination") is True:
            fail(errors, f"sniffer {protocol} must not override destination")
    if sniffer.get("skip-domain"):
        warn(warnings, "sniffer skip-domain is present; keep exceptions minimal and tied to reproducible compatibility issues")

    if data.get("allow-lan") is True:
        fail(errors, "allow-lan must not be enabled in the local-only public template")

    for key in sorted(GEODATA_KEYS):
        if key in data:
            fail(errors, f"{key} should not be configured in the MRS-only template")

    for name, provider in providers.items():
        validate_rule_provider(name, provider, valid_targets, errors, warnings)

    compat = providers.get("fakeip_compat")
    if isinstance(compat, dict):
        if compat.get("type") != "inline" or compat.get("behavior") != "domain":
            fail(errors, "fakeip_compat must be type:inline with behavior:domain")
        payload = {item for item in (compat.get("payload") or []) if isinstance(item, str)}
        for item in sorted(REQUIRED_FAKEIP_COMPAT - payload):
            fail(errors, f"fakeip_compat missing required domain pattern: {item}")

    referenced_rule_providers: set[str] = set()
    for rule in rules:
        if isinstance(rule, str) and rule.startswith("RULE-SET,"):
            parts = rule_parts(rule)
            if len(parts) >= 2:
                referenced_rule_providers.add(parts[1])
    if dns.get("fake-ip-filter-mode") == "rule":
        for item in fake_filter:
            if isinstance(item, str) and item.startswith("RULE-SET,"):
                parts = rule_parts(item)
                if len(parts) >= 2:
                    referenced_rule_providers.add(parts[1])
    for name in sorted(provider_names - referenced_rule_providers):
        warn(warnings, f"rule-provider {name!r} is defined but not referenced")

    for name, provider in proxy_providers.items():
        validate_proxy_provider(name, provider, valid_targets, errors, warnings)

    for name, proxy in proxies_by_name.items():
        if proxy.get("type") == "direct":
            continue
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

    checked_urls = 0
    if check_network:
        for name, provider in providers.items():
            if not isinstance(provider, dict) or provider.get("type") != "http":
                continue
            url = provider.get("url")
            if not isinstance(url, str) or not url or is_placeholder_url(url):
                continue
            ok, detail = check_url(url)
            checked_urls += 1
            if not ok:
                fail(errors, f"rule-provider {name!r} URL is unreachable: {detail} ({url})")

    if warnings:
        print("Warnings:")
        for item in warnings:
            print(f"  - {item}")

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
    print(f"  fake-ip-filter:  {len(fake_filter)} rules")
    print(f"  warnings:        {len(warnings)}")
    print("  secret scan:     passed")
    print(f"  provider URLs:   {checked_urls} checked" if check_network else "  provider URLs:   not checked (use --check-network)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
