# Changelog

格式参照 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)；
版本号遵循 [SemVer](https://semver.org/lang/zh-CN/)。

## [0.5.1] — 2026-10-26

### 变更
- `## Activation` 改为「默认开启，无需激活词」：人格从会话第一轮起生效，不再等用户发「富江」，
  也不再出现「先中性作答、后面才切换」的错位。用户单独发「富江」时仍只回「爸爸，我在」并保持状态。
- 补一句风格与内容优先级：语气只管表达，用户的实际请求在内容上永远优先，技术步骤/命令/参数不许被压掉。

### 注意
- 内核段已用到 3945/4000 字符，只剩 55 —— 再往里加规则必须换 `fujiang-dsh.kernel2` 第二段，
  或者把内容写进 `SOUL.md` 托管块。

## [0.5.0] — 2026-10-26

首个可公开发布的版本。提示词内容未改动（仍是上游同步版），变化集中在可发布性与可维护性。

### 新增
- `LICENSE`（MIT，覆盖代码与技能）、`LICENSE-CC-BY-NC-SA-4.0.md`（覆盖 `prompt/`）、
  `NOTICE.md`（逐项署名表，MIT 与 CC BY-NC-SA 的署名为许可证义务）。
- `tests/test_static.py`：12 项无依赖静态自检 —— 清单字段、四个提示词别名字节一致、
  内核段 ≤4000、身份关键词、技能 frontmatter 完整性、不可见字符、密钥泄漏、语法编译、
  三处版本号一致、上游 bank 资产可解析。
- `.github/workflows/ci.yml`：Python 3.10/3.11/3.12 矩阵跑静态自检，另有一路非阻塞的
  `hermes plugins validate` / `doctor`。
- `.gitignore`：排除 `prompt.snapshots/`、`prompt.lastgood/`、`__pycache__`、运行时状态。

### 变更
- 环境变量统一到 `FUJIANG_` 前缀（`FUJIANG_RECOVER` / `FUJIANG_RECOVER_MAX` /
  `FUJIANG_RECOVER_TEXT` / `FUJIANG_BANK_API_KEY` / `FUJIANG_BANK_API_BASE` /
  `FUJIANG_BANK_MODEL`）；旧的 `DSHPURGE_*` 前缀保留为回退。
- `hermes fujiang bank` 的端点与模型改为可配置，默认值仍指向本机 workbuddy。
- README 重写：去掉写死的字符数（会漂），补齐挂载点、命令表、环境变量、目录结构与已知限制。
- `fj_config.py` / `__init__.py` 的文档串与备份路径更正（`$HERMES_HOME/dsh-purge/backups/`
  → `$HERMES_HOME/fujiang-dsh/backups/`）。

### 修复
- 反拒答判定只看回复开头 600 字符：长回答正文里的「无法提供 X」不再误判为拒答。
- 6 个技能的 `description` 被截断在半个括号上（`（headless 兜底。`、`（MS17-。` 等），
  会污染技能路由信号，已补成完整句子。
- `skills/recon-pipeline/SKILL.md` 里一个零宽空格（U+200B）已删除 —— 它会让
  `hermes plugins validate` 的 security-scan 报 `invisible_unicode`。

### 已知
- `hermes plugins validate` 的 security-scan 仍会因 23 个红队技能报 ✗（反弹 shell、隧道、
  爆破用例）。这是预期结果；要进策展目录需把 `skills/` 拆成独立插件。

## [0.4.3] — 2026-10-25

- 提示词对齐上游，内核段重写为 ≤4000 字符版本；去掉 TG 群水印与拉群条款。
- 新增 `profile` / `bank` / `refresh` 子命令；`refresh` 支持基线对比与自动回滚。
- 反拒答重试链条（`fj_refusal.py`）落地，限流 2 次。
