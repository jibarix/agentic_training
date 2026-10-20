"""Passages and BM25 ranking, standard library only.

BM25 follows Robertson and Zaragoza (2009), Equations 3.3 and 3.15: for each query word, a
saturating function of its count in the passage, normalised by passage length, times an IDF weight.
"""
import math
import re
from collections import Counter
from pathlib import Path

WORD = re.compile(r"[a-z0-9]+")


def words(text):
    return WORD.findall(text.lower())


def passages(folder, size):
    """Each file split into passages of about `size` characters, within one section, at line breaks.

    size=1 gives one line per passage, as Chapter 1's lookup searches. A table row always carries
    its table's header, so a passage of rows still says what each column is.
    """
    out = []
    for f in sorted(Path(folder).glob("*.md")):
        section, header, buf = "", None, []

        def flush():
            if buf:
                out.append((f.name, "\n".join(([header] if header and buf[0] != header else []) + buf)))
                buf.clear()

        for line in f.read_text(encoding="utf-8").splitlines():
            line = re.sub(r"\s+", " ", line.strip())
            if not line or set(line) <= set("|-# "):
                continue
            if line.startswith("#"):
                flush()
                section, header = line.lstrip("# "), None
                continue
            if line.startswith("|"):
                if header is None:
                    flush()
                    header = line
                    continue
            else:
                if header is not None:
                    flush()
                header = None
            if buf and len("\n".join(buf)) + len(line) > size:
                flush()
            if not buf and section and header is None:
                buf.append(f"[{section}]")
            buf.append(line)
        flush()
    return out


class BM25:
    def __init__(self, texts, k1=1.2, b=0.75):
        self.k1, self.b = k1, b
        self.counts = [Counter(words(t)) for t in texts]
        self.lengths = [sum(c.values()) for c in self.counts]
        self.avg = sum(self.lengths) / len(texts)
        n = Counter(w for c in self.counts for w in c)
        N = len(texts)
        # Equation 3.3. A word in more than half the passages would weigh less than zero; it
        # weighs zero here instead, as in Chapter 1's lookup.
        self.idf = {w: max(0.0, math.log((N - k + 0.5) / (k + 0.5))) for w, k in n.items()}

    def score(self, query):
        out = []
        for c, dl in zip(self.counts, self.lengths):
            norm = self.k1 * ((1 - self.b) + self.b * dl / self.avg)        # Equation 3.15
            out.append(sum(c[w] / (norm + c[w]) * self.idf.get(w, 0.0) for w in set(words(query)) if c[w]))
        return out

    def top(self, query, k=5):
        s = self.score(query)
        ranked = sorted(range(len(s)), key=lambda i: -s[i])
        return [(i, s[i]) for i in ranked[:k] if s[i] > 0]
