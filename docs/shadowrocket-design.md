# Shadowrocket 设计说明

## 目标

Shadowrocket 配置不是 Mihomo YAML 的翻译产物。它只复用真正需要一致的分流意图，并采用 iOS 客户端原生、容易更新的实现：

1. 节点订阅与分流配置分离；
2. 公共规则直接使用 blackmatrix7 的 Shadowrocket 格式；
3. 自维护 Direct、ProxyLite、ProxyIP 从共享源自动转换；
4. Fake-IP 兼容项与共享 `FakeIPFilter.list` 保持一处维护；
5. 不引入 iOS 无法可靠复现的进程规则，也不加入 Adobe、MITM、脚本和重写。

## 节点与配置分离

`shadowrocket/shadowrocket.conf` 没有 `[Proxy]` 段，也没有订阅 URL。用户先在 Shadowrocket 首页添加机场订阅或节点，再导入配置。`🚀 默认代理` 使用：

```text
select, policy-regex-filter=.*
```

正则过滤器负责收纳已经导入的全部节点。Shadowrocket 的含正则筛选分组不应再混入显式策略；默认代理组也不包含 `DIRECT`，因此不会破坏“必须代理”的语义。各业务组再按需提供 `DIRECT`。

这样做的好处是节点更新不要求修改配置，配置更新也不接触订阅凭据。更换机场时只需调整首页订阅。

## DNS 与 Fake-IP

普通 DNS 使用 AliDNS 和 DNSPod DoH，直连与故障回退使用系统 DNS。`always-real-ip` 只包含共享 `rules/FakeIPFilter.list` 中已经确认的兼容项。

两种语法之间的映射是：

```text
+.example.com  → *.example.com
example.com    → example.com
```

前者分别是 Mihomo domain behavior 的后缀语法与 Shadowrocket 的通配语法。校验器会按顺序逐项比对，修改共享源后如果忘记同步配置，CI 会直接失败。

Real-IP 例外不会强制目标直连。DNS 返回方式与最终路由出口仍由两个独立层决定。

## 规则来源与优先级

配置按下列顺序匹配：

1. blackmatrix7 `Lan`；
2. OpenAI、Claude、Gemini、Copilot；
3. OneDrive、GitHub；
4. Bing、Xbox、Microsoft；
5. YouTube、Google；
6. Apple、TikTok、Speedtest、Telegram、Netflix、PayPal；
7. 本仓库 Direct、ProxyLite、ProxyIP；
8. blackmatrix7 Global、China；
9. `GEOIP,CN,DIRECT`；
10. `FINAL,🐟 漏网之鱼`。

专用服务必须位于宽泛父集合之前。例如 OneDrive 与 GitHub 都先于 Microsoft，YouTube 先于 Google。Bing 与 Xbox 单独列出是为了可读性和后续独立调整；MSN 已由 Microsoft 集合覆盖，当前三者都进入相同策略组，因此没有必要额外转换一份重复规则。

Global 作为境外常见规则层，China 加 `GEOIP,CN` 作为日常国内兜底。GEOIP 有意不加 `no-resolve`：未命中域名规则的少量目标仍可解析后按中国 IP 直连，这与 Mihomo 的 `cn_ip` 设计一致。没有使用体积明显更大的 ChinaMaxNoIP，因为本配置已经有 IP 兜底，额外规则量对日常命中收益有限。

## 自维护规则转换

`scripts/build_shadowrocket_rules.py` 执行以下转换：

```text
rules/Direct.list    → shadowrocket/rules/Direct.list
rules/ProxyLite.list → shadowrocket/rules/ProxyLite.list
rules/ProxyIP.list   → shadowrocket/rules/ProxyIP.list
```

domain behavior 的 `+.` 转为 `DOMAIN-SUFFIX`，普通完整域名转为 `DOMAIN`；IP 网络按地址族转为 `IP-CIDR` 或 `IP-CIDR6`，并附加 `no-resolve`。输出不保留注释，因为注释只属于共享源的维护上下文。

通配域名不会被生成器擅自猜测语义。若未来 Direct 或 ProxyLite 加入带 `*` / `?` 的规则，生成器会要求人工确认 Shadowrocket 表达方式。

## 明确不支持的内容

- `PROCESS-NAME`：iOS 不提供与 Windows / Android 相同的可维护进程匹配基础；
- Adobe：用户已决定只在电脑端按需启用；
- TUN、Sniffer、Rule Provider anchor：属于 Mihomo 配置模型；
- MITM、重写和脚本：不是当前纯分流目标所必需，也会扩大证书与隐私边界；
- 节点或机场凭据：必须与公开配置分离。

## 校验边界

`scripts/validate_shadowrocket.py` 检查：

- 只出现 General、Proxy Group、Rule、Host 四个段；
- DNS、Real-IP、更新 URL 与项目约定一致；
- 策略组名称、默认顺序和节点收纳方式正确；
- 25 条规则内容和优先级没有漂移；
- 所有规则目标都存在；
- 配置不包含节点、进程规则或 Adobe；
- RULE-SET 只通过 GitHub raw HTTPS 下载。

`scripts/test_shadowrocket_validator.py` 通过故障注入验证这些限制确实能拦截回归。它是仓库策略检查，不替代 Shadowrocket 应用本身的导入测试；首次发布后仍应在真实 iPhone 上完成一次远程更新、DNS、各策略组和常用服务的烟雾测试。
