# TROHUB Skills

面向跨境电商卖家的 [TROHUB API](https://open.trohub.com/) 对应的 Agent Skill —— 一个知识产权（IP）风险检测服务，覆盖美国/欧盟外观专利检索、美国文字商标冲突检测、图形商标以图搜图、全球版权/美术作品溯源，以及 TRO（临时禁令）诉讼监控。

> **📖 English docs** — If you prefer reading in English, check out [README.md](./README.md).

基于开放的 [Agent Skills](https://agentskills.io) 标准构建（`SKILL.md` + 可选的 `scripts/`/`references/`），所以同一个 skill 文件夹可以在 Claude Code、Codex CLI、Cursor 以及其他兼容的 AI 编程工具中直接使用——装一次即可，不用为每个工具重新改写。

## 包含内容

```
trohub-ip-check/
├── SKILL.md                  — 主要的skill说明文件（请先看这个）
├── scripts/
│   ├── trohub_client.py      — 可直接运行的Python客户端 + 命令行工具
│   ├── requirements.txt
│   └── README.md             — 客户端使用示例
└── references/
    ├── tro-cases.md          — TRO诉讼监控
    ├── infringement-tasks.md — 综合图片检测任务的完整生命周期
    ├── patents.md            — 外观专利检索 + 引用反查
    ├── trademarks.md         — 文字商标 + 图形商标检索
    ├── copyright.md          — 全球版权/美术作品检索
    └── errors.md             — 错误码 & 限流说明
```

## 前置条件

在任何工具能真正调用这个 API 之前，你需要先有一个 TROHUB 账号和 API key（这个 skill 只是教会 AI 工具**怎么调用**这个 API——不包含你的账号凭证）。

1. 前往 [app.trohub.com](https://app.trohub.com) 注册/登录
2. 在 **账号 → API Keys** 页面获取你的 API key：`https://app.trohub.com/account/api-keys`

把这两项记下来——下面每个工具都需要把它们配置成环境变量：

```bash
export TROHUB_API_KEY="your_api_key_here"
export TROHUB_BASE_URL="https://api.trohub.com/v1"
```

建议把这两行加进你的 shell 配置文件（`~/.zshrc`、`~/.bashrc` 等），这样就不用每次开新会话都重新设置一遍。

---

## 在 Claude Code 中安装 & 使用

**安装**

```bash
git clone https://github.com/easyamz/trohub-skills.git

# 个人级 —— 所有项目都能用
cp -r trohub-skills/trohub-ip-check ~/.claude/skills/

# 项目级 —— 提交到具体某个仓库，让团队成员也能一起用
mkdir -p .claude/skills
cp -r trohub-skills/trohub-ip-check .claude/skills/
```

**验证**

启动（或重启）Claude Code，然后问它：
```
你现在有哪些可用的skill？
```
`trohub-ip-check` 应该会出现在列表里。

**使用**

直接用自然语言描述你的需求即可——Claude Code 会根据 skill 的 description 自动匹配并加载：
```
帮我检查一下这张产品图在上架之前有没有外观专利风险：https://example.com/product.jpg，这是一个无线耳机
```
```
检查一下这个商品标题有没有商标冲突："Ergonomic Chair"
```

---

## 在 Codex CLI 中安装 & 使用

**安装**

```bash
git clone https://github.com/easyamz/trohub-skills.git

# 个人级 —— 所有项目都能用
cp -r trohub-skills/trohub-ip-check ~/.codex/skills/

# 项目级 —— 提交进仓库，克隆代码的队友也能一起用
mkdir -p .codex/skills
cp -r trohub-skills/trohub-ip-check .codex/skills/
```

Codex 按以下优先级查找 skill：当前目录下的 `.codex/skills/` → 仓库根目录的 `.codex/skills/` → `~/.codex/skills/`（个人级）→ 系统级目录。

**验证**

开启一个新的 Codex 会话（skill 是在会话启动时加载的，如果 Codex 已经在运行了记得重启），然后输入：
```
/skills
```
列表里应该能看到 `trohub-ip-check` 以及它的说明。

**使用**

既可以直接用自然语言描述需求让它自动触发，也可以显式点名让它使用这个 skill：
```
使用 trohub-ip-check 这个skill，帮我检查一下这个logo有没有和已注册的美国图形商标冲突：https://example.com/logo.png
```

---

## 在 Cursor 中安装 & 使用

Cursor（≥ 2.4 版本）原生支持 Agent Skills。目前 Cursor 只在**项目级**发现 skill，所以需要把文件夹提交进你正在使用的仓库：

```bash
git clone https://github.com/easyamz/trohub-skills.git

mkdir -p .cursor/skills
cp -r trohub-skills/trohub-ip-check .cursor/skills/
```

**验证**

重启 Cursor（或者重新加载窗口），让它重新扫描 skill 目录，然后在 Agent 聊天框里输入 `/` 搜索 `trohub-ip-check`——应该能在选择列表里看到它。

**使用**

- 自动触发：直接在 Agent 聊天里描述任务，Cursor 会在合适的时候自动引入这个 skill。
- 手动调用：在 Agent 输入框里输入 `/`，从菜单里选择 `trohub-ip-check`，然后附上你的需求。

---

## 其他支持 Agent Skills 的工具

截至 2026 年年中，Windsurf、Cline、OpenCode、Gemini CLI 等工具也都在不同程度上支持 Agent Skills 格式。通用套路基本一致：

1. 找到该工具的 skill 目录（通常类似 `~/.<工具名>/skills/` 或项目根目录下的 `.<工具名>/skills/`——具体请查该工具自己的文档，因为不同工具在路径规则、以及是否支持个人级/项目级安装上仍有差异）。
2. 把整个 `trohub-ip-check/` 文件夹（不是只有 `SKILL.md`）复制进那个目录。
3. 重启工具，让它重新扫描可用的 skill。
4. 用自然语言描述你的需求，或者如果工具支持的话显式调用这个 skill。

如果某个工具目前完全不支持 Agent Skills 格式，你依然可以从这个仓库里获益——手动把 `trohub-ip-check/SKILL.md` 里的内容粘贴进该工具自己的"自定义指令/规则"文件里（比如 `.cursorrules`、`AGENTS.md`，或者系统提示词）。这样会失去自动发现的能力，但里面的说明内容本身依然有效。

---

## 配置参数说明

| 环境变量 | 是否必填 | 说明 |
|---|---|---|
| `TROHUB_API_KEY` | 是 | 从 `https://app.trohub.com/account/api-keys` 获取 |
| `TROHUB_BASE_URL` | 是 | 固定为 `https://api.trohub.com/v1`，直接使用即可 |

内置的 `scripts/trohub_client.py` 会自动从环境变量里读取这两项——完整的命令行和库用法请看 `trohub-ip-check/scripts/README.md`。

## 常见问题排查

- **复制进去之后 skill 没有出现。** 大部分工具只在启动时扫描一次 skill 目录——需要完全重启工具（不是只开一个新的聊天窗口/标签页）。
- **文件夹路径看起来是对的，但还是识别不到。** 检查一下嵌套层级是否正确：最终应该是 `.../skills/trohub-ip-check/SKILL.md`，而不是 `.../skills/SKILL.md`，也不是 `.../skills/trohub-skills/trohub-ip-check/SKILL.md`。
- **API 请求报认证错误。** 确认 `TROHUB_API_KEY` 是在工具实际运行的那个 shell/会话里设置的——在一个终端标签页里 export 的变量，另一个单独打开的 GUI 应用是看不到的。
- **报 `VALIDATION_BAD_REQUEST` 或类似的 400 错误。** 完整的错误码表和常见原因请看 `trohub-ip-check/references/errors.md`。

## 许可证

MIT —— 详见 [LICENSE](./LICENSE)。
