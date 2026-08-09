from __future__ import annotations

import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "shadowrocket/shadowrocket.conf"
VALIDATOR = ROOT / "scripts/validate_shadowrocket.py"


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise AssertionError(f"expected exactly one occurrence of {old!r}")
    return text.replace(old, new, 1)


def replace_first(text: str, old: str, new: str) -> str:
    if old not in text:
        raise AssertionError(f"expected at least one occurrence of {old!r}")
    return text.replace(old, new, 1)


TEST_CASES: list[tuple[str, Callable[[str], str], str]] = [
    (
        "stale Fake-IP compatibility entry",
        lambda text: replace_once(text, "*.services.googleapis.cn, ", ""),
        "always-real-ip must exactly mirror",
    ),
    (
        "OneDrive shadowed by Microsoft",
        lambda text: replace_once(
            text,
            "RULE-SET,https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Shadowrocket/OneDrive/OneDrive.list,🐬 OneDrive\n"
            "RULE-SET,https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Shadowrocket/GitHub/GitHub.list,👨🏿‍💻 GitHub\n\n"
            "# Bing、Xbox 单独列出便于审计；MSN 已由 Microsoft 集合覆盖，三者使用同一策略组。\n",
            "RULE-SET,https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Shadowrocket/Microsoft/Microsoft.list,🪟 Microsoft\n"
            "RULE-SET,https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Shadowrocket/OneDrive/OneDrive.list,🐬 OneDrive\n"
            "RULE-SET,https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Shadowrocket/GitHub/GitHub.list,👨🏿‍💻 GitHub\n\n"
            "# Bing、Xbox 单独列出便于审计；MSN 已由 Microsoft 集合覆盖，三者使用同一策略组。\n",
        ),
        "content or priority differs",
    ),
    (
        "process rule imported from Mihomo",
        lambda text: replace_once(
            text,
            "FINAL,🐟 漏网之鱼",
            "PROCESS-NAME,onedrive.exe,DIRECT\nFINAL,🐟 漏网之鱼",
        ),
        "must not contain process-name rules",
    ),
    (
        "Adobe rule imported from desktop",
        lambda text: replace_once(
            text,
            "FINAL,🐟 漏网之鱼",
            "DOMAIN-SUFFIX,adobe.com,REJECT\nFINAL,🐟 漏网之鱼",
        ),
        "must not contain Adobe rules",
    ),
    (
        "embedded node section",
        lambda text: text + "\n[Proxy]\nexample = ss, example.com, 443\n",
        "unexpected section",
    ),
    (
        "old repository URL",
        lambda text: replace_first(text, "steveyu8749/proxy-routing-config", "steveyu8749/mihomo-config"),
        "update-url must be",
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
        print("Baseline Shadowrocket configuration unexpectedly failed:")
        print(baseline.stdout + baseline.stderr)
        return 1

    source = CONFIG.read_text(encoding="utf-8")
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="shadowrocket-validator-tests-") as directory:
        root = Path(directory)
        for index, (name, mutate, expected) in enumerate(TEST_CASES):
            path = root / f"case-{index}.conf"
            path.write_text(mutate(source), encoding="utf-8")
            result = run_validator(path)
            output = result.stdout + result.stderr
            if result.returncode == 0:
                failures.append(f"{name}: validator incorrectly accepted the mutation")
            elif expected not in output:
                failures.append(f"{name}: expected {expected!r}, received:\n{output.strip()}")

    if failures:
        print("Shadowrocket validator regression tests failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print(f"Shadowrocket validator regression tests passed: {len(TEST_CASES)} mutations rejected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
