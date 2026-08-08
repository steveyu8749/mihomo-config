from __future__ import annotations

import argparse
import ipaddress
import re
from pathlib import Path
from typing import Any

import yaml
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode
from yaml.resolver import BaseResolver


TEMPLATE_VERSION = "V4.8"
PLACEHOLDER_UUID = "00000000-0000-4000-8000-000000000000"
DEFAULT_PROXY = "🚀 默认代理"
HARD_DIRECT = "直连"
FALLBACK_GROUP = "🐟 漏网之鱼"
APPLE_GROUP = "🍎 Apple"

EXPECTED_TOP_LEVEL_KEYS = {
    "allow-lan",
    "dns",
    "external-controller",
    "find-process-mode",
    "ipv6",
    "keep-alive-idle",
    "keep-alive-interval",
    "log-level",
    "mixed-port",
    "mode",
    "profile",
    "proxies",
    "proxy-groups",
    "proxy-providers",
    "redir-port",
    "rule-anchor",
    "rule-providers",
    "rules",
    "sniffer",
    "tcp-concurrent",
    "tproxy-port",
    "tun",
    "unified-delay",
}

EXPECTED_SERVICE_GROUPS = {
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

DOMAIN_PROVIDER_PATHS = {
    "private_domain": "private.mrs",
    "ai_domain": "category-ai-!cn.mrs",
    "youtube_domain": "youtube.mrs",
    "google_domain": "google.mrs",
    "github_domain": "github.mrs",
    "telegram_domain": "telegram.mrs",
    "netflix_domain": "netflix.mrs",
    "paypal_domain": "paypal.mrs",
    "onedrive_domain": "onedrive.mrs",
    "microsoft_domain": "microsoft.mrs",
    "apple_domain": "apple.mrs",
    "speedtest_domain": "ookla-speedtest.mrs",
    "tiktok_domain": "tiktok.mrs",
    "gfw_domain": "gfw.mrs",
    "geolocation-!cn": "geolocation-!cn.mrs",
    "cn_domain": "cn.mrs",
    "bing_domain": "bing.mrs",
    "msn_domain": "msn.mrs",
    "xbox_domain": "xbox.mrs",
}

IP_PROVIDER_PATHS = {
    "private_ip": "geo/geoip/private.mrs",
    "cn_ip": "geo/geoip/cn.mrs",
    "google_ip": "geo/geoip/google.mrs",
    "telegram_ip": "geo/geoip/telegram.mrs",
    "netflix_ip": "geo/geoip/netflix.mrs",
    "apple_ip": "geo-lite/geoip/apple.mrs",
}

CUSTOM_DOMAIN_PROVIDER_PATHS = {
    "direct_domain": "rules/Direct.list",
    "fakeip_compat": "rules/FakeIPFilter.list",
}

REQUIRED_FAKEIP_COMPAT = {
    "dns.msftncsi.com",
    "+.services.googleapis.cn",
    "+.xn--ngstr-lra8j.com",
    "+.push.apple.com",
    "+.market.xiaomi.com",
}

REQUIRED_DIRECT_DOMAINS = {
    "+.sciencedirect.com",
    "+.sciencedirectassets.com",
    "+.cell.com",
    "+.clinicalkey.com",
    "+.els-cdn.com",
    "+.elsevier-ae.com",
    "+.elsevier.com",
    "+.elsevier.io",
    "+.engineeringvillage.com",
    "+.evise.com",
    "+.fundinginstitutional.com",
    "+.knovel.com",
    "+.mendeley.com",
    "+.reaxys.com",
    "+.scival.com",
    "+.scopus.com",
    "+.clarivate.com",
    "+.isiknowledge.com",
    "+.newisiknowledge.com",
    "+.webofknowledge.com",
    "+.webofscience.com",
}

REQUIRED_RULES = {
    "RULE-SET,private_domain,直连",
    "RULE-SET,private_ip,直连,no-resolve",
    "PROCESS-NAME-REGEX,.*spotify.*,直连",
    "PROCESS-NAME,onedrive.exe,直连",
    "PROCESS-NAME-REGEX,.*xboxone.*,🪟 Microsoft",
    "PROCESS-NAME,com.microsoft.bing,🪟 Microsoft",
    "RULE-SET,ai_domain,🤖 ChatGPT",
    "RULE-SET,direct_domain,直连",
    "RULE-SET,bing_domain,🪟 Microsoft",
    "RULE-SET,msn_domain,🪟 Microsoft",
    "RULE-SET,xbox_domain,🪟 Microsoft",
    "RULE-SET,onedrive_domain,🐬 OneDrive",
    "RULE-SET,github_domain,👨🏿‍💻 GitHub",
    "RULE-SET,microsoft_domain,🪟 Microsoft",
    "RULE-SET,youtube_domain,📹 YouTube",
    "RULE-SET,google_domain,🍀 Google",
    "DOMAIN-SUFFIX,push.apple.com,🍎 Apple",
    "RULE-SET,apple_domain,🍎 Apple",
    "RULE-SET,tiktok_domain,🎵 TikTok",
    "RULE-SET,speedtest_domain,✈️ Speedtest",
    "RULE-SET,telegram_domain,📲 Telegram",
    "RULE-SET,netflix_domain,🎥 NETFLIX",
    "RULE-SET,paypal_domain,💶 PayPal",
    "RULE-SET,gfw_domain,🚀 默认代理",
    "RULE-SET,geolocation-!cn,🚀 默认代理",
    "RULE-SET,cn_domain,直连",
    "RULE-SET,apple_ip,🍎 Apple,no-resolve",
    "RULE-SET,google_ip,🍀 Google,no-resolve",
    "RULE-SET,netflix_ip,🎥 NETFLIX,no-resolve",
    "RULE-SET,telegram_ip,📲 Telegram,no-resolve",
    "RULE-SET,cn_ip,直连",
    "MATCH,🐟 漏网之鱼",
}

RULE_ORDER = [
    ("RULE-SET,bing_domain,", "RULE-SET,microsoft_domain,", "bing_domain must appear before microsoft_domain"),
    ("RULE-SET,msn_domain,", "RULE-SET,microsoft_domain,", "msn_domain must appear before microsoft_domain"),
    ("RULE-SET,xbox_domain,", "RULE-SET,microsoft_domain,", "xbox_domain must appear before microsoft_domain"),
    ("RULE-SET,onedrive_domain,", "RULE-SET,microsoft_domain,", "onedrive_domain must appear before microsoft_domain"),
    ("RULE-SET,github_domain,", "RULE-SET,microsoft_domain,", "github_domain must appear before microsoft_domain"),
    ("RULE-SET,youtube_domain,", "RULE-SET,google_domain,", "youtube_domain must appear before google_domain"),
    ("DOMAIN-SUFFIX,push.apple.com,", "RULE-SET,apple_domain,", "push.apple.com must appear before apple_domain"),
    ("RULE-SET,geolocation-!cn,", "RULE-SET,cn_domain,", "geolocation-!cn must appear before cn_domain"),
]

SPECIAL_RULES_BEFORE_PROXYLITE = [
    "RULE-SET,ai_domain,",
    "RULE-SET,bing_domain,",
    "RULE-SET,msn_domain,",
    "RULE-SET,xbox_domain,",
    "RULE-SET,onedrive_domain,",
    "RULE-SET,github_domain,",
    "RULE-SET,microsoft_domain,",
    "RULE-SET,youtube_domain,",
    "RULE-SET,google_domain,",
    "DOMAIN-SUFFIX,push.apple.com,",
    "RULE-SET,apple_domain,",
    "RULE-SET,tiktok_domain,",
    "RULE-SET,speedtest_domain,",
    "RULE-SET,telegram_domain,",
    "RULE-SET,netflix_domain,",
    "RULE-SET,paypal_domain,",
    "RULE-SET,direct_domain,",
]

DEDICATED_RULES_BEFORE_DIRECT = [
    prefix
    for prefix in SPECIAL_RULES_BEFORE_PROXYLITE
    if prefix != "RULE-SET,direct_domain,"
]

GEODATA_KEYS = {
    "geodata-mode",
    "geodata-loader",
    "geo-auto-update",
    "geo-update-interval",
    "geox-url",
}

BUILTIN_TARGETS = {
    "COMPATIBLE",
    "DIRECT",
    "PASS",
    "REJECT",
    "REJECT-DROP",
}


class UniqueKeyLoader(yaml.SafeLoader):
    """SafeLoader that rejects duplicate literal keys while preserving YAML merges."""


def construct_unique_mapping(
    loader: UniqueKeyLoader, node: MappingNode, deep: bool = False
) -> dict[Any, Any]:
    seen: set[Any] = set()
    for key_node, _ in node.value:
        if key_node.tag == "tag:yaml.org,2002:merge":
            continue
        key = loader.construct_object(key_node, deep=False)
        try:
            duplicate = key in seen
        except TypeError as exc:
            raise ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "found an unhashable mapping key",
                key_node.start_mark,
            ) from exc
        if duplicate:
            raise ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark,
            )
        seen.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


UniqueKeyLoader.add_constructor(
    BaseResolver.DEFAULT_MAPPING_TAG, construct_unique_mapping
)


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


def has_unquoted_comment(line: str) -> bool:
    quote: str | None = None
    escaped = False
    for char in line:
        if quote == '"':
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif quote == "'":
            if char == quote:
                quote = None
        elif char in {"'", '"'}:
            quote = char
        elif char == "#":
            return True
    return False


def validate_comment_coverage(raw: str, errors: list[str]) -> None:
    missing: list[int] = []
    for line_number, line in enumerate(raw.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not has_unquoted_comment(line):
            missing.append(line_number)
    if missing:
        fail(
            errors,
            "active config lines missing explanatory comments: "
            + ", ".join(str(item) for item in missing),
        )


def validate_named_items(
    items: list[Any], section: str, errors: list[str]
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            fail(errors, f"{section}[{index}] must be a mapping")
            continue
        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            fail(errors, f"{section}[{index}] must have a non-empty string name")
            continue
        if name in result:
            fail(errors, f"duplicate {section} name: {name!r}")
            continue
        result[name] = item
    return result


def expected_rule_provider_url(name: str) -> str:
    if name in DOMAIN_PROVIDER_PATHS:
        return (
            "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/"
            f"meta/geo/geosite/{DOMAIN_PROVIDER_PATHS[name]}"
        )
    path = IP_PROVIDER_PATHS[name]
    return (
        "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/"
        f"meta/{path}"
    )


def expected_custom_provider_url(path: str) -> str:
    return f"https://raw.githubusercontent.com/steveyu8749/mihomo-config/main/{path}"


def validate_provider_shape(
    name: str,
    provider: dict[str, Any],
    behavior: str,
    expected_url: str,
    errors: list[str],
) -> None:
    expected = {
        "type": "http",
        "interval": 86400,
        "behavior": behavior,
        "format": "mrs",
    }
    for key, value in expected.items():
        if provider.get(key) != value:
            fail(errors, f"rule-provider {name!r} must use {key}: {value!r}")
    if provider.get("url") != expected_url:
        fail(errors, f"rule-provider {name!r} URL does not match its audited MRS source")
    if "proxy" in provider:
        fail(errors, f"rule-provider {name!r} must not force a fixed download proxy")


def validate_rule_providers(
    providers: dict[str, Any], raw: str, errors: list[str]
) -> None:
    for name in DOMAIN_PROVIDER_PATHS:
        provider = providers.get(name)
        if not isinstance(provider, dict):
            fail(errors, f"missing domain MRS rule-provider: {name}")
            continue
        validate_provider_shape(
            name, provider, "domain", expected_rule_provider_url(name), errors
        )

    for name in IP_PROVIDER_PATHS:
        provider = providers.get(name)
        if not isinstance(provider, dict):
            fail(errors, f"missing IP MRS rule-provider: {name}")
            continue
        validate_provider_shape(
            name, provider, "ipcidr", expected_rule_provider_url(name), errors
        )

    for name, path in CUSTOM_DOMAIN_PROVIDER_PATHS.items():
        provider = providers.get(name)
        if not isinstance(provider, dict):
            fail(errors, f"missing maintained domain text rule-provider: {name}")
            continue
        expected = {
            "type": "http",
            "interval": 86400,
            "behavior": "domain",
            "format": "text",
            "url": expected_custom_provider_url(path),
        }
        for key, value in expected.items():
            if provider.get(key) != value:
                fail(errors, f"rule-provider {name!r} must use {key}: {value!r}")
        if "proxy" in provider:
            fail(errors, f"rule-provider {name!r} must not force a fixed download proxy")

    proxylite = providers.get("proxylite")
    if proxylite is not None:
        if not isinstance(proxylite, dict):
            fail(errors, "proxylite rule-provider must be a mapping")
        else:
            expected = {
                "type": "http",
                "interval": 86400,
                "behavior": "classical",
                "format": "text",
            }
            for key, value in expected.items():
                if proxylite.get(key) != value:
                    fail(errors, f"proxylite must use {key}: {value!r}")
            if not is_placeholder_url(str(proxylite.get("url", ""))):
                fail(errors, "proxylite URL must remain a sanitized placeholder in the public template")
            if "proxy" in proxylite:
                fail(errors, "proxylite must not force a fixed download proxy")

    if "adobeisdumb" in providers:
        fail(errors, "Adobe provider must remain disabled in the shared mobile/desktop template")

    adobe_comment_patterns = {
        "Adobe routing rule": r"(?m)^\s*#\s*-\s*RULE-SET,adobeisdumb,REJECT",
        "Adobe YAML anchor": r"(?m)^\s*#\s*yaml:\s*&yaml\b",
        "Adobe provider": r"(?m)^\s*#\s*adobeisdumb:\s*\{<<:\s*\*yaml,",
    }
    for label, pattern in adobe_comment_patterns.items():
        if re.search(pattern, raw) is None:
            fail(errors, f"missing commented desktop-only activation point: {label}")


def read_domain_text_rules(path: Path, label: str, errors: list[str]) -> list[str]:
    if not path.is_file():
        fail(errors, f"repository rule file missing: {path.as_posix()}")
        return []

    rules: list[str] = []
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), 1
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line != line.lower():
            fail(errors, f"{label}:{line_number} domain rule must be lowercase: {line!r}")
        if any(character.isspace() for character in line) or "," in line or "://" in line:
            fail(errors, f"{label}:{line_number} is not a domain behavior text rule: {line!r}")
            continue
        domain = line[2:] if line.startswith(("+.", "*.")) else line
        if (
            not domain
            or domain.startswith(".")
            or domain.endswith(".")
            or ".." in domain
            or re.fullmatch(r"[a-z0-9*_-]+(?:\.[a-z0-9*_-]+)+", domain) is None
        ):
            fail(errors, f"{label}:{line_number} has an invalid domain pattern: {line!r}")
            continue
        rules.append(line)

    duplicates = sorted({rule for rule in rules if rules.count(rule) > 1})
    if duplicates:
        fail(errors, f"{label} contains duplicate domain rules: {', '.join(duplicates)}")
    return rules


def validate_maintained_rule_files(root: Path, errors: list[str]) -> None:
    direct_path = root / CUSTOM_DOMAIN_PROVIDER_PATHS["direct_domain"]
    fakeip_path = root / CUSTOM_DOMAIN_PROVIDER_PATHS["fakeip_compat"]
    direct_rules = read_domain_text_rules(direct_path, "rules/Direct.list", errors)
    fakeip_rules = read_domain_text_rules(fakeip_path, "rules/FakeIPFilter.list", errors)

    missing_direct = REQUIRED_DIRECT_DOMAINS - set(direct_rules)
    if missing_direct:
        fail(
            errors,
            "rules/Direct.list is missing audited research domains: "
            + ", ".join(sorted(missing_direct)),
        )

    if set(fakeip_rules) != REQUIRED_FAKEIP_COMPAT or len(fakeip_rules) != len(
        REQUIRED_FAKEIP_COMPAT
    ):
        fail(
            errors,
            "rules/FakeIPFilter.list must contain exactly the five audited compatibility entries",
        )


def validate_proxy_providers(
    proxy_providers: dict[str, Any], errors: list[str]
) -> None:
    if not proxy_providers:
        fail(errors, "at least one proxy-provider is required")
        return
    for name, provider in proxy_providers.items():
        if not isinstance(name, str) or not name:
            fail(errors, "proxy-provider names must be non-empty strings")
            continue
        if not isinstance(provider, dict):
            fail(errors, f"proxy-provider {name!r} must be a mapping")
            continue
        if provider.get("type") != "http":
            fail(errors, f"proxy-provider {name!r} must use type:http")
        if provider.get("interval") != 18000:
            fail(errors, f"proxy-provider {name!r} must refresh every 18000 seconds")
        if provider.get("proxy") != HARD_DIRECT:
            fail(errors, f"proxy-provider {name!r} must bootstrap through hard DIRECT")
        if not is_placeholder_url(str(provider.get("url", ""))):
            fail(errors, f"proxy-provider {name!r} URL looks live instead of sanitized")
        health = provider.get("health-check")
        if not isinstance(health, dict):
            fail(errors, f"proxy-provider {name!r} must define health-check")
            continue
        if health.get("enable") is not True:
            fail(errors, f"proxy-provider {name!r} health-check must be enabled")
        if health.get("interval") != 600:
            fail(errors, f"proxy-provider {name!r} health-check interval must be 600 seconds")
        if health.get("url") != "https://www.gstatic.com/generate_204":
            fail(errors, f"proxy-provider {name!r} uses an unexpected health-check URL")


def validate_groups(
    groups: list[Any], proxies: list[Any], errors: list[str]
) -> tuple[dict[str, dict[str, Any]], set[str]]:
    groups_by_name = validate_named_items(groups, "proxy-groups", errors)
    proxies_by_name = validate_named_items(proxies, "proxies", errors)

    collisions = set(groups_by_name) & set(proxies_by_name)
    for name in sorted(collisions):
        fail(errors, f"proxy and proxy-group names must not collide: {name!r}")

    direct_proxy = proxies_by_name.get(HARD_DIRECT)
    if direct_proxy != {"name": HARD_DIRECT, "type": "direct"}:
        fail(errors, "the only manual proxy must be {name: 直连, type: direct}")
    if set(proxies_by_name) != {HARD_DIRECT}:
        fail(errors, "public template must keep only the sanitized hard DIRECT manual proxy")

    expected_group_names = EXPECTED_SERVICE_GROUPS | {DEFAULT_PROXY, APPLE_GROUP}
    missing = expected_group_names - set(groups_by_name)
    extra = set(groups_by_name) - expected_group_names
    for name in sorted(missing):
        fail(errors, f"missing required proxy-group: {name}")
    for name in sorted(extra):
        fail(errors, f"unexpected proxy-group in the maintained template: {name}")

    default_group = groups_by_name.get(DEFAULT_PROXY)
    if isinstance(default_group, dict):
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

    for name, group in groups_by_name.items():
        if group.get("type") in {"fallback", "url-test", "load-balance"}:
            fail(errors, f"proxy-group {name!r} reintroduces removed automatic selection")
        if name != DEFAULT_PROXY and group.get("include-all") is True:
            fail(errors, f"only {DEFAULT_PROXY} may use include-all: true")
        if name in EXPECTED_SERVICE_GROUPS and group.get("proxies") != [DEFAULT_PROXY, HARD_DIRECT]:
            fail(errors, f"service group {name!r} must contain [默认代理, 直连] in that order")
        if name == APPLE_GROUP and group.get("proxies") != [HARD_DIRECT, DEFAULT_PROXY]:
            fail(errors, "Apple group must default to hard DIRECT and retain default proxy as fallback")

    valid_references = set(groups_by_name) | set(proxies_by_name) | BUILTIN_TARGETS
    for name, group in groups_by_name.items():
        references = group.get("proxies") or []
        if not isinstance(references, list):
            fail(errors, f"proxy-group {name!r}.proxies must be a list")
            continue
        for reference in references:
            if not isinstance(reference, str) or reference not in valid_references:
                fail(errors, f"proxy-group {name!r} references unknown proxy/group: {reference!r}")

    return groups_by_name, valid_references


def validate_rules(
    rules: list[Any],
    providers: dict[str, Any],
    valid_targets: set[str],
    errors: list[str],
) -> set[str]:
    rule_strings = [item for item in rules if isinstance(item, str)]
    if len(rule_strings) != len(rules):
        fail(errors, "every routing rule must be a string")

    for rule in sorted(REQUIRED_RULES - set(rule_strings)):
        fail(errors, f"missing required routing rule: {rule}")

    if rules[:2] != [
        "RULE-SET,private_domain,直连",
        "RULE-SET,private_ip,直连,no-resolve",
    ]:
        fail(errors, "private_domain and private_ip must remain the first two routing rules")
    if not rules or rules[-1] != "MATCH,🐟 漏网之鱼":
        fail(errors, "routing rules must end with MATCH,🐟 漏网之鱼")
    if sum(1 for rule in rule_strings if rule.startswith("MATCH,")) != 1:
        fail(errors, "routing rules must contain exactly one MATCH rule")

    referenced_providers: set[str] = set()
    first_business_rule = find_rule(rules, "RULE-SET,ai_domain,")

    for index, rule in enumerate(rule_strings):
        parts = rule.split(",")
        rule_type = parts[0]
        target: str | None = None

        if rule_type == "RULE-SET":
            if len(parts) not in {3, 4}:
                fail(errors, f"malformed RULE-SET rule at index {index}: {rule}")
                continue
            provider_name = parts[1]
            target = parts[2]
            options = parts[3:]
            provider = providers.get(provider_name)
            if not isinstance(provider, dict):
                fail(errors, f"rule references missing provider {provider_name!r}: {rule}")
                continue
            referenced_providers.add(provider_name)
            behavior = provider.get("behavior")
            if options and options != ["no-resolve"]:
                fail(errors, f"unsupported RULE-SET option in: {rule}")
            if options == ["no-resolve"] and behavior != "ipcidr":
                fail(errors, f"no-resolve is only valid for IP rules in this template: {rule}")
            if behavior == "ipcidr" and provider_name != "cn_ip" and options != ["no-resolve"]:
                fail(errors, f"IP fallback {provider_name!r} must use no-resolve")
            if provider_name == "cn_ip" and options:
                fail(errors, "cn_ip intentionally retains resolution and must not use no-resolve")
        elif rule_type in {"PROCESS-NAME", "DOMAIN-SUFFIX"}:
            if len(parts) != 3 or not parts[1]:
                fail(errors, f"malformed {rule_type} rule at index {index}: {rule}")
                continue
            target = parts[2]
        elif rule_type == "PROCESS-NAME-REGEX":
            if len(parts) != 3 or not parts[1]:
                fail(errors, f"malformed PROCESS-NAME-REGEX rule at index {index}: {rule}")
                continue
            try:
                re.compile(parts[1], re.IGNORECASE)
            except re.error as exc:
                fail(errors, f"invalid process regex {parts[1]!r}: {exc}")
            target = parts[2]
        elif rule_type == "MATCH":
            if len(parts) != 2:
                fail(errors, f"malformed MATCH rule at index {index}: {rule}")
                continue
            target = parts[1]
        else:
            fail(errors, f"unexpected rule type {rule_type!r} in maintained template")

        if target is not None and target not in valid_targets:
            fail(errors, f"routing rule references unknown target {target!r}: {rule}")

        if rule_type.startswith("PROCESS-") and first_business_rule is not None and index > first_business_rule:
            fail(errors, f"process rule must remain before business domain rules: {rule}")

    for first, second, message in RULE_ORDER:
        first_index = find_rule(rules, first)
        second_index = find_rule(rules, second)
        if first_index is not None and second_index is not None and first_index > second_index:
            fail(errors, message)

    proxylite_index = find_rule(rules, "RULE-SET,proxylite,")
    if ("proxylite" in providers) != (proxylite_index is not None):
        fail(errors, "proxylite routing rule and provider must be enabled or removed together")
    if proxylite_index is not None:
        for prefix in SPECIAL_RULES_BEFORE_PROXYLITE:
            special_index = find_rule(rules, prefix)
            if special_index is not None and special_index > proxylite_index:
                fail(errors, f"specific service rule {prefix!r} must appear before proxylite")
        for prefix in ("RULE-SET,gfw_domain,", "RULE-SET,geolocation-!cn,", "RULE-SET,cn_domain,"):
            broad_index = find_rule(rules, prefix)
            if broad_index is not None and proxylite_index > broad_index:
                fail(errors, f"proxylite must appear before broad rule {prefix!r}")

    direct_index = find_rule(rules, "RULE-SET,direct_domain,")
    if direct_index is not None:
        for prefix in DEDICATED_RULES_BEFORE_DIRECT:
            dedicated_index = find_rule(rules, prefix)
            if dedicated_index is not None and dedicated_index > direct_index:
                fail(errors, f"dedicated service rule {prefix!r} must appear before direct_domain")

    cn_domain_index = find_rule(rules, "RULE-SET,cn_domain,")
    apple_ip_index = find_rule(rules, "RULE-SET,apple_ip,")
    cn_ip_index = find_rule(rules, "RULE-SET,cn_ip,")
    if cn_domain_index is not None and apple_ip_index is not None and cn_domain_index > apple_ip_index:
        fail(errors, "domain rules must finish before service IP fallback rules")
    for prefix in (
        "RULE-SET,apple_ip,",
        "RULE-SET,google_ip,",
        "RULE-SET,netflix_ip,",
        "RULE-SET,telegram_ip,",
    ):
        index = find_rule(rules, prefix)
        if index is not None and cn_ip_index is not None and index > cn_ip_index:
            fail(errors, f"service IP fallback {prefix!r} must appear before cn_ip")

    return referenced_providers


def validate_dns(
    dns: dict[str, Any], providers: dict[str, Any], errors: list[str]
) -> set[str]:
    expected_scalars = {
        "enable": True,
        "ipv6": False,
        "enhanced-mode": "fake-ip",
        "fake-ip-range": "198.18.0.1/16",
        "fake-ip-filter-mode": "rule",
    }
    for key, value in expected_scalars.items():
        if dns.get(key) != value:
            fail(errors, f"dns.{key} must be {value!r}")

    expected_lists = {
        "default-nameserver": ["223.5.5.5", "119.29.29.29"],
        "nameserver": [
            "https://dns.alidns.com/dns-query",
            "https://doh.pub/dns-query",
        ],
        "direct-nameserver": ["system"],
        "fake-ip-filter": [
            "RULE-SET,private_domain,real-ip",
            "RULE-SET,fakeip_compat,real-ip",
            "MATCH,fake-ip",
        ],
    }
    for key, value in expected_lists.items():
        if dns.get(key) != value:
            fail(errors, f"dns.{key} does not match the audited {TEMPLATE_VERSION} design")

    if dns.get("respect-rules") is True:
        fail(errors, "respect-rules must remain disabled for the direct domestic DoH design")
    if "cache-algorithm" in dns and dns.get("cache-algorithm") not in {"lru", "arc"}:
        fail(errors, "dns.cache-algorithm, when set, must be lru or arc")

    referenced: set[str] = set()
    fake_filter = dns.get("fake-ip-filter")
    if isinstance(fake_filter, list):
        for rule in fake_filter:
            if not isinstance(rule, str) or not rule.startswith("RULE-SET,"):
                continue
            parts = rule.split(",")
            if len(parts) != 3:
                fail(errors, f"malformed DNS Fake-IP rule: {rule!r}")
                continue
            provider_name = parts[1]
            referenced.add(provider_name)
            if provider_name not in providers:
                fail(errors, f"DNS Fake-IP rule references missing provider: {provider_name}")
    return referenced


def validate_sniffer(sniffer: dict[str, Any], errors: list[str]) -> None:
    if sniffer.get("enable") is not True:
        fail(errors, "sniffer must remain enabled")
    if sniffer.get("parse-pure-ip") is not True:
        fail(errors, "sniffer.parse-pure-ip must remain enabled")
    if sniffer.get("override-destination") is not False:
        fail(errors, "sniffer.override-destination must remain false")
    if sniffer.get("skip-domain"):
        fail(errors, "sniffer.skip-domain must remain empty unless a reproducible exception is documented")
    if sniffer.get("force-dns-mapping") is True:
        fail(errors, "force-dns-mapping is unnecessary in this Fake-IP-first design")

    sniff = require_mapping(sniffer.get("sniff"), "sniffer.sniff", errors)
    expected_ports = {
        "HTTP": [80, "8080-8880"],
        "TLS": [443, 8443],
        "QUIC": [443, 8443],
    }
    if set(sniff) != set(expected_ports):
        fail(errors, "sniffer.sniff must contain exactly HTTP, TLS and QUIC")
    for protocol, ports in expected_ports.items():
        config = sniff.get(protocol)
        if not isinstance(config, dict):
            fail(errors, f"sniffer protocol {protocol} must be a mapping")
            continue
        if config.get("ports") != ports:
            fail(errors, f"sniffer protocol {protocol} has unexpected ports")
        if config.get("override-destination") is True:
            fail(errors, f"sniffer protocol {protocol} must not override destination")


def validate_tun(tun: dict[str, Any], errors: list[str]) -> None:
    expected = {
        "enable": True,
        "stack": "mixed",
        "auto-route": True,
        "auto-detect-interface": True,
    }
    for key, value in expected.items():
        if tun.get(key) != value:
            fail(errors, f"tun.{key} must be {value!r}")
    hijack = tun.get("dns-hijack")
    if not isinstance(hijack, list) or set(hijack) != {"any:53", "tcp://any:53"}:
        fail(errors, "tun.dns-hijack must cover both UDP and TCP port 53")
    required_excludes = {
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "169.254.0.0/16",
        "224.0.0.0/4",
        "255.255.255.255/32",
    }
    excludes = tun.get("route-exclude-address")
    if not isinstance(excludes, list):
        fail(errors, "tun.route-exclude-address must be a list")
    else:
        missing = required_excludes - set(str(item) for item in excludes)
        for item in sorted(missing):
            fail(errors, f"tun.route-exclude-address missing required local range: {item}")


def validate_general(data: dict[str, Any], errors: list[str]) -> None:
    if set(data) != EXPECTED_TOP_LEVEL_KEYS:
        for key in sorted(EXPECTED_TOP_LEVEL_KEYS - set(data)):
            fail(errors, f"missing maintained top-level key: {key}")
        for key in sorted(set(data) - EXPECTED_TOP_LEVEL_KEYS):
            fail(errors, f"unexpected top-level key (possible typo): {key}")

    expected = {
        "mode": "rule",
        "allow-lan": False,
        "ipv6": False,
        "unified-delay": True,
        "tcp-concurrent": True,
        "log-level": "warning",
        "keep-alive-idle": 600,
        "keep-alive-interval": 15,
        "find-process-mode": "strict",
        "external-controller": "127.0.0.1:9090",
    }
    for key, value in expected.items():
        if data.get(key) != value:
            fail(errors, f"top-level {key} must be {value!r}")

    ports: list[int] = []
    for key in ("mixed-port", "redir-port", "tproxy-port"):
        value = data.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 65535:
            fail(errors, f"{key} must be an integer TCP/UDP port")
        else:
            ports.append(value)
    if len(ports) != len(set(ports)):
        fail(errors, "mixed-port, redir-port and tproxy-port must be distinct")

    profile = require_mapping(data.get("profile"), "profile", errors)
    if profile != {"store-selected": True, "store-fake-ip": True}:
        fail(errors, "profile must persist both selected groups and Fake-IP mappings")

    for key in sorted(GEODATA_KEYS):
        if key in data:
            fail(errors, f"{key} must not be configured in the MRS-only template")


def validate_public_secrets(
    raw: str, proxies: list[Any], errors: list[str]
) -> None:
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

    for match in re.finditer(
        r"(?i)(?:token|auth|api[_-]?key|secret)=([A-Za-z0-9_.-]{12,})", raw
    ):
        value = match.group(1)
        if not value.upper().startswith("YOUR_"):
            fail(errors, "found a query-string credential that does not look like a placeholder")

    uuid_pattern = r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
    for value in re.findall(uuid_pattern, raw):
        if value.lower() != PLACEHOLDER_UUID:
            fail(errors, "found a UUID that does not match the public placeholder UUID")


def validate_repository_docs(config_path: Path, errors: list[str]) -> None:
    root = config_path.resolve().parent
    required_files = {
        "README.md": root / "README.md",
        "CHANGELOG.md": root / "CHANGELOG.md",
        "docs/design-notes.md": root / "docs/design-notes.md",
        ".github/workflows/validate.yml": root / ".github/workflows/validate.yml",
        "rules/Direct.list": root / "rules/Direct.list",
        "rules/FakeIPFilter.list": root / "rules/FakeIPFilter.list",
    }
    if not (root / "README.md").is_file():
        return
    for label, path in required_files.items():
        if not path.is_file():
            fail(errors, f"repository file missing: {label}")
            return

    readme = required_files["README.md"].read_text(encoding="utf-8")
    changelog = required_files["CHANGELOG.md"].read_text(encoding="utf-8")
    design = required_files["docs/design-notes.md"].read_text(encoding="utf-8")
    workflow = required_files[".github/workflows/validate.yml"].read_text(encoding="utf-8")

    validate_maintained_rule_files(root, errors)

    if TEMPLATE_VERSION not in readme:
        fail(errors, f"README must identify the current template as {TEMPLATE_VERSION}")
    if TEMPLATE_VERSION not in design:
        fail(errors, f"design notes must identify the current template as {TEMPLATE_VERSION}")
    if not changelog.startswith(f"# Changelog\n\n## {TEMPLATE_VERSION}\n"):
        fail(errors, f"CHANGELOG must begin with the current {TEMPLATE_VERSION} entry")

    required_readme_topics = {
        "198.18.0.0/15": "private_ip/Fake-IP overlap",
        "cache-algorithm": "DNS cache algorithm decision",
        "ProxyLite": "ProxyLite priority",
        "respect-rules": "DNS upstream routing",
        "Direct.list": "maintained direct-domain list",
        "FakeIPFilter.list": "maintained Fake-IP compatibility list",
    }
    for text, topic in required_readme_topics.items():
        if text not in readme:
            fail(errors, f"README is missing the {topic} explanation")

    version_match = re.search(r"(?m)^\s*MIHOMO_VERSION:\s*(v\d+\.\d+\.\d+)\s*$", workflow)
    if version_match is None:
        fail(errors, "workflow must pin MIHOMO_VERSION")
    elif version_match.group(1) not in readme:
        fail(errors, "README and workflow disagree about the pinned Mihomo version")
    if "PyYAML==6.0.3" not in workflow:
        fail(errors, "workflow must pin the PyYAML validator dependency")
    for changed_path in ("README.md", "CHANGELOG.md", "docs/design-notes.md", "rules/**"):
        if workflow.count(f'"{changed_path}"') < 2:
            fail(errors, f"workflow path filters must validate changes to {changed_path}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Check repository policy, references, comments and public-template hygiene. "
            "Mihomo remains the authoritative core syntax validator."
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
        loaded = yaml.load(raw, Loader=UniqueKeyLoader)
    except yaml.YAMLError as exc:
        print(f"ERROR: YAML parse failed: {exc}")
        return 1
    if not isinstance(loaded, dict):
        print("ERROR: YAML root must be a mapping")
        return 1

    data: dict[str, Any] = loaded
    errors: list[str] = []

    validate_comment_coverage(raw, errors)
    validate_general(data, errors)

    proxies = require_list(data.get("proxies"), "proxies", errors)
    groups = require_list(data.get("proxy-groups"), "proxy-groups", errors)
    providers = require_mapping(data.get("rule-providers"), "rule-providers", errors)
    proxy_providers = require_mapping(data.get("proxy-providers"), "proxy-providers", errors)
    rules = require_list(data.get("rules"), "rules", errors)
    dns = require_mapping(data.get("dns"), "dns", errors)
    sniffer = require_mapping(data.get("sniffer"), "sniffer", errors)
    tun = require_mapping(data.get("tun"), "tun", errors)
    anchors = require_mapping(data.get("rule-anchor"), "rule-anchor", errors)

    expected_anchor_shapes = {
        "ip": {"type": "http", "interval": 86400, "behavior": "ipcidr", "format": "mrs"},
        "domain": {"type": "http", "interval": 86400, "behavior": "domain", "format": "mrs"},
        "domaintxt": {"type": "http", "interval": 86400, "behavior": "domain", "format": "text"},
        "class": {"type": "http", "interval": 86400, "behavior": "classical", "format": "text"},
    }
    if anchors != expected_anchor_shapes:
        fail(errors, "rule-anchor must contain exactly the audited ip, domain, domaintxt and class templates")

    validate_proxy_providers(proxy_providers, errors)
    validate_rule_providers(providers, raw, errors)
    _, valid_targets = validate_groups(groups, proxies, errors)
    routing_refs = validate_rules(rules, providers, valid_targets, errors)
    dns_refs = validate_dns(dns, providers, errors)
    validate_sniffer(sniffer, errors)
    validate_tun(tun, errors)
    validate_public_secrets(raw, proxies, errors)
    validate_repository_docs(path, errors)

    referenced_providers = routing_refs | dns_refs
    unused_providers = set(providers) - referenced_providers
    for name in sorted(unused_providers):
        fail(errors, f"declared rule-provider is not referenced by routing or DNS: {name}")

    if errors:
        print("Repository policy validation failed:")
        for item in errors:
            print(f"  - {item}")
        return 1

    print("Repository policy validation passed")
    print(f"  template:          {TEMPLATE_VERSION}")
    print(f"  proxy groups:      {len(groups)} checked")
    print(f"  routing rules:     {len(rules)} checked")
    print(f"  rule providers:    {len(providers)} referenced")
    print("  DNS/TUN/sniffer:   policy passed")
    print("  comments/secrets:  policy passed")
    print("  repository docs:   synchronized")
    print("  core semantics:    delegated to mihomo -t")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
