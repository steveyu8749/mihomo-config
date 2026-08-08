# mihomo-config

[![Validate Mihomo template](https://github.com/steveyu8749/mihomo-config/actions/workflows/validate.yml/badge.svg)](https://github.com/steveyu8749/mihomo-config/actions/workflows/validate.yml)

一份面向手机和电脑本机使用的 Mihomo TUN 配置模板。当前版本为 **V4.6**，重点是清晰、稳定、跨客户端一致，并尽量减少不必要的自动策略和兼容例外。

这份模板采用以下基本思路：

- DNS 默认使用 Fake-IP；Fake-IP / Real-IP 只影响解析结果，不决定直连或代理。
- 流量出口完全由 `rules` 和策略组决定。
- Sniffer 只补充识别域名，不改写原始连接目标。
- 公共域名和 IP 分类使用独立的 MRS Rule Provider，不依赖客户端本地 GeoData。
- 节点由用户手工选择，不维护地区筛选、自动测速和故障转移策略组。
- 配置只服务本机，不向局域网其他设备开放代理端口。

## 使用前提

- 建议使用 **Mihomo Core v1.19.10 或更新版本**。
- CI 当前固定使用 **Mihomo v1.19.29** 检查模板。
- 适用于支持 Mihomo 配置的客户端，例如 Clash Verge Rev 及相应移动端客户端。
- GUI 客户端可能合并或覆写 TUN、DNS 等字段，排障时应以客户端显示的最终运行配置为准。

## 快速开始

1. 下载 [`config.example.yaml`](./config.example.yaml)。
2. 将 `Provider_A`、`Provider_B`、`Provider_C` 中的 `订阅url` 替换为自己的订阅地址；不需要的 Provider 可以删除。
3. 处理 `proxylite`：有自定义规则就替换占位地址，没有就同时删除对应路由规则和 Rule Provider。
4. 将配置导入客户端并启用 TUN。
5. 在 `🚀 默认代理` 中选择一个实际代理节点；其他业务组默认继承该选择，也可以单独切换为硬直连。

请勿把真实订阅地址、节点凭据或其他密钥提交到公开仓库。仓库内的地址均应保持为占位内容。

## 配置结构

```text
系统 / 应用
  ↓
Mihomo DNS（默认 Fake-IP，少量 Real-IP 例外）
  ↓
TUN 接管
  ↓
Fake-IP 映射 / DNSMapping / Sniffer 恢复域名
  ↓
Rules 从上到下匹配
  ↓
策略组选择 DIRECT 或代理节点
```

### Proxy Provider

机场订阅统一由 `proxy-providers` 管理：

- 订阅每 5 小时刷新一次；
- 节点健康检查每 10 分钟执行一次；
- 订阅文件使用 `proxy: 直连` 下载，避免首次启动时出现“还没有节点，却需要节点下载订阅”的循环依赖。

如果某个订阅地址无法直连，应只调整对应 Provider，不建议无条件修改所有订阅的下载出口。

### TUN

TUN 使用 `mixed` 网络栈，并接管 TCP / UDP 53 端口 DNS：

```yaml
tun:
  enable: true
  stack: mixed
  dns-hijack:
    - any:53
    - tcp://any:53
  auto-route: true
  auto-detect-interface: true
```

RFC1918 私网、链路本地、组播和广播地址通过 `route-exclude-address` 绕过 TUN，减少访问路由器、NAS、投屏和局域网发现服务时的干扰。

`100.64.0.0/10` 默认保持注释。只有确认当前网络、运营商 CGNAT、Tailscale 或其他软件需要该网段绕过 TUN 时再启用。

### DNS 与 Fake-IP

DNS 使用国内 DoH：

```yaml
nameserver:
  - https://dns.alidns.com/dns-query
  - https://doh.pub/dns-query
```

Fake-IP Filter 使用规则模式：

```yaml
fake-ip-filter:
  - RULE-SET,private_domain,real-ip
  - RULE-SET,fakeip_compat,real-ip
  - MATCH,fake-ip
```

含义如下：

- `private_domain`：私有域名和本地域名返回真实 IP；
- `fakeip_compat`：少量已确认需要兼容的域名返回真实 IP；
- `MATCH,fake-ip`：其余域名，包括普通国内域名，统一返回 Fake-IP。

`fakeip_compat` 当前仅包含：

```text
dns.msftncsi.com
+.push.apple.com
+.market.xiaomi.com
```

这些规则只改变 DNS 返回值，不指定路由出口。例如 `push.apple.com` 返回真实 IP 后，实际连接仍会进入 `🍎 Apple` 策略组。

最终判定为直连的域名通过以下配置重新解析真实地址：

```yaml
direct-nameserver:
  - system
```

模板不启用 `respect-rules`。该选项控制的是 Mihomo 连接 DNS 上游时是否匹配路由规则；当前 AliDNS 和 DNSPod DoH 本来就适合直接访问，启用它没有明显收益，还会引入额外的节点域名解析和启动依赖。

### Sniffer

Sniffer 的原则是“只识别，不改目标”：

```yaml
sniffer:
  enable: true
  parse-pure-ip: true
  override-destination: false
```

HTTP Host、TLS SNI 和 QUIC 信息只用于补充域名识别和规则匹配。当前不设置 `skip-domain`；只有在问题可以稳定复现并确认由嗅探导致时，才应添加最小范围的例外。

### 策略组

`🚀 默认代理` 是唯一直接收纳全部代理节点的策略组：

```yaml
- name: 🚀 默认代理
  type: select
  include-all: true
  exclude-type: direct
```

它排除了 direct 类型，因此始终表示代理出口。

业务策略组不直接使用 `include-all`，只提供两个选择：

```yaml
proxies: [🚀 默认代理, 直连]
```

这样可以统一继承默认节点，也能为单个业务切换为硬直连。`store-selected: true` 会保存每个策略组上次的选择。

当前包含 ChatGPT、YouTube、Google、GitHub、OneDrive、Microsoft、TikTok、Telegram、Netflix、Speedtest、PayPal 和 Apple 等业务组。

需要注意：`🤖 ChatGPT` 当前使用 `category-ai-!cn` 聚合集合，因此也会接管 Claude、Copilot、Perplexity 等其他境外 AI 服务。这是当前配置的有意选择，不是 OpenAI 专用规则。

### OneDrive 的特殊处理

Windows OneDrive 客户端能够正常直连上传，因此配置在域名规则之前保留：

```yaml
- PROCESS-NAME,onedrive.exe,直连
```

最终效果是：

```text
OneDrive.exe 本地客户端 → 硬直连
浏览器访问 OneDrive     → 🐬 OneDrive 策略组
```

网页版 OneDrive 可以选择 `🚀 默认代理`，不会被桌面进程规则影响。

### Apple

Apple 使用完整的 `apple.mrs` 域名集合，而不是只使用 `apple-cn.mrs`：

```yaml
- DOMAIN-SUFFIX,push.apple.com,🍎 Apple
- RULE-SET,apple_domain,🍎 Apple
- RULE-SET,apple_ip,🍎 Apple,no-resolve
```

Apple 域名默认进入 `🍎 Apple`，该组默认选择硬直连，也可以手工切换到 `🚀 默认代理`。完整域名集合已经负责域名流量，因此 `apple_ip` 使用 `no-resolve`，只兜底已有真实目标 IP 的连接。

### 国内 IP 兜底

`cn_ip` 有意不使用 `no-resolve`：

```yaml
- RULE-SET,cn_ip,直连
```

未命中前面域名规则的目标可以在这里解析真实 IP；解析到中国 IP 时直连，否则继续进入最终 `MATCH`。这能保留国内 IP 兜底能力，代价是少量未知域名首次连接时可能增加一次 DNS 查询。

### Rule Provider

公共规则主要使用 MetaCubeX 提供的 MRS 文件：

- 域名集合：`behavior: domain` + `format: mrs`；
- IP 集合：`behavior: ipcidr` + `format: mrs`；
- 自定义 ProxyLite：`behavior: classical` + `format: text`；
- Fake-IP 兼容集合：本地 `type: inline`。

HTTP Rule Provider 默认每 24 小时更新。模板没有为它们设置固定 `proxy`，更新请求作为 Mihomo 内部连接，按照当前路由规则选择出口。

Adobe 屏蔽规则默认完全关闭，不会在手机端加载或下载。只在桌面端需要时，同时取消以下三处注释：

1. `RULE-SET,adobeisdumb,REJECT`；
2. `yaml: &yaml ...` 锚点；
3. `adobeisdumb: {<<: *yaml, ...}` Rule Provider。

### Rules 顺序

Mihomo 从上到下匹配，命中后停止。当前顺序概括为：

```text
私有域名 / 私有 IP
→ 进程规则
→ 具体业务域名
→ GFW / 非中国域名 / 中国域名
→ 业务 IP 兜底
→ 中国 IP 兜底
→ MATCH
```

关键父子关系保持为：

```text
bing / msn / xbox → microsoft
onedrive           → microsoft
github             → microsoft
youtube            → google
geolocation-!cn    → cn_domain
```

## 为什么使用 MRS，而不是客户端 GeoData

本模板不配置 `GEOSITE`、`GEOIP`、`geodata-mode`、`geo-auto-update` 或 `geox-url`。公共规则直接声明 MRS URL 和更新周期，主要是为了：

- 手机和电脑引用相同的数据来源；
- 不依赖不同客户端内置 GeoData 的版本和标签完整性；
- 配置中的规则来源、格式和更新周期可以直接审计；
- MRS 在本地完成匹配，不会在每次连接时访问规则源。

## 本模板没有做什么

- 不向局域网其他设备开放代理端口，`allow-lan` 保持关闭；
- 不提供地区节点筛选、`url-test`、`fallback` 或负载均衡；
- 不启用 IPv6；
- 不保证拦截应用内置的 DoH / DoQ，TUN 的 DNS 劫持主要针对普通 TCP / UDP 53 查询；
- 不预先加入大量 NTP、STUN、游戏或厂商域名 Fake-IP 例外；
- 不保证公共 DNS 可以解析由家庭路由器自定义的局域网域名。

## 自动校验

安装校验脚本依赖：

```bash
python3 -m pip install PyYAML
```

执行仓库策略检查：

```bash
python3 scripts/validate_config.py config.example.yaml
```

如果本地已经安装 Mihomo，可以继续执行核心检查：

```bash
mkdir -p /tmp/mihomo-config-test
mihomo -t -d /tmp/mihomo-config-test -f config.example.yaml
```

GitHub Actions 会同时运行仓库策略校验，并下载经过摘要校验的 Mihomo v1.19.29 执行真实核心测试。

## 文件说明

| 文件 | 作用 |
| --- | --- |
| [`config.example.yaml`](./config.example.yaml) | 公开、脱敏的主配置模板 |
| [`scripts/validate_config.py`](./scripts/validate_config.py) | 仓库设计约束和脱敏检查 |
| [`.github/workflows/validate.yml`](./.github/workflows/validate.yml) | GitHub Actions 自动校验 |
| [`docs/design-notes.md`](./docs/design-notes.md) | 关键设计取舍和流量语义 |
| [`CHANGELOG.md`](./CHANGELOG.md) | 版本变更记录 |

## 维护原则

新增 Fake-IP 例外、Sniffer 跳过项、进程规则或独立服务分类前，先确认：

1. 问题可以稳定复现；
2. 能定位到具体机制；
3. 例外范围可以缩到足够小。

如果默认机制已经能够正确处理，就不继续增加特殊规则。

## 参考资料

- [Mihomo 配置文档](https://wiki.metacubex.one/config/)
- [Mihomo DNS 配置](https://wiki.metacubex.one/config/dns/)
- [Mihomo 路由规则](https://wiki.metacubex.one/config/rules/)
- [Mihomo Rule Provider](https://wiki.metacubex.one/config/rule-providers/)
- [MetaCubeX MRS 规则数据](https://github.com/MetaCubeX/meta-rules-dat)
