import ast, hashlib, re, sys, json, collections
from pathlib import Path

repo = Path(sys.argv[1])
tests_root = repo / "tests"
LEGACY = re.compile(
    r"\b(plot\.md|storylets\.md|storylet-routes\.yaml|knowledge\.yaml|pacing\.yaml|incidents\.yaml|handoffs\.yaml|connections\.yaml|world\.yaml)\b"
)
rows = []
for p in sorted(list(tests_root.rglob("test_*.py")) + list(tests_root.rglob("*_test.py"))):
    src = p.read_text()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        continue
    mod_skip = any(
        isinstance(n, ast.Assign)
        and any(getattr(t, "id", "") == "pytestmark" for t in n.targets)
        and "skip" in ast.unparse(n.value)
        and "skipif" not in ast.unparse(n.value)
        for n in tree.body
    )

    def visit(fn, cls=None):
        decos = [ast.unparse(d) for d in fn.decorator_list]
        body = fn.body
        if (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(getattr(body[0], "value", None), ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            body = body[1:]
        text = "\n".join(ast.unparse(b) for b in body)
        seg = ast.get_source_segment(src, fn) or ""
        nodes = [n for b in body for n in ast.walk(b)]
        has_assert = (
            any(isinstance(n, ast.Assert) for n in nodes)
            or "pytest.raises" in text
            or "pytest.fail" in text
            or ".assert_" in text
            or "assert_" in text
        )
        unconditional_skip = (
            any(d.startswith("pytest.mark.skip(") or d == "pytest.mark.skip" for d in decos)
            or mod_skip
            or bool(re.match(r"\s*pytest\.skip\(", text))
        )
        # normalize: strip names of locals? keep simple: hash text with identifier-free literal masking
        norm = re.sub(r"\s+", " ", text)
        rows.append(
            dict(
                file=str(p.relative_to(repo)),
                name=(cls + "::" if cls else "") + fn.name,
                line=fn.lineno,
                lines=len(body) and (fn.end_lineno - fn.lineno + 1),
                has_assert=has_assert,
                skip=unconditional_skip,
                hash=hashlib.md5(norm.encode()).hexdigest(),
                legacy=bool(LEGACY.search(seg)),
                param="parametrize" in " ".join(decos),
                trivial=len(body) <= 1 and not has_assert,
                size=len(norm),
            )
        )

    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test"):
            visit(n)
        if isinstance(n, ast.ClassDef):
            for m in n.body:
                if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and m.name.startswith("test"):
                    visit(m, n.name)
json.dump(rows, open(sys.argv[2], "w"))
print("test functions:", len(rows), "files:", len({r["file"] for r in rows}))
print("no assertion:", sum(not r["has_assert"] for r in rows))
print("unconditional skip:", sum(r["skip"] for r in rows))
print(
    "mention legacy filenames:",
    sum(r["legacy"] for r in rows),
    "in",
    len({r["file"] for r in rows if r["legacy"]}),
    "files",
)
h = collections.defaultdict(list)
for r in rows:
    if r["size"] > 80:
        h[r["hash"]].append(r)
d = [v for v in h.values() if len(v) > 1]
print("exact duplicate bodies (size>80):", len(d), "groups,", sum(len(v) for v in d), "tests")
