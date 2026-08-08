# mihomo-config

[![Validate Mihomo template](https://github.com/steveyu8749/mihomo-config/actions/workflows/validate.yml/badge.svg)](https://github.com/steveyu8749/mihomo-config/actions/workflows/validate.yml)

一份面向 **手机 / 电脑本机 TUN 使用场景** 的 Mihomo 配置模板。当前版本为 **V4.6**。

核心原则：**Fake-IP 是默认 DNS 语义，Rules 决定 DIRECT / PROXY；Sniffer 只辅助识别域名；规则数据继续使用独立 MRS Rule Provider，不依赖客户端 GeoData。**

## V4.6 的定位

V4.6 不是简单回退到 V4.5，而是保留 V4.6 已确认有价值的结构精简，同时恢复 V4.5 更稳定、跨客户端一致的 MRS 数据层：

- 删除地区筛选、fallback、url-test 和共享 `🌐 全部节点` 中间层；
- `🚀 默认代理` 与每个业务组直接 `include-all`，全部节点手工选择；
- 机场 Proxy Provider 健康检查继续保留；
- Sniffer 改为完全“只识别、不改目标”，并删除全部 `skip-domain`；
- DNS 继续使用 Fake-IP，Real-IP 只保留私有域和少量明确兼容项；
- 域名和 IP 公共规则统一使用 MRS Rule Provider，不使用 `GEOSITE` / `GEOIP`；
- 不启用 `allow-lan`、`respect-rules`、`geodata-mode`、`geo-auto-update` 或 `geox-url`。

## 设计基线

- TUN 作为跨客户端基线保留；RFC1918、链路本地、组播和广播地址在路由层绕过。
- Clash Verge Rev 等 GUI 客户端可能对 TUN / DNS 做全局合并或覆写，排障时应查看客户端最终运行配置。
- 本模板只面向本机使用，因此不启用 `allow-lan`，不会主动向局域网其他设备开放代理端口。
- DNS 默认返回 Fake-IP；普通国内域名同样可以使用 Fake-IP，DIRECT / PROXY 只由 Routing Rules 决定。
- `direct-nameserver: system` 保留给最终确定为 DIRECT 的真实目标解析。
- Sniffer 仅在缺少 Fake-IP / DNSMapping 域名时补充识别 HTTP Host、TLS SNI 或 QUIC 域名，不覆盖实际目标。
- 节点选择完全手工；不维护地区正则、自动测速或故障转移策略组。
- MRS 规则由配置自身声明 URL 和更新周期，手机与电脑使用同一规则来源，不依赖各客户端维护的 GeoData 版本。

## 核心版本前提

建议使用 **Mihomo Core v1.19.10 或更新版本**。V4.6 继续依赖较新版本在 Fake-IP TUN 场景下对 DIRECT TCP / UDP 使用 `direct-nameserver` 重解析的行为。

## DNS / Fake-IP

V4.6 的 Fake-IP Filter 保持最小化：

```yaml
fake-ip-filter:
  - RULE-SET,private_domain,real-ip
  - RULE-SET,fakeip_compat,real-ip
  - MATCH,fake-ip
```

其中：

- `private_domain` 使用 MetaCubeX `private.mrs`，处理私有/本地域名；
- `fakeip_compat` 是本地 `inline` Rule Provider，不依赖远程下载；
- `MATCH,fake-ip` 让其余域名，包括普通国内域名，统一使用 Fake-IP。

`fakeip_compat` 当前只包含：

```text
dns.msftncsi.com
+.push.apple.com
+.market.xiaomi.com
```

`+.market.xiaomi.com` 只用于小米应用商店类 Fake-IP 兼容，不承担局域网“小米互联”修复。

**Fake-IP 不等于 PROXY，Real-IP 也不等于 DIRECT。** 例如普通国内域名仍可以：

```text
DNS 返回 Fake-IP
→ TUN / Mihomo
→ cn_domain / cn_ip
→ 🎯 直连
→ direct-nameserver: system
→ DIRECT
```

## 为什么不启用 `respect-rules`

`respect-rules` 控制的是 **DNS 上游连接本身是否遵守 Routing Rules**，不是“被查询域名应该使用哪个 DNS”。

当前主 DNS 为：

```yaml
nameserver:
  - https://dns.alidns.com/dns-query
  - https://doh.pub/dns-query
```

这两个 DoH 本来就希望直接访问。开启 `respect-rules` 后通常仍然会得到 DIRECT，却会额外引入 `proxy-server-nameserver`、节点域名 bootstrap 和潜在循环依赖，当前没有收益。

如果以后把默认 DNS 改为必须经代理访问的海外 DoH，再重新评估。

## Sniffer

V4.6 统一为“只识别，不改目标”：

```yaml
sniffer:
  enable: true
  parse-pure-ip: true
  override-destination: false
  sniff:
    HTTP:
      ports: [80, 8080-8880]
    TLS:
      ports: [443, 8443]
    QUIC:
      ports: [443, 8443]
```

V4.6 删除全部 `skip-domain`。逻辑是：既然 HTTP / TLS / QUIC 都不再使用嗅探结果覆盖实际目标，就不再预防性禁止微信、QQ、小米等域名被识别。以后只有在问题可稳定复现且能确认由嗅探导致时，才按最小范围加回例外。

## 策略组

V4.6 删除：

- 香港 / 日本 / 美国地区筛选组；
- fallback 故障转移；
- url-test 自动选择；
- 共享 `🌐 全部节点` 中间组。

`🚀 默认代理` 直接包含全部代理节点：

```yaml
- name: 🚀 默认代理
  type: select
  include-all: true
  exclude-type: direct
```

它不提供硬 DIRECT，因此语义始终是“使用代理”。这也保证远程 Rule Provider 的 `proxy: 🚀 默认代理` 不会因为用户误选直连而退化为 GitHub Raw 直连下载。

每个业务组同样直接 `include-all`，因此可以独立选择具体节点，而不是所有业务共享同一个“全部节点”选择状态：

```yaml
- &service
  name: 🐟 漏网之鱼
  type: select
  proxies: [🚀 默认代理, 🎯 直连]
  include-all: true
  exclude-type: direct
```

机场 Proxy Provider 的健康检查保持启用：订阅每 5 小时更新，节点每 10 分钟进行一次健康检查；这与删除 url-test / fallback 无冲突。

## 为什么继续使用 MRS，而不是 GeoData

V4.6 最终选择 **MRS Rule Provider 为主体**。

主要原因不是认为 GeoData “不好”，而是这份配置同时面向手机和电脑：

- MRS 的 URL、版本来源和更新周期由配置明确声明，跨客户端行为更一致；
- 不依赖 Clash Verge Rev、手机端客户端各自维护的 `geosite.dat` / `geoip.dat` 版本；
- `.mrs` 是 Mihomo 原生的二进制 Rule Set 格式，日常匹配在本地完成；
- 24 小时更新一次意味着 Provider 数量增加的主要成本是少量后台下载/缓存管理，而不是每次连接都访问网络；
- 规则来源更容易审计和自动检查。

因此 V4.6 不使用：

```text
GEOSITE
GEOIP
geodata-mode
geodata-loader
geo-auto-update
geox-url
```

这也避免了“配置本身正确，但某个客户端本地 GeoData 缺少 tag”一类隐式依赖。

## Rules 顺序

路由继续遵循“具体规则优先、包含范围更大的父集合靠后”：

```text
private / process
→ service-specific
→ ProxyLite / GFW
→ geolocation-!cn
→ cn_domain
→ service IP fallback
→ cn_ip
→ MATCH
```

关键顺序保持：

```text
onedrive_domain → microsoft_domain
github_domain   → microsoft_domain
youtube_domain  → google_domain
geolocation-!cn → cn_domain
```

APNs 仍显式位于 `apple_domain` 前：

```yaml
- DOMAIN-SUFFIX,push.apple.com,🍎 Apple
- RULE-SET,apple_domain,🍎 Apple
```

## Rule Provider

V4.6 恢复 MRS 公共规则层，共 26 个 Rule Provider：

- 域名分类使用 `behavior: domain` + `format: mrs`；
- IP 分类使用 `behavior: ipcidr` + `format: mrs`；
- ProxyLite / Adobe 保留其原始 classical 格式；
- `fakeip_compat` 继续使用本地 `type: inline`。

所有远程 Rule Provider 统一：

```yaml
interval: 86400
proxy: 🚀 默认代理
```

机场 Proxy Provider 的订阅刷新周期仍为 `18000` 秒，和 Rule Provider 的 24 小时更新周期分开管理。

## 自动校验

完整校验：

```bash
python -m pip install PyYAML
python scripts/validate_config.py config.example.yaml
```

离线环境：

```bash
python scripts/validate_config.py config.example.yaml --skip-network
```

校验器会检查：

- YAML 与引用关系；
- 不存在 fallback / url-test / `🌐 全部节点`；
- `🚀 默认代理` 和业务组使用 `include-all`；
- 不出现 GEOSITE / GEOIP / GeoData 配置；
- Sniffer 不覆盖目标且没有 `skip-domain`；
- `allow-lan` / `respect-rules` 不启用；
- MRS Provider、关键规则顺序、机场健康检查与公开模板脱敏。

## 维护原则

默认机制能解决的，不增加特殊规则。新增 Fake-IP 例外、Sniffer skip、端口/IP 规则之前，应先确认问题能稳定复现、能定位到具体机制，而且例外范围可以缩到最小。
