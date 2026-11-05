# P0：数据诚信修复报告

日期：2026-11-05
分支：`claude/magical-newton-6nyshr`（未合并到 `main`）
依据：`docs/reviews/2026-11-04-project-review-and-gmi-roadmap.md` 与已确认的规格
`docs/superpowers/specs/2026-11-04-scope-framework-and-markets-design.md`（决策 D1：只用真实数据）

---

## 1. 修复后发现的问题比 review 时更严重

除 review 中已列出的合成 deepdive 和手写 Policy Tracker 外，本次在修复过程中又发现：

| 位置 | 问题 | 真实值 vs 页面曾显示的值 |
|---|---|---|
| `scripts/enrich_macro_data_quality.py`（每次构建都会运行） | 往 canonical 里追加手写观测值，并标为 `verified / official_primary / current`，用来"消除过期标记" | **USD/CNY**：真实 6.733（2026-10-09），页面 7.1250；**中国 PPI**：真实 +3.8%（8 月），页面 −2.9%；**M1**：真实 +4.1%，页面 −7.4%；**FAI**：真实 −13.5%，页面 +3.4%；**CGB 10Y**：真实 1.61%，页面 2.15% |
| 同上 | BIS 信贷缺口为手写数据 | CN 真实 −5.1，页面 +15.8；KR 真实 −15.1，页面 +5.2（**连符号都反了**） |
| 同上 | ECB CISS 手写 | 真实约 0.008，页面 0.16 |
| 同上 | 构建时改写 `config/framework_v2.yaml`，虚增覆盖率 | 25 条错误映射，例如把货币水平量映射成"增长"概念，把建筑贷款映射成建筑活动 |
| 欧元区与土耳其 HICP | Eurostat 2026 年改用 ECOICOP 2018，旧数据集 `prc_hicp_manr` 停在 2025-12 | **欧元区 HICP 10 月为 4.0%，能源 +20.8%**，页面停在 2.0%（2025-12）；土耳其同样停在 2025-12 |
| 土耳其政策利率 | EVDS TP.APIFON4 实为"加权平均融资成本"，却被标成一周回购利率 | 改为 BIS 一周回购利率（36%，2026-10-23） |
| 日本、香港政策利率 | 日本用的是月均拆借利率（1.04%）；香港用的是美联储利率（3.88%） | BoJ 1.25%（2026-09-24 起）；HKMA 基本利率 4.25% |
| 中国 1Y LPR "3.10%"（2026-10-21） | 来自上述注入脚本，并非 AKShare | 真实为 3.00%（2025-05-20 起未变） |
| FRED 图表 CSV 回退 | 伪装成浏览器的 User-Agent 被 FRED 限流，请求挂到超时 | 改用如实的客户端标识后 0.4 秒返回 |

## 2. 本次修改

**数据来源**
- 新增共享模块 `src/country_primer/bis_policy.py`，以及三个共享 fetcher（`src/country_primer/shared_fetchers.py`，14 个 data-first 构建器全部接入）：
  - `bis_policy_rate`：BIS WS_CBPOL 日度政策利率，压缩为决议事件序列。单日来回跳动按数据源错误处理，排除后在页面上披露。
  - `bis_credit_gap`：BIS 信贷/GDP 缺口。
  - `bis_fx`：BIS 月末汇率，UZS 更新到 2026-09，EGP 更新到 2026-07。
- CEE 政策利率改为以 BIS 为主源；手工 YAML 降级为后备，使用时标 `watch`。HU 5.50%、CZ 3.75%；另补上了 YAML 漏记的波兰 2025-12 降息。
- 欧元区与土耳其 HICP 切换到 `prc_hicp_minr`（ECOICOP 2018），欧元区 geo 改用 `EA`。
- `refresh_bis_policy_snapshot.py` 在 refresh 时生成 `output/bis_policy_rates.json`，供离线交叉校验使用。

**删除合成与手写内容**
- `enrich_macro_data_quality.py` 重写，只保留可由 canonical 推导的计算：月度实际政策利率（不在政策利率序列结束后外推），以及韩国、台湾的期限利差。质量由评估得出，不再写死。
- 删除合成 deepdive 生成器：劳动力 deepdive（18 国）、全球/新兴市场/中国通胀 deepdive，共 7 个脚本，以及 30 个合成 JSON 产物。
- 新增 `scripts/real_deepdives.py` 与 `config/deepdive_views.yaml`：只渲染真实序列。动量按真实 3/6 个月变化年化；Beveridge 曲线只用真实的（U, V）配对；萨姆规则在数据有缺口时不计算；没有数据的面板不显示。
- Policy Tracker 改为从 canonical 计算：每个数值都带日期、来源和 BIS 参考值，过期数据有标记。删除会议日程、"consensus"与概率、走廊、资产负债表、点阵图和声明 diff，因为这些都是手写的。泰勒规则图标注为 MODEL，并公开参数。
- 删除没有可复现来源的占位指标，改记为数据缺口：中国核心 CPI、土耳其与香港 10Y、Euro Stoxx、S&P 500 YoY。
- 删除 25 条把水平量映射成增长概念的框架映射，构建过程不再修改配置文件。
- CEE 叙述性文字统一标注"静态分析，文中数字不是实时数据"。

**Bug 修复**：日本、南非首页卡片显示 "n/a"；My Dashboard 页面 JS 报错导致页面空白；`data_fetcher.py` 中 `ROOT` 未定义（GIE 储气和 Stooq 两个 fetcher 永远失败）；e-Stat `appId` 未脱敏（现在改为按值脱敏）；中国 PPI"指数"标签错误（它实际是"上年同月=100"）。

**防回归**（`tests/test_data_integrity.py`）
- 代码中不允许出现手写的日期序列。
- 构建步骤不允许写入 `config/`。
- 各页政策利率与 BIS 快照的差异不得超过 5bp。
- 增长类概念不允许映射到水平量序列。

**CI**：定时 workflow 先生成 BIS 快照，最后运行与本地相同的 `make rebuild-ui`；补传 6 个 secret；不再提交 `config/`。

## 3. 遗留问题（已在页面上如实标注）

- 中国约 29 个 Eastmoney 序列因上游接口改版而抓取失败，页面显示的是最后一次真实值，已标为过期。需要单独修复适配器。
- KZ、NG、UZ、EG 的原生政策利率仍未接入；IMF IFS 镜像分别止于 2020-12、2024-08、2024-12、2025-05。KZ/NG/UZ/EG 央行网站从本沙盒无法访问，需要在 CI 运行环境中接入。
- CEE 叙述文字（2026-04）和 `countries.yaml` 中的央行介绍是手写分析，已标注日期，需要整体重写或改为由数据生成。
- 泰勒规则参数，以及中国、尼日利亚等国的参考通胀目标，属于模型假设，已在页面公开。
