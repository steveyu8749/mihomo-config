# Changelog

## V4.6

- 保留 MRS 规则数据层，不依赖 `GEOSITE` / `GEOIP` 或客户端本地 GeoData。
- Sniffer 统一为“只识别、不改目标”，HTTP / TLS / QUIC 均不覆盖原始连接目标，并删除预防性的 `skip-domain`。
- 删除地区筛选、fallback、url-test 和共享 `🌐 全部节点`；只让 `🚀 默认代理` 使用 `include-all`，业务组改为在 `🚀 默认代理` 与硬直连之间选择。
- Proxy Provider 继续每 5 小时刷新订阅、每 10 分钟执行节点健康检查，并使用硬直连完成首次启动的节点加载。
- Rule Provider 不再固定下载代理，更新请求由当前路由规则决定；HTTP Provider 默认每 24 小时更新。
- DNS 使用规则模式 Fake-IP Filter：私有域名和最小兼容集合返回 Real-IP，其余域名统一返回 Fake-IP。
- 新增 `private_ip -> 直连,no-resolve`，为未被 TUN 路由排除覆盖的私有/保留 IP 提供规则层兜底。
- 保留 `cn_ip` 的解析能力，用中国 IP 识别未命中域名规则的国内目标；`apple_ip` 改为 `no-resolve`。
- Apple 域名由 `apple-cn.mrs` 扩展为完整的 `apple.mrs`。
- Windows `onedrive.exe` 保持硬直连，网页版 OneDrive 继续进入独立策略组。
- `category-ai-!cn` 保持为境外 AI 聚合集合，并统一复用 `🤖 ChatGPT` 策略组。
- Adobe 规则、Provider 和专用 YAML 锚点默认全部注释，只在桌面端按需启用。
- Bing、MSN、Xbox 继续单独列出并位于 Microsoft 宽泛集合之前。
- 补齐配置模板中遗漏的字段和规则注释，并补充 `PROCESS-NAME` / `PROCESS-NAME-REGEX` 的使用说明。
- 不启用 `allow-lan`、`respect-rules`、GeoData 自动更新或自定义 `geox-url`。
- 重写 README 和设计说明，使文档、注释、校验脚本与实际配置保持一致。

## V4.5

- 本次只调整 Rule Provider / Rule Set；TUN、Sniffer、端口、策略组、DNS 上游与 Keep Alive 均不变。
- 远程 Rule Provider 更新周期从 18000 秒统一调整为 86400 秒（24 小时）；机场 Proxy Provider 仍保持原来的 18000 秒。
- 新增本地 `inline` 域名规则集 `fakeip_compat`，集中管理少量 Real-IP 兼容项，避免引入整套第三方 Fake-IP 过滤列表。
- `fakeip_compat` 当前包含 `dns.msftncsi.com`、`+.push.apple.com`、`+.market.xiaomi.com`；其中小米项只用于应用商店类 Fake-IP 兼容，不作为局域网“小米互联”修复。
- `fake-ip-filter` 精简为 `private_domain -> real-ip`、`fakeip_compat -> real-ip`、`MATCH -> fake-ip`。
- 删除独立 `cnki_domain` Rule Provider 与对应路由规则；`cn_domain` 已通过 `geolocation-cn -> category-scholar-cn` 覆盖 CNKI，原配置属于重复分流。
- 不引入参考配置中的整套 `fakeipfilter-cn` / `fakeipfilter-!cn`、`private_ip`、`apple_ip`、`winupdate_domain`、NTP/STUN/UU 等额外规则集。

## V4.4

- 核实上游 `microsoft` geosite 包含 `github`，将 `github_domain` 调整到 `microsoft_domain` 前，修复 GitHub 独立策略可能被 Microsoft 提前命中的问题。
- 继续收敛 Fake-IP 例外：`private_domain` 已包含 `.local` 与 `home.arpa`，删除两条重复规则。
- Windows NCSI 仅保留 `dns.msftncsi.com -> real-ip`；删除范围过宽的 `msftconnecttest.com` 与整个 `msftncsi.com` Real-IP 例外。
- 撤回“给 NCSI 增加硬 DIRECT”的方案：NCSI 的固定 DNS 结果需求与 Routing 出口是两个问题，无需额外增加两条路由规则。
- 删除 APNs 的 Sniffer `skip-domain`；继续保留 `push.apple.com -> real-ip` 与 `push.apple.com -> 🍎 Apple`。
- `fake-ip-filter` 从 7 条缩减为 4 条，继续以 `MATCH,fake-ip` 作为默认行为。

## V4.3

- 普通国内域名改为默认 Fake-IP，DIRECT / PROXY 只由 Routing Rules 决定。
- 删除整个 `cn_domain -> real-ip` 保险和 NTP/Google 等重复 Fake-IP/Real-IP 项。

## V4.2

- 修正 Apple Provider 路径、APNs 路由、OpenAI 专用规则和关键规则顺序。

## V4.1

- 新增校验脚本与 GitHub Actions。

## V4

- 重整 TUN、DNS、Sniffer、策略组与规则结构，形成公开脱敏模板。
