import re
import unicodedata


def normalize(s):
    if not s:
        return ""
    n = unicodedata.normalize("NFKD", s.strip().lower())
    n = "".join(ch for ch in n if not unicodedata.combining(ch))
    n = re.sub(r"[^a-z0-9\s]", " ", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


def levenshtein(a, b):
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr = [i]
        for j, cb in enumerate(b, start=1):
            insert = curr[j - 1] + 1
            delete = prev[j] + 1
            replace = prev[j - 1] + (0 if ca == cb else 1)
            curr.append(min(insert, delete, replace))
        prev = curr
    return prev[-1]


rec_home = "Deportivo Alavés"
rec_away = "Real Madrid Club de Fútbol"
api_home = "Deportivo Alaves"
api_away = "Real Madrid CF"

r_home = normalize(rec_home)
r_away = normalize(rec_away)
a_home = normalize(api_home)
a_away = normalize(api_away)
print("normalized:", repr(r_home), repr(a_home), repr(r_away), repr(a_away))

dh = levenshtein(r_home, a_home)
da = levenshtein(r_away, a_away)
print(
    "dist home",
    dh,
    "len max",
    max(1, max(len(r_home), len(a_home))),
    "ratio",
    dh / max(1, max(len(r_home), len(a_home))),
)
print(
    "dist away",
    da,
    "len max",
    max(1, max(len(r_away), len(a_away))),
    "ratio",
    da / max(1, max(len(r_away), len(a_away))),
)
