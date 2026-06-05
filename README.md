# 全栈外卖管理系统 - 部署说明文档

> Takeaway Management System - Deployment Guide

---

## 一、系统概述

本系统是一套基于 B/S 架构的全栈外卖管理系统，实现顾客下单、商家接单、骑手抢单配送的完整业务闭环，支持 WebSocket 实时订单状态推送。

## 二、环境要求

### 2.1 硬件要求

| 项目 | 最低配置 | 推荐配置 |
|---|---|---|
| CPU | 2 核 | 4 核 |
| 内存 | 4 GB | 8 GB |
| 磁盘 | 10 GB 可用 | 50 GB SSD |
| 网络 | 局域网连接 | 100 Mbps+ |

### 2.2 软件要求

| 软件 | 版本 | 必选 | 说明 |
|---|---|---|---|
| Python | 3.10 及以上 | ✅ | 后端运行环境 |
| Node.js | 18 LTS 及以上 | ✅ | 前端运行环境 |
| npm | 9 及以上 | ✅ | 前端包管理器 |
| MySQL | 8.0 及以上 | 生产环境 | 可选，开发用 SQLite |
| Git | 2.40 及以上 | 可选 | 版本管理 |

## 三、项目结构

```
takeaway/
├── 项目开发计划书.md          # 项目计划文档
├── .gitignore                 # Git 忽略规则
├── .vscode/                   # VS Code 配置（隐藏 node_modules）
│   └── settings.json
├── backend/                   # 后端工程
│   ├── requirements.txt       # Python 依赖
│   └── app/                   # 应用源码
│       ├── main.py            # ★ 入口文件
│       ├── config.py          # 配置（数据库/JWT/CORS）
│       ├── database.py        # 数据库初始化
│       ├── models.py          # ORM 模型（7 张表）
│       ├── schemas.py         # Pydantic 校验
│       ├── utils.py           # 工具函数
│       ├── ws_manager.py      # WebSocket 管理
│       ├── service_utils.py   # 服务工具
│       └── routers/           # 路由层
│           ├── auth.py        # 认证（注册/登录）
│           ├── customer.py    # 顾客（下单/地址/订单）
│           ├── merchant.py    # 商家（菜品/接单/拒单）
│           └── courier.py     # 骑手（抢单/送达）
└── frontend/                  # 前端工程
    ├── index.html
    ├── package.json           # Node.js 依赖
    ├── vite.config.js         # Vite 构建配置
    └── src/
        ├── main.js            # ★ 入口文件
        ├── App.vue            # 根组件
        ├── api/
        │   ├── index.js       # Axios + JWT 拦截器
        │   └── services.js    # API 调用封装
        ├── router/
        │   └── index.js       # 路由 + 守卫
        ├── stores/
        │   └── auth.js        # Pinia 认证状态
        └── views/
            ├── Login.vue      # 登录/注册页
            ├── Customer.vue   # 顾客端
            ├── Merchant.vue   # 商家端
            └── Courier.vue    # 骑手端
```

## 四、部署步骤

### 4.1 获取代码

```bash
cd C:\Users\11422\Desktop\takeaway
```

### 4.2 后端部署

#### 4.2.1 安装 Python 依赖

```bash
cd backend
pip install -r requirements.txt
```

#### 4.2.2 配置数据库

编辑 `backend/app/config.py`：

```python
# 开发环境（SQLite，零配置，开箱即用）
DATABASE_URL: str = "sqlite+aiosqlite:///./takeaway.db"

# 生产环境（MySQL）
# DATABASE_URL: str = "mysql+asyncmy://用户名:密码@数据库IP:3306/数据库名"
```

#### 4.2.3 配置 JWT 密钥

```python
# 生产环境务必修改为随机密钥
JWT_SECRET: str = "your-random-secret-key-change-me"
```

#### 4.2.4 配置 CORS 跨域

```python
CORS_ORIGINS: List[str] = [
    "http://localhost:5173",   # Vue dev server
    "http://your-domain.com",  # 生产域名
]
```

#### 4.2.5 启动后端

**开发模式（热重载）：**

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

**生产模式：**

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 4
```

启动成功标志：

```
INFO:     Uvicorn running on http://0.0.0.0:8001
INFO:     Application startup complete.
```

#### 4.2.6 验证后端

浏览器打开 `http://127.0.0.1:8001/`，显示：

```json
{"status":"ok","service":"外卖管理系统 API","version":"1.0.0"}
```

API 文档：`http://127.0.0.1:8001/docs`

### 4.3 前端部署

#### 4.3.1 安装依赖

```bash
cd frontend
npm install
```

#### 4.3.2 启动开发服务器

```bash
cd frontend
npm run dev
```

启动成功标志：

```
VITE v5.x.x  ready in xxx ms
➜  Local:   http://localhost:5173/
```

#### 4.3.3 生产构建

```bash
cd frontend
npm run build
```

构建产物在 `dist/` 目录，可直接部署到 Nginx 等 Web 服务器。

**Nginx 配置示例：**

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    root /path/to/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 反向代理
    location /api/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebSocket 代理
    location /ws/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## 五、环境切换对照表

| 配置项 | 开发环境 | 生产环境 |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./takeaway.db` | `mysql+asyncmy://user:pass@host:3306/db` |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | `["https://your-domain.com"]` |
| `JWT_SECRET` | 默认值 | 随机 64 位字符串 |
| `uvicorn --reload` | ✅ 开启 | ❌ 关闭 |
| `uvicorn --workers` | 1 | 4 (CPU 核数) |
| 前端服务 | `npm run dev` (Vite) | `dist/` → Nginx |

## 六、首次使用指南

### 6.1 启动服务

```bash
# 终端1：后端
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# 终端2：前端
cd frontend
npm install          # 仅首次
npm run dev
```

### 6.2 注册账号

访问 `http://localhost:5173`，分别注册三个角色：

| 角色 | 用户名 | 密码 | 用途 |
|---|---|---|---|
| 🏪 商家 | m1 | 1234 | 登录后添加菜品 |
| 👤 顾客 | u1 | 1234 | 添加地址、浏览菜品、下单 |
| 🛵 骑手 | c1 | 1234 | 查看可抢订单、抢单 |

### 6.3 业务流程测试

```
1. 商家 m1 登录 → 添加菜品（如"黄金炒饭" ¥15）
2. 顾客 u1 登录 → 添加地址 → 浏览菜品 → 加入购物车 → 下单
3. 商家端收到 WebSocket 🔔 弹窗 → 点击"接单"
4. 骑手 c1 登录 → "可抢订单"标签页 → 看到订单 → 点击"抢单"
5. 骑手配送 → 点击"确认送达"
6. 订单流程完成 0→1→2→3
```

> 💡 不同角色请用不同浏览器或无痕窗口登录，避免 Token 互相覆盖。

## 七、常见问题

### Q1：启动报 "ModuleNotFoundError: No module named 'app'"

```bash
# 错误：从 backend/app/ 目录启动
cd backend/app && uvicorn main:app     # ❌

# 正确：从 backend/ 目录启动
cd backend && uvicorn app.main:app     # ✅
```

### Q2：前端 npm 命令不可用

```powershell
# PowerShell 执行策略问题
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

或改用 CMD（命令提示符）终端。

### Q3：数据库被清空

正常重启 uvicorn 不会清数据。只有删除 `takeaway.db` 文件才会重置。

### Q4：WebSocket 连接失败

- 确认后端已启动且端口 8001 可访问
- 确认前端 Vite 代理配置正确（`vite.config.js`）
- 检查浏览器控制台 WebSocket 连接状态

### Q5：如何让其他电脑访问

```bash
# 后端已监听 0.0.0.0，其他电脑可直接通过 IP 访问
# 前端需要其他电脑也运行 npm run dev，或访问本机的 5173 端口

# 查看本机 IP
ipconfig | findstr IPv4

# 其他电脑访问
http://你的IP:5173
```

### Q6：切换 MySQL

1. 确保 MySQL 8.0 已安装并创建数据库：
```sql
CREATE DATABASE takeaway DEFAULT CHARACTER SET utf8mb4;
```

2. 修改 `backend/app/config.py`：
```python
DATABASE_URL: str = "mysql+asyncmy://root:password@127.0.0.1:3306/takeaway"
```

3. 重启后端，表会自动创建。

---

> **版本**：V1.0
>
> **最后更新**：2026/6/1
