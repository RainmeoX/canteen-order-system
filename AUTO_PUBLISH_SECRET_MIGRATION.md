# auto-publish 密钥迁移到 CI Secrets — 改造包

> 适用：把仓库里**已提交的 API 模型密钥**（OpenAI / Anthropic 等 LLM API key）迁到 GitHub Actions Secrets。
> 本包为通用模板；把你的 `.github/workflows/*.yml` + 读 key 的那段代码贴给 AI，可换成精准版。

---

## 0. 前置：先去轮换已提交的密钥（最重要）

密钥曾经 `git commit` 进仓库 → **Git 历史里永远留着明文旧值**。迁到 CI secrets 后历史依旧含旧值，所以必须去对应平台**重生成并作废旧 key**：

- OpenAI: platform.openai.com → API keys → 删除旧 key、新建
- Anthropic: console.anthropic.com → API keys → 轮换
- 其他模型厂商同理

新 key **只填进 GitHub Secrets，绝不进文件 / 不 commit**。

---

## 1. 在 GitHub 添加 Secrets（点几下）

仓库 → **Settings → Secrets and variables → Actions → 「New repository secret」**

逐个添加，NAME 建议全大写 + 下划线：

| Name | Value |
|------|-------|
| `OPENAI_API_KEY` | 新生成的 key |
| `ANTHROPIC_API_KEY` | 新生成的 key |
| （按你实际用的模型补 `XXX_API_KEY`） | … |

---

## 2. 改 workflow：把 key 注入环境变量

文件：`.github/workflows/*.yml`（你仓库里实际文件名贴我可换精准版）

```yaml
name: auto-publish
on: [push]
jobs:
  publish:
    runs-on: ubuntu-latest
    env:                       # ← 关键：从 Secrets 注入
      OPENAI_API_KEY:    ${{ secrets.OPENAI_API_KEY }}
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - run: python publish.py     # 脚本里用 os.environ 读
```

---

## 3. 改代码：从「读文件」改成「读环境变量」

**改前（假设）：**

```python
import json
cfg = json.load(open('config.json'))   # ← 明文密钥提交在 config.json
KEY = cfg['openai_api_key']
```

**改后：**

```python
import os
KEY = os.environ['OPENAI_API_KEY']     # ← 从 CI 注入的环境变量读
# 本地调试：终端先 export OPENAI_API_KEY=xxx 再跑
```

Node / JS 同理：

```js
const KEY = process.env.OPENAI_API_KEY;
```

---

## 4. .gitignore 加一行，删掉明文文件

```
config.json        # 或 secrets.json / .env / 你实际提交密钥的文件
*.secret
.env
```

然后：

```bash
git rm --cached config.json     # 从 git 跟踪移除（本地文件先留着，别急着删）
# 确认本地已备份好旧值后，再手动删除本地明文文件
git add .gitignore
git commit -m "security: move API keys to CI secrets"
git push
```

---

## 5. 校验

- **本地**：`export OPENAI_API_KEY=新key && python publish.py` 应能跑通。
- **仓库**：跑一次 Actions，看 log 里 key 是否注入成功。
  ⚠️ 千万别在 workflow / 脚本里 `echo $KEY` 把 key 打进日志。

---

## 升级为精准版

把这两段贴给 AI，上面的占位会换成你真实的变量名和文件名：

1. `.github/workflows/*.yml` 的完整内容
2. 仓库里**读取 API key 的那段代码**（含文件路径）
