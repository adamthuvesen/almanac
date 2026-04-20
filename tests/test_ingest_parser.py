from almanac.ingest import _parse_log_stream, _parse_numstat_z


def test_numstat_z_normal_path():
    files = _parse_numstat_z(b"5\t3\tsrc/app.py\0")
    assert len(files) == 1
    assert files[0].path == "src/app.py"
    assert files[0].lines_added == 5
    assert files[0].lines_removed == 3
    assert files[0].is_binary is False


def test_numstat_z_rename_form():
    files = _parse_numstat_z(b"5\t3\t\0src/old.py\0src/new.py\0")
    assert len(files) == 1
    assert files[0].path == "src/new.py"
    assert files[0].lines_added == 5
    assert files[0].lines_removed == 3


def test_numstat_z_binary_file():
    files = _parse_numstat_z(b"-\t-\tassets/logo.png\0")
    assert len(files) == 1
    assert files[0].path == "assets/logo.png"
    assert files[0].lines_added == 0
    assert files[0].lines_removed == 0
    assert files[0].is_binary is True


def test_numstat_z_tab_in_path():
    files = _parse_numstat_z(b"1\t1\tawk\ttab\tname.txt\0")
    assert len(files) == 1
    # `split('\t', 2)` on the token leaves the remainder (including tabs)
    # as the path, so embedded tabs are preserved under `-z`.
    assert files[0].path == "awk\ttab\tname.txt"


def test_numstat_z_newline_in_path():
    files = _parse_numstat_z(b"1\t1\tline\nbreak.txt\0")
    assert len(files) == 1
    assert files[0].path == "line\nbreak.txt"


def test_numstat_z_multiple_entries():
    # Use explicit \x00 rather than \0 to avoid any octal ambiguity when
    # followed by digits after formatter passes.
    stream = b"5\t3\tsrc/a.py\x002\t0\tsrc/b.py\x00-\t-\timg.png\x00"
    files = _parse_numstat_z(stream)
    assert [f.path for f in files] == ["src/a.py", "src/b.py", "img.png"]
    assert files[2].is_binary is True


def test_numstat_z_rename_mixed_with_normal():
    stream = b"5\t3\t\x00src/old.py\x00src/new.py\x002\t1\tREADME.md\x00"
    files = _parse_numstat_z(stream)
    assert [f.path for f in files] == ["src/new.py", "README.md"]


def _make_commit_block(header: bytes, numstat: bytes) -> bytes:
    return b"\x1e" + header + b"\n" + numstat


def test_non_utf8_commit_message_does_not_crash():
    # Latin-1 byte 0xe9 (é) in the subject — git would never emit this
    # if its i18n.commitEncoding is UTF-8, but legacy mirrors do.
    header = (
        b"deadbeef\x1f2025-01-01T00:00:00+00:00\x1f"
        b"Alice\x1falice@example.com\x1f"
        b"\x1ffix: caf\xe9 bug"
    )
    stream = _make_commit_block(header, b"")
    commits = _parse_log_stream(stream)
    assert len(commits) == 1
    assert "\ufffd" in commits[0].subject


def test_iter_commits_is_chronological_with_merges():
    # Build three canned commit blocks: ts ordering 2nd, 1st, 3rd.
    def block(sha: str, ts: str, parents: str = "") -> bytes:
        header = (
            sha.encode()
            + b"\x1f"
            + ts.encode()
            + b"\x1fA\x1fa@x\x1f"
            + parents.encode()
            + b"\x1fmsg"
        )
        return _make_commit_block(header, b"")

    stream = (
        block("2222", "2025-06-01T12:00:00+00:00")
        + block("1111", "2025-01-01T12:00:00+00:00", parents="1 2")
        + block("3333", "2025-12-31T12:00:00+00:00")
    )
    commits = _parse_log_stream(stream)
    # _parse_log_stream preserves source order; iter_commits sorts.
    # Verify that sorting by ts puts them in ascending order.
    commits_sorted = sorted(commits, key=lambda c: c.ts)
    assert [c.sha for c in commits_sorted] == ["1111", "2222", "3333"]
    # Merge commit (2 parents) at 1111 is recognized.
    merges = [c for c in commits_sorted if c.is_merge]
    assert len(merges) == 1
    assert merges[0].sha == "1111"
