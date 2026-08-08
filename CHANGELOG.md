# Changelog

## V4.3

- 重新定义 Fake-IP 策略：普通国内域名也默认使用 Fake-IP，DIRECT / PROXY 只由 Routing Rules 决定。
- 删除 `RULE-SET,cn_domain,real-ip`，不再把整个中国域名集合预先排除出 Fake-IP。
- 删除 Google / ProxyLite / GFW / `geolocation-!cn` 的显式 `fake-ip` 项，统一由最终 `MATCH,fake-ip` 兜底。
- 删除 `time.*.com` 与 `pool.ntp.org` Real-IP 例外；当前 Mihomo 在 Fake-IP TUN 下可对 DIRECT 的 TCP/UDP 使用 `direct-nameserver` 重新解析，没有必要预防性排除普通时间同步域名。
- 删除 `services.googleapis.cn` 与 `xn--ngstr-lra8j.com` Real-IP 例外；目前没有足够证据证明它们必须绕过 Fake-IP。
- 保留私有域名、`.local`、`home.arpa`、Windows NCSI 与 Apple APNs 的 Real-IP 例外。
- APNs 继续同时使用 `push.apple.com -> 🍎 Apple`、Real-IP 与 Sniffer skip，兼容 Apple 平台可能绕过 VPN 的系统推送流量。
- `fake-ip-filter` 从 16 条精简为 7 条。
- 校验脚本新增 V4.3 DNS 约束：必须以 `MATCH,fake-ip` 收尾，并禁止再次全局设置 `cn_domain -> real-ip`。
- README 与设计说明更新为“Fake-IP 默认、Real-IP 例外”的模型。

## V4.2

- 修正 `apple_domain` 的 MetaCubeX Rule Provider 路径，补回缺失的 `/geo/`。
- 新增 `DOMAIN-SUFFIX,push.apple.com,🍎 Apple`，让 Apple APNs 默认直连，同时保留手动切换代理能力。
- DNS `fake-ip-filter` 新增 `push.apple.com -> real-ip`，使 APNs 的 DNS 行为与直连策略一致。
- 将 ChatGPT 从宽泛的 `category-ai-!cn` 改为专用 `openai.mrs`，避免 Microsoft Copilot、Google AI、GitHub Copilot 等被错误归入 ChatGPT 组。
- 将 `geolocation-!cn` 调整到 `cn_domain` 之前；DNS Fake-IP 决策同步采用相同优先级。
- 明确 Google / ProxyLite / GFW / `geolocation-!cn` 优先使用 Fake-IP，其余中国域名再使用 Real-IP。
- 修正美国节点筛选中的裸 `us` 匹配，降低误匹配 Australia 等节点名称的概率。
- 校验脚本新增规则顺序、OpenAI/APNs 语义检查，以及公开 Rule Provider URL 可达性检查。
- README 与设计说明补充 iOS APNs、Android FCM、DNS/Fake-IP 与 Rules 的联动逻辑。

## V4.1

- 新增 `scripts/validate_config.py`，统一检查 YAML、策略组引用、Rule Provider 引用和公开模板脱敏状态。
- 新增 GitHub Actions，在相关文件发生 push / pull request 变更时自动执行校验。
- README 增加校验状态徽章、本地校验命令和 CI 说明。

## V4

- 重新整理配置分区与注释。
- 恢复 `redir-port` 与 `tproxy-port` 作为备用透明代理入口。
- 保留 `find-process-mode: strict` 用于桌面端进程分流。
- TUN 使用 mixed stack，并通过 route exclude 优先保护局域网兼容性。
- `100.64.0.0/10` 作为可选项保留，不默认启用。
- Sniffer 使用兼容性优先策略：TLS/QUIC 用于识别域名，HTTP 单独允许覆盖目标。
- DNS 使用 Fake-IP、国内 DoH 和 `direct-nameserver: system`。
- 使用 YAML Anchor 减少重复配置。
- 公开模板不包含真实订阅 Token、服务器地址或 UUID。
