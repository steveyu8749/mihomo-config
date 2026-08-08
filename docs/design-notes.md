# Design Notes

## 目标

V4.6 面向手机和电脑本机运行 Mihomo 的场景。设计优先级依次是：

1. 分流语义正确；
2. 手机和电脑行为尽量一致；
3. 局域网与系统功能兼容；
4. 配置可解释、可验证；
5. 最后才考虑减少 YAML 行数。

模板使用独立 MRS Rule Provider，不依赖客户端内置 GeoData；节点完全手工选择，不维护地区筛选和自动策略组。

## 流量链路

```text
系统 / 应用
  ↓
Mihomo DNS
  ↓
TUN
  ↓
Fake-IP 映射 / DNSMapping / Sniffer 恢复域名
  ↓
Rules
  ↓
策略组
  ↓
DIRECT / Proxy
```

Fake-IP / Real-IP 只决定 DNS 返回值，不决定出口。DIRECT / PROXY 只由路由规则和策略组决定。

## 核心版本

建议使用 Mihomo Core v1.19.10 或更新版本，以获得 Fake-IP TUN 下 DIRECT TCP / UDP 的 `direct-nameserver` 重解析行为。CI 当前固定使用 v1.19.29。

## TUN 与本机边界

TUN 作为手机和电脑的共同基线：

- `stack: mixed`；
- 劫持 TCP / UDP 53 端口 DNS；
- `auto-route: true`；
- `auto-detect-interface: true`；
- RFC1918、链路本地、组播和广播地址绕过 TUN。

`allow-lan` 不启用。它控制其他局域网设备能否访问本机代理端口，与本机访问 NAS、路由器、米家设备或 mDNS 不是同一问题。

Clash Verge Rev 等 GUI 客户端可能合并或覆写 TUN / DNS 字段，因此排障时必须查看最终运行配置。

## DNS / Fake-IP

```yaml
fake-ip-filter:
  - RULE-SET,private_domain,real-ip
  - RULE-SET,fakeip_compat,real-ip
  - MATCH,fake-ip
```

`private_domain` 负责私有/本地域名；`fakeip_compat` 只保留：

```text
dns.msftncsi.com
+.push.apple.com
+.market.xiaomi.com
```

不恢复整个 `cn_domain -> real-ip`，也不预先加入 NTP、STUN、游戏或厂商大类例外。

### respect-rules

当前不启用。它控制 DNS 上游连接本身是否匹配路由规则，并不决定被查询域名的业务流量出口。

主 DNS 是 AliDNS 和 DNSPod DoH，本来就适合直接连接。启用 `respect-rules` 通常不会改变结果，却需要额外处理 `proxy-server-nameserver` 和节点域名启动依赖。以后如果默认 DNS 改为必须经代理访问的境外 DoH，再重新评估。

## Sniffer

Sniffer 统一遵循：

```text
识别域名：是
覆盖目标：否
skip-domain：无
```

`override-destination: false` 适用于 HTTP、TLS 和 QUIC。Sniffer 只在缺少 Fake-IP / DNSMapping 域名时补充识别信息，不替换原始连接目标。

只有在问题可复现并确认由嗅探造成时，才添加最小范围的跳过项。

## 策略组

`🚀 默认代理` 使用：

```text
select
+ include-all
+ exclude-type: direct
```

它直接收纳全部代理节点，并且始终保持“代理出口”语义。

业务组只包含：

```text
🚀 默认代理
直连
```

因此不同业务可以选择继承默认节点或硬直连，但不能在每个业务组里直接展开全部节点。这样减少重复节点列表，也避免多个业务组各自维护大量具体节点状态。

Apple 组同样提供硬直连和默认代理两个选择，但顺序相反，默认优先直连。

## 进程规则

进程规则放在业务域名规则之前：

- Spotify 进程硬直连；
- Windows `onedrive.exe` 硬直连；
- Xbox 和 Android Bing 进入 Microsoft 组。

`PROCESS-NAME` 对进程名执行忽略大小写的精确匹配，Android 上也可匹配包名；`PROCESS-NAME-REGEX` 使用忽略大小写的正则匹配，适合覆盖多个进程名或包名变体。已知稳定名称时优先使用精确规则，避免正则范围过宽。两者都依赖运行平台能够提供进程信息，路由器侧无法识别下游设备进程时不会命中。

OneDrive 的特殊设计是有意的：本地客户端可正常直连同步，但网页版需要代理。浏览器不会命中 `onedrive.exe`，随后由 `onedrive_domain` 进入独立策略组。

## 域名与 IP 规则

专用分类位于宽泛父集合之前：

```text
bing / msn / xbox → microsoft
onedrive           → microsoft
github             → microsoft
youtube            → google
geolocation-!cn    → cn_domain
```

Apple 使用完整 `apple.mrs`。域名流量由 `apple_domain` 处理，因此 `apple_ip` 使用 `no-resolve`，只兜底已有真实目标 IP 的连接。

`cn_ip` 有意不使用 `no-resolve`。未命中域名集合的目标可以在最后的中国 IP 规则处解析：

```text
解析到中国 IP → 直连
不是中国 IP   → MATCH
```

这会为少量未知域名增加一次 DNS 查询，但保留了国内 IP 兜底能力。

`category-ai-!cn` 是境外 AI 聚合集合，并非 OpenAI 专用集合。当前统一复用 `🤖 ChatGPT` 策略组。

## Rule Provider

规则数据按以下方式组织：

```text
公共域名分类 → domain MRS Rule Provider
服务 / 中国 IP → ipcidr MRS Rule Provider
ProxyLite      → classical text Rule Provider
兼容集合       → inline Rule Provider
```

HTTP Rule Provider 默认每 24 小时更新，不指定固定下载代理。更新请求作为 Mihomo 内部连接，由当前路由规则决定出口。

Proxy Provider 不同：它需要在首次启动时提供代理节点，因此订阅文件固定使用硬直连下载，避免循环依赖。

Adobe classical YAML 规则默认关闭。桌面端如需启用，必须同时恢复路由规则、`&yaml` 锚点和 `adobeisdumb` Provider；手机端保持注释。

## 为什么不用 GeoData

V4.6 不配置 `GEOSITE`、`GEOIP`、`geodata-mode`、`geo-auto-update` 或 `geox-url`。

主要考虑：

1. 手机和电脑引用完全相同的规则 URL；
2. 不依赖各客户端本地 GeoData 是否更新、是否包含某个标签；
3. MRS 匹配在本地完成，Provider 更新不会让每次连接访问网络；
4. 数据来源、格式、更新周期和引用关系都能从 YAML 与 CI 直接审计。

## 维护原则

新增特殊项前确认三个条件：

1. 问题可以稳定复现；
2. 能定位到具体机制；
3. 例外范围可以缩到足够小。

默认机制能够解决的问题，不继续增加特殊规则。
