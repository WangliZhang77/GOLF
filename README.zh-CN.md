# 新西兰华人高尔夫协会 CRM

[English README](README.md)

新西兰华人高尔夫协会一体化会员赛事 CRM（V1.0 Web 产品），包含管理后台、会员 Web 端与 FastAPI 后端，支持中英双语。

## 功能概览（V1.0）

| 模块 | 要点 |
|------|------|
| 账号与权限 | JWT 登录、6 级角色、分会/球队数据隔离 |
| 组织架构 | 总会→分会→球队、入队审批 |
| 会员 CRM | 档案分级、等级/黑名单、转正、沉睡扫描 |
| 活动管理 | 发布、报名（含家属）、扫码签到、出勤统计 |
| 财务台账 | 收支流水、对账、作废/退款、会员账单（不接支付） |
| 消息中心 | 站内通知：报名、催缴、活动提醒 |

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
| demo | demo123456 | 普通会员 | 会员端 |

## 测试

```bash
cd backend
.venv\Scripts\activate
pytest -q    # 50 条用例
```

## 开发进度

Phase 0–7 已完成（脚手架 → 权限 → 组织 → 会员 → 活动 → 财务 → 消息 → 联调演示）。

V1.5+ 后置：上云部署、数据合规/KMS、微信小程序、赛事计分、Stripe/PayPal 支付对接。

## 许可

协会内部使用；具体条款请联系仓库维护者。
