"""Tests for the visible-text views of source files (skills/ai-slop-prose/scripts/extract.py)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "skills", "ai-slop-prose", "scripts"))
import extract  # noqa: E402

SCAN = os.path.join(ROOT, "skills", "ai-slop-prose", "scripts", "scan.py")
UI = os.path.join(ROOT, "tests", "fixtures", "ui")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def spans(name):
    raw = read(os.path.join(UI, name))
    text, found, _ = extract.view(raw, name)
    return raw, text, {(raw[a:b], p) for a, b, p in found}


def scan(*args):
    env = dict(os.environ, PYTHONIOENCODING="utf-8", SUPAH_PROSE_HOME=tempfile.mkdtemp())
    out = subprocess.run([sys.executable, SCAN, "--json", *args], capture_output=True, text=True,
                         encoding="utf-8", env=env)
    return json.loads(out.stdout)


class Views(unittest.TestCase):
    def test_tsx_keeps_ui_text_and_purposes(self):
        raw, text, found = spans("Checkout.tsx")
        for item in [("Unlock the full potential of your shopping experience", "heading"),
                     ("Enter your email address", "placeholder"), ("Pay now", "button"),
                     ("Checkout form", "label"), ("Hello", "text"), (", your order is almost ready.", "text")]:
            self.assertIn(item, found)
        self.assertIn("error", {p for t, p in found if t.startswith("Oops!")})

    def test_tsx_drops_comments_logs_and_code(self):
        raw, text, found = spans("Checkout.tsx")
        visible = " ".join(t for t, _ in found)
        for gone in ("delves", "Here's the thing", "Let's dive in", "flex items-center", "user.name", "react"):
            self.assertNotIn(gone, visible, gone)
        self.assertEqual(len(text), len(raw))  # offsets preserved
        self.assertEqual(text.count("\n") >= raw.count("\n"), True)

    def test_locale_values_not_keys_or_paths(self):
        _, _, found = spans("it.json")
        texts = {t for t, _ in found}
        self.assertIn("Paga ora", texts)
        self.assertNotIn("/checkout/step-2", texts)
        self.assertNotIn("checkout", texts)
        self.assertIn(("Il tuo carrello è vuoto.", "empty-state"), found)

    def test_html_skips_comments_and_classes(self):
        _, _, found = spans("page.html")
        texts = {t for t, _ in found}
        self.assertIn("Benvenuto nel nostro negozio", texts)
        self.assertIn(("Logo del negozio", "alt"), found)
        self.assertNotIn("btn btn-primary", texts)
        self.assertFalse(any("commento" in t for t in texts))

    def test_natural_language_filter(self):
        for code in ("flex items-center gap-2", "/api/v1/users", "user.name", "GET", "SELECT * FROM users"):
            self.assertFalse(extract.natural(code), code)
        for words in ("Save", "Pay now", "Il tuo carrello è vuoto.", "Done!"):
            self.assertTrue(extract.natural(words), words)


class ScanningSourceFiles(unittest.TestCase):
    def test_string_quotes_are_not_quoted_speech(self):
        result = scan(os.path.join(UI, "it.json"))[0]
        rules = {h["rule"]: h for h in result["hits"]}
        self.assertIn("chat-residue", rules)
        self.assertIsNone(rules["chat-residue"]["kept"])
        self.assertEqual(rules["chat-residue"]["purpose"], "error")
        self.assertEqual(result["kind"], "locale")

    def test_purpose_flag_reaches_prose_hits(self):
        result = scan("--purpose", "landing page", os.path.join(ROOT, "tests", "fixtures", "slop-en.md"))[0]
        self.assertEqual(result["purpose"], "landing page")
        self.assertTrue(all(h["purpose"] == "landing page" for h in result["hits"]))

    def test_fix_never_touches_code(self):
        d = tempfile.mkdtemp()
        try:
            path = os.path.join(d, "App.tsx")
            src = ('// nota , perchè  commento\nconst cls = "a  b";\n'
                   'export const A = () => <p>Il prodotto , perchè  arriva domani.</p>;\n')
            with open(path, "w", encoding="utf-8") as f:
                f.write(src)
            subprocess.run([sys.executable, SCAN, "fix", path], capture_output=True)
            out = read(path)
            self.assertIn("// nota , perchè  commento", out)
            self.assertIn('"a  b"', out)
            self.assertIn("<p>Il prodotto, perché arriva domani.</p>", out)
        finally:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
