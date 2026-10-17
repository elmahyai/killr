import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from remotes.github_remote import github_remote

out = Path(__file__).resolve().parents[1] / "docs" / "output" / "github_remote-python.txt"
out.parent.mkdir(parents=True, exist_ok=True)


def one():
    try:
        return github_remote("r-lib/remotes#7", auth_token=None)
    except RuntimeError as exc:
        return exc


value = one()

elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

tagged = github_remote("igraph=igraph/rigraph@v1.0.0", auth_token=None)
if (tagged.package, tagged.repo, tagged.ref) != ("igraph", "rigraph", "v1.0.0"):
    raise SystemExit(
        f"tag case returned {tagged.package}, {tagged.repo}, {tagged.ref}"
    )
branch = github_remote("user/repo", ref="branch", auth_token=None)
if branch.ref != "branch":
    raise SystemExit("ref argument was not kept")
kept = github_remote("user/repo/pkg@tag", ref="branch", auth_token=None)
if kept.ref != "tag":
    raise SystemExit("parsed tag was replaced by the ref argument")
missing_ref = github_remote("user/repo", ref=None, auth_token=None)
if missing_ref.ref != "HEAD":
    raise SystemExit("None ref was not HEAD")

tag_line = (
    'github_remote("igraph=igraph/rigraph@v1.0.0", auth_token = NULL) '
    f"returns package {tagged.package}, repo {tagged.repo}, ref {tagged.ref}."
)

if isinstance(value, RuntimeError):
    username = None
    repo = None
    ref = None
    err = str(value)
    pull_text = (
        'github_remote("r-lib/remotes#7", auth_token = NULL) stops with:\n' + err
    )
else:
    username = value.username
    repo = value.repo
    ref = value.ref
    err = None
    pull_text = (
        'github_remote("r-lib/remotes#7", auth_token = NULL) returns username '
        f"{username}, repo {repo}, ref {ref}."
    )

out.write_text(tag_line + "\n" + pull_text + "\n", encoding="utf-8")

print(json.dumps({
    "username": username,
    "repo": repo,
    "ref": ref,
    "error": err,
    "median_ms": statistics.median(elapsed),
}, separators=(",", ":")))
