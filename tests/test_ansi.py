from almanac.renderer.ansi import PALETTE, hbar, sparkline


def test_palette_has_named_colors():
    assert set(PALETTE.keys()) == {
        "ink",
        "cream",
        "rust",
        "olive",
        "sky",
        "plum",
        "mist",
    }
    for name, rgb in PALETTE.items():
        assert len(rgb) == 3
        assert all(0 <= c <= 255 for c in rgb)


def test_hbar_zero_max_returns_blank_width():
    out = hbar(5, 0, 10)
    assert len(out) == 10
    assert out.strip() == ""


def test_hbar_zero_value_returns_blank_width():
    out = hbar(0, 100, 10)
    assert len(out) == 10
    assert out.strip() == ""


def test_hbar_zero_width_returns_empty():
    assert hbar(5, 10, 0) == ""


def test_hbar_full_value_fills_width():
    out = hbar(100, 100, 8)
    assert out.startswith("█" * 8)
    assert len(out) >= 8


def test_hbar_partial_fills_proportionally():
    out = hbar(50, 100, 10)
    # ~5 full blocks expected
    full_count = out.count("█")
    assert 4 <= full_count <= 6
    assert len(out) == 10


def test_sparkline_zeros_returns_flat_line():
    out = sparkline([0, 0, 0, 0], 4)
    assert len(out) == 4
    # All same character (lowest ramp)
    assert len(set(out)) == 1


def test_sparkline_respects_peak():
    out = sparkline([1, 2, 4, 8], 4)
    assert len(out) == 4
    # Last char is the tallest (peak)
    assert out[-1] == "█"


def test_sparkline_empty_returns_empty():
    assert sparkline([], 10) == ""
