# mihomo-config

[![Validate Mihomo template](https://github.com/steveyu8749/mihomo-config/actions/workflows/validate.yml/badge.svg)](https://github.com/steveyu8749/mihomo-config/actions/workflows/validate.yml)

一份面向 **手机 / 电脑本机 TUN 使用场景** 的 Mihomo 配置模板。当前版本为 **V4.3**。核心思路是让 TUN、DNS、Fake-IP、Sniffer 与 Rules 各自只解决自己的问题，避免为了“兼容”不断扩大例外列表。

## 设计目标

- 以 **TUN** 作为主要系统级接管方式，同时保留 `mixed-port`、`redir-port`、`tproxy-port` 作为额外入口。
- RFC1918 私网、链路本地、组播和广播地址在 TUN 路由层直接绕过，优先保证局域网发现和设备互联。
- `100.64.0.0/10` 作为 RFC6598 / CGNAT 可选项保留，但默认不开启。
- DNS 使用 **Fake-IP 作为默认行为**；Real-IP 只保留给局域网和少数系统级兼容场景。
- 普通国内域名同样可以使用 Fake-IP；是否 DIRECT 由 Routing Rules 决定，而不是由 Fake-IP / Real-IP 决定。
- 默认 DNS 上游使用国内 DoH，`direct-nameserver: system` 保留给最终确定为 DIRECT 的真实目标解析。
- Sniffer 用于恢复域名并辅助规则匹配；TLS / QUIC 默认不改写真实连接目标，HTTP 单独允许覆盖。
- OpenAI / ChatGPT 使用独立规则；Apple APNs 显式进入 `🍎 Apple`，Android FCM 继续由 Google 规则覆盖。
- 使用 YAML Anchor 减少 Provider、策略组和 Rule Provider 的重复配置。
- 进程规则保留 `find-process-mode: strict`，方便桌面端按进程分流。

## 文件

- `config.example.yaml`：完整公开模板，已经移除真实订阅地址、Token、私有服务器地址、UUID 和个人自定义规则源。
- `scripts/validate_config.py`：结构、脱敏、DNS 策略、规则顺序与 Rule Provider URL 检查脚本。
- `.github/workflows/validate.yml`：GitHub Actions 自动校验工作流。
- `CHANGELOG.md`：记录配置设计上的重要调整。
- `docs/design-notes.md`：解释 TUN、DNS、Sniffer、推送和规则优先级等关键取舍。
- `.gitignore`：避免实际使用的私密配置被误提交。

## 使用方法

1. 复制模板：

   ```bash
   cp config.example.yaml config.yaml
   ```

2. 在 `config.yaml` 中替换所有占位内容：
   - `YOUR_TOKEN_A / B / C`：机场订阅 Token，并同时替换对应订阅 URL
   - `your-vps.example.com`：自建节点服务器地址与 SNI
   - `00000000-0000-4000-8000-000000000000`：VLESS UUID
   - `YOUR_GITHUB_USERNAME / YOUR_RULE_REPO`：可选的个人 ProxyLite 规则源
   - 其他只属于你自己的节点或规则

3. `config.yaml` 已被 `.gitignore` 忽略，**不要强制提交真实配置**。

4. 导入 Mihomo / Clash Verge Rev 等兼容客户端后，再根据自己的网络环境测试 TUN、局域网发现、国内 App、国外 App 与推送通知。

## 自动校验

修改 `config.example.yaml`、校验脚本或工作流后，GitHub Actions 会自动运行检查。当前检查包括：

- YAML 是否能够正常解析。
- `proxy-groups` 引用的成员是否存在。
- Rules 指向的策略组 / 出站是否存在。
- `RULE-SET` 与 DNS `fake-ip-filter` 引用的 Rule Provider 是否存在。
- `geolocation-!cn` 是否在 `cn_domain` 前，避免宽泛 CN 集合抢先匹配。
- Routing 是否以 `MATCH` 收尾。
- ChatGPT 是否使用 `openai_domain` 专用规则。
- Apple APNs 是否存在显式 `push.apple.com` 分流，且位于宽泛 Apple 规则之前。
- DNS `fake-ip-filter` 是否以 `MATCH,fake-ip` 收尾。
- V4.3 是否误把整个 `cn_domain` 再次强制为 Real-IP。
- 私有域名、本地域名、Windows NCSI 和 APNs 等必要 Real-IP 例外是否仍然存在。
- 公开模板中的机场订阅地址、远程节点地址和 UUID 是否仍为占位形式。
- 常见 query-string Token / API Key / Secret 与 UUID 是否疑似误提交。
- 非占位的公开 Rule Provider URL 是否仍然可访问。

本地运行完整检查：

```bash
python -m pip install PyYAML
python scripts/validate_config.py config.example.yaml
```

如果当前环境无法联网，可以只跳过远程 URL 可达性检查：

```bash
python scripts/validate_config.py config.example.yaml --skip-network
```

这套检查用于发现 YAML、引用、规则优先级、公开资源失效和脱敏问题，**不等同于 Mihomo 内核的完整运行时验证**；真实配置仍应在实际客户端中测试。

## 关键取舍

### DNS / Fake-IP

V4.3 的默认原则是：

```text
只有明确需要真实 DNS 结果的场景 → Real-IP
其他所有普通域名                 → Fake-IP
```

当前 Real-IP 例外只有：

```text
private_domain
.local
home.arpa
msftconnecttest.com
msftncsi.com
push.apple.com
```

因此普通国内网站、国内 App 域名、Google、FCM、国外网站、NTP 等都默认可以得到 Fake-IP。**Fake-IP 不等于 PROXY，Real-IP 也不等于 DIRECT。** DNS 只负责向应用提供地址语义；真正的出口仍由 `rules` 决定。

例如一个国内域名可以经历：

```text
国内域名
→ DNS 返回 Fake-IP
→ 流量进入 TUN / Mihomo
→ cn_domain 命中
→ 🎯 直连
→ direct-nameserver: system 解析真实目标
→ DIRECT
```

这也是 V4.3 删除 `RULE-SET,cn_domain,real-ip` 的原因：没有必要为了让国内流量 DIRECT，就提前把整个中国域名集合排除出 Fake-IP。

V4.3 同时删除了以下 DNS 例外：

- `time.*.com`
- `pool.ntp.org`
- Google / GFW / ProxyLite / `geolocation-!cn` 的显式 `fake-ip`
- `services.googleapis.cn`
- `xn--ngstr-lra8j.com`
- `cn_domain -> real-ip`

前四类中的显式 Fake-IP 已被最终 `MATCH,fake-ip` 覆盖；时间同步和 Google 中国域名目前没有足够证据证明必须使用 Real-IP。如果以后出现可稳定复现的兼容问题，再增加最小范围的例外。

### 为什么仍保留少量 Real-IP

**局域网 / 私有域名**需要真实地址，因为应用可能需要直接看到 `192.168.x.x` 等本地地址，而且这些目标本身会在 TUN 路由层绕过。

**Windows NCSI** 会进行专门的 Web / DNS 连通性探测，其中 DNS 探测预期得到真实结果，因此继续保留 Real-IP。

**Apple APNs** 既显式进入 `🍎 Apple` 默认直连，又保留 Real-IP 和 Sniffer 跳过。原因是 Apple 平台的 VPN 可以让 APNs 等系统服务绕过隧道；如果某条连接绕过 Mihomo，它就不能解释 `198.18.0.0/16` 的 Fake-IP 映射。

### Sniffer

Sniffer 的核心作用是从 HTTP Host、TLS SNI、QUIC 握手中恢复域名，让域名规则在 TUN 场景仍然可用。模板采用：

- 全局 `override-destination: false`
- HTTP 单独 `override-destination: true`
- TLS / QUIC 主要用于识别域名，不主动替换应用原本的目标

这样更偏向兼容性，而不是最大程度介入连接目标。微信、QQ、小米以及 Apple Push 只保留已有实际兼容理由的 `skip-domain`，不继续预防性扩展。

### LAN / TUN

家庭私网直接通过 `route-exclude-address` 绕过 TUN，因此普通局域网流量不需要再进入 Mihomo 后通过规则 `DIRECT` 一次。

`100.64.0.0/10` 不是 RFC1918 私网，所以只以注释形式保留；只有确定自己的 CGNAT、Overlay 或其他网络确实使用它时再启用。

### iPhone / iPad 与 Android 推送

- iPhone / iPad 的系统级代理依赖 Packet Tunnel / VPN 机制；`redir-port` 与 `tproxy-port` 主要为其他平台预留。
- Apple APNs 使用 `push.apple.com` 显式进入 `🍎 Apple`，默认选择 `直连`，并保留 Real-IP 以兼容可能绕过 VPN 的系统流量。
- iOS 上国外 App 的业务流量仍按对应域名规则分流；“收到通知”和“打开 App 后访问国外服务”是两条不同链路。
- Android FCM 属于 Google 网络，本模板不增加粗粒度端口规则，而由 `google_domain` / `google_ip` 统一进入 `🍀 Google`。
- 国内厂商推送不额外写死规则，继续依赖国内域名 / IP 与最终规则自然直连。

### Rules 优先级

规则遵循“越具体越靠前，越宽泛越靠后”：

```text
私有/进程规则
→ 独立业务规则（OpenAI、Google、Apple、Telegram 等）
→ 自定义 ProxyLite / GFW
→ geolocation-!cn
→ cn_domain
→ IP 兜底
→ MATCH
```

`geolocation-!cn` 位于 `cn_domain` 前，是为了在两个集合存在交叉时优先保护明确的非中国服务。

## 安全

这个仓库应只保存**模板**。真实订阅 Token、UUID、私有服务器信息不要进入 Git 历史。即使以后将仓库改为 Private，也建议遵守同样原则。

## 说明

V4.3 之后的原则是：**不再因为“某类服务看起来特殊”而预防性添加 Fake-IP 例外。** 只有出现可以稳定复现、并且能确认与 Fake-IP 有关的问题时，才增加尽可能窄的 Real-IP 规则。