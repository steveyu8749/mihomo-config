# proxy-routing-config

[![Validate proxy routing configs](https://github.com/steveyu8749/proxy-routing-config/actions/workflows/validate.yml/badge.svg)](https://github.com/steveyu8749/proxy-routing-config/actions/workflows/validate.yml)

一套同时面向 **Mihomo** 与 **Shadowrocket（小火箭）** 的个人代理分流配置。当前项目版本为 **V5.1**。

项目不追求把两种客户端机械转换成完全相同的文件，而是共享同一套分流意图：Mihomo 使用 MetaCubeX MRS 和完整的 TUN / DNS / 进程能力；小火箭使用 blackmatrix7 原生规则，并复用本仓库维护的 Direct、ProxyLite、ProxyIP 和 Fake-IP 兼容规则。

## 选择配置

| 客户端 | 配置入口 | 适用设备 | 主要特点 |
| --- | --- | --- | --- |
| Mihomo | [`mihomo/mihomo.yaml`](./mihomo/mihomo.yaml) | Windows、macOS、Linux、Android | TUN、Fake-IP、Sniffer、进程分流、MRS |
| Shadowrocket | [`shadowrocket/shadowrocket.conf`](./shadowrocket/shadowrocket.conf) | iPhone、iPad | 节点与配置分离、原生 RULE-SET / DOMAIN-SET、轻量服务分流 |

两端都不包含真实订阅、节点或凭据。公开文件可以安全复用，但填写过订阅地址的本地副本不要提交到仓库。

## 快速开始

### Mihomo

1. 下载 [`mihomo/mihomo.yaml`](./mihomo/mihomo.yaml)。
2. 把 `Provider_A`、`Provider_B`、`Provider_C` 中的 `订阅url` 替换为自己的订阅地址；数量不够时可继续按相同结构增加 Provider。
3. 在 Clash Verge Rev 或其他 Mihomo 客户端中导入该 YAML。
4. 首次启动后，在 `🚀 默认代理` 中选择实际节点，再按需要调整各业务组。

模板把机场订阅本身固定为硬直连下载，解决首次启动时“还没有节点，却要先通过节点下载订阅”的循环依赖。Rule Provider 没有强制指定下载出口，其更新请求由当时已有路由策略决定。

### Shadowrocket（小火箭）

节点和分流配置可以分开，推荐也确实应该分开：

1. 在 Shadowrocket 首页单独添加机场订阅或节点。
2. 使用下面的远程地址导入配置：

   ```text
   https://raw.githubusercontent.com/steveyu8749/proxy-routing-config/main/shadowrocket/shadowrocket.conf
   ```

3. 启用该配置后，进入 `🚀 默认代理` 选择节点。
4. Apple 默认直连；其他服务默认继承 `🚀 默认代理`，都可单独切换为 `DIRECT`。

小火箭配置不保存节点，不包含 `PROCESS-NAME`、Adobe 拦截、Mihomo TUN 字段或整份 YAML 的机械翻译。这样机场订阅可以独立更新，分流配置也可以独立更新。

## 分流结构

两端的规则顺序遵循同一原则：私有网络最先处理，专用服务先于宽泛厂商集合，自维护例外先于地域兜底，最终再交给漏网之鱼。

| 层级 | Mihomo | Shadowrocket |
| --- | --- | --- |
| 私有网络 | MetaCubeX `private_domain` / `private_ip` | blackmatrix7 `Lan` |
| AI | `category-ai-!cn` | OpenAI、Claude、Gemini、Copilot |
| Microsoft 子类 | OneDrive、GitHub、Bing、MSN、Xbox 优先 | OneDrive、GitHub、Bing、Xbox 优先；MSN 由 Microsoft 覆盖 |
| 其他服务 | Google、YouTube、Apple、Telegram 等专用 MRS | 对应 blackmatrix7 原生 Shadowrocket 列表 |
| 本仓库规则 | Direct、ProxyLite、ProxyIP | 同一规则源自动转换后的 classical 列表 |
| 地域兜底 | GFW、`geolocation-!cn`、CN 域名/IP | Global / China 的 Domain 与 classical 两部分、`GEOIP,CN` |
| 最终兜底 | `MATCH,🐟 漏网之鱼` | `FINAL,🐟 漏网之鱼` |

blackmatrix7 与 MetaCubeX 的数据不会逐条完全一致，但它们都来自持续维护的主流规则生态。对日常使用而言，保持清晰的优先级和可维护边界，比强行追求两个不同客户端逐条一致更可靠。

## 共享规则源

`rules/` 是唯一需要手工修改的本地规则目录。

| 文件 | 含义 | Mihomo 产物 | Shadowrocket 产物 |
| --- | --- | --- | --- |
| [`rules/Direct.list`](./rules/Direct.list) | 必须硬直连的域名补充 | `mihomo/mrs/Direct.mrs` | `shadowrocket/rules/Direct.list` |
| [`rules/FakeIPFilter.list`](./rules/FakeIPFilter.list) | Fake-IP 会导致明确故障的 Real-IP 例外 | `mihomo/mrs/FakeIPFilter.mrs` | 嵌入 `always-real-ip` |
| [`rules/ProxyLite.list`](./rules/ProxyLite.list) | 必须进入默认代理的域名补充 | `mihomo/mrs/ProxyLite.mrs` | `shadowrocket/rules/ProxyLite.list` |
| [`rules/ProxyIP.list`](./rules/ProxyIP.list) | 必须进入默认代理的精确 IP | `mihomo/mrs/ProxyIP.mrs` | `shadowrocket/rules/ProxyIP.list` |

`mihomo/mrs/` 与 `shadowrocket/rules/` 都是生成目录，不应手工修改。MRS 二进制不保留源文件注释；小火箭列表也只保存可执行规则，便于下载和匹配。

### Direct 不是日常直连全集

`Direct.list` 只存放有明确硬直连理由的补充项，目前重点是需要校园或机构出口 IP 认证的科研资源。普通中国域名和中国 IP 已分别由 Mihomo 的 `cn_domain` / `cn_ip`，以及小火箭的 China / `GEOIP,CN` 处理；把它们再复制到 Direct 只会增加重复和维护成本。

专用服务规则位于 Direct 之前，因此 Google、Microsoft、Apple 等服务仍会进入各自策略组。

### Fake-IP Filter 只解决兼容故障

Fake-IP 是否可用，与域名应该直连还是代理是两个问题：

- `Direct.list` 决定出口；
- `FakeIPFilter.list` 决定 DNS 返回真实 IP 还是 Fake-IP。

当前兼容集只保留 Windows NCSI、Google Play 中国前端、Apple APNs、小米系统服务、Wi-Fi Calling、Plex 和微信本地回调等有明确机制的条目。普通国内或国外域名只要 Fake-IP 下能正常工作，一律不加入。

NTP 域名没有加入兼容集。系统校时通常直接使用真实 UDP/IP，现阶段没有证据表明这些域名在本配置的 Fake-IP 模式下会稳定故障；提前加入大量 NTP 例外只会扩大 Real-IP 范围。如果以后出现可复现的校时问题，应定位到具体主机后再最小化补充。

### ProxyLite 的优先级

ProxyLite 是个人代理补充，不是主分类库。它放在全部专用服务与 Direct 之后、Global/GFW/地域规则之前，既能覆盖个人例外，也不会抢先遮蔽 OneDrive、GitHub、Microsoft、Apple 等独立策略组。IP 规则单独放在 `ProxyIP.list`，并使用 `no-resolve`，避免为了匹配精确地址主动解析域名。

## Mihomo 关键设计

### DNS

- 默认使用 Fake-IP；`private_domain` 与 `fakeip_compat` 返回真实 IP。
- 主 DNS 为 AliDNS 与 DNSPod DoH，DIRECT 目标使用系统 DNS。
- 不启用 `respect-rules`。它主要用于让 DNS 上游连接也严格遵守代理规则，例如境外 DoH 必须通过某个代理组访问；当前两个国内 DoH 本来就适合直连，没有必要引入额外依赖。
- 不显式设置 `cache-algorithm`，继续使用默认 LRU。ARC 可以使用，但在没有缓存命中或抖动数据前，不假设它一定更快。

`private_ip` 包含 `198.18.0.0/15`，而 Fake-IP 地址池使用 `198.18.0.1/16`。这不会把正常 Fake-IP 流量误判为私网：Mihomo 在规则匹配前会根据 Fake-IP 映射恢复域名，不会再拿映射地址命中 `private_ip`。`private_ip,no-resolve` 仍用于纯 IP 和未被 TUN 路由排除覆盖的私有流量。

### TUN 与 Sniffer

- TUN 使用 `mixed` 栈并接管 UDP/TCP 53。
- 公共跨平台模板不启用 `strict-route`。它加强系统路由接管与防泄漏，不会让规则“匹配得更严格”，并可能影响 Windows 虚拟化或多宿主网络。确有防泄漏需求时可在个人副本按平台开启。
- Sniffer 只恢复域名，不覆盖原始目标；没有预设 `skip-domain`。只有出现稳定可复现的误嗅探时，才增加最小范围例外。

### 进程规则与 OneDrive

Mihomo 保留少量桌面/Android 进程规则：

- `PROCESS-NAME`：忽略大小写的精确进程名或 Android 包名匹配；
- `PROCESS-NAME-WILDCARD`：使用 `*`、`?` 完成简单通配；
- `PROCESS-NAME-REGEX`：只适合真正需要分组、边界或多分支的正则。

`*xboxone*` 表示名称前后都可出现任意字符，因此可以匹配任意包含 `xboxone` 的进程或包名。进程分流依赖系统提供进程信息，在路由器等无法识别终端进程的平台不会命中；小火箭配置完全不包含进程规则。

OneDrive 的设计是刻意分层：Windows `onedrive.exe` 直连，本地同步不受影响；浏览器不会命中进程规则，网页版 OneDrive 继续进入 `🐬 OneDrive` 策略组。

### Adobe

Adobe 规则在 Mihomo 文件中只保留注释后的桌面启用入口，默认不加载；小火箭配置不包含 Adobe 内容。需要时请只在自己的电脑配置副本中同时启用路由规则、YAML anchor 和 Provider。

## Shadowrocket 关键设计

- 节点订阅与配置文件分离，仓库不会绑定机场格式。
- `🚀 默认代理` 只使用 `policy-regex-filter=.*` 收纳已导入节点，同时不混入显式策略或 `DIRECT`。
- 业务组只在 `🚀 默认代理` 与 `DIRECT` 间切换；Apple 顺序相反，默认直连。
- `always-real-ip` 必须与 `rules/FakeIPFilter.list` 保持一致，校验器会阻止遗漏。
- 公共规则使用 blackmatrix7 的 Shadowrocket 原生格式；Apple、Global、China 按上游要求同时加载 Domain Set 与 classical 两部分，避免只载入 IP / UA 等规则而遗漏主体域名。
- 不下载超大的 `ChinaMaxNoIP`，使用 China Domain/Classical 加 `GEOIP,CN` 兜底。
- 代理节点不支持 UDP 时使用 `REJECT`，避免“必须代理”的 UDP 静默降级为直连。
- 使用最小 TUN 旁路改善私网、组播、广播与 mDNS；不旁路 Fake-IP 地址池，也不预防性排除可能影响 Tailscale 的 `100.64.0.0/10`。
- 没有 `[Proxy]`、MITM、重写、脚本、进程或 Adobe 规则，降低首次使用和后续维护复杂度。

架构边界见 [`docs/shadowrocket-design.md`](./docs/shadowrocket-design.md)；每个配置段、参数和规则的具体理由见 [`docs/shadowrocket-config-guide.md`](./docs/shadowrocket-config-guide.md)。

## 自动生成与校验

GitHub Actions 固定使用 Mihomo **v1.19.29** 和 PyYAML 6.0.3。每次相关改动会执行：

1. Mihomo 仓库策略校验与 18 个故障注入测试；
2. 四份共享规则的 text → MRS 转换；
3. Mihomo 核心 `-t` 真实配置检查；
4. Shadowrocket 三份 classical 规则生成；
5. 小火箭配置校验与 10 个故障注入测试。

只有 `main` 上全部检查通过后，写入 job 才能提交生成物。PR 始终只读，`mihomo/mrs/` 和 `shadowrocket/rules/` 不在触发路径中，因此机器人提交不会形成循环。

本地检查：

```bash
python3 -m pip install PyYAML==6.0.3
python3 scripts/validate_config.py mihomo/mihomo.yaml
python3 scripts/test_validator.py
python3 scripts/build_shadowrocket_rules.py
python3 scripts/build_shadowrocket_rules.py --check
python3 scripts/validate_shadowrocket.py shadowrocket/shadowrocket.conf
python3 scripts/test_shadowrocket_validator.py
```

安装 Mihomo 后还可执行核心检查：

```bash
mkdir -p /tmp/proxy-routing-config-test
mihomo -t -d /tmp/proxy-routing-config-test -f mihomo/mihomo.yaml
```

## 目录结构

| 路径 | 用途 |
| --- | --- |
| [`mihomo/mihomo.yaml`](./mihomo/mihomo.yaml) | Mihomo 公开脱敏主配置 |
| [`mihomo/mrs/`](./mihomo/mrs/) | Actions 生成的 Mihomo MRS 二进制规则 |
| [`shadowrocket/shadowrocket.conf`](./shadowrocket/shadowrocket.conf) | 小火箭远程配置 |
| [`shadowrocket/rules/`](./shadowrocket/rules/) | 自动生成的小火箭 classical 规则 |
| [`rules/`](./rules/) | 两端共享、唯一手工维护的自定义规则源 |
| [`scripts/`](./scripts/) | 生成器、校验器与回归测试 |
| [`docs/mihomo-design.md`](./docs/mihomo-design.md) | Mihomo 机制与取舍 |
| [`docs/shadowrocket-design.md`](./docs/shadowrocket-design.md) | 小火箭架构与使用边界 |
| [`docs/shadowrocket-config-guide.md`](./docs/shadowrocket-config-guide.md) | 小火箭逐节配置说明、与常见模板的差异及排障方法 |
| [`.github/workflows/validate.yml`](./.github/workflows/validate.yml) | CI 校验与生成物发布流程 |

## 维护原则

新增规则前先确认：问题可以复现、原因可以解释、范围可以最小化、优先级不会遮蔽专用服务，并且相应校验与文档同步更新。能由已有公共分类解决的问题，不重复塞进自维护列表。

## 主要上游

- [MetaCubeX/meta-rules-dat](https://github.com/MetaCubeX/meta-rules-dat)：Mihomo 公共 MRS；
- [blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script/tree/master/rule/Shadowrocket)：Shadowrocket 原生规则；
- [LOWERTOP/Shadowrocket](https://github.com/LOWERTOP/Shadowrocket)：Shadowrocket 社区使用手册与配置语法参考。
