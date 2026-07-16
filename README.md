# 智能食堂预订系统

基于 Flask + SQLite + Web 的三层架构智能食堂预订系统，支持用户在线预订、库存管理、订单核销等完整功能。

## 项目结构

```
caidandemo/
├── database/          # 数据库层
│   ├── init_db.py     # 数据库初始化脚本
│   └── canteen.db     # SQLite数据库（运行后生成）
├── server/            # 服务端 API
│   ├── app.py         # Flask RESTful API
│   └── requirements.txt # 依赖配置
└── client/            # 客户端 Web
    ├── index.html     # 用户端界面
    └── admin.html     # 管理端界面
```

## 技术栈

- **后端**: Python 3.x + Flask 2.3 + Flask-CORS
- **数据库**: SQLite（WAL模式支持并发）
- **前端**: HTML5 + CSS3 + JavaScript

## 功能特性

### 用户端
- 🔗 用户身份绑定（姓名+工号）
- 📋 查看今日菜单（库存、限购信息）
- 🔍 菜品搜索（精确匹配+模糊匹配）
- 🛒 在线下单（数量选择）
- 📦 查询个人订单（取餐凭证）

### 管理端
- 🍽️ 菜品管理（上架、下架、库存、限购）
- 📦 订单管理（核销、取消）
- ⚙️ 系统配置（截止时间、取餐时段）
- 📊 数据统计（订单统计、热销TOP5、低库存预警）
- 📝 操作日志

## 快速开始

### 1. 安装依赖

```bash
cd server
pip install -r requirements.txt
```

### 2. 初始化数据库

```bash
python database/init_db.py
```

### 3. 启动服务

```bash
cd server
python app.py
```

服务将运行在 http://localhost:5000

### 4. 访问界面

- **用户端**: 打开 `client/index.html`
- **管理端**: 打开 `client/admin.html`

## API 接口

### 用户端接口
| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/bind` | POST | 用户绑定 |
| `/api/menu` | GET | 获取菜单 |
| `/api/search_dish` | GET | 搜索菜品 |
| `/api/order` | POST | 下单 |
| `/api/user_orders` | GET | 查询订单 |

### 管理端接口
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
| `/api/admin/stats` | GET | 今日统计 |
| `/api/admin/logs` | GET | 操作日志 |
| `/api/verify_order` | POST | 核销订单 |

## 数据库表结构

- **users**: 用户表（用户ID、姓名、工号、角色、绑定状态）
- **dishes**: 菜品表（名称、库存、限购、状态、营养信息、过敏原标签）
- **orders**: 订单表（订单号、用户ID、菜品、数量、下单时间、取餐截止、状态、取餐凭证）
- **system_config**: 系统配置表（配置键、值、更新时间）
- **admin_logs**: 管理员操作日志（操作人、操作类型、详情、时间）

## 配置说明

### 系统配置项（system_config）
- `order_cutoff_time`: 下单截止时间（默认 10:00）
- `take_start`: 取餐开始时间（默认 11:30）
- `take_end`: 取餐结束时间（默认 12:30）

### 默认管理员
- 用户ID: `admin_ma`
- 姓名: 马静
- 工号: `0001`

## 订单状态流转

```
pending（待取餐）→ taken（已取餐）
                → cancelled（已取消）[截止时间前]
                → overtime（超时未取）[自动]
```

## License

MIT License