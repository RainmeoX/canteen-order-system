# 智能食堂预订系统

基于 Flask + SQLite + Web 的三层架构智能食堂预订系统。

## 项目结构

```
caidandemo/
├── database/
│   ├── init_db.py
│   └── canteen.db
├── server/
│   ├── app.py
│   └── requirements.txt
└── client/
    ├── index.html
    └── admin.html
```

## 技术栈

- 后端: Python 3.x + Flask 2.3 + Flask-CORS
- 数据库: SQLite (WAL模式)
- 前端: HTML5 + CSS3 + JavaScript

## 功能特性

### 用户端
- 用户身份绑定
- 查看今日菜单
- 菜品搜索
- 在线下单
- 查询个人订单

### 管理端
- 菜品管理
- 订单管理
- 系统配置
- 数据统计
- 操作日志

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

服务运行在 http://localhost:5000

### 4. 访问界面

- 用户端: http://localhost:5000
- 管理端: http://localhost:5000/admin

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

- users: 用户表
- dishes: 菜品表
- orders: 订单表
- system_config: 系统配置表
- admin_logs: 管理员操作日志表

## 配置说明

系统配置项:
- order_cutoff_time: 下单截止时间 (默认 10:00)
- take_start: 取餐开始时间 (默认 11:30)
- take_end: 取餐结束时间 (默认 12:30)

默认管理员:
- user_id: admin_ma
- name: 马静
- employee_id: 0001

## License

MIT License