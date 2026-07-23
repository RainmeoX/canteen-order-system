# 智能食堂预订系统 · 目标架构（v2 重构蓝图）

> 本文档基于两轮调研（GitHub 开源项目 + CSDN 技术博文 + 好伙狮/戈子等商业化方案）与现有代码底盘，给出**面向"医院病人点餐"的成熟系统架构**。
> 设计原则：**在现有 Flask + SQLite 底盘上原地进化**，不推翻重来；新增领域能力（病区/床位/医嘱/配送/营养）以**不破坏现有 API 契约**的方式扩展。

---

## 0. 现状底盘（必须尊重的约束）

现有系统是一个**职工食堂外卖预订、食堂一楼自取**的最小可用系统。

| 层 | 现状 | 评价 |
|---|---|---|
| 后端 | 单文件 `server/app.py`（Flask + flask-cors），约 1190 行，所有路由平铺 | 能跑、契约清晰，但**无分层、无蓝图、难维护** |
| 数据库 | SQLite 单文件 `database/canteen.db`，5 张表：`users` / `dishes` / `orders` / `system_config` / `admin_logs` | 无病区、床位、医嘱、配送概念 |
| 前端 | `client/index.html` + `css/style.css` + `js/app.js`（暖食市集风，已三层拆分） | 视觉达标，但**逻辑全堆在单文件、无组件化、无状态管理** |
| 管理端 | `client/admin.html`（旧版，未做暖食市集化） | 功能在，体验落后 |

**已存在的后端字段（重构必须保留，含历史拼写）**：
`take_deadline`（deadline 拼写错误，沿用）、`pickup_code`、`order_no`、`items[]`、`today_calories`/`today_sugar`/`today_protein`、`status ∈ {pending, taken, cancelled, overtime}`。

---

## 1. 调研结论：成熟系统长什么样

### 1.1 开源参考（可直接借鉴的结构）

| 项目 | 技术栈 | 可借鉴点 |
|---|---|---|
| **xiaobudian（小不点住院点餐）** | Node + MongoDB + Redis，Framework7，双微信服务号 | **病区/床位 QR 下单**、护理员设食谱、护士审核后录入院内系统、住院结算通道 |
| **apoorvaa227/hospital_food_management** | NestJS + Prisma + Postgres/Mongo + JWT | **三角色分离**：Food Manager（患者档案：病种/过敏/房号/床号/楼层 + 膳食处方 diet chart 早/晚/夜 + 派工给 pantry）、Inner Pantry（备餐任务）、Delivery（送达 marking） |
| **MarianaAzedo/hospitalmenu** | Express + MongoDB | **按饮食医嘱过滤菜单**（糖尿病→隐藏含糖菜）、**到点未填菜单推送提醒** |
| **Sahilvijayvergiya/Hospital-Food-Delivery-System** | React(Vite) + MUI + Context + Express + Mongo + JWT | **清晰三角色前端**（Manager / Inner Pantry / Delivery），React 组件化范式 |
| CSDN 多篇（Flask/Django + Vue3 + MySQL） | 前后端分离、RBAC、JWT、Redis 缓存、WebSocket 推送、ECharts 报表 | 国内"医院食堂订餐"主流实现，技术选型与我们底盘最接近 |

### 1.2 商业化方案（好伙狮 / 戈子科技等，定标准用）

- **"一床一码"床头订餐**：每床贴专属二维码，扫码自动定位科室/床位，预订下一餐或未来多日，选菜→支付→食堂按单备餐→配送员凭**装车表/发餐表**逐床送达。
- **医嘱联动（核心医疗闭环）**：对接 HIS/EMR，实时同步饮食医嘱（糖尿病/低盐低脂/流质/肾病低蛋白…）；点餐时**刚性过滤**——禁忌菜直接隐藏或标"不可选"，适宜菜优先+标"推荐"。
- **治疗膳食标准化**：营养师预设精确到克的标准化食谱（BOM），后厨按色标/图标生产，餐盒加粗标注饮食类型。
- **配送调度**：路径规划、状态追踪（出库→病区→签收）、冷链温控、RFID 餐具回传实际摄入。
- **周期菜单 + 偏好记忆**：周模板提前备料；记录患者禁忌/取消过的菜，下次默认排除。
- **多角色 + 就诊卡一卡通**：医护/病患/陪护独立账户与权限；饭卡/微信/支付宝/挂账多渠道支付。
- **食安与进销存**：留样、溯源、明厨亮灶；采购→收货→出库→盘点→临期预警全链路。

### 1.3 营养科学基线（让"饮食建议"不是摆设）

- 营养风险筛查：**NRS-2002 / MUST**。
- 能量需求：**Harris-Benedict / WHO 公式** × 应激系数；蛋白 0.8–1.0 g/kg/d（常规）、1.2–1.5（术后）、1.5–2.0（烧伤/重症感染）。
- 膳食分型：**流质 / 半流质 / 普食 / 糖尿病 / 肾病低蛋白 / 低盐低脂 / 低嘌呤**。

---

## 2. 目标分层架构

```
┌──────────────────────────────────────────────────────────────────┐
│                          客户端 (Client)                        │
│   用户端 SPA(床头码/自取)   管理端   营养科工作台   配送端   │
│   (vanilla 组件化 / 可选 Vite)                              │
└───────────────────────────────┬──────────────────────────────┘
                                    │  HTTPS / JSON
┌─────────────────────────────────┴──────────────────────────────┐
│                      API 网关层 (Flask Blueprint)               │
│  /api/v1/auth   /menu   /orders   /diet   /delivery        │
│  /admin  (兼容旧 /api/* 端点不破坏)                          │
└───────────────────────────────┬──────────────────────────────┘
                                    │
┌─────────────────────────────────┴──────────────────────────────┐
│                      领域服务层 (Service)                      │
│  认证(JWT-lite)  菜单/库存  订单引擎  医嘱规则引擎           │
│  营养评估(NRS-2002 stub)  配送调度  报表                     │
└───────────────────────────────┬──────────────────────────────┘
                                    │
┌─────────────────────────────────┴──────────────────────────────┐
│                  数据访问层 (DAO) + HIS 适配 stub            │
│  SQLite(WAL)  ‖  his_adapter.py（模拟医嘱/患者主索引）     │
└──────────────────────────────────────────────────────────────────┘
```

**为何不换栈**：Postgres/NestJS 更"标准"，但本沙箱无外网、无 PG 服务，换了等于产出跑不起来的代码。Flask+SQLite 能**本地立即跑通预览**，且 CSDN 主流方案同样用 Flask/Django，足够成熟。模块化靠 **Blueprint + Service + DAO 分层**实现，而非换语言。

---

## 3. 角色模型（来自 hospital_food_management + 好伙狮）

| 角色 | 入口 | 核心职责 |
|---|---|---|
| **患者 / 家属** | 用户端（扫码或自取） | 按医嘱可见菜单内点餐、查订单、收取餐/配送提醒 |
| **营养科 / 护士** | 营养工作台 | 维护患者档案（病种/过敏/床位）、设膳食处方、审核订单、营养评估 |
| **食堂管理员** | 管理端 | 菜品/库存/限购/截止时间/统计/核销（沿用现有） |
| **配送员** | 配送端（移动） | 看装车表/发餐表，逐床送达并 marking |

> 当前阶段先把 **患者端 + 营养工作台（医嘱联动/饮食建议）+ 管理端** 做扎实；配送端可作为"床旁配送模式"的状态追踪，不单独起 APP。

---

## 4. 领域模型扩展（新增表，不破坏旧表）

```sql
-- 病区/床位（一床一码的基础）
wards(id, dept, floor, bed_qr_token UNIQUE)
-- 患者主索引（可经 HIS stub 同步；也可手动建）
patients(id, name, bed_id→wards, dept, diseases JSON,
         allergies JSON, diet_type, energy_target, protein_target,
         created_at)
-- 膳食处方 / 周期菜单模板
diet_charts(id, patient_id, meal_slot∈{早餐,午餐,晚餐,加餐},
            items JSON, note, effective_date)
-- 医嘱规则：菜品 ↔ 饮食类型 的允许/禁忌映射（规则引擎数据源）
diet_rules(id, diet_type, dish_name, action∈{allow,deny,recommend})
-- 配送单（履约模式=床旁配送时生成）
deliveries(id, order_no, ward_id, bed_id, courier,
            status∈{ready,dispatching,delivered}, delivered_at)
-- 营养评估记录
nutrition_assess(id, patient_id, tool∈{NRS2002,MUST},
                 score, risk_level, created_at)
```

`orders` 表**扩展**字段（向后兼容）：加 `fulfillment_mode ∈ {pickup, bed_delivery}`、`patient_id`、`ward_id`、`meal_slot`、`diet_chart_id`。原 `take_deadline`/`pickup_code`/`status` 全部保留。

---

## 5. API 设计（v1 扩展 + 旧端点兼容）

**保留（现有前端依赖，一字不改）**：
`/api/bind` `/api/menu` `/api/categories` `/api/search_dish`
`/api/order` `/api/order_batch` `/api/user_orders` `/api/user_orders/history`
`/api/dietary_suggestion` `/api/verify_order` 及全部 `/api/admin/*`。

**新增 v1（能力扩展）**：
| 端点 | 说明 |
|---|---|
| `POST /api/v1/bed/enter` | 床头码 `bed_qr_token` → 返回病区/床位/绑定患者档案与可见菜单 |
| `GET  /api/v1/diet/rules?diet_type=` | 医嘱规则引擎：返回该饮食类型下允许/禁忌/推荐菜品 |
| `POST /api/v1/diet/charts` | 营养科建膳食处方 |
| `POST /api/v1/orders` | 支持 `fulfillment_mode`，床旁配送自动生成 `deliveries` |
| `GET  /api/v1/nutrition/assess` | NRS-2002 评估 + 能量/蛋白目标计算 |
| `GET  /api/v1/deliveries?status=` | 配送端装车表/发餐表 |
| `POST /api/v1/deliveries/<id>/mark` | 送达 marking |
| `GET  /api/v1/his/patient/<bed>` | HIS 适配 stub：返回模拟医嘱/患者主索引 |

---

## 6. 前端架构（"成熟体系"的具体落点）

不再是单文件堆 JS。结构：

```
client/
├── index.html              # 应用壳（挂载点 + 设计令牌）
├── css/
│   ├── tokens.css         # 设计系统变量（暖食市集：米底/辣椒红/鼠尾草绿）
│   ├── base.css           # 排版/栅格/容器查询响应式
│   └── components.css      # 卡片/按钮/Toast/模态/进度条
├── js/
│   ├── app.js             # 启动 + 路由(Tab/视图状态机)
│   ├── api.js             # 统一 fetch 封装（含错误/超时/重试）
│   ├── store.js           # 轻量状态（用户/购物车/健康档案，localStorage 持久）
│   ├── components/         # 组件化：dishCard / cartBar / orderCard /
│   │                       #   healthPanel / reminderBanner / modal / toast
│   └── views/            # menuView / ordersView / healthView / bedView
└── assets/                # 图标(内联SVG)/字体(Fraunces+Space Mono)
```

**操作逻辑 / 用户流**（对标老板三点 + 成熟范式）：
1. **智能取餐/配送提醒**：订单页横幅 + 实时倒计时；下单后请求通知权限，临近 30 分钟/到点各推一次；床旁配送模式改为"配送员已出发/已送达"推送。`localStorage` 按单去重。
2. **个人订单查询**：今日 + 历史（日期范围），分组展示取餐码/配送状态/明细/合计。
3. **健康数据关联 + 饮食建议（做深）**：本地健康档案（目标 chips + 每日热量目标）叠后端 `/api/dietary_suggestion` → 个性化；接入 `nutrition_assess`（NRS-2002 简化版）算出能量/蛋白目标；**医嘱联动**下菜单刚性过滤禁忌菜、推荐适宜菜。

**设计系统**：沿用已验证的"暖食市集"（医疗场景需稳重，故主色收敛为辣椒红+鼠尾草绿，避免花哨）；Fraunces 展示体 + Space Mono 取餐码；流体 `clamp()` 排版；`@container` 响应式（手机单列→宽屏网格）；指数缓动微交互；`prefers-reduced-motion` 降级；WCAG AA 对比度 + 键盘可达 + ARIA。

---

## 7. 分阶段实施计划

| 阶段 | 范围 | 交付 | 破坏旧功能？ |
|---|---|---|---|
| **P0 架构文档** | 本文 | `ARCHITECTURE.md` | 否 |
| **P1 后端模块化** | `app.py` 拆 Blueprint/Service/DAO；新增表迁移脚本（保留旧表） | 分层清晰、可跑 | 否（旧端点全保留） |
| **P2 用户端成熟重构** | 组件化前端 + 设计系统 + 三大模块（提醒/订单/健康）+ 床头码入口 | 用户端上线 | 否 |
| **P3 医嘱/营养引擎** | `diet_rules` + 规则引擎 + NRS-2002 stub + HIS stub | 禁忌拦截/推荐/评估可用 | 否 |
| **P4 管理端 + 配送** | 管理端暖食市集化 + 营养工作台 + 配送装车/发餐表 | 全角色闭环 | 否 |
| **P5 数据真实化** | 把真实 8 品类 + 群聊报名灌库（需你确认重置 DB） | 脱离示例数据 | 需重置 DB |

---

## 8. 本沙箱的硬限制（必须说清）

- **无外网出口**：Bash 内 `curl`/git 到 GitHub 全部失败；WebFetch 也**无法带 PAT 登录私有库**。故：① 无法在此 `git push` 或拉私有库；② 所有代码**本地写、本地 Flask 跑预览**，你本机再 commit/push。
- **无 Postgres/Node 构建链**：故坚持 Flask+SQLite+原生 JS（或轻量 Vite），不引入需构建/服务的中间件。
- 结论：本轮我能交付**本地可运行、架构清晰、对标成熟方案**的代码与文档；"上线/对接真实 HIS"需你在本机或医院内网完成。

---

## 9. 与老板三点要求的映射（避免"半成品"感）

| 老板要求 | 成熟方案对应 | 本架构落点 |
|---|---|---|
| 智能提醒，记得及时去取 | 好伙狮配送提醒 / hospitalmenu 到点提醒 | P2 提醒横幅+倒计时+系统通知；床旁模式改配送推送 |
| 个人也能查最近订了啥 | 订单追踪（出库→送达） | P2 今日+历史订单查询；P4 配送状态 |
| 健康数据关联 + 饮食建议做深 | 医嘱联动 + NRS-2002 + 能量/蛋白计算 | P3 规则引擎 + 营养评估 + 个性化建议 |
