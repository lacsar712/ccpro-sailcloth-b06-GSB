# SailCloth-01 · 帆布浸渍防水台

帆布间布卷与浸渍固化台账基线项目（Django 5 + DRF + Vue 3 SPA）。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 后端 | Django 5 · DRF · SimpleJWT · django-cors-headers · Gunicorn |
| 前端 | Vue 3 · Vite · Pinia · Vue Router |
| 数据库 | PostgreSQL 15 |
| 部署 | Docker Compose · Nginx（前端反代 `/api`） |

## 路径与端口

- **项目路径**：`d:\work\document\bytecode\claudeCodePro\SailCloth\SailCloth-01`
- **前端**：http://localhost:3740
- **API**：http://localhost:8740
- **PostgreSQL**：localhost:6140

## 演示账号

| 用户名 | 密码 | 角色 |
| --- | --- | --- |
| `admin` | `123456` | 管理员 |
| `worker` | `123456` | 操作工 |

登录页已预填 `admin` / `123456`。后端 entrypoint 执行 migrate + seed。

## 业务规则

布卷状态不可设为「已固化」（`cured`），除非该卷**最近一条** `DipRun` 的 `cureHours` 已记录且 **≥ 12**。

规则实现：`backend/core/rules.py`

## 树脂带过滤

管理员在 **`/resin-band` 树脂带过滤专页**设定显示下限与上限（含端点，0 ~ 100）。保存后：

- 晾晒架下方**浸渍流水**只出现树脂百分比落在带内的记录；
- **浸渍台账**列表用同一套带，带外不得混入；
- 空命中时流水与列表都为 0 条；
- 过滤只影响查询返回，绝不改动任何 `DipRun` 的树脂值。

树脂带全表只存一行；两人几乎同时提交两套上下限时，后写整版覆盖先写，流水与台账都跟最终那一版走。

实现：`backend/core/rules.py`（`get_resin_band` / `save_resin_band` 单行原子写）、`GET/PUT /api/resin-band/`（写操作仅管理员）、`GET /api/dips/` 统一套用树脂带。

## 快速启动

```bash
cd d:\work\document\bytecode\claudeCodePro\SailCloth\SailCloth-01
docker compose up --build
```

浏览器打开 http://localhost:3740

## SPA 信息架构

- **登录** → 进入主工作面
- **完整顶栏**：晾晒架 · 树脂带过滤 · 布卷台账 · 浸渍台账
- **`/` 帆布间晾晒架（主）**：按帆布间挂布卷芯片（挂签状态 `raw` / `dipping` / `cured`）；点击打开右侧面板登记 `DipRun`、切换固化状态；架下为浸渍流水次要信息流（按树脂带过滤）
- **`/resin-band` 树脂带过滤（专页）**：管理员设定显示下限/上限；操作工只读
- **`/rolls` · `/dips`（次要台账）**：保留列表/表单 CRUD；浸渍台账同样套用树脂带

API 契约：JWT、`/api/lofts|rolls|dips|dashboard|resin-band/`。

## 配色

海军蓝（navy）+ 帆布米色（canvas），与温室绿主题区分。
