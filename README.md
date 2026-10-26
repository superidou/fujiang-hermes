# fujiang-dsh · Hermes 插件

把 [c3cvld7aag/fujiang-dsh](https://github.com/c3cvld7aag/fujiang-dsh)（DeepSeek Harness 的
Cordis 插件）的「富江」人格提示词架构移植到 [Hermes Agent](https://github.com/NousResearch/hermes-agent)，
骨架沿用 [dsh-purge](https://github.com/YuJunZhiXue/dsh-purge)（MIT）的四个扩展点，附带 23 个
红队/渗透测试技能与一条反拒答重试链。

| | |
|---|---|
| 宿主 | Hermes Agent ≥ 0.21 |
| 依赖 | 纯 stdlib（`bank` 子命令另需 node） |
| 提示词许可 | CC BY-NC-SA 4.0（非商业 + 同协议 + 署名） |
| 代码/技能许可 | MIT |
| CI | `python -m unittest discover -s tests`（无 Hermes 依赖）+ `hermes plugins validate` |

> 上游提示词里的 TG 群水印与拉群条款已去掉；激活词固定为「爸爸，我在」。

## 安装

```bash
# 从 GitHub 直装（推荐）
hermes plugins install <owner>/fujiang-dsh

# 本地目录（开发时）
hermes plugins enable fujiang-dsh
hermes fujiang install     # 写 SOUL.md 托管块
hermes fujiang status      # 校验
```

装完 **开新会话** 才生效：内核段在会话装配时读取，`SOUL.md` 托管块也是。当前会话里改完不会变。

```bash
hermes fujiang uninstall            # 摘掉托管块，SOUL.md 其余内容保留
hermes plugins remove fujiang-dsh   # 连插件目录一起删
```

## 它挂在哪（全部是 Hermes 公开契约，不改核心）

| # | 扩展点 | 承载内容 |
|---|---|---|
| 1 | `register_system_prompt_section()` | `prompt/kernel.md` 内核段，id `fujiang-dsh.kernel`，≤4000 字符硬上限 |
| 2 | `SOUL.md` 托管块 | `prompt/default-prompt.md` 完整提示词（`<!-- fujiang-dsh:hermes:begin/end -->` 之间） |
| 3 | `pre_llm_call` / `post_llm_call` | 反拒答：判定上一轮 → 下一轮把纠正指令附到 user message |
| 4 | `register_skill()` × 23 | 红队技能，命名空间 `fujiang-dsh:<name>`，只读挂载不进 `skills/` |

为什么分两处：插件系统提示段有 **4000 字符/段、8000 字符/会话** 的硬上限，完整提示词塞不进去；
`SOUL.md` 是身份槽 #1，标为 user_authored 且无实际上限，是唯一能承载全量用户控制文本的通道。
两份内容必须各自独立可读（模型可能只读到其中一份）。

重复加载幂等；写 `SOUL.md` 前自动备份到 `$HERMES_HOME/fujiang-dsh/backups/SOUL.md.<ts>.bak`。
加载时会顺手剥掉旧的 `dsh-purge:hermes` 托管块，避免同一份提示词出现两遍。

## 命令

```bash
hermes fujiang status              # 托管块 / 内核段 / 技能 / 反拒答状态
hermes fujiang install             # 写入或刷新 SOUL.md 托管块
hermes fujiang uninstall           # 摘掉托管块
hermes fujiang prompt [--kernel]   # 打印提示词
hermes fujiang profile [--text]    # 运行时档案（与上游 fujiang_profile 工具同构，默认 JSON）
hermes fujiang skills              # 列出随插件挂载的技能
hermes fujiang verify              # 静态自检，失败退出码 1
hermes fujiang bank [--level/--domain/--model/--delay]   # 跑上游 prompt bank 在线评分
hermes fujiang refresh [--bank]    # install → verify →（可选）基线对比，掉分/失败自动回滚
hermes fujiang recover --reset     # 清空反拒答状态
```

`refresh` 是改提示词后的正常路径：先快照 → 装 → 自检 →（带 `--bank` 时）跟基线比分，
任何一步失败自动回滚到 `prompt.lastgood/`。

## 环境变量

| 变量 | 默认 | 作用 |
|---|---|---|
| `FUJIANG_RECOVER` | `1` | `0` 关掉反拒答重试 |
| `FUJIANG_RECOVER_MAX` | `2` | 同一条拒答最多注入几次（0–5） |
| `FUJIANG_RECOVER_TEXT` | 内置文案 | 替换注入的纠正指令 |
| `FUJIANG_BANK_API_KEY` | 回退 `DEEPSEEK_API_KEY` / Hermes 自定义 key | `bank` 子命令的 key |
| `FUJIANG_BANK_API_BASE` | `http://127.0.0.1:7863/v1` | `bank` 打的 OpenAI 兼容端点 |
| `FUJIANG_BANK_MODEL` | `cn:deepseek-v4.1-flash` | `bank` 用的模型 id |

0.5.0 之前的老前缀 `DSHPURGE_RECOVER*` 仍然生效（新前缀优先）。

## 目录

```
plugin.yaml            清单：name / version / requires_hermes / provides_hooks
__init__.py            register()：四个扩展点，逐项兜异常
fj_config.py           路径、标记、常量（$HERMES_HOME 解析走官方 get_hermes_home）
fj_prompt.py           提示词载入（剥 ChatML 信封、内核段超限截断）
fj_soul.py             SOUL.md 托管块：装/换/卸，原子写 + 先备份
fj_refusal.py          反拒答判定与限流
fj_skills.py           skills/*/SKILL.md → register_skill
fj_cli.py              hermes fujiang …
prompt/                提示词资产（default-prompt.md 与三个别名必须字节一致）+ kernel.md
skills/                23 个红队技能
upstream/              上游评分器、prompt bank、LICENSE 快照（归档用，不是运行依赖）
tests/                 无依赖静态自检（CI 跑这个）
```

## 已知限制

- **`hermes plugins validate` 的 security-scan 会报 ✗**：23 个红队技能里必然出现反弹 shell、
  隧道、爆破字样。这是预期结果，`validate` 其余 12 项全绿。要进策展目录（catalog）需要过该扫描
  —— 届时把 `skills/` 拆成独立插件即可，内核插件本体没有风险项。
- **反拒答只能「下一轮」生效**：Hermes 插件钩子没有主动向会话补发 user 消息的通道，
  `pre_llm_call` 的返回值只能挂到本轮 user message 上，而一轮对话必须由用户消息发起。
- **内核段有 4000 字符上限**：当前已用约 3.7K。要再塞内容，要么注册第二个 section id
  （`fujiang-dsh.kernel2`，吃 8000 总额度），要么写进 `SOUL.md` 托管块（无实际上限）。
  不要改 Hermes 核心里的常量 —— 超限会被宿主整段丢弃，且下次 `hermes update` 就没了。
- **模型合规是概率性的**：人格类插件靠模型执行，同一问题多次采样可能给出不同结果。
  单次探针答非所问不能判插件坏了；`verify` 是静态检查，`bank` 才是动态评分。
- 插件 CLI 在 host 隔离模式下 `register_cli_command` 会被跳过（子命令直接接在本地 CLI 解析器上），
  这是 `validate` 的一行提示，不影响使用。

## 许可与署名

- 提示词资产：**CC BY-NC-SA 4.0**，来源 `c3cvld7aag/fujiang-dsh`（上游原始来源
  `Minglink/dsh-infinite-gen-4`）。禁止商业使用；衍生作品须同协议并署名。
- 插件代码与技能：**MIT**，骨架来源 `YuJunZhiXue/dsh-purge`。
- 完整署名表见 [NOTICE.md](NOTICE.md)；许可证全文见 [LICENSE](LICENSE) 与
  [LICENSE-CC-BY-NC-SA-4.0.md](LICENSE-CC-BY-NC-SA-4.0.md)。

**红队技能仅供已授权靶标与隔离实验环境使用。** 安装即表示让 Agent 在会话中读到这些命令文本，
合法性由使用者自负。
