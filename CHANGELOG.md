# Changelog

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
