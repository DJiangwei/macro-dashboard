# 项目 Review 与 GMI 数据支持路线图（讨论稿）

日期：2026-11-04
状态：**讨论稿，待与需求方迭代**。本文件只是 review 与提案，未改动任何数据、配置或生成产物，也未改动 `main`。
基线：commit `2f1ffde`（与 `origin/main` 相同）

---

## 0. 一页结论

1. **底座是好的**：18 个经济体、1,417 个图表位、Core 48 统一本体、六维质量模型
   （authority / derivation / freshness / validation / comparability / quality）、
   canonical frame、freshness audit、source health 和熔断、离线 `make validate`
   （154 个测试通过，`validate_outputs` 与一致性检查也都通过）。作为 GMI 的数据底座，
   方向正确，工程纪律也优于大多数个人项目。
2. **但最近一轮"机构级 deepdive"扩展破坏了项目自己定的第一条铁律**
   （"Never fabricate, interpolate, or silently backfill"）：劳动力/工资 deepdive（全部 18 国）
   和通胀 deepdive（12 国）里有大量**用系数、偏移量、手写数组合成的数据**，而且以
   "Official Basket" 之类的标签展示。另外，Policy Tracker 和 CEE 政策利率是手工维护的，
   **已经和事实不符**：BIS 数据显示匈牙利基准利率为 5.50%、捷克为 3.75%，页面上仍是
   6.25% 和 3.50%。现有的 validate 抓不到这类问题。**这是给 GMI 用之前的 P0。**
3. **对 GMI 来说最缺的不是更多国家的年度结构数据，而是三块**：
   (a) 商品与跨资产层（能源 / 金属 / 贵金属），
   (b) 薄弱国家的"核心 8 项"月度/日度数据（FX、储备、政策利率、CPI、收益率等），
   (c) "这周变了什么"：真正逐序列的变化摘要。
4. **能源 Tab 非常及时**：FRED 数据显示 Brent 月均价从 2025-10 的 $64.5 涨到 2026-04 的
   $117，2026-06 回落到 $85，2026-10 又到 $124.8；WTI 约 $101，Brent–WTI 价差约
   $23；OVX 为 61.7。与此同时 Henry Hub 只有约 $3.0，欧洲气价 $25.5/MMBtu（9 月），
   美欧气价明显脱钩。仪表盘目前**没有任何商品/能源专页**，只在几个产油国页面里零散放了 Brent。
5. **建议顺序**：P0 诚信修复 → 能源 MVP → 贵金属 → 基本金属。薄弱国家增强与
   GMI 跨资产层可以并行推进。具体顺序见 §9，需要你拍板。

---

## 1. 现状盘点

| 维度 | 现状 |
|---|---|
| 覆盖 | 18 个经济体：CEE-4、CN、EA、JP、ZA、UK、US、TR、HK、KR、TW、KZ、UZ、EG、NG |
| 图表数 | US 182、CN 114、CEE ~117、UK 97、EA 76、ZA 66、JP 59、TR 56、KR 51、TW 50、HK 40、NG 40、EG 38、KZ 38、UZ 37 |
| Core 48 覆盖 | US 43、EA 44、CEE 41、UK 40、JP 38、TR/KR 32、CN 31、ZA 29、TW 26、HK 24、**UZ 20、KZ 19、NG 19、EG 18** |
| 额外页面 | Chart Studio（1,300+ 序列）、My Dashboard、Policy Tracker、各国 Inflation / Labour deepdive |
| 数据栈 | FRED、Eurostat、ECB、BIS、IMF（SDMX/DataMapper）、World Bank、ONS/BoE、SARB、TCMB、BOK、DGBAS/CBC、AKShare、e-Stat 等 |
| 刷新 | GitHub Actions 每个工作日 quick、周六 full，自动提交到 `main` |
| 测试 | `pytest` 154 passed；`validate_outputs.py` passed；`dashboard_consistency_check.py` passed |

**做得好的地方（应保留）**

- Core 48 本体：`indicator_id` 和 `concept_id` 两层身份，country-specific 指标走 deep-dive，不强行映射。
- 质量标签是多维的，而且确实显示在每张卡片上（verified/watch/low、official mirror、projection 等）。
- canonical frame v2（`[date, value]` 加上一次性元数据），refresh 与 rebuild-ui 分离，UI 可以离线重建。
- release calendar 与 freshness 阈值按频率区分；`refresh_fallback/watch` 是显式标记的 last-known-good 机制。
- lightweight-charts 迁移后，页面的交互（区间、框选 Δ、CSV/PNG 导出）对研究者很实用。

---

## 2. 关键问题

### 2.1 P0：合成数据与手工数据（数据诚信）

| 位置 | 问题 | 例子 |
|---|---|---|
| `scripts/enrich_labour_wage_deepdive.py`（1495184，2026-11-02 引入；覆盖全部 18 国） | Beveridge 曲线历史点是手写数组，带叙事标签（共 19 处 `beveridge_history`）；实际工资历史与 ULC 历史由最新值加减常数**构造**；表格里的 prev / 1y-ago 值也是最新值 ± 常数 | `{"date":"2022-06","nominal": wage_val + 2.2, "cpi": cpi_val + 5.5}`；`"Statutory Minimum Wage" = wage_val * 150`；`broad_slack = u * 1.5`；缺数时默认 `u=4.0`、`v=2.0`，LFPR 用硬编码字典 |
| `scripts/enrich_global_inflation_deepdive.py`（UK、JP、HK、EG、NG、KZ、UZ）和 `scripts/enrich_em_inflation_deepdive.py`（TR、ZA、KR、TW） | 分项 CPI = 总指数 × 手设 beta；分项 PPI = 总指数 × factor；预期/调查 gauge 为硬编码值；缺 PPI 时用 CPI × 1.1 | 乌兹别克斯坦页的 12 个 COICOP 分项表标注为 "Uzbekistan Official Basket"，实际配置里只有 IMF 的总 CPI；台湾 "CIER PMI Input Price 56.5" 是写死的 |
| `scripts/enrich_china_inflation_deepdive.py` | 猪肉/蔬菜/食品分项 = 总指数 × 系数；AKShare 猪价接口失败时，回退到一组手写的 "Fallback synthetics" | `"pork_yoy": h_yoy * 3.0 - 1.5` |
| 上述三个脚本里的动量计算 | "3M annualized" 实际算的是 `(1 + 单月MoM×3)^4 − 1`，即**单月环比 ×3**，不是真实的 3 个月变化 | 方法论错误。CEE 与 US 的 deepdive 用的是真实分项序列，初读没有发现同类问题 |
| `scripts/build_policy_tracker.py` | 18 个央行的利率、走廊、12 个月变动、下次会议、"consensus（含概率）"全部手写 | BoJ：写的是 "Hike 25bp to 1.25%"，但 BIS 显示 2026-09-24 已经升到 1.25%；HU：`rate_change_12m: -375`；CZ：`-275`，"Hold at 3.50%" |
| `config/policy_rates.yaml`（CEE 手工维护，标记为 `verified`） | 最后一笔观测在 2026-04/05，之后没有自动核对 | BIS WS_CBPOL 日度：**HU 5.50%**（6/24、7/22、8/26 三次降息），**CZ 3.75%**（6/19 加息）；页面显示 HU 6.25%、CZ 3.50%，CZ 连方向都错了。PL 3.75% 和 RO 6.50% 一致。建议再对照 MNB/CNB 官网确认一次 |

**为什么这对 GMI 是 P0**：页面明确说"Data policy: no fabricated proxies"，质量徽章也让人以为
这些数是 sourced 的。项目自己的经验文档写过："A chart labelled YoY but rendered as an index is
worse than a missing chart because it creates false confidence." 合成的分项表和 Beveridge 曲线
正属于这类，而且影响面更大。

**`make validate` 没有拦住**：现有合同只检查图表数、ID、空容器和 JSON 结构，不检查
"每个展示的数字能不能追溯到 canonical frame 里的某个 (country, indicator_id, date)"。

### 2.2 P1：数据质量与 bug

- **JP / ZA 首页卡片显示 "n/a"**："Overnight call rate n/a"、"SARB repo rate n/a"。canonical 里其实有
  `policy_rate`（JP 月度 1.043，2026-09；ZA 7.25，2026-11-02），是 headline 映射的 bug。
- **`my_dashboard.html` 有 JS 报错**：`COUNTRY_NAV is not defined`。`scripts/build_my_dashboard.py:40`
  里 Python 常量没有输出成 JS 变量，页面高度只有 479px，等于整页没渲染出来。
- **前沿国家的头条卡片陈旧**：UZ 的 USD/UZS 停在 2025-07-01，EG 的 USD/EGP 停在 2025-05-01，都来自 IMF IFS 的滞后。
  对 GMI 来说，FX 是这几国最重要的变量。
- **CEE 的银行 FSI 用 World Bank GFDD**：最新值停在 2021–2023（freshness audit 已标 stale）。
  CEE 的外汇储备、经常账户用 WB 年度数据（2024）；Eurostat/ECB 的季度 BoP 和 IMF IFS 的月度储备都可以替换。
- **Source health 埋点不全**：CN、JP、ZA、UK、US 的调用数是 0（没有埋点，或最近一次是 snapshot 模式）；
  CEE 每国约 850 次调用里约 750 次返回空，回退链太长，又慢又嘈杂。
- **首页卡片格式不统一**：CEE 显示 "56 verified · 49 watch · 13 low"，其他国家显示 "N source groups · M low-confidence"。
- **UZ 页的头条 KPI 重复**：IMF WEO 和 WB 两张卡都是 7.70% 的年度 GDP，信息量低。
- **`what_changed.json` 基本没用**：只有一条 "no_material_change"，没有逐序列的新数据和变化幅度。

### 2.3 P2：工程卫生

- 根目录有约 20 个一次性脚本（`add_constants.py`、`fix_*.py`、`patch_*.py`、`parse_and_move.py`、
  `test_ak.py` 等），还有 39 MB 的 `mhlw_stats.json`（代码里没有引用）和已提交的 `scratch/`（包括 `publish.log`）。
- `chart_studio.html`、`policy_tracker.html`、`my_dashboard.html` 在根目录和 `output/` 各有一份。
- `config/china_indicators_new.yaml` 没有被任何脚本引用；`build_v3.py` 是遗留代码。
- 每天由机器人提交约 64 MB 的生成 HTML 到 `main`，`.git` 在浅克隆 50 个提交时已经 48 MB。
  建议改成用 Actions 构建产物部署 Pages（`actions/deploy-pages`），git 里只保留 canonical JSON。

---

## 3. 方向一：数据丰富度（重点是薄弱国家）

### 3.1 原则：先补"GMI 核心 8 项"，再补结构性年度数据

对前沿/小型经济体，决策相关性最高的是月度和日度的这 8 项：
**FX（官方 + 平行市场如有）、外汇储备（月度）、政策利率（日度）、CPI（月度，含核心）、
本币国债收益率、经常账户/贸易（月度或季度）、私人信贷（月度）、外债/展期需求**。
WDI 年度结构数据可以留在 deep-dive，但不应该占头条位置。

### 3.2 横向快速胜利（一次接入，多国受益）

| 来源 | 已验证 | 用途 |
|---|---|---|
| **BIS WS_CBPOL（日度）** | ✅ 2026-11-04 实测，HU/PL/CZ/RO/JP/ZA 有数 | 替代 CEE 手工政策利率，Policy Tracker 从 canonical 派生；与各国本地源做交叉校验 |
| BIS 其他数据集（WS_SPP 房价、WS_CREDIT_GAP、WS_DSR、WS_TC） | 已在用一部分 | 补齐 HK/KR/TR/ZA 的房价、信贷缺口、偿债率 |
| IMF SDMX IFS 月度 | 已在用 | 储备（含黄金吨数，§6 也会用）、利率、货币量 |
| ECB Data Portal / Eurostat 季度 BoP | ✅ ECB 可访问 | 替换 CEE 的 WB 年度经常账户、FSI |
| **日本财务省 JGB 收益率曲线 CSV** | ✅ 1Y–40Y，最新 2026-11-02 | 补 JP 收益率曲线；目前 JP 质量是 8 verified / 19 watch |

### 3.3 分国家建议（按 Core 48 缺口排序）

| 国家 | Core 48 | 建议 |
|---|---|---|
| EG（18） | FX 停在 2025-05 | CBE（官方 FX、政策利率、CPI、储备）。本沙盒访问超时或被拒，需要在 GitHub Actions runner 上实测；如果不可用，就把 FX 卡片降级并明确标注滞后 |
| KZ（19） | | NBK（已有 XML：基准利率、储备月度）；BNS Taldau API（端点需确认，本次实测返回 500）；KASE 收益率 |
| NG（19） | | CBN（已有 FX；补储备日度、MPR）；NBS（本沙盒超时）；DMO 国债收益率 |
| UZ（20） | FX 停在 2025-07 | CBU JSON 汇率接口（本沙盒超时，需在 CI 上实测）；CBU 统计 xlsx；stat.uz 开放数据 |
| HK（24） | | HKMA Open API（HIBOR、总结余、银行贷存、按揭调查；端点需确认）；差饷物业估价署（RVD）房价指数 |
| TW（26） | | 已经较原生；补就业、工资（DGBAS）、出口订单 |
| ZA（29） | | SARB 再扩展（BoP、信贷）；Stats SA 采矿产量（与 PGM 联动，§6） |
| CN（31，48 个 low-confidence 图表） | | 是 low-confidence 最多的国家：逐项评估 NBS `easyquery` 与 PBoC 原生接口能否替换 AKShare 封装 |
| KR（32） | | CI 已预留 `BOK_ECOS_API_KEY`，扩大 ECOS 使用；修复 9 个 FRED HTTP 错误；KOSIS（需 key） |

### 3.4 宇宙扩展（值得讨论）

对 Global Macro 来说，现在的国家集合偏 CEE 和前沿市场。**G10 里缺 CA、AU、NZ、NO、SE、CH，
大型 EM 里缺 IN、BR、MX、ID、SA/GCC、CL**。其中 AUD、CAD、NOK、CLP、ZAR 都是商品货币，
和能源/金属 Tab 天然联动。比起继续把 UZ/EG 从 20 项补到 30 项，加 3–5 个 G10 或大 EM 国家
（FRED/OECD/BIS 覆盖好、成本低）可能对 GMI 更有价值。

---

## 4. 方向二：能源 Tab（Energy）

### 4.1 定位

主视角是**对通胀和资产价格的传导**，但要把产业链看全：价格 → 期限结构 → 炼化/产品 →
天然气/LNG/电力 → 供给 → 需求 → 库存 → 贸易流与地缘 → 资金持仓 → 宏观传导。
页面形态和国家页一致（复用 page renderer 和质量徽章），但用一套**市场框架**代替 Core 48（见 §8）。

### 4.2 板块与指标（✅ 表示本次在当前环境实测可访问）

**E0 快照条**：Brent、WTI、Brent–WTI、Brent–Dubai、HH、欧洲气价、亚洲 LNG、美国零售汽油、
柴油裂解价差；以本币计价的 Brent（EUR/CNY/JPY/INR/TRY）；1w/1m/3m/YoY 变化，5 年 z-score。

| 板块 | 指标 | 来源 |
|---|---|---|
| **E1 原油价格与期限结构** | Brent/WTI 日度 ✅（FRED，滞后约 1 周）；Dubai 月度；WTI M1–M4 曲线与 M1–M4 价差（期限结构/backwardation） ✅（EIA hist_xls RCLC1–4，无需 key）；INE SC 对 Brent 溢价（AKShare）；OVX ✅（FRED，目前 61.7） | FRED、EIA、AKShare |
| **E2 成品油与炼化** | 美湾汽油/ULSD/航煤 ✅；3-2-1 裂解与柴油裂解（派生；柴油对运价和食品通胀是关键）；美国炼厂开工率（EIA 周度）；中国成品油调价 ✅（AKShare，2026-10-30） | EIA、FRED、AKShare |
| **E3 天然气·LNG·电力·煤** | HH 日度 ✅ 与 NG M1–M4 ✅；欧洲气价与亚洲 LNG 月度 ✅（FRED/IMF）；TTF 日度属于 ICE 授权数据，作为缺口标注；美国储气周度 vs 5 年区间（EIA）；欧盟储气（GIE AGSI，免费 key）；挪威管道流量与 LNG 送出（ENTSOG ✅）；德/法/意电力日前价格（energy-charts ✅）；纽卡斯尔煤 ✅、铀 ✅（月度） | EIA、GIE、ENTSOG、Fraunhofer、FRED |
| **E4 供给** | 美国原油产量周度（EIA）；OPEC+ 分国产量与闲置产能（EIA STEO，需免费 key；或 JODI 月度 ✅）；钻机数（Baker Hughes 在本沙盒 403，作为缺口或用 STEO 替代）；KZ/NG/EG 产量与国家页联动 | EIA、JODI |
| **E5 需求** | 美国表观消费（周度，4 周均值）；中国原油进口与表观需求（海关 + 加工量）；印度（PPAC，待验证）；全球需求（STEO；IEA 付费，作为缺口） | EIA、AKShare/NBS |
| **E6 库存** | 美国商业原油（不含 SPR）✅ 与 Cushing、SPR、汽油/馏分油库存天数；OECD 商业库存（STEO）；欧盟储气；中国官方库存不公开，作为缺口 | EIA、GIE |
| **E7 贸易流与地缘** | 美国原油净进出口（周度）；中国进口来源国（海关月度，待验证）；关键海峡（EIA World Oil Transit Chokepoints，静态）与各国暴露度；制裁/限价时间线（手工，带日期与来源）。油轮运价属于 Baltic/Kpler 授权数据，作为缺口 | EIA、手工策展 |
| **E8 资金持仓** | CFTC 管理基金净多头 ✅（WTI 的 NYMEX 与 ICE Europe、NG、RBOB、ULSD，周度，最新 2026-10-27）及 3 年 z-score；ICE Brent COT（ICE 自行发布，待验证） | CFTC Socrata API |
| **E9 宏观传导（核心视角）** | ① 18 国**本币计价油价同比**（用 canonical frame 里的 FX 换算），这是各国实际面对的进口成本冲击；② 各国能源 CPI 同比及对总通胀的拉动（US、EA、UK、TR、CEE 已有分项，汇成一张横向表）；③ 传导链：Brent → 美国零售汽油 → CPI 能源 → 5Y 盈亏平衡与 5y5y ✅（T5YIE/T5YIFR），展示滞后结构；④ **贸易条件暴露热力图**：各国能源净进口占 GDP（进口国 JP/KR/TW/TR/HU/CZ/PL 对比出口国 NG/KZ），可链接到对应国家页；⑤ 资产敏感度：滚动 beta（油价对商品货币 CAD ✅/NOK ✅、盈亏平衡、美债 10Y） | 派生 |
| **E10 情景计算器（模型，需明确标注）** | +$10/bbl → 各国总 CPI 冲击 = 能源权重 × 传导弹性（参数可见、可编辑），一律标为 **MODEL**，不进入 canonical 数据 | 模型 |

**MVP 建议**：先做 E0、E1、E2、E3（不含电力）、E6（美国 + 欧盟）、E8、E9 的 ①②③④，
大约 35–40 张图，基本都能用免 key 或免费 key 的来源完成。

---

## 5. 方向三：基本金属 Tab（Base Metals）

### 5.1 定位

聚焦**市场本身**：价格与期限结构、跨市场套利、可见库存、供给、需求、持仓。
宏观链接只作为附录。

### 5.2 板块与指标

| 板块 | 指标 | 来源 |
|---|---|---|
| **M0 快照** | LME 与 SHFE 的铜、铝、锌、镍、铅、锡；铁矿石；碳酸锂（GFEX）；钴（月度） | AKShare、FRED |
| **M1 价格与期限结构** | LME 3M 日度 ✅（AKShare 新浪 `futures_foreign_hist`，铜 2026-11-04 收 $14,053.5）；SHFE 主力连续 ✅；SHFE 近远月价差（contango/backwardation）；中国现货与期货基差（AKShare `futures_spot_price`，待验证）；LME cash–3M 属于授权数据，作为缺口；月度 IMF 价格 ✅（FRED，到 2026-09） | AKShare、FRED |
| **M2 跨市场套利** | SHFE/LME 比值与**进口盈亏窗口**（含 13% 增值税与汇率，派生）；**COMEX–LME 铜价差**（关税驱动，2025–26 的核心结构变化，COMEX HG 来自新浪，待验证） | 派生 |
| **M3 可见库存** | SHFE 周度 ✅（AKShare，铜 2026-11-04）；COMEX 库存（AKShare，待验证）；LME 库存（AKShare/jin10 停在 2026-07-17，需要换源或标陈旧）；三地合计可见库存，折算成全球消费天数（分母用 ICSG 年度消费，手工） | AKShare |
| **M4 供给** | 中国精炼铜、铝、锌月产量（NBS）；智利（Cochilco/INE）、秘鲁（MINEM）铜矿产量；印尼镍；中国电解铝 45Mt 产能红线（静态）；TC/RC（年度长单，手工）；电价对铝成本（与能源 Tab 联动） | NBS、Cochilco、手工 |
| **M5 需求** | 中国：地产新开工与竣工、电网投资、新能源车产量（中国页已有，做链接）、空调与汽车产量；中国铜进口（精炼铜与铜精矿）和未锻轧铝出口（海关）；全球制造业 PMI 属于授权数据，用 OECD CLI 替代并标注 | NBS、海关 |
| **M6 持仓** | CFTC COMEX 铜管理基金 ✅；SHFE 前 20 会员净持仓（AKShare）；LME COTR（本沙盒 403，待验证） | CFTC、AKShare |
| **M7 黑色与电池金属（子板块）** | 铁矿石（DCE 日度 + IMF 月度 ✅）、螺纹钢、中国粗钢产量；碳酸锂（GFEX）、锂 ✅、钴 ✅、钼 ✅（月度） | AKShare、FRED |
| **附：宏观链接** | 铜金比 vs 美债 10Y；金属价格 vs 中国信贷脉冲（中国页的 TSF）；商品货币（CLP、PEN、AUD ✅、ZAR） | 派生 |

---

## 6. 方向四：贵金属 Tab（Precious Metals）

| 板块 | 指标 | 来源 |
|---|---|---|
| **P0 快照** | 金、银、铂、钯（USD）；多币种金价（EUR/JPY/CNY/INR/TRY）；金银比、金铜比、金油比 | 派生 |
| **P1 价格** | 日度：SGE Au99.99 ✅（2026-11-04）与上海金基准价 ✅、COMEX 金银（新浪，待验证）；月度：World Bank Pink Sheet ✅ 与 IMF（DBnomics 镜像停在 2025-06，**要换成 IMF 原生 API 或 Pink Sheet**）。LBMA 定价属于授权数据，本沙盒 403 | AKShare、World Bank |
| **P2 宏观驱动** | 美债 10Y 实际利率 ✅（DFII10）、广义美元 ✅、5y5y ✅、联邦基金利率；**金价对实际利率的滚动回归**（展示 2022 年后的脱钩，派生并标注）；GVZ ✅（25.8） | FRED |
| **P3 官方部门** | 各国央行黄金储备（吨数与占储备比例，IMF IFS 月度）：CN、PL、TR、IN、CZ、KZ、UZ 等。其中 KZ/UZ 既是产金国又是央行黄金交易方，与国家页联动。PBoC 月度已有；WGC 数据需注册，作为手工策展 | IMF IFS |
| **P4 投资需求** | 黄金 ETF 持仓（SPDR 站点返回非 CSV，jin10 超时，待在 CI 上验证）；COMEX 与 SHFE 金银库存 | AKShare |
| **P5 区域溢价** | **上海溢价** = SGE 价（CNY/g）换算成 USD/oz 后，对国际价的价差（日度，派生）；印度溢价没有免费源，作为缺口 | 派生 |
| **P6 持仓** | CFTC 金、银、铂、钯管理基金 ✅；SHFE 前 20 | CFTC、AKShare |
| **P7 PGM 供给侧** | 南非 PGM 采矿产量与电力约束（与 ZA 页联动）；俄罗斯钯（没有免费源）；汽车催化剂需求（年度，手工） | Stats SA、手工 |

---

## 7. 方向五：GMI 支持层（跨资产与工作流）

| 模块 | 内容 | 价值 |
|---|---|---|
| **G1 跨资产监控（日度）** | 美债 2/10/30 年与实际利率、盈亏平衡；Bund/JGB ✅/Gilt；DXY 与 EM FX；信用（US IG/HY/EM OAS，FRED）；波动（VIX、OVX、GVZ；MOVE 属于授权数据）；自建商品篮子指数（BCOM 授权，用现有价格按产量加权并标注） | 一屏看 regime |
| **G2 What changed（周度摘要）** | 逐序列：上次构建以来的新数据、Δ、相对历史的 z-score、Top movers、数据修订 | 替代目前无效的 `what_changed.json`，对 PM 价值最高 |
| **G3 无共识的 surprise 代理** | 实际值对过去 3/12 个月趋势的偏离 z-score；跨国 diffusion index（改善指标占比） | 共识数据授权问题解决前的替代方案 |
| **G4 Regime 地图** | 增长 × 通胀四象限，带 3 个月动量箭头，跨国对比（在现有 regimes 上加动量） | 资产配置框架 |
| **G5 央行日历** | 会议日期来自官方日历文件，而不是手写；与 BIS 实际利率路径对照 | 替换 Policy Tracker 的手工字段 |
| **G6 权益（低优先级）** | 国家指数的 USD 与本币表现；估值数据难以免费获取（Stooq 需 key，Yahoo 在本沙盒 429） | 可选 |

---

## 8. 架构建议：新增 "market" 页面类型

- **新框架**：`config/markets_framework.yaml` 定义市场支柱（E1–E10 / M0–M7 / P0–P7），
  作用相当于国家页的 Core 48；指标放在 `config/markets/{energy,base_metals,precious_metals}.yaml`。
- **复用**：`data_first_pipeline`（fetcher 协议）、canonical frame v2（产出 `*_market_canonical_frame.json`，
  把 `country` 字段换成 `market`）、`page_renderer` 图表卡片、质量模型、freshness（日/周阈值）、
  source health、validate。
- **新 fetcher（按优先级）**：`bis_cbpol`（同时修复 P0）、`eia_hist_xls`（免 key）、`cftc_socrata`、
  `worldbank_pinksheet`、`akshare_futures`（库存、外盘、SGE）、`eia_v2`（key）、`gie_agsi`（key）、
  `entsog`、`energy_charts`、`imf_ifs_gold`。
- **派生 vs 模型分离**：裂解价差、比值、溢价、本币油价都属于 `derivation: derived`，公式字符串写进元数据；
  情景计算器和回归 beta 属于**模型产物**，单独存放，界面上用 "MODEL" 徽章和虚线区分，**不进 canonical**。
- **双向链接**：商品 Tab 的暴露表 ↔ 国家页（KZ/NG 链到原油，ZA 链到 PGM，CN 链到金属需求，
  JP/KR/TW 链到进口成本）。

### 8.1 验证合同升级（配合 P0）

1. **Provenance 合同**：deepdive、policy、market 的 JSON 里每个数值都要能追溯到
   canonical 的 `(scope, indicator_id, date)`；否则必须是 `manual`，带 `as_of`、`source_url`
   和过期期限（如 45 天），过期即 validate 失败。
2. **Lint**：`scripts/enrich_*.py` 里不允许出现裸数值数组或 `x * 常数` 形式的序列构造
   （权重除外，权重必须注明来源与 vintage）。
3. **跨源校验**：政策利率 vs BIS WS_CBPOL、FX vs 央行/ECB，差异超过阈值即失败。

---

## 9. 建议路线（供讨论）

| 阶段 | 内容 | 规模估计 |
|---|---|---|
| **P0 诚信修复** | 下线或改造合成的 deepdive 元素；政策利率改为 BIS 自动 + 本地源交叉校验；Policy Tracker 从 canonical 派生；修 JP/ZA "n/a"、My Dashboard JS 报错、UZ/EG FX；加 provenance 验证 | 小到中 |
| **P1 能源 MVP** | §4.2 的 MVP 范围，约 35–40 张图 + 市场框架骨架 | 中 |
| **P2 贵金属** | §6，约 25 张图（数据可得性最好） | 小到中 |
| **P3 基本金属** | §5，约 35 张图（AKShare 依赖较多，需逐项验证） | 中 |
| **并行 A** | 薄弱国家"核心 8 项"、横向快速胜利（§3.2） | 持续 |
| **并行 B** | GMI 层：What changed、跨资产监控、regime 动量 | 中 |
| **卫生** | 清理根目录、迁移 Pages 部署方式 | 小 |

---

## 10. 需要你决定的问题

1. **合成内容的处置**：(a) 全部下线；(b) 能用真实分项替换的替换（例如 TR 用 Eurostat HICP 分项、
   ZA 用 SARB/Stats SA、KR 用 ECOS），其余下线；(c) 保留但标注为 "Illustrative / Model"。
   我推荐 (b)：Beveridge 历史、构造的工资史、硬编码 gauge 一律下线。
2. **优先级**：是否同意 P0 → 能源 → 贵金属 → 基本金属？还是先补薄弱国家或扩国家宇宙？
3. **能源范围**：是否包含电力市场（欧洲、中国）和煤？是否需要情景计算器（会明确标为模型）？
4. **数据权限**：是否愿意注册免费 key（EIA、GIE AGSI、e-Stat、KOSIS、Ember）？有没有 Bloomberg/LSEG
   等付费数据可以接入（这样可以补齐 TTF 日度、LME 期限结构、油轮运价、ETF 持仓等缺口）？
5. **国家宇宙**：是否加 G10 商品货币国（AU、CA、NO）和大 EM（IN、BR、MX、ID、SA）？
6. **发布方式**：是否把 Pages 改为 Actions 构建产物部署，让 `main` 不再每天提交几十 MB 的 HTML？

---

## 附录 A：本次数据源可达性实测（2026-11-04，本云沙盒出口）

| 来源 | 结果 | 备注 |
|---|---|---|
| FRED fredgraph CSV（无 key） | ✅ | Brent/WTI/HH 到 2026-10-27；GASREGW 到 2026-11-02；IMF 月度金属/能源到 2026-09；OVX、GVZ、DFII10、T5YIFR 到 2026-11-02/03 |
| EIA API v2 | ❌ 403 | 需要免费 key |
| EIA hist_xls（WCESTUS1、RCLC1、RNGC1） | ✅ | 无需 key |
| World Bank Pink Sheet 月度 xlsx | ✅ | |
| CFTC Socrata（COT 分类持仓） | ✅ | 最新 2026-10-27 |
| DBnomics IMF PCPS | ⚠ | 镜像只到 2025-06 |
| BIS WS_CBPOL 日度 | ✅ | |
| 日本财务省 JGB 曲线 CSV | ✅ | 到 2026-11-02 |
| ENTSOG API、energy-charts API、ECB Data Portal、JODI | ✅ | |
| GIE AGSI | ✅ 端点可达 | 需要免费 key |
| AKShare：SHFE 库存、SHFE 铜、新浪 LME 铜、SGE Au99.99、上海金基准价、中国成品油调价 | ✅ | 均为最新 |
| AKShare：LME 库存（jin10） | ⚠ | 停在 2026-07-17 |
| AKShare：SPDR/SLV 持仓（jin10） | ❌ | 超时 |
| IEA、LME 官网、LBMA JSON、Baker Hughes | ❌ 403 | 授权数据或屏蔽 |
| Yahoo Finance | ❌ 429 | 限流 |
| CBU（UZ）、CBE（EG）、NBS（NG） | ⏱ 超时 | 需在 GitHub Actions runner 上复测 |
| HKMA API、Taldau API | ? | 端点需确认，本次路径不对或返回 500 |
