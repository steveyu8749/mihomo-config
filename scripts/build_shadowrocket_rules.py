from __future__ import annotations

import argparse
import ipaddress
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class RuleSpec:
    source: Path
    output: Path
    kind: str


SPECS = (
    RuleSpec(ROOT / "rules/Direct.list", ROOT / "shadowrocket/rules/Direct.list", "domain"),
    RuleSpec(
        ROOT / "rules/ProxyLite.list",
        ROOT / "shadowrocket/rules/ProxyLite.list",
        "domain",
    ),
    RuleSpec(ROOT / "rules/ProxyIP.list", ROOT / "shadowrocket/rules/ProxyIP.list", "ipcidr"),
)


def source_rules(path: Path) -> list[tuple[int, str]]:
    result: list[tuple[int, str]] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if line and not line.startswith("#"):
            result.append((line_number, line))
    return result


def convert_domain(path: Path, line_number: int, rule: str) -> str:
    if any(character.isspace() for character in rule) or "," in rule or "://" in rule:
        raise ValueError(f"{path}:{line_number}: invalid domain behavior rule: {rule!r}")
    if rule.startswith("+."):
        value = rule[2:]
        rule_type = "DOMAIN-SUFFIX"
    elif rule.startswith("full:"):
        value = rule[5:]
        rule_type = "DOMAIN"
    elif rule.startswith("keyword:"):
        value = rule[8:]
        rule_type = "DOMAIN-KEYWORD"
    elif rule.startswith("regexp:"):
        value = rule[7:]
        rule_type = "DOMAIN-REGEX"
    elif "*" in rule or "?" in rule:
        raise ValueError(
            f"{path}:{line_number}: wildcard domain rules need an explicit Shadowrocket review: {rule!r}"
        )
    else:
        value = rule
        rule_type = "DOMAIN"
    if not value:
        raise ValueError(f"{path}:{line_number}: empty domain rule")
    return f"{rule_type},{value}"


def convert_ipcidr(path: Path, line_number: int, rule: str) -> str:
    try:
        network = ipaddress.ip_network(rule, strict=True)
    except ValueError as exc:
        raise ValueError(f"{path}:{line_number}: invalid IP CIDR rule: {rule!r}") from exc
    rule_type = "IP-CIDR6" if network.version == 6 else "IP-CIDR"
    return f"{rule_type},{network},no-resolve"


def render(spec: RuleSpec) -> str:
    converted: list[str] = []
    seen: set[str] = set()
    for line_number, rule in source_rules(spec.source):
        if spec.kind == "domain":
            output = convert_domain(spec.source, line_number, rule)
        else:
            output = convert_ipcidr(spec.source, line_number, rule)
        if output in seen:
            raise ValueError(f"{spec.source}:{line_number}: duplicate converted rule: {output!r}")
        seen.add(output)
        converted.append(output)
    return "\n".join(converted) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert shared Mihomo domain/ipcidr text rules to Shadowrocket classical lists."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail when committed Shadowrocket outputs differ from their shared sources",
    )
    args = parser.parse_args()

    stale: list[str] = []
    for spec in SPECS:
        expected = render(spec)
        if args.check:
            actual = spec.output.read_text(encoding="utf-8") if spec.output.is_file() else None
            if actual != expected:
                stale.append(spec.output.relative_to(ROOT).as_posix())
            continue
        spec.output.parent.mkdir(parents=True, exist_ok=True)
        spec.output.write_text(expected, encoding="utf-8")
        print(f"generated {spec.output.relative_to(ROOT)}")

    if stale:
        print("Shadowrocket rule outputs are stale: " + ", ".join(stale))
        print("Run: python scripts/build_shadowrocket_rules.py")
        return 1
    if args.check:
        print(f"Shadowrocket rule outputs are synchronized: {len(SPECS)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
