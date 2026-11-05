# 交接文档（给新会话）

更新：2026-11-05。分支 `claude/magical-newton-6nyshr` 已通过 PR #6 合并入 `main`；之后的工作从 `main` 新建分支。
新会话请先读本文件，再读 `AGENTS.md` 和 `PROJECT_LESSONS.md`（§9 是数据诚信规则）。

---

## 0. 同步与版本（请先读，避免倒回旧版本）

**现状**：`main` 已包含全部改动（PR #6，2026-11-05），是唯一的基线。`claude/magical-newton-6nyshr` 只作历史保留，不再在上面开发。

**开始一次会话**（本地 `/Users/jiangwei/Claude/Country_Primer` 或云端）

```bash
git status                                # 有未提交改动先处理
git switch main && git pull --ff-only     # 必须 fast-forward；失败就停下来检查，不要强推
git switch -c <topic-branch>              # 每项新工作一个分支
```

**结束一次会话**：`make validate` 通过 → commit → `git push -u origin <topic-branch>` → 开 PR → 等 CI（`Validate dashboard` 在 PR 上运行；看 `status == completed` 和 `conclusion`）→ CI 通过就合并，然后跑 publish_smoke.py --version <合并提交> 检查线上页面。交接内容写进本文件，不要只留在对话里。合并后本地执行 `git switch main && git pull --ff-only`。

**规则**

1. `main` 上的定时刷新（Scheduled Macro Data Refresh & Publish：cron 是每天 02:00 UTC，实际通常 08:00–09:00 UTC 才开始）会直接向 `main` 提交生成文件。合并 PR 时如果生成文件冲突：代码、`config/`、`docs/`、`tests/` 以 PR 分支为准；生成文件（`output/`、根目录的 `*.html`、`*_AUDIT.md`、`CORE_COVERAGE_MATRIX.md`、`DATA_SOURCE_CATALOG.md`、`MACRO_WORKBENCH_BRIEFING.md`、`chart_studio_catalog.json`）也以 PR 分支为准，然后用 `make rebuild-ui && make validate` 重新生成。
2. **自检**（任一项不满足，说明拿到的是旧版本）：
   - `config/scopes.yaml`、`docs/HANDOFF.md` 和 `scripts/build_scope.py` 存在；
   - `scripts/build_turkey_dashboard.py` 已经不存在；
   - `make validate` 通过（测试数 ≥ 186），其中 `tests/test_data_integrity.py` 会拒绝手写序列和占位回退值。
3. 不要在两个地方同时改同一个分支；并行工作各开一个分支。
4. 被 gitignore 的本地文件（`.env.local`、`.venv/`、`.uv-cache/`、`cache/`）不会同步，换机器时需要重新准备；key 只放 `.env.local`。
5. 切换到 Pages 方案 C 以后，数据在 `data` 分支，见 `docs/PAGES_DEPLOYMENT.md`。

## 1. 用户已确认的决策

| 编号 | 决策                                                                                 |
| -- | ---------------------------------------------------------------------------------- |
| D1 | **只用真实数据**。缺数据就留空或记为 data gap，不写死、不估算、不用 0 或 50 之类的占位值                             |
| D2 | 顺序：P0 诚信修复 → 能源 → 贵金属 → 基本金属；重点是框架，降低以后加国家的成本                                      |
| D3 | 能源页包含电力和煤；模型可以做，但必须标 MODEL，并且不进 canonical frame                                    |
| D4 | key 只放在本地或环境密钥里，**绝不能贴进对话、提交到仓库或写进日志**                                             |
| D5 | Pages 采用方案 C（`data` 分支 + Actions 部署），并放在开关后面，由用户切换（见 `docs/PAGES_DEPLOYMENT.md`）   |
| 其他 | 试点国家是印度；中国数据以 AKShare 为主，NBS 官方接口在境外 403，DBnomics 的 NBS 镜像已停更；**不要改动 `main` 上的数据** |

## 2. 已完成（按提交顺序）

1. **P0 诚信修复**：删除合成数据和手写注入；政策利率改用 BIS WS_CBPOL；Policy Tracker 由数据生成；修复中国数据源（AKShare 超时 bug）；增加防回归测试。报告见 `docs/reviews/2026-11-05-p0-data-integrity-fixes.md`。
2. **F1 框架**
   - `config/scopes.yaml` 是页面注册表；`scripts/build_scope.py` 是通用构建器（替代了 14 个逐国脚本）。
   - `src/country_primer/fetchers.py` 是全局数据源注册表。
   - 所有消费方从注册表读取国家列表。
   - 指标模板放在 `config/templates/`，由 `src/country_primer/indicator_templates.py` 展开。
   - 印度试点只用了两个文件：注册表条目和 `config/countries/india.yaml`。
   - Pages 方案 C 已就绪（`scripts/data_branch.sh` 和 `.github/workflows/deploy_pages.yml`），由 `PAGES_MODE` 变量控制。
3. **F2 能源页**（`config/markets/energy.yaml`，54 张图）
   - 注册表新增市场类型 `kind: market`。
   - 免 key 数据源写在 `src/country_primer/energy_adapters.py`：EIA 历史表、CFTC 持仓、energy-charts 电价、外盘期货、上海黄金交易所。
   - 派生序列由 `src/country_primer/derived.py` 计算，只允许白名单算子。
   - 跨经济体面板在 `src/country_primer/transmission.py`（能源冲击对照表）。
4. **M2 贵金属页**（`config/markets/precious_metals.yaml`，49 张图）：价格、比价、本币金价、实际利率与美元、18 家央行黄金储备（IMF IL）、上海溢价、CFTC 持仓。
5. **M3 基本金属页**（`config/markets/base_metals.yaml`，47 张图）：LME 三个月期 6 种金属、SHFE/DCE/GFEX 主力（含铁矿石、螺纹、氧化铝、碳酸锂）、上期所进口窗口（含 13% 增值税）、COMEX–LME 铜价差、上期所库存（数据源只有约 3 个月）、IMF 月度（含钴、锂；IMF 锂序列实为人民币/吨）、中国需求（`reference` 算子直接引用中国页序列）、CFTC 铜、铜金比与铜相关货币。
6. **油价冲击 → CPI 模型**（MODEL）：`src/country_primer/oil_shock_model.py`，输出 `output/models/oil_shock_cpi.json`，显示在能源页宏观传导版块，冲击幅度可在页面上编辑。传导系数由能源 CPI 同比对本币布伦特同比（滞后 0–6 个月，自 2015 年起）的 OLS 回归估计；能源权重取官方数据（Eurostat `prc_hicp_iw` 的 NRG，以及 ONS CJVF），作为输入序列放在能源页的模型输入版块。美国权重无免费来源（BLS 返回 403），记为缺口。土耳其新增 BIS 月度 `usd_try_bis`。
7. **本币汇率历史**：CEE 的 `fx_vs_eur` 原先只取 ECB 最近 90 天的 XML，现在改为 ECB Data API（`EXR/D.<CUR>.EUR.SP00.A`）自 2010 年的完整日度历史（`src/country_primer/fetch.py`，90 天 XML 只作后备）。已用 Alpha Vantage 月末收盘价交叉核对 HUF，差异 ≤0.3%。现在所有经济体的本币油价都有数据，模型也全部改用本币。
8. **能源页的带 key 数据源**（2026-11-05，能源页 61 → 86 张图）
   - 新 fetcher（`energy_adapters.py`，已在 `fetchers.py` 注册）：`eia_steo`（EIA STEO，API v2）、`gie_agsi`（GIE AGSI+ 储气，`x-key` 头）、`ember_generation`（Ember 月度发电结构）。出错信息只含来源和 HTTP 状态，不含 URL（URL 里可能有 key）。
   - `eia_steo` 只保留到「当前月 −2」：STEO 的汇总序列含预测，一直到明年年底，预测不上页面（D1）。`steo_unit` 用来核对 EIA 报告的单位，不一致就让该图为空，而不是标错单位。
   - 新增图表：OPEC/OPEC+ 原油产量、OPEC 闲置产能、7 个产油国（沙特、俄罗斯、伊拉克、伊朗、哈萨克斯坦、利比亚、委内瑞拉；STEO 没有单列阿联酋）、全球液体燃料产量与消费、中国与印度消费、全球净库存提取、OECD 商业库存及相对五年同月偏离、欧盟与德国储气率及欧盟相对五年同日偏离、欧盟燃气/燃煤/风光发电占比、中国与印度燃煤发电占比。
   - `derived.py` 的 `dev_from_5y_seasonal` 新增日度分支（比较同一日历日，2 月 29 日自然丢弃）；原来的周度和月度行为不变。
   - CEE `gas_storage_level`：`data_fetcher.GIEAGSIFetcher` 改为调用同一个 AGSI 客户端，缓存按天过期（原来的缓存永不过期，URL 和鉴权头也是猜的）。四国现在是 2015 年起的日度序列，单位 `% WGV`，来源等级 official_primary；ENTSOG 手录快照只在没有 key 时作后备。

## 3. 架构速查

| 要做的事                       | 位置                                                                                                                                                                                                                                                                  |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 新增国家（不改代码）                 | `config/scopes.yaml` 加一条 + `config/countries/<slug>.yaml`（templates + params），见 AGENTS.md「Adding a Country」                                                                                                                                                         |
| 新增市场页                      | `config/scopes.yaml`（`kind: market`，排在经济体之后）+ `config/markets/<slug>.yaml`                                                                                                                                                                                          |
| 新数据源                       | 在 `adapters.py` 或 `energy_adapters.py` 写函数，然后在 `fetchers.py` 的 `FETCHERS` 里注册（写明 call 方式、后处理模式、所在模块）                                                                                                                                                                |
| 派生序列                       | YAML 里写 `derivation: derived`、`op`、`inputs`。可用算子：reference、spread、linear、ratio、product、rolling_mean、zscore、dev_from_5y_seasonal、yoy_pct，输入可加 `@monthly_mean`，可跨 scope 引用（如 `ENERGY:brent_spot`、`CN:manufacturing_pmi_akshare`）。市场页按注册表顺序构建：ENERGY → PRECIOUS → BASE |
| 面板（表格）                     | `transmission.py` 的 `PANELS`；在市场 YAML 里用 `panels:` 声明                                                                                                                                                                                                               |
| 跨国角色（政策利率、CPI、能源 CPI、汇率方向） | `config/scopes.yaml` 各 scope 下的 `roles`                                                                                                                                                                                                                             |
| 核心 48 映射                   | `config/framework_v2.yaml`，或在指标 YAML 上加 `concept:`（会自动合并）                                                                                                                                                                                                           |
| 来源等级                       | 在 YAML 里声明 `source_authority`（official_primary / official_mirror / public_wrapper），否则按名字推断                                                                                                                                                                          |

## 4. 工作方式与验证

```bash
scripts/uv_project.sh run python scripts/build_scope.py <ID>         # 联网刷新一个 scope
COUNTRY_PRIMER_ONLY_INDICATORS=a,b scripts/uv_project.sh run python scripts/build_scope.py <ID>   # 只刷新指定指标
make rebuild-ui                                                        # 离线重建全部页面
make golden-diff                                                       # 与 HEAD 比较（忽略时间戳）；重构时必须为 0 差异
make validate                                                          # 提交前必须通过（当前 186 个测试）
scripts/uv_project.sh run python scripts/publish_smoke.py --local      # 页面冒烟检查
```

- 提交信息结尾要带会话要求的归属行。每项工作一个分支加一个 PR；合并由用户决定。
- snapshot 模式（`rebuild-ui`）不会重写 canonical frame；要更新数据或来源字段，需要对那个 scope 做一次 refresh。
- 截图检查：Playwright 已预装，参考写法 `node shot.js <html> <png>`（用 `chromium.launch()`）。

## 5. 密钥

- 变量名：`FRED_API_KEY`、`EIA_API_KEY`、`GIE_AGSI_API_KEY`、`EMBER_API_KEY`、`ENTSOE_API_TOKEN`、`ESTAT_APP_ID`、`BLS_API_KEY`、`BOK_ECOS_API_KEY`、`TCMB_EVDS_API_KEY`、`FINMIND_API_TOKEN`、`KOSIS_API_KEY`。
- 云环境的密钥只对新开的会话生效。**新会话第一步**：只检查变量名是否存在，不要打印值，例如：
  `for k in EIA_API_KEY GIE_AGSI_API_KEY EMBER_API_KEY ENTSOE_API_TOKEN; do [ -n "$(printenv $k)" ] && echo "$k set" || echo "$k missing"; done`
- 本地运行时，`scripts/uv_project.sh` 会读取被 gitignore 的 `.env.local`。日志按值脱敏（`source_health.py`）。
- 2026-11-05 本地状态：EIA、GIE、Ember、FRED、ESTAT、BLS、TCMB、FinMind、ENTSO-E 都在 `.env.local`；BOK_ECOS、KOSIS 本地没有（GitHub secrets 里有 BOK_ECOS，没有 KOSIS）。
- **ENTSO-E**：token 已配置，但 API 对所有请求返回 `999 User is not authorized`。这是账户还没开通 Restful API 权限：需要用户用注册邮箱发邮件给 <transparency@entsoe.eu>，主题写 "Restful API access"。开通后再接 fetcher。

## 6. 待办（按优先级）

1. **能源页里需要 key 的部分**：EIA STEO、GIE AGSI+、Ember 和 CEE 储气率已完成（见 §2 第 8 项）。剩下的是 **ENTSO-E**，等用户开通 API 权限（见 §5）。开通后建议先做：德国燃气发电（日度，代表电力部门的燃气需求）、法国核电发电量（日度）、挪威水库蓄水（周度）。
2. **油价模型的后续**：美国能源权重（BLS relative importance，可尝试其他公开镜像）；英国车用燃料（07.2.2）纳入能源口径；更长的滞后窗口或分段样本；二轮效应模型（另立 MODEL，不与一轮效应混在一起）。
3. **基本金属页的后续**：矿山供给（Cochilco、INE、MINEM）、中国精炼产量和分品种进出口、COMEX 铜库存、更长的上期所库存历史（可以考虑在 refresh 时累积历史）、上期所近远月价差。
4. **后续小项**
   - KZ/NG/UZ/EG 的原生政策利率。
   - CEE 叙述文字需要重写（例如 HU 行长写的还是 Matolcsy，应为 Varga）。
   - 欧元区职位空缺和协议工资已过期。
   - **已知 bug（未修）**：`scripts/dashboard_summary_utils.load_canonical_data_first_frame` 读回上一版快照时不恢复 `prior_vintage`/`has_revisions`，所以 `track_revisions_and_vintages` 里「沿用前次 vintage」的分支拿到的总是 None：前次数据只能保留一次构建，下次刷新就丢。2026-11-05 刷新中国卡片时，`usd_cny_midpoint` 的前次数据就这样被清掉了。
   - 中国 PBC 卡片（2026-11-05 已修）：DR007 页面的「Latest Update」是浏览器用访问者当天日期填的，所以卡片日期取页面的 `createDate`（M2 页的 createDate 与显示的更新日期一致）。DR007 当前值 1.4935% 的日期是 2026-09-23，PBC 英文页更新不频繁；要看日度 DR007 需另接时间序列。
   - 印度 IMF FSI 返回 403；可接入 MOSPI/RBI 原生数据。
   - 黄金 ETF 持仓缺来源；可加 `rolling_beta` 算子（金价对实际利率）。
   - Pages 切换由用户操作；第三阶段（`main` 不再跟踪生成文件）见 `docs/PAGES_DEPLOYMENT.md`。

## 7. 环境与数据源特性（已实测）

| 数据源           | 情况                                                                                                           |
| ------------- | ------------------------------------------------------------------------------------------------------------ |
| energy-charts | 连续请求会返回 429，fetcher 已加 Retry-After 退避                                                                        |
| IMF           | `IMF.STA,IL` 的 key 是 `<ISO3>.RGV_REVS.FTO.M`（四段，五段会 403）；FSIC 数据流在本环境返回 403                                  |
| FRED          | 部分 OECD 镜像已停更（印度 10Y 与 3M、M3 等）。不要上页面，记为 gap                                                                 |
| EIA           | 期货曲线 RCLC1-4 止于 2024-04-05                                                                                   |
| 中国            | Eastmoney 部分接口会重置连接；NBS easyquery 返回 403                                                                     |
| 外盘期货 / SGE    | 当天那一行是未收盘的会话，fetcher 只保留已收盘的交易日                                                                              |
| GIE AGSI+     | `?type=eu` 是欧盟合计，`?country=XX` 是分国；每页最多 300 天，按 `last_page` 翻页（`total` 是当页行数）；行按日期倒序；最近几天 `status` 为 `E`（估计） |
| EIA STEO      | 分国序列只到最后一个历史月（2026-11 时是 2026-09）；汇总序列带预测到明年年底；没有阿联酋原油产量                                                     |
| Ember         | 欧盟用 `entity=EU`（`entity_code` 为空），国家用 ISO3 `entity_code`；月度数据从 2016 年起（印度从 2019 年起）                          |
| ENTSO-E       | token 未开通 API 权限时一律返回 `999 User is not authorized`                                                           |

## 8. 当前关键读数（做 sanity check 用，2026-11-05 构建）

- **能源**
  - 原油：Brent 现货 107.03（11-03）；近月期货 94.55（11-04）。
  - 裂解价差：3-2-1 为 $44/桶，柴油为 $95.5/桶。
  - 电价与天然气：德国日前电价 €249/MWh；欧美气价差 $22.5/MMBtu。
  - 能源通胀：美国能源 CPI +20.4%，欧元区能源 HICP +20.8%。
- **贵金属**
  - 价格：金 4,072；银 52.3；金银比 77.8。
  - 驱动与比较：10Y 实际利率 2.65%；上海金较 COMEX 低 $73。
  - 央行购金（过去 12 个月）：波兰 +157 吨，乌兹别克斯坦 +67 吨，哈萨克斯坦 +57 吨，中国 +48 吨。
- **基本金属**：伦铜 14,013、沪铜 106,170；COMEX–LME 铜价差 +$120/t；沪铜进口窗口 −¥207/t；上期所铜库存 6,574 t（7 月底为 26,924 t）；铜价同比 +44.8%（9 月）。
- **国家**：印度 RBI 5.50%（与 BIS 一致）；USD/INR 94.94。
- **能源（带 key 数据源，2026-11-05 刷新）**
  - 储气：欧盟 74.07%（11-03），相对五年同日 −15.8pp；德国 60.56%；CEE：匈牙利 76.9%、波兰 99.0%、捷克 75.4%、罗马尼亚 88.1%。
  - STEO（2026-09）：OPEC 原油 20.8 mb/d，OPEC 闲置产能 0.02 mb/d（2026-01 为 2.96）；全球消费 104.24、产量 101.30，净库存提取 +2.94 mb/d（正好等于两者之差）；OECD 商业库存 2,683 mb，较五年同月低 112 mb。
  - Ember（欧盟，2026-10）：燃气发电占比 18.4%，燃煤 11.3%，风光 35.0%。
