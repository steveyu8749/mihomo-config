# Design Notes

## 目标

本模板面向手机和电脑本机运行 Mihomo 的场景，以 TUN 为主要系统级接管方式。设计顺序是：正确分流、局域网兼容、移动端稳定性、可解释性，最后才是参数数量。

## 流量链路

```text
系统 / App
  ↓
DNS（默认 Fake-IP，少量 Real-IP）
  ↓
TUN
  ↓
Fake-IP / DNSMapping / Sniffer 恢复域名
  ↓
Rules 从上到下匹配
  ↓
策略组
  ↓
DIRECT / Proxy
```

DNS 的 Fake-IP / Real-IP 不承担“国内直连 / 国外代理”的职责；出口只由 Routing Rules 决定。

## 核心版本前提

V4.5 假定 Mihomo Core 支持 v1.19.10 之后的行为：Fake-IP TUN 场景下，DIRECT 的 `direct-nameserver` 重解析同时适用于 TCP 和 UDP。旧核心可能无法完整满足这套 DNS 设计。

## TUN 与局域网

- TUN 是主要接管方式。
- RFC1918、IPv4 Link-local、Multicast 和 Limited Broadcast 通过 `route-exclude-address` 绕过 TUN。
- `100.64.0.0/10` 属于 RFC6598，不默认排除。
- 不默认启用 `strict-route` 或 Linux 特定的 `auto-redirect`。

## DNS / Fake-IP

V4.5 将最小 Real-IP 例外集中到 Rule Provider：

```yaml
fake-ip-filter:
  - RULE-SET,private_domain,real-ip
  - RULE-SET,fakeip_compat,real-ip
  - MATCH,fake-ip
```

`private_domain` 的实际上游集合已经包含 `.local` 和 `home.arpa`，所以不再重复声明。

`fakeip_compat` 使用 `type: inline` + `behavior: domain`，当前只包含：

```text
dns.msftncsi.com
+.push.apple.com
+.market.xiaomi.com
```

Windows NCSI 中，`dns.msftncsi.com` 的 DNS 探测会验证特定 A 记录；APNs 保留 Real-IP 是为了兼容可能绕过 VPN 的系统流量。`+.market.xiaomi.com` 作为小米应用商店兼容项加入，但它只影响 Fake-IP/Real-IP，不承担局域网小米互联修复。

普通国内域名、国外域名、FCM、NTP 等统一使用 Fake-IP；命中 DIRECT 后再由 `direct-nameserver: system` 获取真实目标地址。

## Sniffer

当前策略：

- `parse-pure-ip: true`
- `override-destination: false`
- HTTP 单独允许 `override-destination: true`
- TLS / QUIC 主要用于识别域名
- 微信、QQ、小米保留已有兼容例外

APNs 不再单独 `skip-domain`。Real-IP 过滤会建立 DNSMapping，且 443 回退连接允许 Sniffer 辅助识别；没有证据表明 APNs TLS 元数据识别本身需要禁用。

## Apple APNs

```yaml
- DOMAIN-SUFFIX,push.apple.com,🍎 Apple
```

`🍎 Apple` 默认 `直连`，仍允许手动切换代理。`apple-cn.mrs` 只处理适合中国大陆直连的 Apple 子集，不能替代 APNs 的显式规则。

不采用：

- `DST-PORT,5223,DIRECT`
- 整段 `17.0.0.0/8,DIRECT`
- 为 APNs 增加专用 Sniffer 端口

## Android FCM

Google 上游集合包含 `googlefcm`，因此 Android FCM 继续通过 `google_domain` / `google_ip` 进入 `🍀 Google`，不增加端口级规则。

## 父子规则顺序

一些上游 geosite 本身包含其他集合，因此专用规则必须在父集合前：

```text
onedrive_domain → microsoft_domain
github_domain   → microsoft_domain
youtube_domain  → google_domain
```

其中 V4.4 修复了 GitHub 原先位于 Microsoft 之后的问题。

整体顺序保持：

```text
private / process
→ service-specific
→ ProxyLite / GFW
→ geolocation-!cn
→ cn_domain
→ IP fallback
→ MATCH
```

## Rule Provider / Rule Set

远程 Rule Provider 统一按 24 小时更新；机场 Proxy Provider 的刷新周期不变。GitHub Raw 规则继续通过 `♻️ 自动选择` 下载，不引入第三方 GitHub 反代。

没有整包引入参考配置的 `fakeipfilter-cn` / `fakeipfilter-!cn`，因为其中包含 NTP、STUN、音乐、游戏、运营商登录、UU 加速器等大量当前没有必要强制 Real-IP 的域名。需要兼容的项目只进入本地 `fakeip_compat`。

独立 `cnki_domain` 被删除：`cn` 上游已经包含 `geolocation-cn`，其学术分类继续包含 CNKI；两条规则最终又都是 `🎯 直连`，单独 Provider 没有行为收益。ScienceDirect、Elsevier、Clarivate 则继续保留，因为它们是海外学术服务，需要在 `geolocation-!cn` 之前显式直连。

## 维护原则

新增兼容项前先确认：

1. 问题可稳定复现；
2. 能定位到 Fake-IP、TUN、Sniffer、规则集或 DNS 中的具体一层；
3. 例外范围能缩到最小。

不能满足这些条件时，不增加新规则。