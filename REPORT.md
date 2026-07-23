# 智能食堂预订系统 — 交付与测试报告

> 生成时间：2026-07-23（沙箱本地）
> 系统：医疗类职工食堂 / 医院病人点餐预订系统
> 技术栈：Flask + SQLite(WAL) + 原生 HTML/CSS/JS（组件化）
> 验证环境：系统 Python 3.12（含 Flask 2.3.3），服务端口 5003

---

## 一、项目定位与边界

- **业务性质**：医疗类职工食堂外卖预订。所有餐品**提前下单/报名、售完即止**，中午到食堂一楼大厅自取；病人支持**床旁配送**。
- **三大核心模块（老板要求，已全部落地）**：
  1. **智能取餐 / 配送提醒** —— 订单页顶部横幅 + 实时倒计时；临近 30 分钟 / 到点用浏览器 Notification 提醒（localStorage 按 order_no 去重）；下单成功请求通知权限。
  2. **个人订单查询** —— 今日订单 + 历史按日期范围查询 + 配送状态展示。
  3. **健康数据关联 + 饮食建议（做深）** —— 健康档案 chips（控卡/低糖/高蛋白/低盐/清淡）+ 每日热量目标；拉取营养评估后叠加档案生成个性化建议（控卡比对、低糖>50g 警示、高蛋白且当日蛋白不足则推卤牛肉/鸡爪）。
- **真实菜单（8 品类）**：大肉包子 / 大馒头 / 红糖馒头 / 卤牛肉 / 柠檬鸡爪 / 凉拌猪耳朵 / 麻薯 / 水果双皮奶。

---

## 二、架构与本次交付

### 后端（Flask，分层：Blueprint / Service / DAO）
- 保留并修复了 `v1` Blueprint 全部端点。
- 修复了 `POST /api/v1/orders` 的 **17 值 / 16 列 INSERT bug**（多写一个 `?`），重写为 14 `?` ↔ 14 参数 ↔ 16 列，编译通过。
- 新增 `GET /api/v1/orders`：按 `order_no` 分组返回订单，含 `fulfillment_mode`、`delivery_status`、每品 `nutrition_info`。
- **履约模式统一**：`orders.fulfillment_mode ∈ {pickup, bed_delivery}`；床旁配送下单自动 `INSERT deliveries(status='ready')`。
- **医嘱规则引擎**（`server/services/diet_engine.py`）：按 `diet_type` 刚性过滤菜单（deny 隐藏、recommend 标注）。
- **营养科学**：Harris-Benedict 能量公式 + 蛋白目标；NRS-2002 筛查接口已留。
- **HIS 适配桩**：床头码 token 返回模拟患者档案 + 饮食医嘱。

### 前端（用户端，组件化「暖食市集」设计系统）
- `client/index.html`（骨架） + `client/css/{tokens,base,components}.css` + `client/js/{api,store}.js`
- `client/js/components/`：toast / modal / dishCard / cartBar / orderCard / healthPanel / reminderBanner
- `client/js/views/`：bedView（一床一码进入）/ menuView / ordersView / healthView
- `client/js/app.js`：路由状态机 + 提醒引擎 + 结算流程 + 身份切换
- 设计令牌：暖米底 `#FBF7F0` + 辣椒红 `#D8542B` + 鼠尾草绿 `#4F8A6A`；Fraunces 展示体 + Space Mono 取餐码；clamp() 流体排版、@container 响应式、`prefers-reduced-motion` 降级。

---

## 三、最终测试结果（24 / 24 全部通过）

测试脚本：`/tmp/final_test.py`（urllib 直连 `http://localhost:5003`，UTF-8 正确编码）
数据库状态：执行 `database/init_db.py` 重置为规范演示数据后运行一次。

| # | 测试项 | 结果 |
|---|---|---|
| 1 | 床头码进入 QR-END01 → 糖尿病饮食（菜单 5 项，隐藏红糖馒头/麻薯/水果双皮奶，推荐大肉包子/卤牛肉） | ✅ |
| 2 | 床头码进入 QR-CAR03 → 低盐低脂（隐藏卤牛肉/凉拌猪耳朵） | ✅ |
| 3 | 床头码进入 QR-SUR02 → 流质（仅水果双皮奶可选） | ✅ |
| 4 | 床头码进入 QR-REN05 → 肾病低蛋白（隐藏卤牛肉/柠檬鸡爪/凉拌猪耳朵） | ✅ |
| 5–10 | 医嘱规则引擎：diabetic / low_salt / liquid / renal_low_protein / low_purine / normal 六类（deny/recommend 符合预期） | ✅ |
| 11 | 下单（自取）：U1001 大馒头 ×1，履约模式 pickup，生成取餐码 | ✅ |
| 12 | 下单（床旁配送）：P001 大肉包子 ×1，履约模式 bed_delivery，自动建配送单 | ✅ |
| 13 | 订单查询：含床旁单且 `delivery_status=ready` | ✅ |
| 14 | 配送单列表：含本单（ready） | ✅ |
| 15 | 配送 marking：ready → dispatching → delivered | ✅ |
| 16 | 订单配送状态回写 delivered | ✅ |
| 17 | 营养评估：Harris-Benedict（能量 1744 kcal / 蛋白 78 g） | ✅ |
| 18–21 | HIS 适配：4 个床头码均返回正确患者档案 + 饮食类型 | ✅ |
| 22 | 饮食建议 `dietary_suggestion`（今日热量 550 / 糖 16 + 推荐项） | ✅ |
| 23 | 错误用例：缺 user_id → 拒绝（400/401） | ✅ |
| 24 | 错误用例：无效床头码 → 拒绝（404） | ✅ |

**汇总：PASS = 24，FAIL = 0。**

> 说明：过程中曾出现 3 次"假失败"，经核查均为**测试端伪影**而非代码缺陷 ——
> ① 测试曾误用不存在的 `/api/v1/dietary_suggestion` 路径（前端实际调用正确的 `/api/dietary_suggestion`）；
> ② 重复跑测试时同一用户命中"每人限购"被拒（**正确行为**）；
> ③ shell 把 curl 中文参数搅成非法 UTF-8 致静默解析失败。
> 重置数据库后单次运行即 24/24。

---

## 四、如何运行

```bash
# 1. 初始化 / 重置数据库（可选，已含演示数据）
python database/init_db.py

# 2. 启动服务（系统 Python 3.12，已含 flask）
python server/app.py
# 或指定端口：python -c "import server.app as a; a.app.run(port=5003)"

# 3. 访问
#    用户端：http://localhost:5000  （或 5003）
#    管理端：http://localhost:5000/admin
```
床头码演示入口：`QR-END01`（内分泌科/糖尿病）、`QR-CAR03`（心内科/低盐）、`QR-SUR02`（普外科/流质）、`QR-REN05`（肾内科/低蛋白）。

---

## 五、密钥 / 凭证问题处理状态

> 关键环境限制：**本沙箱无外网出口**（`curl api.github.com` = 000，且未安装 `gh` CLI）。
> 因此"联网侧"的密钥动作无法在本环境执行，以下区分**本环境已完成**与**需你本机执行**。

### ✅ 本环境已完成（本地可做的部分）
1. **已从用户级记忆文件移除明文 GitHub PAT**。
   - 原 `~/.workbuddy/MEMORY.md` 第 48 行以明文存储令牌 `ghp_…`，存在被同步/备份泄露的风险。
   - 已改写为"令牌已移出明文记忆，本地改用 `gh auth login`（OAuth）或环境变量 `GH_TOKEN`；勿将令牌写入会被同步的明文文件"的安全指引。
2. 产出 **`SECRETS_REMEDIATION.md`** —— 一份逐步可执行清单，覆盖下面所有联网侧动作。

### ⏳ 需你本机执行（必须联网，沙箱做不到）
1. **轮换 GitHub PAT**（原明文令牌视为已暴露）：GitHub → Settings → Developer settings → Personal access tokens → 撤销并新建，scope 收窄到最小。
2. **`auto-publish` 仓库密钥迁移**：把已提交进 Git 历史/仓库的 API 模型密钥迁出，改为 **GitHub Actions secrets**（Settings → Secrets and variables → Actions）。历史提交中的旧值仍需视为泄露并轮换对应密钥。
3. **桌面秘钥迁环境变量**：配置 LLM 的 API key 等不放明文文件，改用系统环境变量或密钥库。
4. 复核 `Desktop` 下无残留明文秘钥文件（此前全量扫描多为误报：boto3/cryptography 库源码、游戏存档、含 token 字样的代码）。

---

## 六、已知限制与后续（P4，尚未开始）

- 管理端 `admin.html` 尚未做"暖食市集"视觉统一。
- 营养工作台（膳食处方录入 / NRS-2002 筛查录入）仅留接口，未做 UI。
- 配送装车表 / 发餐表 UI 未做（后端 `deliveries` 端点已就绪）。
- 沙箱无外网，无法 `git push`；代码需你本机 `commit / push` 到 `github.com/RainmeoX/canteen-order-system`。
- SQLite 时区：本沙箱 `PRAGMA timezone='localtime'` 为 no-op，但 `'localtime'` 修饰符（`DATE('now','localtime')`）生效，订单按本地日期归类的逻辑已对齐。

---

## 七、本次收尾动作记录

1. ✅ 最终综合测试运行（24/24）
2. ✅ 写本报告（`REPORT.md`）
3. ✅ 密钥问题本地处理（擦除明文 PAT + 产出 `SECRETS_REMEDIATION.md`）
4. ⏻ PowerShell 关机（最后执行）

---
*报告结束。系统已验证可用，可交付预览。*
