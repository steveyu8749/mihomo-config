# mihomo-config

[![Validate Mihomo template](https://github.com/steveyu8749/mihomo-config/actions/workflows/validate.yml/badge.svg)](https://github.com/steveyu8749/mihomo-config/actions/workflows/validate.yml)

一份面向 **手机 / 电脑本机 TUN 使用场景** 的 Mihomo 配置模板。当前版本为 **V4.4**。核心原则是：TUN 负责接管，DNS 默认使用 Fake-IP，Rules 决定 DIRECT / PROXY，Real-IP 只保留给确实依赖真实 DNS 结果或可能绕过隧道的少数场景。

## 设计基线

- TUN 是主要系统级接管方式；`mixed-port`、`redir-port`、`tproxy-port` 作为额外入口保留。
- RFC1918 私网、链路本地、组播和广播地址在 TUN 路由层绕过，优先保证局域网发现和设备互联。
- `100.64.0.0/10` 是 RFC6598 Shared Address Space，仅作为可选 route exclude，不默认启用。
- DNS 默认返回 Fake-IP；普通国内域名同样可以使用 Fake-IP，最终仍可由 `cn_domain` / `cn_ip` DIRECT。
- `direct-nameserver: system` 保留给最终确定为 DIRECT 的真实目标解析。
- Sniffer 只辅助恢复域名；TLS / QUIC 默认不改写目标，HTTP 单独允许覆盖。
- OpenAI / ChatGPT、GitHub、YouTube 等具体服务规则必须位于包含它们的宽泛父集合之前。
- Apple APNs 显式进入 `🍎 Apple`，默认直连；Android FCM 由 Google 规则覆盖。

## 核心版本前提

V4.4 的“普通域名默认 Fake-IP + DIRECT 时由 `direct-nameserver` 重解析”设计，依赖较新的 Mihomo DNS 行为。**建议使用 Mihomo Core v1.19.10 或更新版本**；从 v1.19.10 起，Fake-IP TUN 场景下 `direct-nameserver` 的重解析同样适用于 UDP。

## 文件

- `config.example.yaml`：完整公开模板；真实订阅、Token、UUID、服务器地址和个人规则源均已脱敏。
- `scripts/validate_config.py`：检查 YAML、引用关系、关键规则顺序、DNS 约束、公开模板脱敏与 Rule Provider URL。
- `.github/workflows/validate.yml`：GitHub Actions 自动校验。
- `CHANGELOG.md`：版本变更记录。
- `docs/design-notes.md`：关键设计说明。

## 使用方法

```bash
cp config.example.yaml config.yaml
```

然后替换模板中的订阅 URL / Token、VLESS `server` / `uuid` / `servername`，以及个人 ProxyLite 规则源。`config.yaml` 已被 `.gitignore` 忽略，不要强制提交真实配置。

## DNS / Fake-IP

当前 `fake-ip-filter` 只保留三个 Real-IP 场景：

```yaml
fake-ip-filter:
  - RULE-SET,private_domain,real-ip
  - DOMAIN,dns.msftncsi.com,real-ip
  - DOMAIN-SUFFIX,push.apple.com,real-ip
  - MATCH,fake-ip
```

其中：

- `private_domain` 已包含 `.local`、`home.arpa` 等私有/本地域名，无需重复声明。
- Windows NCSI 只有 `dns.msftncsi.com` 的 DNS 探测需要特定真实 A 记录；`msftconnecttest.com` 的 Web 探测不需要因此整体退出 Fake-IP。
- APNs 保留 Real-IP，是为了兼容 Apple 平台可能将 APNs 流量排除在 VPN 隧道之外的情况。
- 其他普通域名统一由 `MATCH,fake-ip` 兜底，包括国内网站、国外网站、Google/FCM 与 NTP。

**Fake-IP 不等于 PROXY，Real-IP 也不等于 DIRECT。** 例如国内域名仍可以：

```text
DNS 返回 Fake-IP
→ TUN / Mihomo
→ cn_domain 命中
→ 🎯 直连
→ direct-nameserver: system
→ DIRECT
```

## Sniffer

当前策略：

- `parse-pure-ip: true`
- 全局 `override-destination: false`
- HTTP 单独 `override-destination: true`
- TLS / QUIC 主要用于识别域名
- 只对微信、QQ、小米等已有兼容理由的域名跳过嗅探

APNs 不再单独加入 `skip-domain`：它的兼容重点是 Real-IP 与明确路由，而不是禁止 TLS 元数据识别。

## Rules 顺序

规则遵循“具体规则优先、包含范围更大的父集合靠后”：

```text
private / process
→ service-specific
→ ProxyLite / GFW
→ geolocation-!cn
→ cn_domain
→ IP fallback
→ MATCH
```

特别注意：

- `onedrive_domain` 必须在 `microsoft_domain` 前。
- `github_domain` 必须在 `microsoft_domain` 前，因为 Microsoft 上游集合包含 GitHub。
- `youtube_domain` 必须在 `google_domain` 前，因为 Google 上游集合包含 YouTube。
- `geolocation-!cn` 在 `cn_domain` 前，处理两个宽泛集合可能出现的交叉。

## Apple / Android 推送

- iPhone / iPad 的 APNs 使用 `push.apple.com → 🍎 Apple`，默认选择 `直连`；DNS 保留真实 IP。
- 不增加 `DST-PORT,5223,DIRECT`、Apple `17.0.0.0/8` 整段直连或额外 APNs Sniffer 端口。
- Android FCM 继续由 `google_domain` / `google_ip` 进入 `🍀 Google`，不增加 5228–5230 端口规则。
- 国内厂商推送不额外写死规则，由国内域名/IP规则自然 DIRECT。

## 自动校验

完整校验：

```bash
python -m pip install PyYAML
python scripts/validate_config.py config.example.yaml
```

离线环境跳过 Rule Provider URL 检查：

```bash
python scripts/validate_config.py config.example.yaml --skip-network
```

校验脚本用于发现 YAML、引用、关键顺序、资源失效和脱敏问题，不等同于 Mihomo Core 的完整运行时验证。

## 维护原则

不再为“看起来特殊”的服务预防性添加参数。新增 Fake-IP 例外、Sniffer skip、端口/IP 规则之前，应先确认问题能稳定复现，并且确实由对应机制导致。
