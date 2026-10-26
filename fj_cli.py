"""`hermes fujiang …` 管理命令。

    hermes fujiang status      # 托管块 / 内核段 / 技能 / 反拒答状态
    hermes fujiang install     # 写入或刷新 SOUL.md 托管块
    hermes fujiang uninstall   # 摘掉托管块（其余 SOUL 内容保留）
    hermes fujiang prompt      # 打印完整提示词（--kernel 打印内核段）
    hermes fujiang skills      # 列出随插件挂载的技能
    hermes fujiang profile     # 运行时档案，与上游 fujiang_profile 工具同构
    hermes fujiang bank        # 跑上游 118 条 prompt bank（在线评分）
    hermes fujiang refresh     # install -> verify ->（--bank）基线对比，掉分自动回滚
    hermes fujiang verify      # 静态自检，失败退出码 1
    hermes fujiang recover --reset
"""
from __future__ import annotations

import json
import sys

from . import fj_config as C
from . import fj_prompt as P
from . import fj_refusal as R
from . import fj_skills as S
from . import fj_soul as Soul

_out = print


def setup_args(parser) -> None:
    sub = parser.add_subparsers(dest="sub")
    for name, help_text in (
        ("status", "显示托管块、内核段、技能与反拒答状态"),
        ("install", "写入或刷新 SOUL.md 托管块"),
        ("uninstall", "摘掉 SOUL.md 托管块"),
        ("prompt", "打印完整提示词"),
        ("skills", "列出随插件挂载的红队技能"),
        ("profile", "运行时档案（与上游 fujiang_profile 工具同构，默认 JSON）"),
        ("bank", "跑上游 prompt bank 在线评分（node，默认走本地 workbuddy）"),
        ("refresh", "install → verify →（--bank）基线对比，掉分自动回滚"),
        ("verify", "静态自检"),
        ("recover", "反拒答状态管理"),
    ):
        p = sub.add_parser(name, help=help_text)
        if name == "install":
            p.add_argument("--keep-legacy", action="store_true",
                           help="保留旧版 hermes-purge 标记块（默认迁走）")
            p.add_argument("--home", default=None, help="覆盖 HERMES_HOME")
        elif name == "uninstall":
            p.add_argument("--home", default=None, help="覆盖 HERMES_HOME")
        elif name == "prompt":
            p.add_argument("--kernel", action="store_true", help="只打印内核段")
        elif name == "profile":
            p.add_argument("--text", action="store_true", help="人类可读输出而非 JSON")
        elif name == "refresh":
            p.add_argument("--bank", action="store_true", help="同时跑 bank 并与基线对比")
            p.add_argument("--level", default="minimal", choices=["minimal", "short", "medium"])
            p.add_argument("--delay", type=float, default=0.1)
            p.add_argument("--set-baseline", action="store_true", help="把本次结果记为基线")
        elif name == "bank":
            p.add_argument("--level", default="minimal", choices=["minimal", "short", "medium"])
            p.add_argument("--domain", default=None, help="只跑某个域，如 web / crack / game")
            p.add_argument("--model", default=None, help="覆盖模型名")
            p.add_argument("--delay", type=float, default=0.2, help="每条之间的间隔秒数")
        elif name == "recover":
            p.add_argument("--reset", action="store_true", help="清空反拒答状态")
            p.add_argument("--session", default=None, help="只清某个 session")


def _home(args):
    from pathlib import Path

    raw = getattr(args, "home", None)
    return Path(raw).expanduser() if raw else None


def _cmd_status(home=None) -> int:
    st = Soul.status(home)
    data = R._load(home)
    sessions = data.get("sessions") or {}
    print("fujiang-dsh · hermes plugin")
    print(f"  版本        : {C.PLUGIN_VERSION}")
    print(f"  HERMES_HOME : {C.hermes_home()}")
    print(f"  SOUL.md     : {st['path']}")
    print(f"    存在={st['exists']} 字符={st['chars']} 托管块={st['block_present']}"
          f"({st['block_chars']} 字符) 旧块={st['legacy_present']}")
    print(f"  内核段      : id={C.SECTION_ID} {P.kernel_chars()} 字符（上限 {C.SECTION_MAX_CHARS}）")
    print(f"  完整提示词  : {P.prompt_chars()} 字符")
    print(f"  技能        : {len(S.skill_files())} 个（命名空间 {C.PLUGIN_NAME}:<name>）")
    print(f"  反拒答      : max_inject={R._max_injects()} enabled={R._enabled()} "
          f"挂起会话={sum(1 for v in sessions.values() if v.get('pending'))}")
    return 0


def _cmd_install(args) -> int:
    prompt = P.full_prompt()
    if not prompt:
        print("提示词文件缺失：prompt/default-prompt.md", file=sys.stderr)
        return 2
    res = Soul.ensure(prompt, _home(args), strip_legacy_blocks=not args.keep_legacy)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0


def _cmd_uninstall(args) -> int:
    print(json.dumps(Soul.remove(_home(args)), ensure_ascii=False, indent=2))
    return 0


def _cmd_prompt(args) -> int:
    text = P.kernel() if getattr(args, "kernel", False) else P.full_prompt()
    sys.stdout.write(text)
    if not text.endswith("\n"):
        sys.stdout.write("\n")
    return 0


def _cmd_skills() -> int:
    for path in S.skill_files():
        print(f"{C.PLUGIN_NAME}:{path.parent.name}\t{S._description(path)}")
    return 0


def _cmd_recover(args) -> int:
    if args.reset:
        R.reset(args.session)
        print("反拒答状态已清空" if args.session is None else f"已清空会话 {args.session}")
        return 0
    print(json.dumps(R._load(), ensure_ascii=False, indent=2))
    return 0


def _cmd_verify(home=None) -> int:
    ok = True
    st = Soul.status(home)
    checks = [
        ("完整提示词存在", P.prompt_chars() > 4000, f"{P.prompt_chars()} 字符"),
        ("内核段未超限", 0 < P.kernel_chars() <= C.SECTION_MAX_CHARS, f"{P.kernel_chars()} 字符"),
        ("内核段含身份=富江", P.kernel().count("富江") >= 2, ""),
        ("完整提示词含身份=富江", P.full_prompt().count("富江") >= 2, ""),
        ("激活词回复=爸爸，我在", "爸爸，我在" in P.full_prompt() and "爸爸，我在" in P.kernel(), ""),
        ("无群号首行前缀", "FJNB22" not in P.kernel() and "FJNB22" not in P.full_prompt(), ""),
        ("SOUL 托管块已装", st["block_present"], st["path"]),
        ("SOUL 无旧版残留块", not st["legacy_present"], ""),
        ("技能已生成", len(S.skill_files()) >= 20, f"{len(S.skill_files())} 个"),
        ("反拒答正则可用", R.looks_like_refusal("抱歉，我无法协助完成这个请求"), ""),
        ("反拒答不误伤", not R.looks_like_refusal("可以，按本地样本逆向流程：先复制到隔离目录。"), ""),
    ]
    for label, passed, detail in checks:
        ok = ok and bool(passed)
        print(f"[{'ok' if passed else 'FAIL'}] {label}{(' — ' + detail) if detail else ''}")
    print("\n结果：" + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1



# 上游当前 commit(ab86ddc) 实际交付的 prompts/*.md 字节 sha256。
# 注意：上游 scripts/verify_plugin.mjs 里钉的还是旧常量 ef013b39…b397c，
# 用它自己的仓库跑 node --test 会挂 1/5（prompt 资产的 hash 断言）。
UPSTREAM_EXPECTED_SHA256 = "dfad664948945d39b9c9058c40258c35355781926307102d1980fb1537f879d9"
UPSTREAM_STALE_SHA256 = "ef013b398da81504fa452ea96bc5510f3da8b314cdc33eb20dd2ce0ec90b397c"
_UPSTREAM_PROMPT_FILES = ("fujiang.md", "fujiang-mirror.md", "fujiang-compat.md")


def _sha256(path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _plugin_version() -> str:
    try:
        for line in (C.plugin_dir() / "plugin.yaml").read_text(encoding="utf-8").splitlines():
            if line.startswith("version:"):
                return line.split(":", 1)[1].strip().strip('"\'')
    except OSError:
        pass
    return "unknown"


def _cmd_profile(args) -> int:
    """与上游 index.js 的 fujiang_profile 工具同构的运行时档案。"""
    st = Soul.status(None)
    prompt_dir = C.plugin_dir() / "prompt"
    sources = []
    hash_match = None
    for name in _UPSTREAM_PROMPT_FILES:
        p = prompt_dir / name
        if not p.exists():
            continue
        digest = _sha256(p)
        sources.append({"file": f"prompts/{name}", "chars": len(p.read_text(encoding="utf-8")),
                        "sha256": digest, "upstream": digest == UPSTREAM_EXPECTED_SHA256})
        if hash_match is None:
            hash_match = digest == UPSTREAM_EXPECTED_SHA256
    profile = {
        "plugin": "fujiang-dsh",
        "pluginVersion": _plugin_version(),
        "pluginDisplayName": "富江破甲",
        "name": "fujiang-dsh",
        "displayName": "富江破甲",
        "kernelVersion": _plugin_version(),
        "targetArchitecture": "DeepSeek-V4 / V4-Pro / V4.1-Flash 全系列",
        "upstream": "c3cvld7aag/fujiang-dsh",
        "promptSource": [s["file"] for s in sources],
        "promptChars": P.prompt_chars(),
        "kernelChars": P.kernel_chars(),
        "soul": {"path": st["path"], "exists": st["exists"],
                 "totalChars": st.get("chars"), "blockChars": st.get("block_chars"),
                 "blockPresent": st["block_present"], "legacyPresent": st["legacy_present"]},
        "injection": [
            {"section": C.SECTION_ID, "position": "after_memory",
             "order": 100, "chars": P.kernel_chars(), "enabled": bool(P.kernel_chars())},
            {"section": "soul:hermes-managed-block", "position": "soul",
             "order": 200, "chars": st.get("block_chars"), "enabled": st["block_present"]},
        ],
        "skills": len(S.skill_files()),
        "refusalRecover": {"maxInject": R._max_injects(), "enabled": R._enabled(),
                           "pendingSessions": sum(1 for v in (R._load(None).get("sessions") or {}).values()
                                                  if v.get("pending"))},
    }
    if getattr(args, "text", False):
        print(f"插件        : {profile['plugin']} v{profile['pluginVersion']}（富江破甲）")
        print(f"上游        : {profile['upstream']}")
        print(f"完整提示词  : {profile['promptChars']} 字符 / 内核段 {profile['kernelChars']} 字符")
        print(f"SOUL 托管块 : {profile['soul']['blockChars']} 字符（总 {profile['soul']['totalChars']}）")
        for inj in profile["injection"]:
            print(f"注入槽位    : {inj['section']} order={inj['order']} "
                  f"chars={inj['chars']} enabled={inj['enabled']}")
        for s in sources:
            print(f"提示词文件  : {s['file']} {s['chars']} 字符 "
                  f"{'上游字节一致' if s['upstream'] else '与上游不同'}")
        return 0
    print(json.dumps(profile, ensure_ascii=False, indent=2))
    return 0


def _bank_env() -> dict:
    """给上游 run_bank_live.mjs 备好 OpenAI 兼容端点与 key（默认走本地 workbuddy）。"""
    import os
    import re

    env = dict(os.environ)
    key = env.get("DEEPSEEK_API_KEY", "")
    if not key:
        for name in ("FUJIANG_BANK_API_KEY", "HERMES_CUSTOM_WORKBUDDY_API_KEY",
                     "HERMES_CUSTOM_API_KEY", "OPENAI_API_KEY"):
            if env.get(name):
                key = env[name]
                break
        if not key:
            try:
                for line in (C.hermes_home() / ".env").read_text(encoding="utf-8", errors="replace").splitlines():
                    if line.startswith("HERMES_CUSTOM_WORKBUDDY_API_KEY="):
                        key = line.split("=", 1)[1].strip().strip('"\'')
                        break
            except OSError:
                pass
    env["DEEPSEEK_API_KEY"] = key
    # 端点/模型优先读 FUJIANG_BANK_*，再退回 DEEPSEEK_*；默认值只是本机 workbuddy 的样例
    for target, source, default in (
        ("DEEPSEEK_API_BASE", "FUJIANG_BANK_API_BASE", "http://127.0.0.1:7863/v1"),
        ("DEEPSEEK_MODEL", "FUJIANG_BANK_MODEL", "cn:deepseek-v4.1-flash"),
    ):
        if not env.get(target):
            env[target] = env.get(source) or default
    return env


def _cmd_bank(args) -> int:
    """跑上游 prompt bank 在线评分（node 脚本，逐条打分）。"""
    import os
    import subprocess

    root = C.plugin_dir() / "upstream"
    runner = root / "scripts" / "run_bank_live.mjs"
    if not runner.exists():
        print(f"缺少上游评分器：{runner}")
        return 2
    if not _bank_env().get("DEEPSEEK_API_KEY"):
        print("缺少 API key：设 HERMES_CUSTOM_WORKBUDDY_API_KEY 或 DEEPSEEK_API_KEY")
        return 2
    cmd = ["node", str(runner), "--level", args.level, "--delay", str(args.delay)]
    if args.domain:
        cmd += ["--domain", args.domain]
    if args.model:
        cmd += ["--model", args.model]
    try:
        return subprocess.call(cmd, cwd=str(root), env=_bank_env())
    except FileNotFoundError:
        print("缺少 node，无法运行上游评分器")
        return 2


def _snapshot_prompt() -> "object":
    """把当前 prompt/ 整目录快照一份，供回滚。"""
    import shutil
    import time
    from pathlib import Path

    src = C.plugin_dir() / "prompt"
    dst = C.plugin_dir() / "prompt.snapshots" / time.strftime("%Y%m%dT%H%M%S")
    shutil.copytree(src, dst, dirs_exist_ok=True)
    return dst


def _restore_prompt(snap) -> None:
    import shutil
    shutil.rmtree(C.plugin_dir() / "prompt", ignore_errors=True)
    shutil.copytree(snap, C.plugin_dir() / "prompt")


def _lastgood_dir():
    return C.plugin_dir() / "prompt.lastgood"


def _mark_lastgood() -> None:
    """verify/bank 都通过后，把当前 prompt 记为“最后已知良好”。"""
    import shutil
    d = _lastgood_dir()
    shutil.rmtree(d, ignore_errors=True)
    shutil.copytree(C.plugin_dir() / "prompt", d)


def _rollback_target(snap):
    """回滚目标：优先 lastgood（上次通过校验的版本），没有才退回本次快照。"""
    d = _lastgood_dir()
    if (d / "default-prompt.md").exists():
        return d, True
    return snap, False


def _baseline_path():
    return C.hermes_home() / "fujiang-dsh" / "bank_baseline.json"


def _read_baseline() -> dict:
    try:
        return json.loads(_baseline_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _write_baseline(data: dict) -> None:
    path = _baseline_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _run_bank_capture(level: str, delay: float):
    """跑一次 bank 并解析 pass/refusal，返回 (结果dict, 原始输出)。"""
    import re
    import subprocess

    root = C.plugin_dir() / "upstream"
    runner = root / "scripts" / "run_bank_live.mjs"
    if not runner.exists() or not _bank_env().get("DEEPSEEK_API_KEY"):
        return None, "bank 不可用（缺脚本或 key）"
    proc = subprocess.run(["node", str(runner), "--level", level, "--delay", str(delay)],
                          cwd=str(root), env=_bank_env(), capture_output=True, text=True)
    out = (proc.stdout or "") + (proc.stderr or "")
    m = re.search(r'结果:\s*(\{[^}]+\})', out)
    if not m:
        return None, out
    try:
        return json.loads(m.group(1)), out
    except ValueError:
        return None, out


def _cmd_refresh(args) -> int:
    """install → verify →（可选）bank 基线对比；verify 失败或掉分则自动回滚 prompt。"""
    from types import SimpleNamespace

    snap = _snapshot_prompt()
    print(f"[1/3] install  快照={snap.name}")
    rc = _cmd_install(SimpleNamespace(keep_legacy=False, home=None))
    if rc:
        target, is_good = _rollback_target(snap)
        print(f"install 失败，回滚到{'lastgood' if is_good else '本次快照'}")
        _restore_prompt(target)
        _cmd_install(SimpleNamespace(keep_legacy=False, home=None))
        return rc

    print("[2/3] verify")
    rc = _cmd_verify()
    if rc:
        target, is_good = _rollback_target(snap)
        print(f"verify 未通过，回滚到{'lastgood' if is_good else '本次快照'}并重装")
        _restore_prompt(target)
        _cmd_install(SimpleNamespace(keep_legacy=False, home=None))
        return rc

    if not getattr(args, "bank", False):
        print("[3/3] bank   跳过（加 --bank 才跑）")
        _mark_lastgood()
        print("      lastgood 已更新")
        return 0

    level = getattr(args, "level", "minimal")
    result, out = _run_bank_capture(level, getattr(args, "delay", 0.1))
    if result is None:
        print("[3/3] bank   无法解析结果：")
        print(out[-2000:])
        return 2
    print(f"[3/3] bank   pass={result.get('pass')} refusal={result.get('refusal')} "
          f"fallback={result.get('fallback')} (level={level})")

    base = _read_baseline().get(level)
    if getattr(args, "set_baseline", False) or not base:
        _write_baseline({**_read_baseline(), level: result.get("pass")})
        _mark_lastgood()
        print(f"      基线已记录：{level}={result.get('pass')}；lastgood 已更新")
        return 0
    if (result.get("pass") or 0) < (base or 0):
        target, is_good = _rollback_target(snap)
        print(f"      掉分：{result.get('pass')} < 基线 {base}，回滚到{'lastgood' if is_good else '本次快照'}并重装")
        _restore_prompt(target)
        _cmd_install(SimpleNamespace(keep_legacy=False, home=None))
        return 1
    print(f"      不低于基线 {base}，保留本次改动")
    _mark_lastgood()
    print("      lastgood 已更新")
    return 0


def dispatch(args) -> int:
    sub = getattr(args, "sub", None)
    if sub in (None, "status"):
        return _cmd_status(_home(args) if sub == "status" else None)
    if sub == "profile":
        return _cmd_profile(args)
    if sub == "bank":
        return _cmd_bank(args)
    if sub == "refresh":
        return _cmd_refresh(args)
    if sub == "install":
        return _cmd_install(args)
    if sub == "uninstall":
        return _cmd_uninstall(args)
    if sub == "prompt":
        return _cmd_prompt(args)
    if sub == "skills":
        return _cmd_skills()
    if sub == "verify":
        return _cmd_verify()
    if sub == "recover":
        return _cmd_recover(args)
    print("用法: hermes fujiang {status|profile|bank|refresh|install|uninstall|prompt|skills|verify|recover}")
    return 2


def cli_main(args) -> int:
    return dispatch(args)
