# 交接文档（给新会话）

更新：2026-11-05。分支 `claude/magical-newton-6nyshr`（**未合并**；`main` 至今没有被改动过）。
新会话请先读本文件，再读 `AGENTS.md` 和 `PROJECT_LESSONS.md`（§9 是数据诚信规则）。

---

## 1. 用户已确认的决策

| 编号 | 决策 |
|---|---|
| D1 | **只用真实数据**。缺数据就留空或记为 data gap，不写死、不估算、不用 0 或 50 之类的占位值 |
| D2 | 顺序：P0 诚信修复 → 能源 → 贵金属 → 基本金属；重点是框架，降低以后加国家的成本 |
| D3 | 能源页包含电力和煤；模型可以做，但必须标 MODEL，并且不进 canonical frame |
| D4 | key 只放在本地或环境密钥里，**绝不能贴进对话、提交到仓库或写进日志** |
| D5 | Pages 采用方案 C（`data` 分支 + Actions 部署），并放在开关后面，由用户切换（见 `docs/PAGES_DEPLOYMENT.md`） |
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
6. **油价冲击 → CPI 模型**（MODEL）：`src/country_primer/oil_shock_model.py`，输出 `output/models/oil_shock_cpi.json`，显示在能源页宏观传导版块，冲击幅度可在页面上编辑。传导系数由能源 CPI 同比对本币布伦特同比（滞后 0–6 个月，自 2015 年起）的 OLS 回归估计；能源权重取官方数据（Eurostat `prc_hicp_iw` 的 NRG，以及 ONS CJVF），作为输入序列放在能源页的模型输入版块。美国权重无免费来源（BLS 返回 403），记为缺口。CEE 因汇率历史不足，用欧元计价的布伦特作驱动并在页面注明。土耳其新增 BIS 月度 `usd_try_bis`。

## 3. 架构速查

| 要做的事 | 位置 |
|---|---|
| 新增国家（不改代码） | `config/scopes.yaml` 加一条 + `config/countries/<slug>.yaml`（templates + params），见 AGENTS.md「Adding a Country」 |
| 新增市场页 | `config/scopes.yaml`（`kind: market`，排在经济体之后）+ `config/markets/<slug>.yaml` |
| 新数据源 | 在 `adapters.py` 或 `energy_adapters.py` 写函数，然后在 `fetchers.py` 的 `FETCHERS` 里注册（写明 call 方式、后处理模式、所在模块） |
| 派生序列 | YAML 里写 `derivation: derived`、`op`、`inputs`。可用算子：reference、spread、linear、ratio、product、rolling_mean、zscore、dev_from_5y_seasonal、yoy_pct，输入可加 `@monthly_mean`，可跨 scope 引用（如 `ENERGY:brent_spot`、`CN:manufacturing_pmi_akshare`）。市场页按注册表顺序构建：ENERGY → PRECIOUS → BASE |
| 面板（表格） | `transmission.py` 的 `PANELS`；在市场 YAML 里用 `panels:` 声明 |
| 跨国角色（政策利率、CPI、能源 CPI、汇率方向） | `config/scopes.yaml` 各 scope 下的 `roles` |
| 核心 48 映射 | `config/framework_v2.yaml`，或在指标 YAML 上加 `concept:`（会自动合并） |
| 来源等级 | 在 YAML 里声明 `source_authority`（official_primary / official_mirror / public_wrapper），否则按名字推断 |

## 4. 工作方式与验证

```bash
scripts/uv_project.sh run python scripts/build_scope.py <ID>         # 联网刷新一个 scope
COUNTRY_PRIMER_ONLY_INDICATORS=a,b scripts/uv_project.sh run python scripts/build_scope.py <ID>   # 只刷新指定指标
make rebuild-ui                                                        # 离线重建全部页面
make golden-diff                                                       # 与 HEAD 比较（忽略时间戳）；重构时必须为 0 差异
make validate                                                          # 提交前必须通过（当前 178 个测试）
scripts/uv_project.sh run python scripts/publish_smoke.py --local      # 页面冒烟检查
```

- 提交信息结尾要带会话要求的归属行。只推送到上面的分支，不要开 PR，除非用户要求。
- snapshot 模式（`rebuild-ui`）不会重写 canonical frame；要更新数据或来源字段，需要对那个 scope 做一次 refresh。
- 截图检查：Playwright 已预装，参考写法 `node shot.js <html> <png>`（用 `chromium.launch()`）。

## 5. 密钥

- 变量名：`FRED_API_KEY`、`EIA_API_KEY`、`GIE_AGSI_API_KEY`、`EMBER_API_KEY`、`ENTSOE_API_TOKEN`、`ESTAT_APP_ID`、`BLS_API_KEY`、`BOK_ECOS_API_KEY`、`TCMB_EVDS_API_KEY`、`FINMIND_API_TOKEN`、`KOSIS_API_KEY`。
- 云环境的密钥只对新开的会话生效。**新会话第一步**：只检查变量名是否存在，不要打印值，例如：
  `for k in EIA_API_KEY GIE_AGSI_API_KEY EMBER_API_KEY ENTSOE_API_TOKEN; do [ -n "$(printenv $k)" ] && echo "$k set" || echo "$k missing"; done`
- 本地运行时，`scripts/uv_project.sh` 会读取被 gitignore 的 `.env.local`。日志按值脱敏（`source_health.py`）。

## 6. 待办（按优先级）

1. **能源页里需要 key 的部分**（用户已添加 key，新会话应该能看到）
   - EIA API v2 / STEO：OPEC+ 分国产量、闲置产能、OECD 库存、全球供需平衡。需要新 fetcher `eia_v2`。
   - GIE AGSI+：欧盟及分国储气率。同时修复 CEE 的 `gas_storage_level` 路径。
   - Ember：发电结构。ENTSO-E 可选。
   - 补上以后，从 `energy.yaml` 的 data_gaps 里删掉对应条目。
2. **油价模型的后续**：美国能源权重（BLS relative importance，可尝试其他公开镜像）；英国车用燃料（07.2.2）纳入能源口径；更长的滞后窗口或分段样本；二轮效应模型（另立 MODEL，不与一轮效应混在一起）。
3. **基本金属页的后续**：矿山供给（Cochilco、INE、MINEM）、中国精炼产量和分品种进出口、COMEX 铜库存、更长的上期所库存历史（可以考虑在 refresh 时累积历史）、上期所近远月价差。
4. **后续小项**
   - 土耳其和中东欧的汇率历史太短，本币油价那一列为空（可以加 BIS `bis_fx` 月度序列）。
   - KZ/NG/UZ/EG 的原生政策利率。
   - CEE 叙述文字需要重写（例如 HU 行长写的还是 Matolcsy，应为 Varga）。
   - 欧元区职位空缺和协议工资已过期。
   - 中国 PBC 卡片里 DR007 显示 n/a。
   - 印度 IMF FSI 返回 403；可接入 MOSPI/RBI 原生数据。
   - 黄金 ETF 持仓缺来源；可加 `rolling_beta` 算子（金价对实际利率）。
   - Pages 切换由用户操作；第三阶段（`main` 不再跟踪生成文件）见 `docs/PAGES_DEPLOYMENT.md`。

## 7. 环境与数据源特性（已实测）

| 数据源 | 情况 |
|---|---|
| energy-charts | 连续请求会返回 429，fetcher 已加 Retry-After 退避 |
| IMF | `IMF.STA,IL` 的 key 是 `<ISO3>.RGV_REVS.FTO.M`（四段，五段会 403）；FSIC 数据流在本环境返回 403 |
| FRED | 部分 OECD 镜像已停更（印度 10Y 与 3M、M3 等）。不要上页面，记为 gap |
| EIA | 期货曲线 RCLC1-4 止于 2024-04-05 |
| 中国 | Eastmoney 部分接口会重置连接；NBS easyquery 返回 403 |
| 外盘期货 / SGE | 当天那一行是未收盘的会话，fetcher 只保留已收盘的交易日 |

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
