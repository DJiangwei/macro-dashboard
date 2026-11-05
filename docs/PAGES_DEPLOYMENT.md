# GitHub Pages 部署：方案 C（data 分支 + Actions 部署）

规格见 `docs/superpowers/specs/2026-11-04-scope-framework-and-markets-design.md` §7。

**状态：已于 2026-11-05 切换完成**（data 分支 bootstrap → `PAGES_MODE=actions` → Pages 来源改为 GitHub Actions → 首次部署 run 42109278643 成功，线上冒烟 51/51）。下面的切换步骤保留作记录与回滚参考。

## 结构

| 位置 | 内容 | 谁写入 |
|---|---|---|
| `main` | 代码与配置 | 人工提交 |
| `data` 分支 | `output/*.json`、`output/*.md`、`data/*.json`（canonical、summary、快照、缓存） | 定时刷新（`scripts/data_branch.sh push`） |
| Pages 站点 | 部署时用 `make rebuild-ui` 从 data 分支离线重建全部页面 | `deploy_pages.yml` |

HTML 不再存在任何分支上，每次部署都从数据重新生成。部署使用与"从分支发布"相同的
Jekyll 构建，所以现有 URL（包括 `.md` 审计页）全部不变。

## 开关

所有新流程都受仓库变量 `PAGES_MODE` 控制：

- 未设置（默认）：和现在完全一样，定时刷新把产物提交到 `main`，Pages 从 `main` 发布。
- `PAGES_MODE=actions`：定时刷新先拉取 data 分支，再把刷新后的数据推回 data 分支，然后调用部署；
  不再向 `main` 提交任何产物。

## 切换步骤（需要你在 GitHub 上操作）

1. 把本分支合并到 `main`。此时 `PAGES_MODE` 未设置，线上行为不变。
2. Actions → **Bootstrap data branch** → Run workflow（ref 用 `main`）。这会用 `main` 上当前的
   JSON 创建 `data` 分支；如果该分支已存在，会拒绝运行。
3. 以下两项请同时完成：
   - Settings → Secrets and variables → Actions → **Variables** → 新建 `PAGES_MODE`，值为 `actions`
   - Settings → Pages → Build and deployment → Source 改为 **GitHub Actions**
4. Actions → **Deploy Pages from data branch** → Run workflow。部署结束后会自动对线上站点跑
   `scripts/publish_smoke.py`；本地也可以运行 `make publish-check`。

## 日常使用

- 本地开发前先运行 `make pull-data`，把 data 分支上的最新数据覆盖到工作区。
- 手工刷新数据后发布：`make publish-data MSG="说明"`（推送数据并触发部署，需要 `gh`）。
- 修改代码后推送到 `main`，`deploy_pages.yml` 会自动用最新代码和 data 分支数据重建并部署。

## 回滚

1. Settings → Pages → Source 改回 **Deploy from a branch**（`main` / root）。
2. 删除 `PAGES_MODE` 变量（或改成其他值）。定时刷新会恢复为向 `main` 提交产物。
3. 如果 data 分支上的数据比 `main` 新：`make pull-data && make rebuild-ui`，然后提交到 `main`。

## 第三阶段（稳定运行一段时间后再做）

确认部署稳定后，可以让 `main` 不再跟踪生成文件，仓库体积和冲突都会明显下降：

```bash
git rm -r --cached output index.html chart_studio.html my_dashboard.html policy_tracker.html chart_studio_catalog.json CORE_COVERAGE_MATRIX.md DATA_FRESHNESS_AUDIT.md DATA_SOURCE_CATALOG.md MACRO_WORKBENCH_BRIEFING.md
```

然后把这些路径加入 `.gitignore` 并提交。这一步之后 `make validate` 需要先 `make pull-data && make rebuild-ui`
（CI 的 `validate.yml` 已经会在 data 分支存在时自动这样做）。
