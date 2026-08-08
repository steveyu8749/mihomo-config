# mihomo-config

[![Validate Mihomo template](https://github.com/steveyu8749/mihomo-config/actions/workflows/validate.yml/badge.svg)](https://github.com/steveyu8749/mihomo-config/actions/workflows/validate.yml)

一份面向 **手机 / 电脑本机 TUN 使用场景** 的 Mihomo 配置模板。当前版本为 **V4.6**。

核心原则：**Fake-IP 是默认 DNS 语义，Rules 决定 DIRECT / PROXY；Sniffer 只辅助识别域名；公共域名分类使用 GeoSite，自定义与特殊规则继续使用 Rule Provider。**

## 设计基线

- TUN 作为跨客户端基线保留；RFC1918、链路本地、组播和广播地址在路由层绕过。
- Clash Verge Rev 等 GUI 客户端可能对 TUN / DNS 做全局合并或覆写，排障时应查看客户端最终运行配置。
- 不启用 `allow-lan`；本模板只面向本机使用，不向局域网其他设备开放代理端口。
- DNS 使用 Fake-IP；Real-IP 仅保留私有域和少量明确兼容项。
- 不启用 `respect-rules`：当前 DNS 上游为 AliDNS / DNSPod，本来就应直接访问，没有必要让 DoH 连接再进入 Routing Rules。
- Sniffer 保留为域名识别兜底，但 HTTP / TLS / QUIC 均不使用嗅探结果覆盖原始目标。
- 删除地区、fallback、url-test 策略组，节点完全手工选择；机场 Provider 健康检查继续保留。
- 公共域名规则优先使用 `GEOSITE`；中国 IP 使用标准 `GEOIP,CN`；Google / Telegram / Netflix 服务 IP 继续使用独立 MRS。

## 核心版本与 GeoData

建议使用 **Mihomo Core v1.19.10 或更新版本**。V4.6 继续依赖 Fake-IP TUN 下 DIRECT 的 `direct-nameserver` 重解析行为。

V4.6 使用 `GEOSITE`，因此客户端需要可用的 `geosite.dat`。配置本身不写 `geo-auto-update` / `geox-url`，GeoData 生命周期交给客户端管理；Clash Verge Rev 等客户端可直接更新 GeoData。

V4.6 **没有启用 `geodata-mode: true`**。该选项只决定 `GEOIP` 使用 DAT 还是 MMDB；本模板的 `GEOIP,CN` 继续使用默认 MMDB，而服务级 IP 集合继续使用 MRS，不要求全面切换到 `geoip.dat`。

## DNS / Fake-IP

```yaml
fake-ip-filter:
  - GEOSITE,private,real-ip
  - RULE-SET,fakeip_compat,real-ip
  - MATCH,fake-ip
```

`fakeip_compat` 是本地 inline Rule Provider，目前只包含：

```text
dns.msftncsi.com
+.push.apple.com
+.market.xiaomi.com
```

其中小米项只用于应用商店类 Fake-IP 兼容，不承担局域网“小米互联”修复。

普通国内域名同样可以使用 Fake-IP：

```text
DNS 返回 Fake-IP
→ TUN / Mihomo
→ GEOSITE,cn 或 GEOIP,CN
→ 🎯 直连
→ direct-nameserver: system
→ DIRECT
```

## `respect-rules` 为什么不启用

`respect-rules` 控制的是 **DNS 上游连接本身是否遵守 Routing Rules**，不是“被查询域名应该用哪个 DNS”。当前 `nameserver` 是 AliDNS / DNSPod，目标就是直接访问，因此开启后通常仍会得到 DIRECT，但会额外引入 `proxy-server-nameserver` 与节点域名 bootstrap 依赖。

如果以后把默认 DNS 改为必须通过代理访问的海外 DoH，再重新评估 `respect-rules`。

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

已有微信、QQ、小米 `skip-domain` 暂时保留，不继续扩大。后续如要删除，应单独做兼容性验证，不与其他架构调整同时进行。

## 策略组

V4.6 删除：

- 香港 / 日本 / 美国地区组；
- fallback 故障转移；
- url-test 自动选择。

只保留 `🚀 默认代理`、`🌐 全部节点`、各业务组、`🍎 Apple`、`🎯 直连` 和 `🐟 漏网之鱼`。`🌐 全部节点` 用于手工选择实际节点。

机场 Proxy Provider 的健康检查仍保持启用，与删除自动策略组无冲突。

## GeoSite + Rule Provider 混用

V4.6 不采用“全 GeoData”或“全 MRS”任一极端方案。

公共域名分类使用 GeoSite，例如：

```yaml
- GEOSITE,openai,🤖 ChatGPT
- GEOSITE,github,👨🏿‍💻 GitHub
- GEOSITE,youtube,📹 YouTube
- GEOSITE,google,🍀 Google
- GEOSITE,gfw,🚀 默认代理
- GEOSITE,geolocation-!cn,🚀 默认代理
- GEOSITE,cn,🎯 直连
```

Rule Provider 只保留：

- `fakeip_compat`：本地兼容集；
- `proxylite`：个人规则；
- `adobeisdumb`：独立第三方规则；
- `google_ip` / `telegram_ip` / `netflix_ip`：服务级 IP 集合。

远程 Rule Provider 统一每 24 小时更新，并通过 `🚀 默认代理` 下载。

## Rules 顺序

继续遵循“具体规则优先、父集合靠后”：

```text
private / process
→ specific services
→ ProxyLite / GFW
→ geolocation-!cn
→ cn
→ service IP fallback
→ GEOIP,CN
→ MATCH
```

因此仍保持：

```text
onedrive → microsoft
github   → microsoft
youtube  → google
geolocation-!cn → cn
```

APNs 仍显式位于 `apple-cn` 前：

```yaml
- DOMAIN-SUFFIX,push.apple.com,🍎 Apple
- GEOSITE,apple-cn,🍎 Apple
```

## 自动校验

```bash
python -m pip install PyYAML
python scripts/validate_config.py config.example.yaml
```

离线环境：

```bash
python scripts/validate_config.py config.example.yaml --skip-network
```

校验器会检查 YAML、引用关系、GeoSite 关键顺序、Sniffer 不覆盖目标、Fake-IP 约束、手动策略组结构、机场健康检查、Rule Provider 更新策略和公开模板脱敏。

## 维护原则

默认机制能解决的，不增加特殊规则。新增 Fake-IP 例外、Sniffer skip、端口/IP规则之前，应先确认问题能稳定复现并定位到具体机制。