# 智能食堂预订系统

基于 Flask + SQLite + Web 的三层架构智能食堂预订系统。

## 项目结构

```
canteen-order-system/
├── database/
│   ├── init_db.py          # 数据库初始化（含示例菜品）
│   └── canteen.db          # SQLite 数据库（自动生成）
├── server/
│   ├── app.py              # Flask 后端服务
│   └── requirements.txt
├── client/
│   ├── index.html          # 用户端页面
│   └── admin.html          # 管理端页面
├── start.bat               # Windows 一键启动
├── start.sh                # Linux/Mac 一键启动
└── README.md
```

## 技术栈

- 后端: Python 3.8+ / Flask 3.1 / Flask-CORS
- 数据库: SQLite (WAL 模式)
- 前端: HTML5 + CSS3 + 原生 JavaScript

## 快速开始

### Windows
```bash
# 双击 start.bat 即可
# 或命令行执行
start.bat
```

### Linux / Mac
```bash
./start.sh
```

### 手动启动
```bash
# 1. 安装依赖
pip install flask flask-cors

# 2. 初始化数据库（首次必须执行，会创建表 + 示例菜品 + 管理员）
python database/init_db.py

# 3. 启动服务
python server/app.py
```

服务启动后：
- 用户端: http://localhost:5000
- 管理端: http://localhost:5000/admin

## 默认账号

| 角色 | 入口 | 登录方式 |
|------|------|---------|
| 管理员 | http://localhost:5000/admin | ID 固定为 `admin`（马静），前端已内置 |
| 普通用户 | http://localhost:5000 | 输入「姓名 + 工号」即可登录，系统会自动用工号生成 user_id |

## 功能特性

### 用户端
- 用户登录（姓名 + 工号）
- 查看今日菜单（含营养信息、过敏标签）
- 菜品搜索（支持菜名 + 别名模糊匹配）
- 在线下单（自动校验截止时间、库存、限购）
- 查询今日订单 / 历史订单（订单号醒目显示）
- 健康饮食建议（基于今日订单统计热量糖分）
- 取餐提醒

### 管理端
- **数据概览**（可交互）
  - 今日订单 / 待取餐 / 已取餐 三个统计卡片，**点击可弹出对应订单详情**
  - 最近订单列表（直接展示最近 5 条，含下单人、菜品、状态）
  - 菜品库存概览（进度条可视化，低库存红色预警）
  - 热销菜品 TOP 5
  - 低库存预警
- 菜品管理（上架 / 下架 / 改库存 / 补货 / 改限购）
- 订单管理（核销 / 取消 / 列表查询，显示下单人姓名和工号）
- 系统配置（下单截止时间、取餐时段）
- 操作日志
- 超时订单处理

## API 接口

### 用户端
| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/bind` | POST | 用户登录/绑定 |
| `/api/menu` | GET | 获取今日菜单 |
| `/api/search_dish` | GET | 搜索菜品 |
| `/api/order` | POST | 下单 |
| `/api/user_orders` | GET | 查询今日订单 |
| `/api/user_orders/history` | GET | 查询历史订单 |
| `/api/dietary_suggestion` | GET | 健康饮食建议 |

### 管理端（所有接口需传 `admin_id`）
| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/admin/add_dish` | POST | 上架菜品 |
| `/api/admin/remove_dish` | POST | 下架菜品 |
| `/api/admin/update_stock` | POST | 修改库存 |
| `/api/admin/restock` | POST | 补货 |
| `/api/admin/update_limit` | POST | 修改限购 |
| `/api/admin/update_cutoff` | POST | 修改截止时间 |
| `/api/admin/update_take_time` | POST | 修改取餐时段 |
| `/api/admin/cancel_order` | POST | 取消订单 |
| `/api/admin/stats` | GET | 数据统计 |
| `/api/admin/orders` | GET | 订单列表 |
| `/api/admin/logs` | GET | 操作日志 |
| `/api/verify_order` | POST | 核销订单 |
| `/api/process_overtime` | POST | 处理超时订单 |

## 常见问题

**Q: 管理端所有操作都提示"无权限"？**
A: 数据库未初始化。请先执行 `python database/init_db.py`，会自动创建管理员 `admin`。

**Q: 用户下单提示"下单已截止"？**
A: 默认截止时间是每日 10:00。请在管理端「系统配置」修改截止时间，或测试时改成 23:59。

**Q: 启动报错 `ModuleNotFoundError: No module named 'flask'`？**
A: 执行 `pip install flask flask-cors` 安装依赖。

**Q: 想重置数据库？**
A: 删除 `database/canteen.db` 文件，再执行 `python database/init_db.py`。
