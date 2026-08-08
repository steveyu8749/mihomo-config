# Changelog

## V4.6

- Sniffer 改为纯识别模式：删除 HTTP 单独的 `override-destination: true`，HTTP / TLS / QUIC 均不覆盖实际目标。
- 删除所有地区筛选组、fallback 与 url-test 自动策略组；保留 `🌐 全部节点` 手工选择和各业务策略组。
- 机场 Proxy Provider 健康检查保持启用。
- 公共域名分类由大量 MetaCubeX MRS Rule Provider 迁移为 `GEOSITE`，包括 private、OpenAI、GitHub、Microsoft、Google、Apple CN、GFW、CN 等。
- `fake-ip-filter` 改为 `GEOSITE,private -> real-ip`、`RULE-SET,fakeip_compat -> real-ip`、`MATCH -> fake-ip`。
- `cn_ip` MRS 改为标准 `GEOIP,CN`；不启用 `geodata-mode: true`，继续使用默认 MMDB。
- Google / Telegram / Netflix 服务 IP 继续使用 MRS，不做全 GeoIP DAT 化。
- Rule Provider 从 26 个收敛为 6 个：`fakeip_compat`、`proxylite`、`adobeisdumb`、`google_ip`、`telegram_ip`、`netflix_ip`。
- 远程 Rule Provider 继续使用 86400 秒更新周期，下载策略从已删除的 `♻️ 自动选择` 改为 `🚀 默认代理`。
- 不启用 `allow-lan`、`respect-rules`、`geo-auto-update` 或自定义 `geox-url`。
- TUN 继续作为跨客户端基线保留；文档明确 GUI 客户端可能合并/覆写 TUN/DNS，应以最终运行配置为准。

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