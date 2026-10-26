# NOTICE — 来源与署名

本仓库是 [c3cvld7aag/fujiang-dsh](https://github.com/c3cvld7aag/fujiang-dsh)（DeepSeek Harness
的 Cordis 插件）到 [Hermes Agent](https://github.com/NousResearch/hermes-agent) 插件体系的移植，
骨架沿用 [YuJunZhiXue/dsh-purge](https://github.com/YuJunZhiXue/dsh-purge) 的四个扩展点。

按 MIT 与 CC BY-NC-SA 4.0 的要求，以下署名为**许可证义务**，删除即违约：

| 内容 | 来源 | 许可证 |
|---|---|---|
| `prompt/*.md`（人格提示词） | c3cvld7aag/fujiang-dsh | CC BY-NC-SA 4.0 |
| 上游提示词原始来源 | Minglink/dsh-infinite-gen-4 | CC BY-NC-SA 4.0 |
| 插件骨架（`fj_*.py` 四扩展点结构） | YuJunZhiXue/dsh-purge | MIT |
| `skills/` 23 个红队技能 | dsh-purge（署名保留，内容按 Hermes skill 规范重写） | MIT |
| `upstream/`（评分器、prompt bank、LICENSE） | c3cvld7aag/fujiang-dsh 快照 | 见 `upstream/LICENSE` |
| Hermes 宿主契约（`register_*` API） | NousResearch/hermes-agent | MIT |

## 本移植版所做的修改

- DSH 的 `index.js` / `cordis.patch.yml` / `client.js` 宿主胶水**未**移植 —— Hermes 的扩展点不同，
  这里落在 `register_system_prompt_section` + `SOUL.md` 托管块 + `register_hook` +
  `register_skill` + `register_cli_command` 上。
- 提示词资产重新编码：剥掉 ChatML 信封，去掉 TG 群水印与拉群条款，激活词固定为「爸爸，我在」。
- 新增 `prompt/kernel.md`（≤4000 字符的内核段），上游没有对应文件。
- 新增 `hermes fujiang {status,install,uninstall,prompt,skills,profile,bank,refresh,verify,recover}` 管理命令。

## 许可证适用范围

| 路径 | 许可证 | 文件 |
|---|---|---|
| `*.py`、`skills/`、`tests/`、`.github/` | MIT | [LICENSE](LICENSE) |
| `prompt/*.md` | CC BY-NC-SA 4.0 | [LICENSE-CC-BY-NC-SA-4.0.md](LICENSE-CC-BY-NC-SA-4.0.md) |
| `upstream/` | 上游原样，见 `upstream/LICENSE` | — |

GitHub 侧识别为 MIT（仓库根 `LICENSE`）；`prompt/` 的非商业约束以
`LICENSE-CC-BY-NC-SA-4.0.md` 为准，两者不冲突：代码可商用（MIT），提示词不可商用（CC）。

## 安全提示

`skills/` 里是**红队/渗透测试**技能，故意包含反弹 shell、隧道、爆破、WebShell 用例。
它们是给已授权靶标和隔离实验环境用的文档，不是可执行载荷。安装本插件等于让 Agent
在会话里读到这些命令 —— 请自行确认使用场景的合法性。`hermes plugins validate` 的
security-scan 项会因此报 ✗，这是预期结果，不是缺陷。
