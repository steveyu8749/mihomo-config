from __future__ import annotations

import argparse
import re
import urllib.error
import urllib.request
from pathlib import Path

import yaml

PLACEHOLDER_UUID = "00000000-0000-4000-8000-000000000000"
BUILTIN_TARGETS = {"DIRECT", "REJECT", "REJECT-DROP", "PASS", "COMPATIBLE"}
FAKE_IP_RESULTS = {"real-ip", "fake-ip"}
REQUIRED_REAL_IP_FILTERS = {
    "GEOSITE,private,real-ip",
    "RULE-SET,fakeip_compat,real-ip",
}
REQUIRED_FAKEIP_COMPAT = {
    "dns.msftncsi.com",
    "+.push.apple.com",
    "+.market.xiaomi.com",
}
RULE_PROVIDER_INTERVAL = 86400
RULE_PROVIDER_PROXY = "🚀 默认代理"
FORBIDDEN_GROUP_TYPES = {"fallback", "url-test"}


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def is_placeholder_url(url: str) -> bool:
    upper = url.upper()
    return "YOUR_" in upper or "EXAMPLE.COM" in upper


def check_url(url: str, timeout: float = 15.0) -> tuple[bool, str]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "mihomo-config-validator/1.0", "Range": "bytes=0-0"},
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


def rule_index(rules: list[str], prefix: str) -> int | None:
    for index, rule in enumerate(rules):
        if isinstance(rule, str) and rule.startswith(prefix):
            return index
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the public Mihomo template")
    parser.add_argument("config", nargs="?", default="config.example.yaml")
    parser.add_argument("--skip-network", action="store_true", help="skip remote Rule Provider URL reachability checks")
    args = parser.parse_args()

    path = Path(args.config)
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
    proxy_providers = data.get("proxy-providers") or {}

    proxy_names = {item.get("name") for item in proxies if isinstance(item, dict) and isinstance(item.get("name"), str)}
    group_names = {item.get("name") for item in groups if isinstance(item, dict) and isinstance(item.get("name"), str)}
    provider_names = set(providers) if isinstance(providers, dict) else set()
    valid_targets = proxy_names | group_names | BUILTIN_TARGETS

    for group in groups:
        if not isinstance(group, dict):
            fail(errors, f"proxy-group entry is not a mapping: {group!r}")
            continue
        name = group.get("name", "<unnamed>")
        if group.get("type") in FORBIDDEN_GROUP_TYPES:
            fail(errors, f"proxy-group {name!r} uses removed automatic group type {group.get('type')!r}")
        for member in group.get("proxies") or []:
            if member not in valid_targets:
                fail(errors, f"proxy-group {name!r} references missing member {member!r}")

    for index, rule in enumerate(rules, start=1):
        if not isinstance(rule, str):
            fail(errors, f"rule #{index} is not a string: {rule!r}")
            continue
        parts = [part.strip() for part in rule.split(",")]
        kind = parts[0] if parts else ""
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

    dns = data.get("dns") or {}
    fake_filter = dns.get("fake-ip-filter") or []
    for index, item in enumerate(fake_filter, start=1):
        if not isinstance(item, str):
            fail(errors, f"fake-ip-filter #{index} is not a string: {item!r}")
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
        elif len(parts) >= 3 and parts[-1] not in FAKE_IP_RESULTS:
            fail(errors, f"fake-ip-filter #{index} has invalid result {parts[-1]!r}")

    order_pairs = [
        ("GEOSITE,geolocation-!cn,", "GEOSITE,cn,", "geolocation-!cn must appear before cn"),
        ("GEOSITE,onedrive,", "GEOSITE,microsoft,", "onedrive must appear before microsoft"),
        ("GEOSITE,github,", "GEOSITE,microsoft,", "github must appear before microsoft"),
        ("GEOSITE,youtube,", "GEOSITE,google,", "youtube must appear before google"),
    ]
    for first, second, message in order_pairs:
        first_index = rule_index(rules, first)
        second_index = rule_index(rules, second)
        if first_index is not None and second_index is not None and first_index > second_index:
            fail(errors, message)

    if not rules or not isinstance(rules[-1], str) or not rules[-1].startswith("MATCH,"):
        fail(errors, "routing rules must end with MATCH")

    required_rules = {
        "GEOSITE,private,直连",
        "GEOSITE,openai,🤖 ChatGPT",
        "GEOSITE,cn,🎯 直连",
        "GEOIP,CN,🎯 直连",
    }
    missing_rules = required_rules - {item for item in rules if isinstance(item, str)}
    for item in sorted(missing_rules):
        fail(errors, f"missing required routing rule: {item}")

    apns_rule = rule_index(rules, "DOMAIN-SUFFIX,push.apple.com,🍎 Apple")
    apple_rule = rule_index(rules, "GEOSITE,apple-cn,🍎 Apple")
    if apns_rule is None:
        fail(errors, "Apple APNs must have an explicit push.apple.com rule")
    elif apple_rule is not None and apns_rule > apple_rule:
        fail(errors, "Apple APNs rule must appear before GEOSITE,apple-cn")

    if not fake_filter or fake_filter[-1] != "MATCH,fake-ip":
        fail(errors, "fake-ip-filter must end with MATCH,fake-ip")

    missing_real_ip = REQUIRED_REAL_IP_FILTERS - {item for item in fake_filter if isinstance(item, str)}
    for item in sorted(missing_real_ip):
        fail(errors, f"missing required Real-IP compatibility rule: {item}")

    if dns.get("respect-rules") is True:
        fail(errors, "respect-rules must remain disabled for the current direct domestic DoH design")

    sniffer = data.get("sniffer") or {}
    if sniffer.get("enable") is not True:
        fail(errors, "sniffer must remain enabled as a domain-identification fallback")
    if sniffer.get("override-destination") is not False:
        fail(errors, "sniffer override-destination must be false")
    for protocol, config in (sniffer.get("sniff") or {}).items():
        if isinstance(config, dict) and config.get("override-destination") is True:
            fail(errors, f"sniffer {protocol} must not override destination")

    if data.get("allow-lan") is True:
        fail(errors, "allow-lan must not be enabled in the local-only template")

    if isinstance(providers, dict):
        compat = providers.get("fakeip_compat")
        if not isinstance(compat, dict):
            fail(errors, "missing inline fakeip_compat rule-provider")
        else:
            if compat.get("type") != "inline" or compat.get("behavior") != "domain":
                fail(errors, "fakeip_compat must be type:inline with behavior:domain")
            payload = {item for item in (compat.get("payload") or []) if isinstance(item, str)}
            for item in sorted(REQUIRED_FAKEIP_COMPAT - payload):
                fail(errors, f"fakeip_compat missing required domain pattern: {item}")

        for name, provider in providers.items():
            if not isinstance(provider, dict) or provider.get("type") != "http":
                continue
            if provider.get("interval") != RULE_PROVIDER_INTERVAL:
                fail(errors, f"rule-provider {name!r} must use {RULE_PROVIDER_INTERVAL}s update interval")
            if provider.get("proxy") != RULE_PROVIDER_PROXY:
                fail(errors, f"rule-provider {name!r} must download through {RULE_PROVIDER_PROXY!r}")

    if isinstance(proxy_providers, dict):
        for name, provider in proxy_providers.items():
            if not isinstance(provider, dict):
                continue
            url = str(provider.get("url", ""))
            if url and not is_placeholder_url(url):
                fail(errors, f"proxy-provider {name!r} URL looks live instead of sanitized")
            health = provider.get("health-check") or {}
            if not isinstance(health, dict) or health.get("enable") is not True:
                fail(errors, f"proxy-provider {name!r} must keep health-check enabled")

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

    checked_urls = 0
    if not args.skip_network and isinstance(providers, dict):
        for name, provider in providers.items():
            if not isinstance(provider, dict):
                continue
            url = str(provider.get("url", ""))
            if not url or is_placeholder_url(url):
                continue
            if not url.startswith(("https://", "http://")):
                fail(errors, f"rule-provider {name!r} has a non-HTTP URL: {url}")
                continue
            ok, detail = check_url(url)
            checked_urls += 1
            if not ok:
                fail(errors, f"rule-provider {name!r} URL is unreachable: {detail} ({url})")

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
    print("  secret scan:     passed")
    print("  provider URLs:   skipped" if args.skip_network else f"  provider URLs:   {checked_urls} checked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())