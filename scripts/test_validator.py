from __future__ import annotations

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


def remove_mode_comment(text: str) -> str:
    old = "mode: rule                                                # 使用规则模式；DIRECT / PROXY 由下方 rules 与策略组决定"
    return replace_once(text, old, "mode: rule")


TEST_CASES: list[tuple[str, Callable[[str], str], str]] = [
    ("duplicate YAML key", add_duplicate_mode, "found duplicate key 'mode'"),
    (
        "ProxyLite shadows a dedicated service",
        move_proxylite_before_bing,
        "must appear before proxylite",
    ),
    (
        "missing referenced provider",
        remove_bing_provider,
        "missing domain MRS rule-provider: bing_domain",
    ),
    (
        "unknown rule target",
        lambda text: replace_once(
            text,
            "RULE-SET,onedrive_domain,🐬 OneDrive",
            "RULE-SET,onedrive_domain,🐬 Missing",
        ),
        "unknown target '🐬 Missing'",
    ),
    (
        "protocol-local destination override",
        add_protocol_override,
        "sniffer protocol TLS must not override destination",
    ),
    (
        "invalid process regex",
        lambda text: replace_once(text, ".*spotify.*", "(*spotify"),
        "invalid process regex",
    ),
    (
        "domain rule with no-resolve",
        lambda text: replace_once(
            text,
            "RULE-SET,bing_domain,🪟 Microsoft",
            "RULE-SET,bing_domain,🪟 Microsoft,no-resolve",
        ),
        "no-resolve is only valid for IP rules",
    ),
    (
        "live subscription URL",
        lambda text: replace_first(
            text,
            'url: "订阅url"',
            'url: "https://subscriptions.invalid/api?token=not-a-placeholder-token"',
        ),
        "URL looks live instead of sanitized",
    ),
    (
        "missing field comment",
        remove_mode_comment,
        "active config lines missing explanatory comments",
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

    source = CONFIG.read_text(encoding="utf-8")
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="mihomo-validator-tests-") as directory:
        temp_root = Path(directory)
        for index, (name, mutate, expected_message) in enumerate(TEST_CASES):
            candidate = temp_root / f"case-{index}.yaml"
            candidate.write_text(mutate(source), encoding="utf-8")
            result = run_validator(candidate)
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
