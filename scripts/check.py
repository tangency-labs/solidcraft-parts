#!/usr/bin/env python3
"""Checks for the SolidCraft parts index.

    python3 scripts/check.py manifests [--network] [PATH ...]   # check manifests (default: all)
    python3 scripts/check.py pr --base SHA --head SHA --author LOGIN [--network]

`manifests` checks each manifest on its own and the index as a whole: the schema, the path,
the id, unique ids, the licence. With --network it also looks up the repository, the release
and its asset on GitHub, downloads the asset and checks its SHA-256 and its file list.

`pr` checks a pull request: which files it may change, the tier and example rules, then the
`manifests` checks for every manifest it adds or changes (with --network for the release).

Nothing from a library's repository is ever run. The asset is downloaded, hashed and its zip
directory read; it is never unpacked. Needs Python 3.10+ and the `jsonschema` package.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

# The checks' own files (schema, licence list, maintainers) come from the checkout this script is
# in; the manifests come from TREE, which CI sets with --tree to the pull request's checkout, so
# a pull request can't loosen the checks it is checked by.
ROOT = Path(__file__).resolve().parent.parent
TREE = ROOT
LIBRARIES = "libraries"
SCHEMA = ROOT / "schema" / "library.schema.json"
SPDX = ROOT / "schema" / "spdx.json"
MAINTAINERS = ROOT / ".github" / "maintainers.txt"

# The largest asset CI downloads (GitHub's own limit for a release asset is 2 GiB).
MAX_ASSET = 2 * 1024**3
# File types the Parts Library panel shows.
PART_EXTS = {".sc", ".solidcraft", ".step", ".stp", ".stl", ".3mf", ".obj", ".glb", ".gltf"}
# Files that may sit beside the parts: pictures, notes, licences, glTF buffers.
SIDE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".svg", ".md", ".txt", ".pdf", ".json", ".bin", ".mtl"}
SIDE_NAMES = {"license", "licence", "copying", "notice", "readme", "authors", "changelog"}
# Programs and scripts have no place in a parts library.
BANNED_EXTS = {
    ".exe", ".dll", ".so", ".dylib", ".msi", ".app", ".bat", ".cmd", ".com", ".ps1", ".sh", ".bash",
    ".py", ".pyc", ".js", ".mjs", ".cjs", ".vbs", ".jar", ".wasm", ".scr", ".lnk", ".deb", ".rpm",
    ".appimage", ".dmg", ".pkg",
}
MANIFEST_RE = re.compile(r"^libraries/([^/]+)/([^/]+)\.json$")


class Report:
    def __init__(self) -> None:
        self.errors = 0
        self.warnings = 0
        self.lines: list[str] = []

    def _emit(self, kind: str, path: str | None, msg: str) -> None:
        where = f" file={path}" if path else ""
        if os.environ.get("GITHUB_ACTIONS"):
            print(f"::{kind}{where}::{msg}")
        else:
            print(f"{kind.upper()}: {path + ': ' if path else ''}{msg}")
        self.lines.append(f"- **{kind}** {('`' + path + '`: ') if path else ''}{msg}")

    def error(self, path: str | None, msg: str) -> None:
        self.errors += 1
        self._emit("error", path, msg)

    def warn(self, path: str | None, msg: str) -> None:
        self.warnings += 1
        self._emit("warning", path, msg)

    def ok(self, msg: str) -> None:
        print(msg)
        self.lines.append(f"- {msg}")

    def summary(self, title: str) -> None:
        out = os.environ.get("GITHUB_STEP_SUMMARY")
        if out:
            with open(out, "a", encoding="utf-8") as f:
                f.write(f"## {title}\n\n" + "\n".join(self.lines) + "\n\n")
                f.write(f"{self.errors} error(s), {self.warnings} warning(s)\n")


# ---------------------------------------------------------------- licences

def _spdx() -> dict:
    return json.loads(SPDX.read_text(encoding="utf-8"))


def check_license(expr: str, spdx: dict) -> tuple[list[str], list[str]]:
    """Errors and warnings for an SPDX licence expression (ids joined by AND, OR, WITH, brackets)."""
    licenses = {x.lower(): x for x in spdx["licenses"]}
    deprecated = {x.lower(): x for x in spdx["deprecated_licenses"]}
    exceptions = {x.lower(): x for x in spdx["exceptions"]}
    errors: list[str] = []
    warnings: list[str] = []
    tokens = re.findall(r"\(|\)|[^\s()]+", expr)
    depth = 0
    expect_id = True
    after_with = False
    for tok in tokens:
        up = tok.upper()
        if tok == "(":
            if not expect_id:
                errors.append(f"unexpected '(' in licence {expr!r}")
            depth += 1
        elif tok == ")":
            depth -= 1
            if depth < 0 or expect_id:
                errors.append(f"unbalanced ')' in licence {expr!r}")
                depth = max(depth, 0)
        elif up in ("AND", "OR", "WITH"):
            if expect_id:
                errors.append(f"'{tok}' without a licence before it in {expr!r}")
            if tok != up:
                errors.append(f"SPDX operators are upper case: write {up}, not {tok}")
            expect_id = True
            after_with = up == "WITH"
            continue
        else:
            if not expect_id:
                errors.append(f"two licences without AND/OR between them in {expr!r}")
            base = tok[:-1] if tok.endswith("+") else tok
            if after_with:
                if base.lower() not in exceptions:
                    errors.append(f"{tok!r} is not an SPDX licence exception id")
                elif exceptions[base.lower()] != base:
                    errors.append(f"write the exception as {exceptions[base.lower()]!r}, not {tok!r}")
            elif base.lower() in licenses:
                if licenses[base.lower()] != base:
                    errors.append(f"write the licence as {licenses[base.lower()]!r}, not {tok!r}")
            elif base.lower() in deprecated:
                warnings.append(f"{tok!r} is a deprecated SPDX id; use its current id")
            elif base.startswith("LicenseRef-"):
                errors.append(f"{tok!r}: use a licence from the SPDX list (https://spdx.org/licenses/)")
            else:
                errors.append(f"{tok!r} is not an SPDX licence id (see https://spdx.org/licenses/)")
            expect_id = False
        after_with = False
    if depth != 0:
        errors.append(f"unbalanced brackets in licence {expr!r}")
    if expect_id and tokens:
        errors.append(f"licence {expr!r} ends with an operator")
    if not tokens:
        errors.append("the licence is empty")
    return errors, warnings


# ---------------------------------------------------------------- manifests

def load_validator():
    try:
        import jsonschema  # noqa: PLC0415
    except ImportError:
        sys.exit("the jsonschema package is needed: pip install jsonschema")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    cls = jsonschema.validators.validator_for(schema)
    cls.check_schema(schema)
    return cls(schema)


def all_manifests() -> list[str]:
    return sorted(p.relative_to(TREE).as_posix() for p in (TREE / LIBRARIES).glob("*/*.json"))


def read_manifest(rel: str, rep: Report) -> dict | None:
    try:
        raw = (TREE / rel).read_bytes()
    except OSError as e:
        rep.error(rel, f"can't be read: {e}")
        return None
    if raw.startswith(b"\xef\xbb\xbf"):
        rep.error(rel, "remove the byte-order mark; manifests are plain UTF-8")
        raw = raw[3:]
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        rep.error(rel, f"is not valid JSON: {e}")
        return None
    if not isinstance(data, dict):
        rep.error(rel, "must be a JSON object")
        return None
    return data


def check_manifest(rel: str, data: dict, validator, spdx: dict, rep: Report) -> bool:
    """The checks that need nothing but the manifest and its path. True when it passed."""
    before = rep.errors
    for err in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path)):
        at = "/".join(str(p) for p in err.absolute_path) or "(top level)"
        rep.error(rel, f"schema: {at}: {err.message}")
    m = MANIFEST_RE.match(rel)
    if not m:
        rep.error(rel, "manifests go at libraries/<publisher>/<library>.json")
        return False
    folder, stem = m.groups()
    if folder != folder.lower() or stem != stem.lower():
        rep.error(rel, "folder and file names are lower case")
    publisher = data.get("publisher")
    if isinstance(publisher, str) and publisher != folder:
        rep.error(rel, f"publisher is {publisher!r} but the file is in the {folder!r} folder")
    want_id = f"{folder}.{stem}"
    if isinstance(data.get("id"), str) and data["id"] != want_id:
        rep.error(rel, f"id is {data['id']!r}; for this path it must be {want_id!r}")
    repo = data.get("repo")
    if isinstance(repo, str) and "/" in repo and isinstance(publisher, str):
        owner = repo.split("/", 1)[0]
        if owner.lower() != publisher:
            rep.error(rel, f"repo {repo!r} is owned by {owner!r}, not the publisher {publisher!r}")
    lic = data.get("license")
    if isinstance(lic, str):
        errs, warns = check_license(lic, spdx)
        for e in errs:
            rep.error(rel, f"license: {e}")
        for w in warns:
            rep.warn(rel, f"license: {w}")
    return rep.errors == before


def check_unique(manifests: dict[str, dict], rep: Report) -> None:
    seen: dict[str, str] = {}
    for rel, data in sorted(manifests.items()):
        mid = data.get("id")
        if not isinstance(mid, str):
            continue
        key = mid.lower()
        if key in seen:
            rep.error(rel, f"id {mid!r} is already used by {seen[key]}")
        else:
            seen[key] = rel


# ---------------------------------------------------------------- GitHub

def _get(url: str, token: str | None, accept: str = "application/vnd.github+json") -> tuple[int, dict | None]:
    req = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": "solidcraft-parts-check"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read()
            return r.status, (json.loads(body) if body else None)
    except urllib.error.HTTPError as e:
        return e.code, None


def _q(s: str) -> str:
    return urllib.parse.quote(s, safe="")


def download_and_hash(url: str, limit: int, dest: Path) -> tuple[str, int]:
    """Stream `url` to `dest` (no token sent), returning its SHA-256 and size."""
    req = urllib.request.Request(url, headers={"User-Agent": "solidcraft-parts-check", "Accept": "application/octet-stream"})
    h = hashlib.sha256()
    size = 0
    with urllib.request.urlopen(req, timeout=300) as r, open(dest, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            size += len(chunk)
            if size > limit:
                raise ValueError(f"the asset is larger than {limit // 1024**2} MiB")
            h.update(chunk)
            f.write(chunk)
    return h.hexdigest(), size


def check_zip(rel: str, path: Path, rep: Report) -> None:
    """Read the zip's directory (never unpack it) and check what it holds."""
    try:
        zf = zipfile.ZipFile(path)
    except zipfile.BadZipFile:
        rep.error(rel, "the release asset is not a zip file")
        return
    parts = 0
    other: list[str] = []
    with zf:
        for info in zf.infolist():
            name = info.filename
            if name.startswith("/") or "\\" in name or re.match(r"^[A-Za-z]:", name) or ".." in name.split("/"):
                rep.error(rel, f"the zip holds an unsafe path: {name!r}")
                continue
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode):
                rep.error(rel, f"the zip holds a symbolic link: {name!r}")
                continue
            if info.is_dir():
                continue
            leaf = name.rsplit("/", 1)[-1]
            ext = os.path.splitext(leaf)[1].lower()
            if ext in BANNED_EXTS:
                rep.error(rel, f"programs and scripts don't belong in a parts library: {name!r}")
            elif ext in PART_EXTS:
                parts += 1
            elif leaf.startswith(".") or leaf.startswith("~") or ext in SIDE_EXTS or os.path.splitext(leaf)[0].lower() in SIDE_NAMES:
                pass
            else:
                other.append(name)
    if parts == 0:
        rep.error(rel, "the zip holds no parts (.sc, .step, .stp, .stl, .3mf, .obj, .glb or .gltf files)")
    else:
        rep.ok(f"{rel}: the zip holds {parts} part file(s)")
    if other:
        shown = ", ".join(repr(x) for x in other[:5]) + (" and more" if len(other) > 5 else "")
        rep.warn(rel, f"{len(other)} file(s) the Parts Library panel doesn't show: {shown}")


def check_release(rel: str, data: dict, rep: Report, token: str | None, workdir: Path) -> None:
    repo = data["repo"]
    release = data["release"]
    api = "https://api.github.com"
    status, info = _get(f"{api}/repos/{repo}", token)
    if status != 200 or not info:
        rep.error(rel, f"repository {repo} was not found (or is not public)")
        return
    if info.get("private"):
        rep.error(rel, f"repository {repo} is private; it must be public")
        return
    if info.get("full_name", "").lower() != repo.lower():
        rep.error(rel, f"repository {repo} has moved to {info.get('full_name')}; use the new name")
    owner = info.get("owner", {}).get("login", "")
    if owner.lower() != data["publisher"]:
        rep.error(rel, f"repository {repo} is owned by {owner}, not the publisher {data['publisher']}")
    if info.get("archived"):
        rep.warn(rel, f"repository {repo} is archived")
    gh_license = (info.get("license") or {}).get("spdx_id")
    if gh_license and gh_license not in ("NOASSERTION", "OTHER") and gh_license not in data["license"]:
        rep.warn(rel, f"GitHub reads the repository's licence as {gh_license}; the manifest says {data['license']}")

    tag = release["tag"]
    status, rinfo = _get(f"{api}/repos/{repo}/releases/tags/{_q(tag)}", token)
    if status != 200 or not rinfo:
        rep.error(rel, f"{repo} has no published release with the tag {tag!r}")
        return
    if rinfo.get("prerelease"):
        rep.warn(rel, f"release {tag} is marked as a pre-release")
    if "commit" in release:
        status, cinfo = _get(f"{api}/repos/{repo}/commits/{_q(tag)}", token)
        if status != 200 or not cinfo:
            rep.error(rel, f"tag {tag!r} could not be resolved to a commit")
        elif cinfo.get("sha") != release["commit"]:
            rep.error(rel, f"tag {tag!r} points to {cinfo.get('sha')}, not {release['commit']}")
    asset = next((a for a in rinfo.get("assets", []) if a.get("name") == release["asset"]), None)
    if asset is None:
        names = ", ".join(a.get("name", "?") for a in rinfo.get("assets", [])) or "none"
        rep.error(rel, f"release {tag} has no asset named {release['asset']!r} (it has: {names})")
        return
    if asset.get("state") != "uploaded":
        rep.error(rel, f"asset {release['asset']} is not fully uploaded")
        return
    if asset.get("size", 0) > MAX_ASSET:
        rep.error(rel, f"asset {release['asset']} is larger than {MAX_ASSET // 1024**2} MiB")
        return
    if "size" in release and asset.get("size") != release["size"]:
        rep.error(rel, f"asset size is {asset.get('size')} bytes, the manifest says {release['size']}")
    dest = workdir / "asset.zip"
    try:
        digest, size = download_and_hash(asset["browser_download_url"], MAX_ASSET, dest)
    except (urllib.error.URLError, ValueError, OSError) as e:
        rep.error(rel, f"downloading {release['asset']} failed: {e}")
        return
    if digest != release["sha256"]:
        rep.error(rel, f"asset SHA-256 is {digest}, the manifest says {release['sha256']}")
    else:
        rep.ok(f"{rel}: {repo}@{tag}/{release['asset']} matches its SHA-256 ({size} bytes)")
    check_zip(rel, dest, rep)
    dest.unlink(missing_ok=True)


# ---------------------------------------------------------------- pull requests

def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(TREE), *args], check=True, capture_output=True, text=True).stdout


def base_manifest(base: str, rel: str) -> dict | None:
    try:
        return json.loads(git("show", f"{base}:{rel}"))
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return None


def maintainers() -> set[str]:
    if not MAINTAINERS.exists():
        return set()
    out = set()
    for line in MAINTAINERS.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip().lstrip("@").lower()
        if line:
            out.add(line)
    return out


def may_publish(author: str, publisher: str, token: str | None, cache: dict) -> bool:
    """The author may publish for their own account, or for an organisation they publicly belong to."""
    if author == publisher:
        return True
    if publisher not in cache:
        status, _ = _get(f"https://api.github.com/orgs/{_q(publisher)}/public_members/{_q(author)}", token)
        cache[publisher] = status == 204
    return cache[publisher]


def cmd_pr(args, rep: Report) -> None:
    author = args.author.lower()
    is_maintainer = author in maintainers()
    token = os.environ.get("GITHUB_TOKEN")
    rep.ok(f"Pull request by **{args.author}**{' (maintainer)' if is_maintainer else ''}")
    changes = []
    for line in git("diff", "--name-status", "--no-renames", f"{args.base}...{args.head}").splitlines():
        status, path = line.split("\t", 1)
        changes.append((status[0], path))
    if not changes:
        rep.ok("No files changed.")
        return
    orgs: dict[str, bool] = {}
    touched: list[str] = []
    for status, path in changes:
        m = MANIFEST_RE.match(path)
        if not is_maintainer:
            if not m:
                rep.error(path, "only maintainers change files outside libraries/<publisher>/<library>.json")
                continue
            folder = m.group(1)
            if not may_publish(author, folder.lower(), token, orgs):
                rep.error(path, f"{args.author} may only add or change libraries in libraries/{author}/ "
                                f"(or the folder of an organisation they are a public member of)")
                continue
        if m and status != "D":
            touched.append(path)
        elif m and status == "D":
            rep.ok(f"{path}: removed")
        elif not m and status != "D" and path.startswith(f"{LIBRARIES}/"):
            rep.error(path, "only manifests (libraries/<publisher>/<library>.json) go in libraries/")

    validator = load_validator()
    spdx = _spdx()
    for rel in touched:
        data = read_manifest(rel, rep)
        if data is None:
            continue
        before = base_manifest(args.base, rel)
        if not is_maintainer:
            tier = data.get("tier")
            allowed = {"unverified"} | ({before.get("tier")} if before else set())
            if tier not in allowed:
                rep.error(rel, f"tier must be \"unverified\"; maintainers set {tier!r}")
            if data.get("example") and not (before and before.get("example")):
                rep.error(rel, "only maintainers add example entries")
            if before and before.get("id") != data.get("id"):
                rep.error(rel, "a listed library keeps its id")
        if check_manifest(rel, data, validator, spdx, rep):
            if args.network:
                with tempfile.TemporaryDirectory() as d:
                    check_release(rel, data, rep, token, Path(d))
            else:
                rep.ok(f"{rel}: ok (release not checked without --network)")
    # Ids stay unique across the whole index, including entries this PR didn't touch.
    everything = {}
    for rel in all_manifests():
        d = read_manifest(rel, Report())
        if d is not None:
            everything[rel] = d
    check_unique(everything, rep)


def cmd_manifests(args, rep: Report) -> None:
    validator = load_validator()
    spdx = _spdx()
    paths = args.paths or all_manifests()
    token = os.environ.get("GITHUB_TOKEN")
    loaded: dict[str, dict] = {}
    for rel in paths:
        rel = Path(rel).resolve().relative_to(TREE).as_posix() if Path(rel).is_absolute() else Path(rel).as_posix()
        data = read_manifest(rel, rep)
        if data is None:
            continue
        loaded[rel] = data
        if check_manifest(rel, data, validator, spdx, rep):
            if args.network:
                with tempfile.TemporaryDirectory() as d:
                    check_release(rel, data, rep, token, Path(d))
            else:
                rep.ok(f"{rel}: ok")
    for rel in all_manifests():
        if rel not in loaded:
            d = read_manifest(rel, Report())
            if d is not None:
                loaded[rel] = d
    check_unique(loaded, rep)
    stray = [p.relative_to(TREE).as_posix() for p in (TREE / LIBRARIES).rglob("*")
             if p.is_file() and p.name != ".gitkeep" and not MANIFEST_RE.match(p.relative_to(TREE).as_posix())]
    for s in stray:
        rep.error(s, "only manifests (libraries/<publisher>/<library>.json) go in libraries/")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("manifests", help="check manifests (default: all of them)")
    m.add_argument("--network", action="store_true", help="also check the repository, release and asset hash")
    m.add_argument("paths", nargs="*")
    p = sub.add_parser("pr", help="check a pull request's changes")
    p.add_argument("--base", required=True)
    p.add_argument("--head", required=True)
    p.add_argument("--author", required=True)
    p.add_argument("--network", action="store_true")
    for sp in (m, p):
        sp.add_argument("--tree", default=None, help="the checkout holding libraries/ (default: this one)")
    args = ap.parse_args()
    global TREE
    if args.tree:
        TREE = Path(args.tree).resolve()
    rep = Report()
    if args.cmd == "pr":
        cmd_pr(args, rep)
        title = "Pull request checks"
    else:
        cmd_manifests(args, rep)
        title = "Manifest checks"
    rep.summary(title)
    print(f"\n{rep.errors} error(s), {rep.warnings} warning(s)")
    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main())
