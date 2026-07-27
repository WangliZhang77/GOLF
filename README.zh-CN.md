# 新西兰华人高尔夫协会 CRM

[English README](README.md)

新西兰华人高尔夫协会一体化会员、活动与赛事 CRM，包含管理后台、会员 Web 端与 FastAPI 后端，支持中英双语。V1.0 覆盖协会基础管理，V1.5 将系统扩展为完整的高尔夫赛事运营平台（报名 → 分组 → 计分 → 审核 → 排名 → Handicap 沉淀）。

## 功能概览

### V1.0 — 基础 CRM

| 模块 | 要点 |
|------|------|
| 账号与权限 | JWT 登录、6 级角色、分会/球队数据隔离 |
| 组织架构 | 总会→分会→球队、入队审批 |
| 会员 CRM | 档案分级、等级/黑名单、转正、沉睡扫描 |
| 活动管理 | 发布、报名（含家属）、扫码签到、出勤统计 |
| 财务台账 | 收支流水、对账、作废/退款、会员账单（不接支付） |
| 消息中心 | 站内通知：报名、催缴、活动提醒 |

### V1.5 — 赛事运营平台

| 模块 | 要点 |
|------|------|
| 赛事管理 | 创建/发布赛事，报名资格校验（黑名单、欠费、差点上限） |
| 分组系统 | 差点均衡分组算法，尽量避免同队扎堆，支持排定 Tee Time、手动移组/换组 |
| 18洞计分 | 数字化逐洞记分，实时计算总杆/净杆，草稿→提交流程 |
| 成绩审核 | 同组球员确认 → 赛事总监审核，驳回后可修改重新提交 |
| 排名系统 | 个人排名（净杆）与球队排名（队内净杆均值），冠亚季军自动标注，支持人工调整奖项 |
| Handicap | 带审计轨迹的手动调整，变更历史 + 趋势仪表盘（下降/上升/稳定） |
| 球场管理 | 球场档案（洞数/标准杆/球场评分/坡度评分） |
| 赞助商 CRM | 企业档案 + 合同管理（金额/周期/权益，可关联具体赛事） |
| 数据分析 | 会员/活动/比赛/财务四大分析板块，理事按分会隔离查看 |

## 技术栈

- **后端：** Python 3.12 + FastAPI + SQLAlchemy 2.0 + Alembic + PostgreSQL
- **管理后台：** React + TypeScript + Ant Design（`admin-web`，端口 **5173**）
- **会员端：** React + TypeScript + antd-mobile（`member-web`，端口 **5174**）

## 目录结构

```text
golfststem/
  backend/          # FastAPI 后端
  admin-web/        # 管理后台
  member-web/       # 会员 Web App
  scripts/          # 一键启动/停止脚本
  docs/             # 开发日志与演示走查
  docker-compose.yml
```

## 快速启动（Windows）

**环境要求：** Docker Desktop、Python 3.12+、Node.js 18+

```powershell
# 一键启动（自动打开 API、管理后台、会员端三个窗口）
.\start.bat

# 或 PowerShell
.\scripts\start.ps1

# 日常开发（跳过种子与依赖检查，更快）
.\scripts\start.ps1 -SkipSeed -SkipInstall
```

**手动启动：**

```bash
docker compose up -d db
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

```bash
cd admin-web && npm install && npm run dev   # http://localhost:5173
cd member-web && npm install && npm run dev  # http://localhost:5174
```

- API 文档：http://localhost:8000/docs
- 演示走查：[docs/演示走查.md](docs/演示走查.md)

## 演示账号

| 用户名 | 密码 | 角色 | 端 |
|--------|------|------|-----|
| admin | admin123456 | 超级管理员 | 管理后台 |
| finance | demo123456 | 财务专员 | 管理后台 |
| council | demo123456 | 理事管理员 | 管理后台 |
| captain | demo123456 | 球队队长 | 管理后台 |
| director | demo123456 | 赛事总监 | 管理后台 |
| demo | demo123456 | 普通会员 | 会员端 |

## 测试

```bash
cd backend
.venv\Scripts\activate
pytest -q    # 137 条用例
```

> **说明：** 测试套件基于内存 SQLite 运行，137/137 全部通过。Alembic 迁移链尚未在真实 PostgreSQL 环境中完整验证过——建议在部署前先执行 `docker compose up -d db` + `alembic upgrade head` 做一次真库验证。

## 开发进度

**V1.0（Phase 0-7）** 已完成：脚手架 → 权限 → 组织 → 会员 → 活动 → 财务 → 消息 → 联调演示。

**V1.5（Phase 8-17）** 已完成：赛事CRUD与报名资格校验 → 分组 → 计分与审核 → 排名 → Handicap 管理 → 球场管理 → 赞助商 CRM → 数据分析看板 → 会员端首页升级。

**后置事项：** 上云部署、数据合规/KMS、微信小程序、性别相关分组规则、NZ Golf 官方 Handicap API 对接、Stripe/PayPal 支付网关对接。

## 许可

协会内部使用；具体条款请联系仓库维护者。
