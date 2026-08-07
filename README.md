# mihomo-config

一份面向 **手机 / 电脑本机 TUN 使用场景** 的 Mihomo 配置模板。重点不是堆叠参数，而是让每个配置项都能解释、能维护，并尽量降低局域网、DNS、Sniffer 与 TUN 之间的兼容性问题。

## 设计目标

- 以 **TUN** 作为主要系统级接管方式，同时保留 `mixed-port`、`redir-port`、`tproxy-port` 作为额外入口。
- RFC1918 私网、链路本地、组播和广播地址在 TUN 路由层直接绕过，优先保证局域网发现和设备互联。
- `100.64.0.0/10` 作为 RFC6598 / CGNAT 可选项保留，但默认不开启。
- DNS 使用 **Fake-IP**；默认上游采用国内 DoH，`direct-nameserver` 保留为 `system`。
- Sniffer 用于恢复域名并辅助规则匹配；TLS / QUIC 默认不改写真实连接目标，HTTP 单独允许覆盖。
- 使用 YAML Anchor 减少 Provider、策略组和 Rule Provider 的重复配置。
- 进程规则保留 `find-process-mode: strict`，方便桌面端按进程分流。

## 文件

- `config.example.yaml`：完整公开模板，已经移除真实订阅地址、Token、服务器地址和 UUID。
- `CHANGELOG.md`：记录配置设计上的重要调整。
- `docs/design-notes.md`：解释 TUN、DNS、Sniffer 等关键设计取舍。
- `.gitignore`：避免实际使用的私密配置被误提交。

## 使用方法

1. 复制模板：

   ```bash
   cp config.example.yaml config.yaml
   ```

2. 在 `config.yaml` 中替换：
   - 机场订阅 URL / Token
   - 自建节点服务器地址
   - VLESS UUID
   - 其他只属于你自己的节点或规则

3. `config.yaml` 已被 `.gitignore` 忽略，**不要强制提交真实配置**。

4. 导入 Mihomo / Clash Verge Rev 等兼容客户端后，再根据自己的网络环境测试 TUN、局域网发现和应用分流。

## 关键取舍

### DNS

`nameserver` 是 Mihomo 默认 DNS 上游，本模板使用 AliDNS 与 DNSPod 的 DoH：兼顾国内直连可达性和 DNS 传输加密。

`direct-nameserver: system` 被刻意保留：当流量最终确定为 DIRECT 时，可以使用当前系统 / 路由器 / 运营商 DNS 得到适合本地网络的最终解析结果。

### Sniffer

Sniffer 的核心作用是从 HTTP Host、TLS SNI、QUIC 握手中恢复域名，让域名规则在 TUN 场景仍然可用。模板采用：

- 全局 `override-destination: false`
- HTTP 单独 `override-destination: true`
- TLS / QUIC 主要用于识别域名，不主动替换应用原本的目标

这样更偏向兼容性，而不是最大程度介入连接目标。

### LAN / TUN

家庭私网直接通过 `route-exclude-address` 绕过 TUN，因此普通局域网流量不需要再进入 Mihomo 后通过规则 `DIRECT` 一次。

`100.64.0.0/10` 不是 RFC1918 私网，所以只以注释形式保留；只有确定自己的 CGNAT、Overlay 或其他网络确实使用它时再启用。

## 安全

这个仓库应只保存**模板**。真实订阅 Token、UUID、私有服务器信息不要进入 Git 历史。即使以后将仓库改为 Private，也建议遵守同样原则。

## 说明

该模板针对特定使用习惯持续整理，并不是“所有 Mihomo 用户的唯一最佳配置”。网络环境、客户端平台和服务规则不同，都可能需要局部调整。
