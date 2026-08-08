# Design Notes

## 目标

V4.6 面向手机和电脑本机运行 Mihomo 的场景。设计优先级是：正确分流、跨客户端一致性、局域网兼容、移动端稳定、可解释性，最后才是 YAML 行数。

V4.6 最终没有采用 GeoData 作为主规则数据库，而是保留 V4.5 的 MRS Rule Provider 数据层，同时完成策略组和 Sniffer 的结构精简。

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

建议 Mihomo Core v1.19.10 或更新版本，以获得 Fake-IP TUN 下 DIRECT TCP / UDP 的 `direct-nameserver` 重解析行为。

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
  - RULE-SET,private_domain,real-ip
  - RULE-SET,fakeip_compat,real-ip
  - MATCH,fake-ip
```

`private_domain` 继续使用 MetaCubeX `private.mrs`，避免把私有域解析行为交给客户端本地 GeoData。

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
skip-domain：无
```

全局 `override-destination: false`，HTTP / TLS / QUIC 都不再局部覆盖。Sniffer 只在缺少 Fake-IP / DNSMapping 域名时作为补充识别来源。

V4.6 删除此前的微信、QQ、小米 `skip-domain`。既然 Sniffer 不再改写实际目标，就不预防性禁止这些域名被识别；若未来出现可复现问题，再按最小范围加回。

## 策略组

删除地区筛选、fallback、url-test 和共享 `🌐 全部节点`。

`🚀 默认代理`：

```text
select
+ include-all
+ exclude-type: direct
```

因此它始终表示代理出口，不再允许被误切为硬 DIRECT。

每个业务组也直接 `include-all`：

```text
业务组
├─ 🚀 默认代理
├─ 🎯 直连
└─ 全部具体代理节点
```

这样不同业务可以独立选择不同节点，同时 `store-selected: true` 保存各自状态。机场 Proxy Provider 的 health-check 独立保留，用于节点健康状态，不依赖自动策略组。

## 为什么不用 GeoData

V4.6 最终选择统一 MRS 数据层：

```text
公共域名分类 → domain MRS Rule Provider
服务 / 中国 IP → ipcidr MRS Rule Provider
定制规则      → classical Rule Provider
兼容集合      → inline Rule Provider
```

主要考虑：

1. 配置同时用于手机和电脑，MRS 能让不同客户端引用完全相同的规则 URL；
2. 不依赖各客户端本地 `geosite.dat` / `geoip.dat` 是否存在、是否更新、是否包含某个 tag；
3. MRS 是二进制 Rule Set，日常规则匹配在本地完成；Provider 数量主要影响更新与缓存管理，而不是每个连接都产生网络请求；
4. 数据来源、更新周期和引用关系都可以直接从 YAML 与 CI 审计。

因此 V4.6 不配置 `GEOSITE`、`GEOIP`、`geodata-mode`、`geo-auto-update` 或 `geox-url`。

## Rule Provider

远程 Rule Provider 统一按 24 小时更新；机场 Proxy Provider 的刷新周期仍为 5 小时。

所有远程 Rule Provider 使用：

```yaml
proxy: 🚀 默认代理
```

由于 `🚀 默认代理` 已排除 direct 类型，GitHub Raw 更新不会因用户把默认组切成直连而退化为 DIRECT。

Domain / IPCIDR 公共规则继续使用 `format: mrs`。ProxyLite 和 Adobe 保留 classical text/yaml；`fakeip_compat` 继续使用 inline。

## 规则顺序

专用分类继续位于父集合之前：

```text
onedrive_domain → microsoft_domain
github_domain   → microsoft_domain
youtube_domain  → google_domain
```

宽泛分类保持：

```text
gfw_domain
→ geolocation-!cn
→ cn_domain
→ service IP fallback
→ cn_ip
→ MATCH
```

APNs 显式规则继续位于 `apple_domain` 前，DNS 同时通过 `fakeip_compat` 保持 Real-IP。

## 维护原则

新增特殊项前确认三个条件：问题可复现、能定位到具体机制、例外范围可以足够小。否则不添加。
