"""Checks the simulated security boundary (spec 5.1): code in attacks/query/
and the client may not import the detector, the service internals, the
experiment driver or hmac, and may not mention the key file or service state
files. Key-access attacks (attacks/key/) are allowed to use the key.

Run:  python -m unittest tests.test_boundary -v
"""
import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

FORBIDDEN_IMPORTS = {"wmark", "service", "experiments", "hmac", "scripts"}
FORBIDDEN_STRINGS = ("key.hex", "accounts.json", "ratelimit.json", "clock.json",
                     "requests.jsonl", "WMARK_SERVICE_STATE", "settings.json")


def violations(path: Path, forbidden_imports, forbidden_strings) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found = []
    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names = [node.module]
        for n in names:
            if n.split(".")[0] in forbidden_imports:
                found.append(f"{path.relative_to(ROOT)}:{node.lineno} imports {n}")
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            for s in forbidden_strings:
                if s in node.value:
                    found.append(f"{path.relative_to(ROOT)}:{node.lineno} mentions {s!r}")
    return found


class TestBoundary(unittest.TestCase):
    def test_query_attack_code_stays_outside_the_service(self):
        found = []
        for path in sorted((ROOT / "attacks" / "query").rglob("*.py")):
            found += violations(path, FORBIDDEN_IMPORTS, FORBIDDEN_STRINGS)
        self.assertEqual(found, [], "Query-access attack code crosses the boundary:\n" + "\n".join(found))

    def test_client_does_not_load_the_key(self):
        found = violations(ROOT / "client" / "__init__.py", {"wmark", "service", "experiments", "hmac"},
                           ("key.hex", "accounts.json", "ratelimit.json", "clock.json", "requests.jsonl"))
        self.assertEqual(found, [], "\n".join(found))

    def test_checker_catches_a_violation(self):
        import tempfile
        with tempfile.TemporaryDirectory(dir=ROOT) as d:
            bad = Path(d) / "bad.py"
            bad.write_text("from wmark.detector import word_color\nopen('config/key.hex')\n", encoding="utf-8")
            self.assertEqual(len(violations(bad, FORBIDDEN_IMPORTS, FORBIDDEN_STRINGS)), 2)


if __name__ == "__main__":
    unittest.main()
