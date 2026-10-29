# GitHub Actions 自动化流水线配置与运维指南

本项目已搭建全自动、无人值守的 **宏观经济数据看板 CI/CD 流水线** (`.github/workflows/scheduled_refresh.yml`)。为确保云端运行顺畅并具备自动提交发布权限，请在 GitHub 仓库中完成以下简要配置。

---

## 一、工作流触发规则与调度机制

1. **分层定时执行 (Schedule)**：
   - **工作日高频轻量刷新**：周一至周五 UTC 02:00（北京时间 10:00），重点覆盖隔夜外汇、利率、商品价格与高频金融市场指标。
   - **周末深度全量构建**：每周六 UTC 02:00（北京时间 10:00），全量运行 18 个国家/地区数据刷新、Core 48 覆盖率矩阵更新与数据源健康审计。
2. **控制台手动触发 (Manual Trigger)**：
   - 支持在 GitHub 控制台 `Actions` -> `Scheduled Macro Data Refresh & Publish` -> `Run workflow` 手动一键运行。
   - 可选参数：
     - `mode`: `auto`（默认自动判断）、`full`（强制全量 18 国深度构建）、`quick`（高频重点市场刷新）。
     - `country`: `ALL`（默认）或单独指定国家代码（如 `KR`, `TW`, `TR`, `CN`, `US`）。
3. **智能变动检测与自动发布**：
   - 仅当抓取到新增观测值、历史数据修正或状态变化时，由 `github-actions[bot]` 自动生成提交并推送至 `main` 分支。
   - 推送至 `main` 后，GitHub Pages 自动热更新上线；若无数据变动则静默安全退出，不污染 Git 历史。
4. **可视化运行仪表盘 (Job Summary)**：
   - 每次工作流运行详情页底部均会自动生成富文本 Markdown 仪表盘，呈现更新概况、18 国最新数据时间与数据源健康度评分。

---

## 二、必须配置的 GitHub 仓库权限

为允许流水线在抓取到新数据后自动 commit 并 push 回 `main` 分支：

1. 打开 GitHub 仓库页面：`https://github.com/DJiangwei/macro-dashboard`
2. 点击顶部导航栏 **`Settings`**
3. 在左侧侧边栏中找到 **`Actions`** -> **`General`**
4. 向下滚动至 **`Workflow permissions`** 区域：
   - 选择 **`Read and write permissions`**（读写权限）
   - 勾选 **`Allow GitHub Actions to create and approve pull requests`**
5. 点击 **`Save`** 保存设置。

---

## 三、配置 API 密钥 (Repository Secrets)

流水线支持云端自动读取第三方数据源的授权凭据。请在 GitHub 仓库中添加以下密钥：

1. 在仓库的 **`Settings`** -> **`Secrets and variables`** -> **`Actions`** 页面中；
2. 点击 **`New repository secret`** 分别添加如下密钥（名称须完全一致）：

| 密钥名称 (Secret Name) | 对应数据源 / 机构 | 说明 / 默认回退机制 |
| :--- | :--- | :--- |
| **`EIA_API_KEY`** | 美国能源信息署 (EIA) | 用于埃及、哈萨克斯坦、尼日利亚原油及凝析油日均产量月度数据。 |
| **`FINMIND_API_TOKEN`** | 台湾金融数据 API (FinMind) | 用于台湾加权股价指数 (TAIEX) 高频序列。 |
| **`TCMB_EVDS_API_KEY`** | 土耳其共和国中央银行 (EVDS) | 用于土耳其官方实体部门信心指数与央行外汇储备。 |
| **`BOK_ECOS_API_KEY`** | 韩国银行经济统计系统 (ECOS) | 用于韩国 PPI、核心 CPI 与广义货币 M2（未配置时自动回退为开源 sample 密钥）。 |
| **`FRED_API_KEY`** | 圣路易斯联储 FRED (可选) | 用于美联储官方 API（未配置时自动走公开无密钥 fred_graph CSV 机制）。 |

---

## 四、本地调试与运维常用命令

可在本地终端通过项目内置命令快速测试流水线各环节：

```bash
# 1. 模拟定时任务刷新 (自动判断工作日/周末)
make refresh-scheduled

# 2. 仅刷新重点高频市场
make refresh-quick

# 3. 本地预览生成的 GitHub Actions 富文本仪表盘
make ci-summary

# 4. 全量回归测试与质量契约校验
make validate

# 5. 手动发布本地变动至 GitHub Pages
make publish MSG="Update dashboard"
```
