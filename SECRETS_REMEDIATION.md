# 密钥 / 凭证 整改清单（SECRETS_REMEDIATION）

> 背景：此前 GitHub PAT 以明文存于用户级记忆文件 `~/.workbuddy/MEMORY.md`（该文件可能被 WorkBuddy 同步/备份），属泄露风险。
> 本沙箱**无外网**（`curl api.github.com`=000，未装 `gh`），故"联网侧"动作只能由你在本机执行。
> 本环境已完成：**已从明文记忆文件移除 PAT** + 本清单。

---

## ⏃ 第 1 步：轮换 GitHub PAT（视为已暴露）

明文曾落入同步文件 = 视为泄露。立即撤销并新建：

1. 打开 https://github.com → 右上角头像 → **Settings** → 左侧 **Developer settings** → **Personal access tokens** → **Tokens (classic)**（或 Fine-grained）。
2. 找到原 PAT（即此前明文存于记忆文件的那个 `ghp_…`），点 **Revoke / Delete**。
3. 点 **Generate new token**，按最小权限原则勾选 scope：
   - 仅本地推送/API 需要：`repo`（或按仓库细分）、`read:org`（可选）。
   - 不要勾 workflow / admin 等无关权限。
4. 复制新 token，**只存一处**：
   - 推荐：`gh auth login`（OAuth，免令牌文件）；或
   - 系统环境变量 `GH_TOKEN`（下文第 3 步），**不要**写进任何会被同步/备份的明文文件。

---

## ⏃ 第 2 步：把 `auto-publish` 仓库密钥迁到 GitHub Actions secrets

该仓库历史/当前提交里含有 API 模型密钥（LLM API key 等），需从代码移除并改为 Actions 密钥：

1. 打开 https://github.com/RainmeoX/auto-publish → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**。
2. 把每个密钥（如 `OPENAI_API_KEY`、`ANTHROPIC_API_KEY` 等）逐个录入为 Repository secret。
3. 修改仓库内使用密钥的代码/工作流，改为从 `secrets.XXX` 读取（GitHub Actions 中 `${{ secrets.XXX }}`；本地脚本读环境变量）。
4. **清理已提交的历史密钥**：
   - 历史提交仍含旧值 → 旧值同样视为泄露，去对应服务商后台轮换。
   - 用 `git filter-repo` 或 BFG 从 git 历史擦除密钥文件/字符串（注意：会改变历史哈希，需 force push，协作仓库先沟通）。
   - 擦除后**必须轮换**对应密钥（擦历史 ≠ 旧值安全）。

---

## ⏃ 第 3 步：桌面 / 本地秘钥迁环境变量

配置 LLM 的 API key 等不放明文文件：

**Windows（PowerShell）：**
```powershell
# 用户级环境变量（永久）
[System.Environment]::SetEnvironmentVariable("OPENAI_API_KEY", "sk-xxx", "User")
[System.Environment]::SetEnvironmentVariable("GH_TOKEN", "ghp-新值", "User")
# 当前会话立即生效：
$env:OPENAI_API_KEY = "sk-xxx"
```
**或** 系统"设置 → 关于 → 高级系统设置 → 环境变量" 图形界面录入。

**代码中读取（Python 示例）：**
```python
import os
api_key = os.environ["OPENAI_API_KEY"]   # 不写死、不进文件
```

**核查**：全 `Desktop` 下若有 `.env` / `config.json` / 含 `key=` `token=` `password=` 的明文文件，移入环境变量或系统凭据管理器（Windows Credential Manager / `cmdkey`）。

---

## ⏃ 第 4 步：复核无残留明文

1. 确认 `~/.workbuddy/MEMORY.md` 已无 `ghp_` 明文（本环境已改）。
2. 全局搜本机同步目录（OneDrive / WorkBuddy 备份 / Desktop）是否还有 `ghp_`、`sk-`、`api_key=` 等明文，有则迁移。
3. （可选）把 `~/.workbuddy/` 加入同步工具的"忽略列表"，避免记忆文件再次被备份/分享。

---

## ✅ 完成判据

- [ ] GitHub 旧 PAT 已撤销，新 PAT 仅存于 `gh auth` 或 `GH_TOKEN` 环境变量
- [ ] `auto-publish` 仓库密钥已迁 Actions secrets，代码改为读 `secrets.XXX`
- [ ] `auto-publish` 历史密钥已擦除且对应密钥已轮换
- [ ] 桌面 API key 全部走环境变量 / 凭据管理器
- [ ] 同步目录无 `ghp_` / `sk-` / `api_key=` 明文残留

> 完成后，本机即可安全 `git commit / push` 智能食堂项目到 `github.com/RainmeoX/canteen-order-system`。
