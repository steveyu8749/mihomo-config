# Design Notes

## 目标

这份模板面向手机和电脑本机运行 Mihomo 的场景，以 TUN 为主要系统级接管方式。设计优先级依次是：正确分流、局域网兼容、移动端稳定性、可解释性，最后才是参数数量或“功能完整度”。

## 流量链路

```text
系统 / App
  ↓
TUN
  ↓
DNS / Fake-IP
  ↓
Sniffer 恢复域名
  ↓
Rules 从上到下匹配
  ↓
策略组
  ↓
DIRECT / Proxy
```

每一层都尽量只解决自己的问题，避免在 Sniffer、DNS 和 Rules 中重复做同一件事。

## TUN 与局域网

TUN 是主要接管方式；`mixed-port`、`redir-port`、`tproxy-port` 保留为额外入口。

RFC1918 私网、IPv4 Link-local、Multicast 和 Limited Broadcast 使用 `route-exclude-address` 在路由层绕过 TUN。这样局域网发现、设备互联和文件传输不必先进入 Mihomo 再由规则 DIRECT。

`100.64.0.0/10` 属于 RFC6598 Shared Address Space，不是 RFC1918，因此默认只保留为注释选项。

## DNS / Fake-IP

默认 DNS 使用国内 DoH；`direct-nameserver: system` 用于最终确定为 DIRECT 的目标。

Fake-IP 决策顺序与 Routing 规则保持一致：

1. 私有域名、本地域名、系统连通性检测、APNs、时间同步等兼容项优先 Real-IP。
2. Google、ProxyLite、GFW、`geolocation-!cn` 等明确代理集合优先 Fake-IP。
3. 其余中国域名使用 Real-IP。
4. 其余域名使用 Fake-IP。

这样做的目的不是让所有代理流量都必须 Fake-IP，而是减少宽泛 `cn_domain` 与明确代理集合交叉时产生的解析歧义。

## Sniffer

Sniffer 用于从 HTTP Host、TLS SNI 和 QUIC 元数据恢复域名，不做 HTTPS MITM。

当前策略：

- `parse-pure-ip: true`
- 全局 `override-destination: false`
- HTTP 单独 `override-destination: true`
- TLS / QUIC 只用于识别域名
- 只对微信、QQ、小米、Apple Push 等有实际兼容理由的域名跳过嗅探

`skip-domain` 只表示“不要嗅探”，不表示 DIRECT。

## Apple APNs

Apple Push 单独使用：

```yaml
- DOMAIN-SUFFIX,push.apple.com,🍎 Apple
```

`🍎 Apple` 默认选择 `直连`，但保留手动代理选项。DNS 同时对 `push.apple.com` 返回 Real-IP，Sniffer 对其跳过嗅探，使三层行为一致。

`apple-cn.mrs` 只用于 Apple 中国区域名，不把全部 Apple 域名一刀切成 DIRECT。

## Android FCM

Android FCM 属于 Google 网络，继续由 `google_domain` / `google_ip` 进入 `🍀 Google`。不使用 `DST-PORT,5228-5230` 之类粗粒度规则，也不为 FCM 单独复制域名列表。

国内厂商 Push 不额外写死规则，优先让国内域名/IP规则自然 DIRECT。

## OpenAI 与 AI 聚合规则

`category-ai-!cn` 是一个包含多种 AI 服务的聚合集合，不等同于 ChatGPT。因此 V4.2 将 `🤖 ChatGPT` 改为使用 `openai.mrs`，避免 Copilot、Google AI、Anthropic 等服务被提前吸收到 ChatGPT 策略组。

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

## 不采用的方案

当前不默认启用：

- `strict-route`
- `auto-redirect`
- `100.64.0.0/10` route exclude
- Apple `17.0.0.0/8` 整段 DIRECT
- APNs / FCM 端口级分流
- 大量无证据的 Sniffer `skip-domain`
- 海外 DoH + 更复杂的 DNS 代理依赖链

这些能力在特定环境可能有用，但不应该为了“配置更全”而默认打开。

## 安全

公开仓库只保存模板。订阅 Token、UUID、私有服务器地址和个人私有规则源必须留在本地配置中，不进入 Git 历史。
