# Changelog

## V4.4

- 核实上游 `microsoft` geosite 包含 `github`，将 `github_domain` 调整到 `microsoft_domain` 前，修复 GitHub 独立策略可能被 Microsoft 提前命中的问题。
- 继续收敛 Fake-IP 例外：`private_domain` 已包含 `.local` 与 `home.arpa`，删除两条重复规则。
- Windows NCSI 仅保留 `dns.msftncsi.com -> real-ip`；删除范围过宽的 `msftconnecttest.com` 与整个 `msftncsi.com` Real-IP 例外。
- 撤回“给 NCSI 增加硬 DIRECT”的方案：NCSI 的固定 DNS 结果需求与 Routing 出口是两个问题，无需额外增加两条路由规则。
- 删除 APNs 的 Sniffer `skip-domain`；继续保留 `push.apple.com -> real-ip` 与 `push.apple.com -> 🍎 Apple`，不增加 5223 端口、Apple IP 段或额外 Sniffer 端口规则。
- `fake-ip-filter` 从 7 条缩减为 4 条，继续以 `MATCH,fake-ip` 作为默认行为。
- README / Design Notes 明确 V4.4 的 DNS 设计建议使用 Mihomo Core v1.19.10 或更新版本，以获得 Fake-IP TUN 下 DIRECT UDP 的 `direct-nameserver` 重解析行为。
- 校验脚本同步新的最小 Real-IP 集合，并新增 `github_domain` 必须位于 `microsoft_domain` 前的顺序检查。

## V4.3

- 重新定义 Fake-IP 策略：普通国内域名也默认使用 Fake-IP，DIRECT / PROXY 只由 Routing Rules 决定。
- 删除 `RULE-SET,cn_domain,real-ip`，不再把整个中国域名集合预先排除出 Fake-IP。
- 删除 Google / ProxyLite / GFW / `geolocation-!cn` 的显式 `fake-ip` 项，统一由最终 `MATCH,fake-ip` 兜底。
- 删除 `time.*.com` 与 `pool.ntp.org` Real-IP 例外。
- 删除 `services.googleapis.cn` 与 `xn--ngstr-lra8j.com` Real-IP 例外。
- 保留私有域名、Windows NCSI 与 Apple APNs 的 Real-IP 兼容项。
- 校验脚本新增 `MATCH,fake-ip` 与禁止全局 `cn_domain -> real-ip` 的约束。

## V4.2

- 修正 `apple_domain` 的 MetaCubeX Rule Provider 路径。
- 新增 `push.apple.com -> 🍎 Apple`。
- ChatGPT 改用专用 `openai.mrs`。
- 将 `geolocation-!cn` 调整到 `cn_domain` 之前。
- 修正美国节点筛选中的裸 `us` 误匹配。
- 校验脚本新增关键顺序、语义与 Rule Provider URL 检查。

## V4.1

- 新增 `scripts/validate_config.py`。
- 新增 GitHub Actions 自动校验。
- README 增加 CI 与本地校验说明。

## V4

- 重新整理配置分区与注释。
- 恢复 `redir-port` 与 `tproxy-port` 作为备用透明代理入口。
- 保留 `find-process-mode: strict`。
- TUN 使用 mixed stack，并通过 route exclude 优先保护局域网兼容性。
- `100.64.0.0/10` 作为可选项保留，不默认启用。
- Sniffer 使用兼容性优先策略。
- DNS 使用 Fake-IP、国内 DoH 和 `direct-nameserver: system`。
- 使用 YAML Anchor 减少重复配置。
- 公开模板不包含真实订阅 Token、服务器地址或 UUID。
