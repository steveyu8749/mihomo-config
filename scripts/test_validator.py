from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config.example.yaml"
VALIDATOR = ROOT / "scripts" / "validate_config.py"


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise AssertionError(f"expected exactly one occurrence of {old!r}")
    return text.replace(old, new, 1)


def replace_first(text: str, old: str, new: str) -> str:
    if old not in text:
        raise AssertionError(f"expected at least one occurrence of {old!r}")
    return text.replace(old, new, 1)


def move_proxylite_before_bing(text: str) -> str:
    lines = text.splitlines(keepends=True)
    proxylite_index = next(
        index
        for index, line in enumerate(lines)
        if line.lstrip().startswith("- RULE-SET,proxylite,")
    )
    proxylite_line = lines.pop(proxylite_index)
    bing_index = next(
        index
        for index, line in enumerate(lines)
        if line.lstrip().startswith("- RULE-SET,bing_domain,")
    )
    lines.insert(bing_index, proxylite_line)
    return "".join(lines)


def move_direct_before_bing(text: str) -> str:
    lines = text.splitlines(keepends=True)
    direct_index = next(
        index
        for index, line in enumerate(lines)
        if line.lstrip().startswith("- RULE-SET,direct_domain,")
    )
    direct_line = lines.pop(direct_index)
    bing_index = next(
        index
        for index, line in enumerate(lines)
        if line.lstrip().startswith("- RULE-SET,bing_domain,")
    )
    lines.insert(bing_index, direct_line)
    return "".join(lines)


def remove_bing_provider(text: str) -> str:
    lines = [
        line
        for line in text.splitlines(keepends=True)
        if not line.lstrip().startswith("bing_domain:")
    ]
    return "".join(lines)


def add_duplicate_mode(text: str) -> str:
    return text + "\nmode: direct  # regression test: duplicate key\n"


def add_protocol_override(text: str) -> str:
    tls_line = "    TLS:                                                  # TLS ClientHello SNI 嗅探\n"
    replacement = (
        tls_line
        + "      override-destination: true                         # regression test: local override\n"
    )
    return replace_once(text, tls_line, replacement)


def add_skip_domain(text: str) -> str:
    anchor = "  override-destination: false                             # 嗅探域名只用于识别/分流，不替换原始连接目标\n"
    replacement = (
        anchor
        + "  skip-domain: [\"+.example.com\"]                       # regression test: undocumented exception\n"
    )
    return replace_once(text, anchor, replacement)


def add_strict_route(text: str) -> str:
    anchor = "  auto-route: true                                        # 自动写入系统路由，把普通流量导入 TUN\n"
    replacement = (
        anchor
        + "  strict-route: true                                      # regression test: platform-specific override\n"
    )
    return replace_once(text, anchor, replacement)


def disable_lazy_health_check(text: str) -> str:
    return replace_once(
        text,
        "      lazy: true                                          # 仅在 Provider 节点被实际使用时执行周期检查，降低移动端后台开销",
        "      lazy: false                                         # regression test: background checks always active",
    )


def remove_mode_comment(text: str) -> str:
    old = "mode: rule                                                # 使用规则模式；DIRECT / PROXY 由下方 rules 与策略组决定"
    return replace_once(text, old, "mode: rule")


TEST_CASES: list[tuple[str, str, Callable[[str], str], str]] = [
    (
        "duplicate YAML key",
        "config.example.yaml",
        add_duplicate_mode,
        "found duplicate key 'mode'",
    ),
    (
        "ProxyLite shadows a dedicated service",
        "config.example.yaml",
        move_proxylite_before_bing,
        "must appear before proxylite",
    ),
    (
        "Direct shadows a dedicated service",
        "config.example.yaml",
        move_direct_before_bing,
        "must appear before direct_domain",
    ),
    (
        "missing referenced provider",
        "config.example.yaml",
        remove_bing_provider,
        "missing domain MRS rule-provider: bing_domain",
    ),
    (
        "unknown rule target",
        "config.example.yaml",
        lambda text: replace_once(
            text,
            "RULE-SET,onedrive_domain,🐬 OneDrive",
            "RULE-SET,onedrive_domain,🐬 Missing",
        ),
        "unknown target '🐬 Missing'",
    ),
    (
        "protocol-local destination override",
        "config.example.yaml",
        add_protocol_override,
        "sniffer protocol TLS must not override destination",
    ),
    (
        "undocumented sniffer skip-domain",
        "config.example.yaml",
        add_skip_domain,
        "sniffer.skip-domain must remain omitted",
    ),
    (
        "cross-platform strict-route override",
        "config.example.yaml",
        add_strict_route,
        "tun.strict-route must remain omitted",
    ),
    (
        "eager provider health checks",
        "config.example.yaml",
        disable_lazy_health_check,
        "health-check.lazy must be True",
    ),
    (
        "invalid process regex",
        "config.example.yaml",
        lambda text: replace_once(
            text,
            "PROCESS-NAME-WILDCARD,*spotify*,直连",
            "PROCESS-NAME-REGEX,(*spotify,直连",
        ),
        "invalid process regex",
    ),
    (
        "domain rule with no-resolve",
        "config.example.yaml",
        lambda text: replace_once(
            text,
            "RULE-SET,bing_domain,🪟 Microsoft",
            "RULE-SET,bing_domain,🪟 Microsoft,no-resolve",
        ),
        "no-resolve is only valid for IP rules",
    ),
    (
        "live subscription URL",
        "config.example.yaml",
        lambda text: replace_first(
            text,
            'url: "订阅url"',
            'url: "https://subscriptions.invalid/api?token=not-a-placeholder-token"',
        ),
        "URL looks live instead of sanitized",
    ),
    (
        "missing field comment",
        "config.example.yaml",
        remove_mode_comment,
        "active config lines missing explanatory comments",
    ),
    (
        "missing audited Fake-IP exception",
        "rules/FakeIPFilter.list",
        lambda text: replace_once(text, "+.services.googleapis.cn\n", ""),
        "must contain exactly the 9 audited compatibility entries",
    ),
    (
        "unapproved NTP Fake-IP exception",
        "rules/FakeIPFilter.list",
        lambda text: text + "\ntime.windows.com\n",
        "must contain exactly the 9 audited compatibility entries",
    ),
    (
        "classical syntax in domain text list",
        "rules/Direct.list",
        lambda text: text + "\nDOMAIN-SUFFIX,example.com\n",
        "is not a domain behavior text rule",
    ),
    (
        "classical syntax in ProxyLite domain list",
        "rules/ProxyLite.list",
        lambda text: text + "\nDOMAIN-SUFFIX,example.com\n",
        "is not a domain behavior text rule",
    ),
    (
        "domain syntax in ProxyIP CIDR list",
        "rules/ProxyIP.list",
        lambda text: text + "\nDOMAIN-SUFFIX,example.com\n",
        "is not an IP CIDR behavior text rule",
    ),
]


def run_validator(config: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), str(config)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def main() -> int:
    baseline = run_validator(CONFIG)
    if baseline.returncode != 0:
        print("Baseline configuration unexpectedly failed:")
        print(baseline.stdout + baseline.stderr)
        return 1

    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="mihomo-validator-tests-") as directory:
        temp_root = Path(directory)
        for index, (name, target, mutate, expected_message) in enumerate(TEST_CASES):
            case_root = temp_root / f"case-{index}"
            shutil.copytree(
                ROOT,
                case_root,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            target_path = case_root / target
            target_path.write_text(
                mutate(target_path.read_text(encoding="utf-8")), encoding="utf-8"
            )
            result = run_validator(case_root / "config.example.yaml")
            output = result.stdout + result.stderr
            if result.returncode == 0:
                failures.append(f"{name}: validator incorrectly accepted the mutation")
            elif expected_message not in output:
                failures.append(
                    f"{name}: expected {expected_message!r}, received:\n{output.strip()}"
                )

    if failures:
        print("Validator regression tests failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print(f"Validator regression tests passed: {len(TEST_CASES)} mutations rejected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
