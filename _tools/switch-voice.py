"""
One-off: switch the site's business voice from "we" to "I" (sole trader).

A blind find-and-replace would be wrong in four ways, so each is masked out
before any substitution happens:

  1. <summary> FAQ questions are the CLIENT asking — "Is our data kept
     confidential?" must keep "our".
  2. JSON-LD "name" fields are those same client questions.
  3. Quoted client speech in prose — "our reporting is a mess".
  4. HTML element tags, so ids and hrefs survive: `\\bwe\\b` matches inside
     `what-we-need` because a hyphen is a word boundary, which would break
     both the anchor and the link that targets it.

HTML comments are deliberately NOT masked — the page metadata block is a
comment, and its title/description are business voice that should switch.

Verb agreement is handled before the generic pronoun swap: English first
person singular and plural differ only on to-be, so "we are" -> "I am" and
"we were" -> "I was" are special-cased.

Usage:  py _tools/switch-voice.py [--dry-run]
"""
import io, os, re, sys

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_src")
DRY = "--dry-run" in sys.argv

AP = r"['’]"  # straight or curly apostrophe

# Client speech that must keep the plural voice. Apostrophes kept flexible.
CLIENT_QUOTES = [
    r"Our reporting takes too long to put together",
    r"Two of our systems don" + AP + r"t agree",
    r"We don" + AP + r"t have anyone who really knows Excel or Power BI",
    r"We need to understand our bank statements or cashflow properly",
    r"our reporting is a mess",
]

# (pattern, replacement) applied in order. Agreement cases come first.
RULES = [
    (r"\bWe\s+are\b",              "I am"),
    (r"\bwe\s+are\b",              "I am"),
    (r"\bWe\s+were\b",             "I was"),
    (r"\bwe\s+were\b",             "I was"),
    (r"\bourselves\b",             "myself"),
    (r"\bOurselves\b",             "Myself"),
    (r"\bWe" + AP + r"ll\b",       "I'll"),
    (r"\bwe" + AP + r"ll\b",       "I'll"),
    (r"\bWe" + AP + r"re\b",       "I'm"),
    (r"\bwe" + AP + r"re\b",       "I'm"),
    (r"\bWe" + AP + r"ve\b",       "I've"),
    (r"\bwe" + AP + r"ve\b",       "I've"),
    (r"\bWe" + AP + r"d\b",        "I'd"),
    (r"\bwe" + AP + r"d\b",        "I'd"),
    (r"\bOurs\b",                  "Mine"),
    (r"\bours\b",                  "mine"),
    (r"\bOur\b",                   "My"),
    (r"\bour\b",                   "my"),
    (r"\bUs\b",                    "Me"),
    (r"\bus\b",                    "me"),
    (r"\bWe\b",                    "I"),
    (r"\bwe\b",                    "I"),
]


def transform(text):
    masked = []

    def mask(m):
        masked.append(m.group(0))
        return f"\x00{len(masked) - 1}\x00"

    # Order matters: whole <summary> elements first (they contain tags), then
    # schema question names, then client quotes, then remaining element tags.
    text = re.sub(r"<summary>.*?</summary>", mask, text, flags=re.S)
    text = re.sub(r'"name":\s*"[^"]*"', mask, text)
    for q in CLIENT_QUOTES:
        text = re.sub(q, mask, text)
    text = re.sub(r"<[a-zA-Z/][^>]*>", mask, text, flags=re.S)

    for pat, rep in RULES:
        text = re.sub(pat, rep, text)

    # Unmask (indices are stable; placeholders never nest)
    def unmask(m):
        return masked[int(m.group(1))]

    return re.sub(r"\x00(\d+)\x00", unmask, text)


def main():
    changed = 0
    for root, _, files in os.walk(SRC):
        for f in sorted(files):
            if not f.endswith((".html", ".js")):
                continue
            p = os.path.join(root, f)
            before = io.open(p, encoding="utf-8").read()
            after = transform(before)
            if before == after:
                continue
            changed += 1
            rel = os.path.relpath(p, SRC).replace("\\", "/")
            print(f"  {'would change' if DRY else 'changed'}  {rel}")
            if not DRY:
                io.open(p, "w", encoding="utf-8", newline="\n").write(after)
    print(f"\n{changed} file(s) {'to change' if DRY else 'rewritten'}")


if __name__ == "__main__":
    main()
