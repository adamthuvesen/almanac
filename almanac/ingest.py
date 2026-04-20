import subprocess
from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from typing import NamedTuple

from almanac.window import Window


class FileChange(NamedTuple):
    path: str
    lines_added: int
    lines_removed: int
    is_binary: bool = False


class Commit(NamedTuple):
    sha: str
    ts: str
    author_name: str
    author_email: str
    parents: list[str]
    subject: str
    files: list[FileChange]

    @property
    def is_merge(self) -> bool:
        return len(self.parents) > 1


def _decode(b: bytes) -> str:
    return b.decode("utf-8", errors="replace")


def _parse_numstat_z(stream: bytes) -> list[FileChange]:
    """Parse the NUL-terminated numstat stream for a single commit.

    The `-z` format uses `\\0` as the record terminator. Normal entries
    look like ``added\\tremoved\\tpath\\0``. Renames emit an empty path
    in the main record followed by two extra NUL-terminated tokens:
    ``added\\tremoved\\t\\0old\\0new\\0``. Binary files show ``-\\t-``
    for added/removed — recorded here with zero line counts and
    ``is_binary=True``.
    """
    tokens = stream.split(b"\0")
    files: list[FileChange] = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if not token.strip():
            i += 1
            continue
        parts = token.split(b"\t", 2)
        if len(parts) < 3:
            i += 1
            continue
        added_raw, removed_raw, path_bytes = parts
        is_binary = added_raw == b"-" or removed_raw == b"-"
        added = 0 if is_binary else int(added_raw)
        removed = 0 if is_binary else int(removed_raw)
        if path_bytes == b"":
            # Rename: next two tokens are old and new paths.
            if i + 2 >= len(tokens):
                break
            _old = tokens[i + 1]
            new = tokens[i + 2]
            files.append(
                FileChange(
                    path=_decode(new),
                    lines_added=added,
                    lines_removed=removed,
                    is_binary=is_binary,
                )
            )
            i += 3
        else:
            files.append(
                FileChange(
                    path=_decode(path_bytes),
                    lines_added=added,
                    lines_removed=removed,
                    is_binary=is_binary,
                )
            )
            i += 1
    return files


def _parse_log_stream(raw: bytes) -> list[Commit]:
    # Each commit starts with \x1e emitted by the --pretty format.
    blocks = raw.split(b"\x1e")
    commits: list[Commit] = []
    for block in blocks:
        if not block.strip():
            continue
        # Split header from numstat stream on the first \n.
        nl = block.find(b"\n")
        if nl < 0:
            header_bytes, numstat_bytes = block, b""
        else:
            header_bytes, numstat_bytes = block[:nl], block[nl + 1 :]
        fields = header_bytes.split(b"\x1f")
        if len(fields) < 6:
            continue
        sha = _decode(fields[0])
        ts = _decode(fields[1])
        author_name = _decode(fields[2])
        author_email = _decode(fields[3])
        parents_str = _decode(fields[4])
        subject = _decode(fields[5])
        parents = parents_str.split() if parents_str.strip() else []
        files = _parse_numstat_z(numstat_bytes)
        commits.append(
            Commit(
                sha=sha,
                ts=ts,
                author_name=author_name,
                author_email=author_email,
                parents=parents,
                subject=subject,
                files=files,
            )
        )
    return commits


def _run_git_log(repo: Path, window: Window, include_merges: bool) -> list[Commit]:
    cmd = [
        "git",
        "-C",
        str(repo),
        "log",
        "--use-mailmap",
        "--numstat",
        "-z",
        "--pretty=format:\x1e%H\x1f%aI\x1f%aN\x1f%aE\x1f%P\x1f%s",
        f"--since={window.since.isoformat()}",
        f"--until={window.until.isoformat()}",
    ]
    if not include_merges:
        cmd.append("--no-merges")
    result = subprocess.run(cmd, capture_output=True, check=False)
    return _parse_log_stream(result.stdout)


def iter_commits(
    repo: Path, window: Window, include_merges: bool = False
) -> Iterator[Commit]:
    commits = _run_git_log(repo, window, include_merges=include_merges)
    commits.sort(key=lambda c: c.ts)
    yield from commits


def coalesce_identities(commits: list[Commit]) -> dict[str, str]:
    email_names: dict[str, Counter] = {}
    for c in commits:
        email = c.author_email.lower()
        if email not in email_names:
            email_names[email] = Counter()
        email_names[email][c.author_name] += 1

    return {
        email: name_counter.most_common(1)[0][0]
        for email, name_counter in email_names.items()
    }
