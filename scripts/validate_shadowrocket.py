from __future__ import annotations

import argparse
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "shadowrocket/shadowrocket.conf"
PROJECT_RAW = "https://raw.githubusercontent.com/steveyu8749/proxy-routing-config/main"
BLACKMATRIX_RAW = (
    "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/"
    "master/rule/Shadowrocket"
)

DEFAULT_PROXY = "🚀 默认代理"
FALLBACK_GROUP = "🐟 漏网之鱼"
APPLE_GROUP = "🍎 Apple"
SERVICE_GROUPS = {
    FALLBACK_GROUP,
    "🤖 ChatGPT",
    "📹 YouTube",
    "🍀 Google",
    "👨🏿‍💻 GitHub",
    "🐬 OneDrive",
    "🪟 Microsoft",
    "🎵 TikTok",
    "📲 Telegram",
    "🎥 NETFLIX",
    "✈️ Speedtest",
    "💶 PayPal",
}

EXPECTED_RULES = [
    f"RULE-SET,{BLACKMATRIX_RAW}/Lan/Lan.list,DIRECT",
    f"RULE-SET,{BLACKMATRIX_RAW}/OpenAI/OpenAI.list,🤖 ChatGPT",
    f"RULE-SET,{BLACKMATRIX_RAW}/Claude/Claude.list,🤖 ChatGPT",
    f"RULE-SET,{BLACKMATRIX_RAW}/Gemini/Gemini.list,🤖 ChatGPT",
    f"RULE-SET,{BLACKMATRIX_RAW}/Copilot/Copilot.list,🤖 ChatGPT",
    f"RULE-SET,{BLACKMATRIX_RAW}/OneDrive/OneDrive.list,🐬 OneDrive",
    f"RULE-SET,{BLACKMATRIX_RAW}/GitHub/GitHub.list,👨🏿‍💻 GitHub",
    f"RULE-SET,{BLACKMATRIX_RAW}/Bing/Bing.list,🪟 Microsoft",
    f"RULE-SET,{BLACKMATRIX_RAW}/Xbox/Xbox.list,🪟 Microsoft",
    f"RULE-SET,{BLACKMATRIX_RAW}/Microsoft/Microsoft.list,🪟 Microsoft",
    f"RULE-SET,{BLACKMATRIX_RAW}/YouTube/YouTube.list,📹 YouTube",
    f"RULE-SET,{BLACKMATRIX_RAW}/Google/Google.list,🍀 Google",
    f"RULE-SET,{BLACKMATRIX_RAW}/Apple/Apple.list,🍎 Apple",
    f"RULE-SET,{BLACKMATRIX_RAW}/TikTok/TikTok.list,🎵 TikTok",
    f"RULE-SET,{BLACKMATRIX_RAW}/Speedtest/Speedtest.list,✈️ Speedtest",
    f"RULE-SET,{BLACKMATRIX_RAW}/Telegram/Telegram.list,📲 Telegram",
    f"RULE-SET,{BLACKMATRIX_RAW}/Netflix/Netflix.list,🎥 NETFLIX",
    f"RULE-SET,{BLACKMATRIX_RAW}/PayPal/PayPal.list,💶 PayPal",
    f"RULE-SET,{PROJECT_RAW}/shadowrocket/rules/Direct.list,DIRECT",
    f"RULE-SET,{PROJECT_RAW}/shadowrocket/rules/ProxyLite.list,{DEFAULT_PROXY}",
    f"RULE-SET,{PROJECT_RAW}/shadowrocket/rules/ProxyIP.list,{DEFAULT_PROXY}",
    f"RULE-SET,{BLACKMATRIX_RAW}/Global/Global.list,{DEFAULT_PROXY}",
    f"RULE-SET,{BLACKMATRIX_RAW}/China/China.list,DIRECT",
    "GEOIP,CN,DIRECT",
    f"FINAL,{FALLBACK_GROUP}",
]


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def parse_config(raw: str, errors: list[str]) -> dict[str, list[tuple[int, str]]]:
    sections: dict[str, list[tuple[int, str]]] = {}
    current: str | None = None
    for line_number, raw_line in enumerate(raw.splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith(("#", ";")):
            continue
        if line.startswith("[") and line.endswith("]"):
            name = line[1:-1].strip()
            if not name:
                fail(errors, f"line {line_number}: empty section name")
                current = None
            elif name in sections:
                fail(errors, f"line {line_number}: duplicate section [{name}]")
                current = name
            else:
                current = name
                sections[name] = []
            continue
        if current is None:
            fail(errors, f"line {line_number}: active content appears outside a section")
            continue
        sections[current].append((line_number, line))
    return sections


def parse_assignments(
    lines: list[tuple[int, str]], section: str, errors: list[str]
) -> dict[str, str]:
    result: dict[str, str] = {}
    for line_number, line in lines:
        if "=" not in line:
            fail(errors, f"line {line_number}: [{section}] entry must use key = value")
            continue
        key, value = (part.strip() for part in line.split("=", 1))
        if not key or not value:
            fail(errors, f"line {line_number}: [{section}] has an empty key or value")
            continue
        if key in result:
            fail(errors, f"line {line_number}: duplicate [{section}] key {key!r}")
            continue
        result[key] = value
    return result


def csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def fakeip_source_rules(errors: list[str]) -> list[str]:
    path = ROOT / "rules/FakeIPFilter.list"
    if not path.is_file():
        fail(errors, "shared Fake-IP source is missing: rules/FakeIPFilter.list")
        return []
    result: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        result.append(f"*.{line[2:]}" if line.startswith("+.") else line)
    return result


def validate_general(values: dict[str, str], errors: list[str]) -> None:
    expected_keys = {
        "ipv6",
        "dns-server",
        "direct-dns-server",
        "fallback-dns-server",
        "private-ip-answer",
        "icmp-auto-reply",
        "always-real-ip",
        "hijack-dns",
        "update-url",
    }
    for key in sorted(expected_keys - set(values)):
        fail(errors, f"[General] is missing required key: {key}")
    for key in sorted(set(values) - expected_keys):
        fail(errors, f"[General] contains an unaudited key: {key}")

    expected_scalars = {
        "ipv6": "false",
        "direct-dns-server": "system",
        "fallback-dns-server": "system",
        "private-ip-answer": "true",
        "icmp-auto-reply": "true",
        "update-url": f"{PROJECT_RAW}/shadowrocket/shadowrocket.conf",
    }
    for key, expected in expected_scalars.items():
        if values.get(key) != expected:
            fail(errors, f"[General] {key} must be {expected!r}")

    if csv(values.get("dns-server", "")) != [
        "https://dns.alidns.com/dns-query",
        "https://doh.pub/dns-query",
    ]:
        fail(errors, "[General] dns-server does not match the audited domestic DoH design")
    if csv(values.get("hijack-dns", "")) != ["8.8.8.8:53", "8.8.4.4:53"]:
        fail(errors, "[General] hijack-dns must cover the two hard-coded Google DNS endpoints")

    expected_real_ip = fakeip_source_rules(errors)
    actual_real_ip = csv(values.get("always-real-ip", ""))
    if actual_real_ip != expected_real_ip:
        fail(
            errors,
            "[General] always-real-ip must exactly mirror rules/FakeIPFilter.list",
        )


def validate_groups(values: dict[str, str], errors: list[str]) -> set[str]:
    expected_names = SERVICE_GROUPS | {DEFAULT_PROXY, APPLE_GROUP}
    for name in sorted(expected_names - set(values)):
        fail(errors, f"[Proxy Group] is missing required group: {name}")
    for name in sorted(set(values) - expected_names):
        fail(errors, f"[Proxy Group] contains an unexpected group: {name}")

    default = csv(values.get(DEFAULT_PROXY, ""))
    if default != ["select", "policy-regex-filter=.*"]:
        fail(
            errors,
            f"{DEFAULT_PROXY} must select all imported nodes without exposing DIRECT",
        )
    for name in SERVICE_GROUPS:
        if csv(values.get(name, "")) != ["select", DEFAULT_PROXY, "DIRECT"]:
            fail(errors, f"service group {name!r} must use [默认代理, DIRECT] in that order")
    if csv(values.get(APPLE_GROUP, "")) != ["select", "DIRECT", DEFAULT_PROXY]:
        fail(errors, "Apple group must default to DIRECT and retain default proxy")
    return expected_names | {"DIRECT", "REJECT"}


def validate_rules(lines: list[tuple[int, str]], targets: set[str], errors: list[str]) -> None:
    rules = [line for _, line in lines]
    if rules != EXPECTED_RULES:
        fail(errors, "[Rule] content or priority differs from the audited rule sequence")

    for line_number, rule in lines:
        lowered = rule.lower()
        if "process-name" in lowered:
            fail(errors, f"line {line_number}: iOS config must not contain process-name rules")
        if "adobe" in lowered:
            fail(errors, f"line {line_number}: iOS config must not contain Adobe rules")
        parts = [item.strip() for item in rule.split(",")]
        if parts[0] == "RULE-SET":
            if len(parts) != 3:
                fail(errors, f"line {line_number}: malformed RULE-SET rule")
                continue
            parsed = urlparse(parts[1])
            if parsed.scheme != "https" or parsed.netloc != "raw.githubusercontent.com":
                fail(errors, f"line {line_number}: RULE-SET URL must use GitHub raw HTTPS")
            target = parts[2]
        elif parts[0] == "GEOIP":
            if parts != ["GEOIP", "CN", "DIRECT"]:
                fail(errors, f"line {line_number}: malformed China GEOIP fallback")
                continue
            target = "DIRECT"
        elif parts[0] == "FINAL":
            if len(parts) != 2:
                fail(errors, f"line {line_number}: malformed FINAL rule")
                continue
            target = parts[1]
        else:
            fail(errors, f"line {line_number}: unsupported rule type {parts[0]!r}")
            continue
        if target not in targets:
            fail(errors, f"line {line_number}: rule references unknown target {target!r}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the maintained Shadowrocket configuration and its project invariants."
    )
    parser.add_argument("config", nargs="?", default=str(DEFAULT_CONFIG))
    args = parser.parse_args()
    path = Path(args.config)
    if not path.is_file():
        print(f"ERROR: config not found: {path}")
        return 2

    raw = path.read_text(encoding="utf-8")
    errors: list[str] = []
    sections = parse_config(raw, errors)
    expected_sections = {"General", "Proxy Group", "Rule", "Host"}
    for name in sorted(expected_sections - set(sections)):
        fail(errors, f"missing required section: [{name}]")
    for name in sorted(set(sections) - expected_sections):
        fail(errors, f"unexpected section (nodes and rewrites must stay separate): [{name}]")

    general = parse_assignments(sections.get("General", []), "General", errors)
    groups = parse_assignments(sections.get("Proxy Group", []), "Proxy Group", errors)
    hosts = parse_assignments(sections.get("Host", []), "Host", errors)
    validate_general(general, errors)
    valid_targets = validate_groups(groups, errors)
    validate_rules(sections.get("Rule", []), valid_targets, errors)
    if hosts != {"localhost": "127.0.0.1"}:
        fail(errors, "[Host] must contain only localhost = 127.0.0.1")

    if errors:
        print("Shadowrocket validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("Shadowrocket validation passed")
    print(f"  policy groups: {len(groups)} checked")
    print(f"  routing rules: {len(sections['Rule'])} checked")
    print("  Fake-IP exceptions: synchronized with rules/FakeIPFilter.list")
    print("  nodes/process/Adobe: intentionally absent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
