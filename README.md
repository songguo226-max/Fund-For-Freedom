# 基金查询 Web 应用

多基金查询工具：输入基金代码或名称，查看收益日历、月度分析、净值走势，支持自选、最近查看和 CSV 导出。

## 技术栈

- 后端：Python 3.12+、FastAPI、httpx、pytest。
- 前端：Vue 3、Vite、ECharts、Vitest。
- 依赖管理：根目录和 `backend/` 均保留 `pyproject.toml` / `uv.lock`，前端使用 npm。

## 目录结构

```text
backend/      FastAPI 后端，按 app / modules / integrations / infrastructure 分层
frontend/     Vue 前端，按 app / modules / integrations / shared 分层
scripts/      开发脚本和遗留静态报表脚本
assets/       静态模板等项目资产
docs/         架构、目录和开发说明
output/       本地生成的报表产物，不作为源码维护
```

详细规则见 [docs/directory-structure.md](docs/directory-structure.md)。

## 一键启动

在项目根目录运行：

```powershell
uv run main.py
```

启动后访问：

- 前端：http://127.0.0.1:5173
- 后端健康检查：http://127.0.0.1:8010/api/v1/health

按 `Ctrl+C` 停止前后端进程。

## 分开启动

后端：

```powershell
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8010
```

前端：

```powershell
cd frontend
npm install
npm run dev
```

前端开发代理在 [frontend/vite.config.js](frontend/vite.config.js) 中将 `/api` 转发到 `http://127.0.0.1:8010`。

## 测试与构建

```powershell
cd backend
python -m pytest
```

```powershell
cd frontend
npm test
npm run build
```

## 环境与配置

后端应用配置集中在 [backend/app/config/settings.py](backend/app/config/settings.py)。当前包含应用名称、版本和 CORS 来源。前端接口基址默认使用 `/api/v1`，也可通过 `VITE_API_BASE` 覆盖。

## 遗留静态报表

原始单基金静态 HTML 脚本已归档到 `scripts/legacy-static-reports/`，模板位于 `assets/templates/fund-calendar/`。它们保留作历史参考，不作为 Web 应用的主要 Module。

## 更多文档

- [docs/architecture.md](docs/architecture.md)：整体架构、Module 职责和调用关系。
- [docs/directory-structure.md](docs/directory-structure.md)：目录职责和新增文件放置规则。
- [docs/development-guide.md](docs/development-guide.md)：新增 Module、路由、数据源 Adapter 和测试的方法。
