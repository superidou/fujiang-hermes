"""红队技能注册：fujiang-dsh/skills/*/SKILL.md -> ctx.register_skill()

技能不复制进 ~/.hermes/skills/，由插件命名空间只读挂载，名字形如
``fujiang-dsh:webshell-toolkit``（skills_list / skill_view 可见）。
"""
from __future__ import annotations

import re
from pathlib import Path

from . import fj_config as C

_FM_DESC = re.compile(r"^description\s*:\s*(.+)$", re.M)


def skill_files() -> list[Path]:
    root = C.plugin_dir() / "skills"
    if not root.is_dir():
        return []
    return sorted(root.glob("*/SKILL.md"))


def _description(path: Path) -> str:
    try:
        head = path.read_text(encoding="utf-8")[:2000]
    except OSError:
        return ""
    m = _FM_DESC.search(head)
    if not m:
        return ""
    return m.group(1).strip().strip('"').strip("'")


def register_all(ctx) -> list[str]:
    names: list[str] = []
    for path in skill_files():
        name = path.parent.name
        try:
            ctx.register_skill(name, path, description=_description(path))
            names.append(name)
        except Exception:  # 单个技能坏掉不能拖垮插件加载
            continue
    return names
