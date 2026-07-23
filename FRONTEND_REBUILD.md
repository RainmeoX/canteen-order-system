# 智能食堂预订系统 · 用户端组件化重构（本轮交付）

## 范围
按 `ARCHITECTURE.md §6` 把原单文件用户端（751 行 `index.html`）重构为**成熟组件化体系**，并补齐老板三点要求；后端 v1 端点收尾 + 新增「按用户查订单」接口。

## 后端（server/app.py · 已验证）
- 修复 v1 `POST /api/v1/orders` 的 **17 值/16 列** INSERT bug（多写一个 `?` + 僵尸进程/`__pycache__` 掩盖），现 14 `?` ↔ 14 参数 ↔ 16 列对齐。
- 新增 `GET /api/v1/orders?user_id=&scope=today|history`：按 `order_no` 分组，含 `fulfillment_mode`、`delivery_status`、`每品 nutrition_info`（JOIN dishes）。旧 `/api/user_orders` 不含这些字段，前端统一走 v1。
- 全链路实测（urllib 打本机 5003）8 项全绿：bed/enter 医嘱过滤菜单、床旁配送下单自动生成 deliveries、marking、nutrition/assess(1957kcal/78g)、his/patient、diet/rules、旧 user_orders 时区修复。

## 前端（client/ · 暖食市集设计系统）
```
client/
├── index.html              # 应用壳：nav + 提醒横幅 + 三视图 + 购物车栏 + 底部 tab + 床头码进入层
├── css/{tokens,base,components}.css   # 设计令牌 / 重置排版容器查询 / 全部组件类
└── js/
    ├── api.js    # 统一 fetch（超时/错误归一）
    ├── store.js   # session/cart/health（localStorage 持久）
    ├── components/  # toast / modal / dishCard / cartBar / orderCard / healthPanel / reminderBanner
    ├── views/      # bedView(一床一码) / menuView / ordersView / healthView
    └── app.js    # 路由状态机 + 提醒引擎 + 结算
```
**三大模块**
1. **智能取餐/配送提醒**：订单页顶部横幅 + 实时倒计时；临近 30 分钟 / 到点触发浏览器 Notification（按单 localStorage 去重）；床旁配送改显「配送员已出发 / 已送达」。
2. **个人订单查询**：今日 + 历史（日期范围），展示取餐码 / 履约模式 / 配送状态 / 明细 / 合计。
3. **健康关联 + 饮食建议（做深）**：本地健康档案（目标 chips + 每日热量目标）→ 叠 `/api/dietary_suggestion`；`nutrition/assess` 算 NRS-2002 + 能量/蛋白目标；医嘱联动刚性过滤禁忌菜、推荐适宜菜；今日热量/蛋白/糖 vs 目标进度条。

床头码入口（`QR-END01` 糖尿病 / `QR-CAR03` 低盐 / `QR-SUR02` 流质 / `QR-REN05` 低蛋白）经 HIS 适配桩自动定位科室床位、同步患者主索引、按医嘱过滤菜单；职工/访客走 `fulfillment_mode=pickup` 自取。

## 校验
- 13 个 JS 文件 `node --check` 全过；命名空间交叉审计（所有 `Canteen.*` 调用均有定义）。
- 用 Node 全局 `fetch` 实测 `api.js`+`store.js` 对 5003 真实可用；修复 1 个真 bug：前端 `healthView` 读 `na.data.xxx`，但 `nutrition/assess` 返回**顶层字段**（无 data 包裹）→ 已改读顶层。

## 预览
- 开发服务：http://localhost:5003 （Flask 后台运行中）
- 注意：沙箱无外网，无法 push GitHub；需你本机 commit / push。管理端暖食市集化（P4）尚未开始。
