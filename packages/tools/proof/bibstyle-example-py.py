from tools.bibstyle import bibstyle

bibstyle(
    "unsorted",
    sortKeys=lambda refs: list(range(1, len(refs) + 1)),
    fmtPrefix=lambda paper: f"[{paper['.index']}]",
    _init=True,
)
env = bibstyle("unsorted", _default=False)
print(",".join(str(x) for x in env["sortKeys"]([{}, {}])))
print(env["fmtPrefix"]({".index": 1}))
