# Design Notes

## 目标

V4.6 面向手机和电脑本机运行 Mihomo 的场景。设计优先级：正确分流、局域网兼容、移动端稳定、可解释性、最后才是参数数量。

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
Rules
  ↓
策略组
  ↓
DIRECT / Proxy
```

Fake-IP / Real-IP 不负责决定出口；DIRECT / PROXY 只由 Routing Rules 决定。

## 核心版本前提

建议 Mihomo Core v1.19.10 或更新版本，以获得 Fake-IP TUN 下 DIRECT TCP/UDP 的 `direct-nameserver` 重解析行为。

## TUN 与 GUI 客户端

TUN 块继续作为跨客户端基线：

- `stack: mixed`
- DNS hijack 53/UDP + 53/TCP
- `auto-route`
- `auto-detect-interface`
- RFC1918、Link-local、Multicast、Limited Broadcast 路由排除

Clash Verge Rev 等 GUI 客户端可能通过全局设置参与配置合并，因此排障时应查看最终运行配置，而不是只看订阅 YAML。

`allow-lan` 不启用：它用于允许其他局域网设备访问本机代理端口，与本机访问 NAS、米家设备、mDNS 等不是同一问题。

## DNS / Fake-IP

```yaml
fake-ip-filter:
  - GEOSITE,private,real-ip
  - RULE-SET,fakeip_compat,real-ip
  - MATCH,fake-ip
```

`fakeip_compat` 仅保留：

```text
dns.msftncsi.com
+.push.apple.com
+.market.xiaomi.com
```

不恢复整个 `cn -> real-ip`，不添加 NTP、STUN、UU、音乐、游戏等大范围兼容列表。

### respect-rules

不启用。该选项控制 DNS 上游连接是否遵守 Routing Rules，并要求配套 `proxy-server-nameserver`。当前 AliDNS / DNSPod 本来就应直接访问，开启后路径通常仍为 DIRECT，却增加节点域名解析和 bootstrap 依赖。

如果未来默认 DNS 改为必须经代理访问的海外 DoH，再重新评估。

## Sniffer

V4.6 统一为：

```text
识别域名：是
覆盖目标：否
```

全局 `override-destination: false`，HTTP 不再单独覆盖。Sniffer 仅在缺少 Fake-IP/DNSMapping 域名时作为补充识别来源。

现有微信、QQ、小米 `skip-domain` 暂时保留，避免 V4.6 同时改变过多兼容变量。

## 策略组

删除地区筛选、fallback 和 url-test。节点选择变为完全手工：

```text
🚀 默认代理
  → 🌐 全部节点
      → 手工选择节点
```

机场 Proxy Provider 的 health-check 独立保留，用于节点健康状态，不依赖自动策略组。

## GeoData 与 Rule Provider

V4.6 采用混合架构：

```text
公共域名分类 → GEOSITE
中国 IP      → GEOIP,CN（默认 MMDB）
定制规则      → RULE-SET
服务 IP       → MRS RULE-SET
```

不设置 `geodata-mode: true`，因此 `GEOIP,CN` 不要求切换到 `geoip.dat`。GeoSite 依赖 `geosite.dat`，由客户端管理；配置不重复启用 `geo-auto-update` 或指定 `geox-url`。

Rule Provider 最终只保留：

- `fakeip_compat`
- `proxylite`
- `adobeisdumb`
- `google_ip`
- `telegram_ip`
- `netflix_ip`

远程 Provider 每 24 小时更新，并通过 `🚀 默认代理` 拉取。

## 规则顺序

专用分类继续位于父集合之前：

```text
onedrive → microsoft
github   → microsoft
youtube  → google
```

宽泛分类保持：

```text
gfw
→ geolocation-!cn
→ cn
→ service IP fallback
→ GEOIP,CN
→ MATCH
```

APNs 显式规则继续位于 `apple-cn` 前，DNS 同时通过 `fakeip_compat` 保持 Real-IP。

## 维护原则

新增特殊项前确认三个条件：问题可复现、能定位到具体机制、例外范围可以足够小。否则不添加。