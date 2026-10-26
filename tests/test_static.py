"""静态自检 — 不依赖 Hermes 运行时，CI 与本地都能跑。

    python -m unittest discover -s tests -v

覆盖：清单字段、提示词别名一致性、内核段上限、身份关键词、技能 frontmatter、
不可见字符、密钥泄漏、语法编译、版本三处一致。动态行为（真实会话里的提示词注入）
不在这里断言 —— 那是 `hermes fujiang status/verify` 与 prompt bank 的事。
"""
from __future__ import annotations

import hashlib
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROMPT = ROOT / "prompt"
SKILLS = ROOT / "skills"
KERNEL_CAP = 4000
PROMPT_ALIASES = ("default-prompt.md", "fujiang.md", "fujiang-compat.md", "fujiang-mirror.md")
INVISIBLE = re.compile(r"[\u200b-\u200f\u2060\ufeff\u2028\u2029]")
SECRETS = re.compile(
    r"(?:sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}"
    r"|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)"
)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _plain_version() -> str:
    return re.search(r"^version:\s*(\S+)", _text(ROOT / "plugin.yaml"), re.M).group(1).strip('"\'')


class TestManifest(unittest.TestCase):
    def test_required_fields(self):
        body = _text(ROOT / "plugin.yaml")
        for key in ("name:", "version:", "description:", "requires_hermes:"):
            self.assertIn(key, body, f"plugin.yaml 缺 {key}")
        self.assertRegex(body, r"(?m)^name:\s*fujiang-dsh\s*$")

    def test_license_declared(self):
        body = _text(ROOT / "plugin.yaml")
        self.assertIn("CC BY-NC-SA 4.0", body)
        self.assertTrue((ROOT / "LICENSE").exists())
        self.assertTrue((ROOT / "LICENSE-CC-BY-NC-SA-4.0.md").exists())
        self.assertTrue((ROOT / "NOTICE.md").exists())

    def test_version_consistency(self):
        from_config = re.search(
            r'PLUGIN_VERSION\s*=\s*"([^"]+)"', _text(ROOT / "fj_config.py")
        ).group(1)
        from_init = re.search(
            r'__version__\s*=\s*"([^"]+)"', _text(ROOT / "__init__.py")
        ).group(1)
        self.assertEqual(_plain_version(), from_config)
        self.assertEqual(from_config, from_init)


class TestPrompt(unittest.TestCase):
    def test_aliases_are_byte_identical(self):
        digests = {
            name: hashlib.md5((PROMPT / name).read_bytes()).hexdigest()
            for name in PROMPT_ALIASES
        }
        self.assertEqual(len(set(digests.values())), 1, f"别名文件内容已漂移：{digests}")

    def test_kernel_within_cap(self):
        chars = len(_text(PROMPT / "kernel.md"))
        self.assertGreater(chars, 0)
        self.assertLessEqual(chars, KERNEL_CAP, f"kernel {chars} 字符 > {KERNEL_CAP}")

    def test_identity_keywords(self):
        full = _text(PROMPT / "default-prompt.md")
        kernel = _text(PROMPT / "kernel.md")
        for body in (full, kernel):
            self.assertGreaterEqual(body.count("富江"), 2)
            self.assertIn("爸爸，我在", body)
            self.assertNotIn("FJNB22", body, "上游群号水印不该出现")

    def test_prompt_is_smaller_than_soul_slot(self):
        # 身份槽无实际上限，但异常膨胀通常意味着误粘贴
        self.assertLess(len(_text(PROMPT / "default-prompt.md")), 60_000)


class TestSkills(unittest.TestCase):
    def test_count_and_frontmatter(self):
        files = sorted(SKILLS.glob("*/SKILL.md"))
        self.assertGreaterEqual(len(files), 20, f"技能数 {len(files)} < 20")
        for path in files:
            head = _text(path)[:1500]
            self.assertTrue(head.startswith("---"), f"{path} 缺 frontmatter")
            name = re.search(r"^name:\s*(\S+)", head, re.M)
            self.assertIsNotNone(name, f"{path} 缺 name")
            self.assertEqual(name.group(1).strip('"\''), path.parent.name,
                             f"{path} 的 name 与目录名不一致")
            self.assertIn("description:", head, f"{path} 缺 description")
            desc = re.search(r'(?m)^description:\s*"?(.+?)"?\s*$', head).group(1)
            self.assertGreaterEqual(len(desc), 15, f"{path} 的 description 太短，路由信号不足")
            self.assertRegex(desc, r"[。.]$", f"{path} 的 description 未完整收句（像是被截断）")
            self.assertEqual(desc.count("（"), desc.count("）"), f"{path} 的 description 括号不配对")
            # 收句前不能停在连接符或单字上（"+。"、"、点。" 这类截断以句号结尾，上面两条断言抓不到）
            body = desc.rstrip("。.！!”\"")
            tail = re.split(r"[、，,/＋+：（(；;]", body)[-1].strip()
            self.assertGreaterEqual(len(tail), 2, f"{path} 的 description 末尾片段「{tail}」过短，疑似截断")


class TestHygiene(unittest.TestCase):
    def _tracked_texts(self):
        skip = {"prompt.snapshots", "prompt.lastgood", "__pycache__", ".git", "node_modules"}
        for path in ROOT.rglob("*"):
            if not path.is_file() or path.suffix not in {".py", ".md", ".yaml", ".json", ".mjs", ".jsonl"}:
                continue
            if skip & set(path.relative_to(ROOT).parts):
                continue
            yield path

    def test_no_invisible_unicode(self):
        bad = []
        for path in self._tracked_texts():
            for lineno, line in enumerate(_text(path).splitlines(), 1):
                if INVISIBLE.search(line):
                    bad.append(f"{path.relative_to(ROOT)}:{lineno}")
        self.assertEqual(bad, [], f"不可见字符：{bad}")

    def test_no_secrets(self):
        bad = []
        for path in self._tracked_texts():
            if SECRETS.search(_text(path)):
                bad.append(str(path.relative_to(ROOT)))
        self.assertEqual(bad, [], f"疑似密钥：{bad}")

    def test_python_compiles(self):
        import py_compile
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            for path in ROOT.glob("*.py"):
                py_compile.compile(str(path), cfile=str(Path(tmp) / (path.stem + ".pyc")), doraise=True)


class TestUpstreamArtefacts(unittest.TestCase):
    def test_bank_assets_present(self):
        self.assertTrue((ROOT / "upstream" / "scripts" / "run_bank_live.mjs").exists())
        self.assertTrue((ROOT / "upstream" / "LICENSE").exists())
        banks = list((ROOT / "upstream" / "tests").glob("prompt-bank*.jsonl"))
        self.assertTrue(banks, "缺少 prompt bank")
        for bank in banks:
            rows = [json.loads(line) for line in bank.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertTrue(rows, f"{bank.name} 空文件")
            for row in rows[:3]:  # 抽样：最少要能被解析且带用例标识
                self.assertTrue({"scenario", "prompt"} <= set(row), f"{bank.name} 用例结构异常")


if __name__ == "__main__":
    unittest.main()
