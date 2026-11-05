# Scope 框架、市场页与数据诚信：设计规格

日期：2026-11-04
状态：**设计稿，待确认后开工**
前置文档：`docs/reviews/2026-11-04-project-review-and-gmi-roadmap.md`

## 0. 已确认的决策（2026-11-04）

| # | 决策 |
|---|---|
| D1 | 只用真实数据。合成内容中能用真实数据替换的就替换，其余下线，不保留"示意"版本 |
| D2 | 顺序：P0 诚信修复 → 能源 → 贵金属 → 基本金属。**重点是把框架搭好，让以后新增国家的成本更低** |
| D3 | 能源页包含电力市场和煤；可以做模型，但必须显式标注为模型 |
| D4 | 用户已有全部免费 key，需要一套安全的使用方案（§6） |
| D5 | Pages 部署方式需要利弊分析后再决定（§7） |

---

## 1. 现状的结构性成本（证据）

1. **新增一个国家要改约 24 个文件。** 以 `uzbekistan` 或 `"UZ"` 为关键词，命中：`Makefile`、`build_v4.py`、
   `scripts/publish_dashboard.sh`、`run_scheduled_refresh.py`、`validate_outputs.py`、`core_coverage_matrix.py`、
   `freshness_audit.py`、`macro_workbench.py`、`build_dashboard_archive.py`、`data_source_catalog.py`、
   `build_chart_studio.py`、`build_my_dashboard.py`、`build_policy_tracker.py`、`enrich_*`（5 个）、
   `render_*`（2 个）、`fetch_bruegel_reer.py`、`page_renderer.py`、`adapters.py`、`data_quality.py`，以及两个测试文件。
2. **14 个 `scripts/build_<country>_dashboard.py` 约 95% 相同**，差异只在：config 路径、国家码、
   `SUMMARY_KEY_IDS`、fetcher 子集、头条 FX 的 id。
3. **fetcher 注册表分散在每个脚本里**，source health 埋点不一致：最近一次 refresh 中 CN/JP/ZA/UK/US 记录到的调用数为 0。
4. **两套管线并存**：CEE 用的 v4 管线（`build_v4.py` 4,880 行 + `data_fetcher.py` 4,562 行），
   其余 14 个经济体用 data-first 管线。
5. **密钥读取逻辑分散在至少 6 处**，各自的回退方式不同。定时刷新的 workflow 只传了 5 个 secret
   （缺 `ESTAT_APP_ID`、`GIE_AGSI_API_KEY`、`BLS_API_KEY` 等）。另外，`data_fetcher.py:573` 引用了未定义的 `ROOT`，
   导致 GIE 储气和 Stooq 两个 fetcher 每次调用都报 NameError，即使配了 key 也拿不到数据。

---

## 2. 目标架构

### 2.1 Scope 注册表：`config/scopes.yaml`（唯一事实来源）

所有页面（国家、区域、市场、全局）都在这里登记。导航、Makefile、验证、覆盖矩阵、freshness、
workbench、归档、目录、Chart Studio、My Dashboard、Policy Tracker、发布冒烟测试**全部从注册表读取**，
不再硬编码国家列表。

```yaml
scopes:
  - id: UZ
    kind: country            # country | region | market | global
    slug: uzbekistan         # → output/uzbekistan.html, *_canonical_frame.json
    name: {en: Uzbekistan, zh: 乌兹别克斯坦}
    nav_group: frontier      # cee | g10 | asia | em | frontier | markets
    pipeline: data_first     # data_first | cee_v4（遗留，后续迁移）
    framework: country_core48
    indicators: config/countries/uzbekistan.yaml
    currency: UZS
    fx_usd_indicator: usd_uzs          # 供市场页做本币换算
    headline: [usd_uzs, policy_rate, cpi_inflation]
    deepdives: [inflation, labour]     # 只在有真实分项数据时渲染
    min_chart_count: 20
  - id: ENERGY
    kind: market
    slug: energy
    name: {en: Energy, zh: 能源}
    nav_group: markets
    pipeline: data_first
    framework: market_energy
    indicators: config/markets/energy.yaml
    depends_on: [scope_kind:country]   # 本币油价需要各国 FX
    headline: [brent_spot, henry_hub_spot, eu_gas_monthly, crack_321]
```

### 2.2 通用构建器：`scripts/build_scope.py`

- `build_scope.py UZ`、`build_scope.py --kind market`、`build_scope.py --all [--snapshot]`
- 按注册表加载配置，从**全局 fetcher 注册表**取 fetcher，复用现有的 `fetch_all` →
  `retain_last_known_good_series` → `track_revisions_and_vintages` → `build_country_page`（改名为 `build_scope_page`）。
- 构建顺序由 `depends_on` 计算（国家先于市场）。
- 迁移完成后删除 14 个逐国脚本。

### 2.3 全局 fetcher 注册表：`src/country_primer/fetchers/`

```python
@register("eia_xls", authority="official_primary", health_key="eia", secret=None)
def fetch_eia_xls(spec: IndicatorSpec, session: Session) -> Series: ...
```

- 每个数据源一个模块；统一签名；统一包上 source health、重试、熔断和**基于值的密钥脱敏**。
- 先把现有 adapters 包装注册进来，不重写；新数据源直接按新协议写。

### 2.4 指标模板：降低新增国家成本的关键

`config/templates/*.yaml` 把全球通用源参数化，一个新国家只需引用模板，就能自动得到基线覆盖：

| 模板 | 内容（按 ISO/IMF 代码参数化） | 预计图表数 |
|---|---|---|
| `imf_baseline` | WEO 增长/通胀/经常账户/财政/债务；IFS 月度 FX、政策利率、储备、CPI | ~12 |
| `bis_baseline` | 日度政策利率（WS_CBPOL）、信贷缺口、房价、偿债率、有效汇率 | ~6 |
| `wb_structural` | 人口、劳动参与率、私人信贷/GDP、能源进口依存度等年度数据 | ~6 |
| `oecd_baseline` | 适用于 OECD 成员：CLI、季度 GDP、失业率、CPI、利率 | ~8 |
| `fred_mirror` | 适用于 FRED 有镜像的国家：FX 日度、长端利率 | ~3 |

国家配置示例（加拿大 pilot）：

```yaml
templates: [imf_baseline, bis_baseline, oecd_baseline, fred_mirror]
params: {iso2: CA, iso3: CAN, imf: CAN, bis: CA, fred_fx: DEXCAUS}
indicators:            # 原生源，按 id 覆盖模板中的同名指标
  - id: cpi_trim
    fetcher: boc_valet
    ...
```

**验收标准**：新增一个 G10 国家只需要 2 个文件（注册表 1 条 + 国家 YAML），基线不少于 25 张图，
其余 23 个消费方无需改动。

### 2.5 框架（本体）泛化：`config/frameworks/`

- `country_core48.yaml`：现有的 `framework_v2.yaml` 迁过来，内容不变。
- `market_energy.yaml`、`market_precious.yaml`、`market_base_metals.yaml`：各自定义支柱与概念
  （能源的支柱见 §4，金属页的支柱见 review 文档 §5–§6）。
- 指标在 YAML 里直接写 `concept:`，不再在 `framework_v2.yaml` 里按国家 scope 单独映射（保留向后兼容的读取）。
- 覆盖矩阵按框架生成：`CORE_COVERAGE_MATRIX.md` 之外，新增能源和金属页各自的覆盖矩阵。

### 2.6 派生序列 DAG（白名单算子）

```yaml
- id: brent_wti_spread
  derivation: derived
  inputs: [ENERGY:brent_spot, ENERGY:wti_spot]
  op: spread               # 白名单：spread | ratio | product | fx_convert | resample | yoy | mom_ann
                           #        | ann_3m | zscore | dev_from_5y_seasonal | rolling_beta | cross_scope_table
```

- 不允许自由代码。每个派生值记录公式和输入序列的 vintage。
- **`ann_3m` 采用真实的 3 个月变化做年化**：`(I_t / I_{t-3})^4 − 1`。同时修复现有 deepdive 里
  "单月环比 ×3" 的错误。
- 跨 scope 引用：`UZ:usd_uzs`；构建时校验依赖存在且新鲜。

### 2.7 模型层（与数据严格分离）

- 产物写到 `output/models/<model_id>.json`，参数全部显式、可在页面上编辑，输入以 `scope:indicator@vintage` 形式引用。
- 页面上带 **MODEL** 徽章，用虚线绘制，不计入 canonical frame、覆盖矩阵和质量统计。
- 第一个模型：`oil_shock_cpi`。逐国冲击 = 能源 CPI 权重（官方权重：Eurostat `prc_hicp_iw`、BLS relative importance、
  ONS 等）× 本币油价变动 × 传导弹性（文献值，注明出处，可编辑）。

### 2.8 手工策展数据：`config/manual/*.yaml`

```yaml
- id: cb_meeting_calendar_2026_hu
  as_of: 2026-11-04
  source_url: https://www.mnb.hu/...
  expires_after_days: 60
  reviewer: human
  values: [...]
```

- 适用范围：央行会议日历、制裁/限价时间线、关键海峡流量（EIA 年度）、中国电解铝产能红线、TC/RC 长单。
- **过期即导致 validate 失败**，不会悄悄变旧。
- 页面上统一显示 `manual · as of <date>`。

### 2.9 Deepdive 改为"canonical 之上的视图"

- 每个面板声明所需的序列 id。缺任何一项就**不渲染该面板**，并在 Data Gaps 中列出。
  不再有默认值、偏移量或系数。
- 实施时逐国核对有没有真实分项数据，以下是待核对的候选源：

| 国家 | 通胀分项候选源 | 劳动力面板 |
|---|---|---|
| US、CEE-4 | 已经是真实分项（保留） | U、V 都有真实序列，可以画 Beveridge 曲线 |
| UK | ONS CPI 分项 | ONS 职位空缺 |
| EA | Eurostat HICP 分项 | Eurostat 职位空缺率 |
| TR | Eurostat HICP（TR 在 Eurostat 覆盖范围内） | 无职位空缺序列：只保留 U 与工资 |
| JP | e-Stat（需要 key） | 求人倍率（e-Stat） |
| KR | ECOS（需要 key） | 视 ECOS 可得性而定 |
| ZA、TW、HK、CN | 逐项核对原生源，核对不了就下线该表 | 只保留真实序列 |
| KZ、UZ、EG、NG | 一般没有可自动化的分项：下线分项表，只保留总 CPI 的真实动量 | 只保留 U |

### 2.10 验证合同（新增）

1. **Provenance**：deepdive、policy、市场页和模型 JSON 里的每个数值，都必须能追溯到
   `(scope, indicator_id, date)`，或者属于未过期的 manual 条目。
2. **Lint**：`scripts/enrich_*.py` 和 `render_*.py` 中禁止出现裸数值数组和 `x * 常数` 形式的序列构造
   （AST 检查；权重表必须带 `source` 和 `vintage`）。
3. **跨源校验**：政策利率对 BIS WS_CBPOL 的差异不超过 5bp（允许公告日到生效日的时滞）；FX 对央行或 ECB 的差异不超过 1%。
4. **密钥扫描**：对所有已跟踪文件和产物扫描已知 secret 的值以及通用模式；validate 和 CI 都要跑。
5. **注册表一致性**：每个 scope 都要有页面、导航项、canonical frame 和 summary，并满足 `min_chart_count`。

---

## 3. 实施阶段与验收

| 阶段 | 内容 | 验收 |
|---|---|---|
| **P0 诚信修复**（在现有架构上做，先止血） | ① 下线或替换合成内容（§2.9 的核对表）；② 政策利率：新增 `bis_cbpol` fetcher，替代 CEE 手工 YAML（YAML 降级为交叉校验）；③ Policy Tracker 的利率、12 个月变动、上次变动日期从 canonical 派生，删除无来源的 "consensus"，会议日期改为 manual + 过期机制；④ 修 bug：JP/ZA 首页 "n/a"、My Dashboard 的 JS 报错、`ROOT` NameError、e-Stat `appId` 脱敏；UZ/EG 的 FX 改走原生或 BIS/IFS 中较新的源，都拿不到时降级并标注 | `make validate` 通过；新增 provenance 测试通过；HU/CZ 政策利率与 BIS 一致；扫描不到硬编码的序列数组 |
| **F1 框架基础** | 注册表、通用构建器、fetcher 注册表、secrets 模块、指标模板、Pages 部署迁移（如果选 §7 的方案 C） | 14 个 data-first scope 的 `rebuild-ui` 产物与迁移前一致（canonical 逐字节相同，HTML 去掉时间戳后相同）；逐国脚本已删除；**加拿大 pilot 只改 2 个文件** |
| **F2 市场页类型 + 能源 MVP** | `kind: market`、框架泛化、派生 DAG、模型层、能源 MVP（约 45 张图，见草案中 `mvp: true` 的条目）+ `oil_shock_cpi` 模型 | 能源页通过同一套 validate；所有派生值都有公式和输入 vintage；模型带 MODEL 徽章，且不进入 canonical |
| **M2 贵金属** | 约 25 张图 | 同上 |
| **M3 基本金属** | 约 35 张图 | 同上 |
| **后续** | CEE v4 管线迁移到 data-first（最大的技术债）；按模板扩国家（G10 商品货币国、大型 EM） | |

---

## 4. 能源页框架（`market_energy`）

| 支柱 | 主要问题 |
|---|---|
| `crude_benchmarks` | 价格水平、地区价差（Brent–WTI、Brent–Dubai）、波动率、期限结构（免费数据只能用 INE SC 代理） |
| `refining_products` | 裂解价差、炼厂开工、零售价格（对 CPI 最直接） |
| `gas_lng` | HH、欧洲、亚洲三大气价，以及储气相对季节常态的偏离 |
| `power_coal` | 欧洲日前电价、煤价、铀价、发电结构 |
| `supply` | 美国产量、OPEC+ 分国产量与闲置产能 |
| `demand` | 美国周度表观消费、中国进口与加工量 |
| `inventories` | 美国原油/产品/SPR/Cushing，欧盟储气，OECD 库存 |
| `trade_geography` | 美国进出口、关键海峡暴露度、制裁时间线（manual） |
| `positioning` | CFTC 管理基金净持仓及 z-score |
| `macro_transmission` | 本币油价、各国能源 CPI 及拉动、盈亏平衡通胀率、贸易条件暴露、商品货币 beta |
| `models` | 油价冲击 → CPI（MODEL） |

逐条指标草案（含实测可达性）见 `docs/superpowers/specs/drafts/energy_indicators.draft.yaml`。

---

## 5. 新数据源：实测结果（2026-11-04，本云沙盒出口）

| fetcher | 源 | 状态 | 说明 |
|---|---|---|---|
| `eia_xls` | EIA `dnav/*/hist_xls/*.xls` | ✅ 免 key | 现货与周度序列最新到 2026-10-30 至 11-03；**期货 RCLC1–4、RNGC1–4 止于 2024-04-05，不能用** |
| `eia_v2` | EIA API v2 | 需要 key | STEO（OPEC+ 产量、闲置产能、OECD 库存）、国际数据库 |
| `akshare_foreign_futures` | 新浪外盘期货 | ✅ | OIL、CL、NG、HG、GC、SI、XPT、XPD、AHD、ZSD、NID 都有当日数据（2026-11-04）；属于 public wrapper，质量记为 watch |
| `akshare_cn_futures` | 新浪内盘期货、东方财富库存、SGE | ✅ | SC 各合约、SHFE 库存、Au99.99 |
| `imf_sdmx`（PCPS） | `api.imf.org` `IMF.RES,PCPS`，key 形如 `G001.<COMMODITY>.USD.M` | ✅ | 金、银、铂、钯、锂、钴等到 2026-09；**替代 DBnomics 镜像（停在 2025-06）** |
| `fred_graph` | FRED | ✅ | IMF 月度能源与金属价格（不含贵金属）、OVX、GVZ、盈亏平衡、零售油价 |
| `cftc_socrata` | `publicreporting.cftc.gov` 数据集 `72hh-3qpy` | ✅ | **必须按 `cftc_contract_market_code` 查询**，因为合约名称历史上改过多次。WTI 067651、ICE WTI 067411、NG 023651、RBOB 111659、ULSD 022651、铜 085692、金 088691、银 084691、铂 076651、钯 075651 |
| `energy_charts` | `api.energy-charts.info` | ✅ | 德国等日前电价（15 分钟粒度，CC BY 4.0，数据来自 SMARD） |
| `gie_agsi` | GIE AGSI+ | 需要 key | 欧盟及分国储气 |
| `bis_cbpol` | BIS WS_CBPOL | ✅ | 日度政策利率 |
| `worldbank_pinksheet` | Pink Sheet 月度 xlsx | ✅ | 煤（澳洲/南非）、LNG、贵金属等的备份源 |
| 授权数据（作为缺口） | ICE TTF/Brent 曲线、CME 曲线、LME cash–3M、Platts/Argus、油轮运价、Baker Hughes | ❌ | 明确标注为缺口 |

---

## 6. 密钥安全方案

**原则**：key 永远不进 git、配置文件、生成产物、日志或聊天记录；每个运行环境用各自的密钥存储；代码只通过一个入口读取。

| 运行位置 | 存放方式 |
|---|---|
| 你的本机 | 仓库根目录的 `.env.local`（`.gitignore` 里的 `.env.*` 已覆盖，并用 `!.env.example` 放行模板），`chmod 600`，由 `scripts/uv_project.sh` 自动加载。更进一步可以用 1Password CLI（`op run --env-file=.env.tpl -- make refresh-data`）或 macOS Keychain，磁盘上就不留明文 |
| 本云会话（Claude 用） | Claude Code 云环境设置：会话标题栏的环境菜单 → Edit → **Network secrets**（旧版应用里叫 API credentials）；如果没有这个区域，就作为环境变量添加。**新开的会话才会读到**。请不要把 key 粘贴到聊天里 |
| GitHub Actions 定时刷新 | 仓库 Settings → Secrets and variables → Actions。workflow 需要补传 `ESTAT_APP_ID`、`GIE_AGSI_API_KEY`、`BLS_API_KEY` 等（F1 中处理） |

**统一变量名**（三处必须一致）：
`FRED_API_KEY`、`EIA_API_KEY`、`GIE_AGSI_API_KEY`、`ESTAT_APP_ID`、`BOK_ECOS_API_KEY`、`KOSIS_API_KEY`、
`TCMB_EVDS_API_KEY`、`FINMIND_API_TOKEN`、`BLS_API_KEY`、`EMBER_API_KEY`，以及可选的 `ENTSOE_API_TOKEN`（ENTSO-E 欧洲电力透明平台）。

**代码侧加固（F1）**：

1. 用单一入口 `country_primer/secrets.py:get_secret(name)` 替代分散的读取逻辑；
   `config/secrets_manifest.yaml` 只登记名称、用途、注册网址和依赖它的指标，**不放值**。
2. `make doctor` 只报告每个 key 是 set 还是 unset，从不打印值。
3. **按值脱敏**：source health、日志和异常信息中出现任何已加载 secret 的**实际值**都替换成 `[redacted]`，
   不再只靠正则；同时补上 `appId=` 模式。
4. validate 和 CI 加入密钥扫描；建议在 GitHub 上打开 secret scanning 与 push protection（仓库设置，需要你操作）。
5. 这些都是免费、只读的 key。一旦怀疑泄露，到各自网站重新生成即可。

---

## 7. Pages 部署方式：利弊分析

**现状**：生成的 HTML（约 20 MB）和 JSON（canonical 约 38 MB，其他约 9 MB）都提交到 `main`，
Pages 直接从分支发布；工作日机器人每天提交一次（一次自动刷新就改动约 59 个文件）。
`.git` 在 50 个提交的浅克隆下已经 48 MB，定时 workflow 又用 `fetch-depth: 0` 拉全量历史。

| 方案 | 优点 | 缺点 |
|---|---|---|
| **A. 维持现状** | 最简单；每个已发布的状态都是一个提交，可回溯、可 `git revert`；JSON diff 能看出数据变化；`rebuild-ui`、last-known-good 和修订追踪都直接读仓库里的 canonical | 仓库持续膨胀，clone 和 CI 越来越慢；机器人提交和人工提交混在一起；**功能分支改动 `output/` 必然和每日机器人提交冲突**（框架重构期间会很痛）；PR diff 被生成文件淹没 |
| **B. 只用 Actions 部署产物，仓库不存任何产物** | `main` 干净；不冲突；部署是原子的 | **丢掉持久状态**：last-known-good、修订/vintage 追踪和 snapshot 重建都依赖上一版 canonical（Actions cache 只保留 7 天，不可靠）；本地开发拿不到数据；失去"某天页面显示了什么"的历史 |
| **C. 混合（推荐）**：`main` 只放源码和配置；独立的 `data` 分支存 canonical/summary JSON 和审计 md；Actions 从 `data` 分支离线 `rebuild-ui` 后用 `deploy-pages` 部署 | 保留数据 vintage 历史和 LKG（JSON 可 diff，体积可控，可以定期压缩历史并保留月度 tag）；`main` 不再有机器人提交，功能分支不再冲突；任何历史日期都能用当时的 JSON + 当时的代码确定性重建；URL 不变（产物目录结构保持一致） | 组件更多（两个分支、一个部署 workflow）；需要你把 Settings → Pages 的 Source 改成 "GitHub Actions"；`make publish` 从 git push 改为触发 workflow；本地开发要先 `make pull-data`；迁移需要一次性的工作量 |

**建议**：采用方案 C，并**放在 F1 早期做**，否则框架重构期间每天都要解决 `output/` 冲突。
迁移期间保留方案 A 作为回退（Pages 设置可以随时切回）。
