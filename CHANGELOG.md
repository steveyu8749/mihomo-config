# Changelog

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
