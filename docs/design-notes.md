# Design Notes

## 目标

这份模板面向手机和电脑本机运行 Mihomo 的场景，以 TUN 为主要系统级接管方式。设计优先级依次是：正确分流、局域网兼容、移动端稳定性、可解释性，最后才是参数数量或“功能完整度”。

## 流量链路

```text
系统 / App
  ↓
DNS 返回 Fake-IP 或少量 Real-IP
  ↓
TUN
  ↓
Mihomo 恢复域名 / Sniffer 辅助识别
  ↓
Rules 从上到下匹配
  ↓
策略组
  ↓
DIRECT / Proxy
```

V4.3 的一个核心变化是：**DNS 的 Fake-IP / Real-IP 选择不再承担“国内直连 / 国外代理”的职责。** 出口只由 Routing Rules 决定。

## TUN 与局域网

TUN 是主要接管方式；`mixed-port`、`redir-port`、`tproxy-port` 保留为额外入口。

RFC1918 私网、IPv4 Link-local、Multicast 和 Limited Broadcast 使用 `route-exclude-address` 在路由层绕过 TUN。这样局域网发现、设备互联和文件传输不必先进入 Mihomo 再由规则 DIRECT。

`100.64.0.0/10` 属于 RFC6598 Shared Address Space，不是 RFC1918，因此默认只保留为注释选项。

## DNS / Fake-IP

默认 DNS 使用国内 DoH；`direct-nameserver: system` 用于最终确定为 DIRECT 的目标。

V4.3 使用“Fake-IP 默认、Real-IP 例外”的模型：

```yaml
fake-ip-filter:
  - RULE-SET,private_domain,real-ip
  - DOMAIN-SUFFIX,local,real-ip
  - DOMAIN-SUFFIX,home.arpa,real-ip
  - DOMAIN-SUFFIX,msftconnecttest.com,real-ip
  - DOMAIN-SUFFIX,msftncsi.com,real-ip
  - DOMAIN-SUFFIX,push.apple.com,real-ip
  - MATCH,fake-ip
```

这意味着普通国内网站和国内 App 域名同样可以获得 Fake-IP。后续命中 `cn_domain` 时仍然可以 DIRECT；Mihomo 在最终 DIRECT 时再通过 `direct-nameserver` 获取真实目标地址。

因此 V4.3 删除：

- `cn_domain -> real-ip`
- Google / ProxyLite / GFW / `geolocation-!cn` 的显式 `fake-ip`
- `time.*.com` 与 `pool.ntp.org` Real-IP 例外
- `services.googleapis.cn` 与 `xn--ngstr-lra8j.com` Real-IP 例外

这些项目要么已经被最终 `MATCH,fake-ip` 覆盖，要么没有足够证据证明必须使用 Real-IP。

## 为什么仍保留 Real-IP 例外

### 私有 / 本地域名

`private_domain`、`.local` 与 `home.arpa` 可能直接对应局域网地址。应用有时需要真实看到 `192.168.x.x`、`10.x.x.x` 等地址，而且这些目标本身会被 `route-exclude-address` 绕过 TUN，因此保留 Real-IP 更合理。

### Windows NCSI

Windows 会使用 `msftconnecttest.com` 和 `msftncsi.com` 做网络连通性探测，其中 DNS 探测会检查预期解析结果。这里保留 Real-IP 是针对系统机制，而不是因为 Microsoft 流量本身必须直连。

### Apple APNs

Apple Push 继续使用：

```yaml
- DOMAIN-SUFFIX,push.apple.com,🍎 Apple
```

`🍎 Apple` 默认选择 `直连`，但保留手动代理选项。DNS 对 `push.apple.com` 返回 Real-IP，Sniffer 对其跳过嗅探。

这样做不是因为 APNs 无法使用 Fake-IP，而是为了兼容 Apple 平台可能将 APNs 作为系统例外绕过 VPN 的情况：如果连接没有进入 Mihomo，就不能依赖 Mihomo 的 Fake-IP 映射表。

## Sniffer

Sniffer 用于从 HTTP Host、TLS SNI 和 QUIC 元数据恢复域名，不做 HTTPS MITM。

当前策略：

- `parse-pure-ip: true`
- 全局 `override-destination: false`
- HTTP 单独 `override-destination: true`
- TLS / QUIC 只用于识别域名
- 只对微信、QQ、小米、Apple Push 等有实际兼容理由的域名跳过嗅探

`skip-domain` 只表示“不要嗅探”，不表示 DIRECT。

## Android FCM

Android FCM 属于 Google 网络，继续由 `google_domain` / `google_ip` 进入 `🍀 Google`。不使用 `DST-PORT,5228-5230` 之类粗粒度规则，也不为 FCM 单独复制域名列表。

FCM 本身默认仍使用 Fake-IP；其是否代理由 Google Routing Rules 决定。

国内厂商 Push 不额外写死规则，优先让国内域名/IP规则自然 DIRECT。

## OpenAI 与 AI 聚合规则

`category-ai-!cn` 是一个包含多种 AI 服务的聚合集合，不等同于 ChatGPT。因此 `🤖 ChatGPT` 使用 `openai.mrs`，避免 Copilot、Google AI、Anthropic 等服务被提前吸收到 ChatGPT 策略组。

如果以后确实需要统一管理所有海外 AI 服务，应新增独立的 `AI` 策略组，而不是复用 `🤖 ChatGPT`。

## Rules 顺序

采用“具体优先、宽泛靠后”的原则：

```text
private / process
→ service-specific
→ ProxyLite / GFW
→ geolocation-!cn
→ cn_domain
→ IP fallback
→ MATCH
```

`geolocation-!cn` 位于 `cn_domain` 前，是为了在规则集合交叉时优先保护已经明确判定为非中国服务的域名。

这一顺序只决定出口，不决定 DNS 返回 Fake-IP 还是 Real-IP。

## 不采用的方案

当前不默认启用：

- `strict-route`
- `auto-redirect`
- `100.64.0.0/10` route exclude
- Apple `17.0.0.0/8` 整段 DIRECT
- APNs / FCM 端口级分流
- 整个 `cn_domain` 强制 Real-IP
- 时间同步域名批量 Real-IP
- 大量无证据的 Sniffer `skip-domain`
- 海外 DoH + 更复杂的 DNS 代理依赖链

这些能力在特定环境可能有用，但不应该为了“配置更全”而默认打开。

## 维护原则

以后新增 `fake-ip-filter` 例外时，应先确认：

1. 问题能稳定复现；
2. 问题确实来自 Fake-IP，而不是 TUN 路由、Sniffer、规则集或上游 DNS；
3. 例外范围可以尽量缩小到具体域名或服务。

如果不能满足这些条件，默认继续使用 Fake-IP。

## 安全

公开仓库只保存模板。订阅 Token、UUID、私有服务器地址和个人私有规则源必须留在本地配置中，不进入 Git 历史。
