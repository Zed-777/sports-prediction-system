import generate_fast_reports


def test_pct_palette_mapping():
    # Create uninitialized instance to avoid heavy init side-effects
    gen = generate_fast_reports.SingleMatchGenerator.__new__(
        generate_fast_reports.SingleMatchGenerator
    )
    # Provide controlled settings
    gen._settings = {
        "constants": {
            "color_thresholds": [25, 50, 75],
            "color_palette": ["#R", "#O", "#Y", "#G"],
        }
    }

    assert gen.pct_to_color(10) == "#R"
    assert gen.pct_to_color(25) == "#O"  # boundary: 25 -> second bucket
    assert gen.pct_to_color(30) == "#O"
    assert gen.pct_to_color(60) == "#Y"
    assert gen.pct_to_color(90) == "#G"
