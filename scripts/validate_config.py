from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

import yaml


PLACEHOLDER_UUID = "00000000-0000-4000-8000-000000000000"
BUILTIN_TARGETS = {"DIRECT", "REJECT", "REJECT-DROP", "PASS", "COMPATIBLE"}
FAKE_IP_RESULTS = {"real-ip", "fake-ip"}
REQUIRED_REAL_IP_FILTERS = {
    "RULE-SET,private_domain,real-ip",
    "DOMAIN,dns.msftncsi.com,real-ip",
    "DOMAIN-SUFFIX,push.apple.com,real-ip",
}


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

    proxy_names = {item.get("name") for item in proxies if isinstance(item, dict) and isinstance(item.get("name"), str)}
    group_names = {item.get("name") for item in groups if isinstance(item, dict) and isinstance(item.get("name"), str)}
    provider_names = set(providers) if isinstance(providers, dict) else set()
    valid_targets = proxy_names | group_names | BUILTIN_TARGETS

    for group in groups:
        if not isinstance(group, dict):
            fail(errors, f"proxy-group entry is not a mapping: {group!r}")
            continue
        name = group.get("name", "<unnamed>")
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

    geo_rule = rule_index(rules, "RULE-SET,geolocation-!cn,")
    cn_rule = rule_index(rules, "RULE-SET,cn_domain,")
    if geo_rule is not None and cn_rule is not None and geo_rule > cn_rule:
        fail(errors, "geolocation-!cn must appear before cn_domain in routing rules")

    github_rule = rule_index(rules, "RULE-SET,github_domain,")
    microsoft_rule = rule_index(rules, "RULE-SET,microsoft_domain,")
    if github_rule is not None and microsoft_rule is not None and github_rule > microsoft_rule:
        fail(errors, "github_domain must appear before microsoft_domain because microsoft includes github")

    if not rules or not isinstance(rules[-1], str) or not rules[-1].startswith("MATCH,"):
        fail(errors, "routing rules must end with MATCH")

    if rule_index(rules, "RULE-SET,openai_domain,🤖 ChatGPT") is None:
        fail(errors, "ChatGPT group must use the dedicated openai_domain rule-provider")

    apns_rule = rule_index(rules, "DOMAIN-SUFFIX,push.apple.com,🍎 Apple")
    apple_rule = rule_index(rules, "RULE-SET,apple_domain,🍎 Apple")
    if apns_rule is None:
        fail(errors, "Apple APNs must have an explicit push.apple.com rule")
    elif apple_rule is not None and apns_rule > apple_rule:
        fail(errors, "Apple APNs rule must appear before the broader apple_domain rule")

    if not fake_filter or fake_filter[-1] != "MATCH,fake-ip":
        fail(errors, "fake-ip-filter must end with MATCH,fake-ip")

    missing_real_ip = REQUIRED_REAL_IP_FILTERS - {item for item in fake_filter if isinstance(item, str)}
    for item in sorted(missing_real_ip):
        fail(errors, f"missing required Real-IP compatibility rule: {item}")

    if "RULE-SET,cn_domain,real-ip" in fake_filter:
        fail(errors, "cn_domain must not be globally forced to Real-IP")

    proxy_providers = data.get("proxy-providers") or {}
    if isinstance(proxy_providers, dict):
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
