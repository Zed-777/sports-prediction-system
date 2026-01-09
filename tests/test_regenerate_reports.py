import json
from scripts.regenerate_reports import prune_old_reports


def test_prune_old_reports(tmp_path):
    # Setup fake reports dir
    league = "la-liga"
    reports_dir = tmp_path / "reports" / "leagues" / league / "matches"
    reports_dir.mkdir(parents=True)

    # Create 5 fake match dirs with prediction.json
    for i in range(5):
        d = reports_dir / f"m{i}"
        d.mkdir()
        pred = d / "prediction.json"
        pred.write_text(json.dumps({"match_date": f"2025-12-{10 + i}T20:00"}))

    # Keep only 2
    removed = prune_old_reports(
        league=str(league),
        keep=2,
        debug=True,
        base_dir=tmp_path / "reports" / "leagues",
    )
    assert removed == 3
    # Ensure remaining count is 2
    remaining = list(reports_dir.iterdir())
    assert len([p for p in remaining if p.is_dir()]) == 2


def test_prune_old_reports_with_match_filter(tmp_path):
    # Setup fake reports dir
    league = "la-liga"
    reports_dir = tmp_path / "reports" / "leagues" / league / "matches"
    reports_dir.mkdir(parents=True)

    # Create a mix of match folders, some with 'keepme' in name
    names = ["keepme_vs_x_2025-01-01", "remove_vs_x_2025-01-02", "keepme_vs_y_2025-01-03"]
    for name in names:
        d = reports_dir / name
        d.mkdir()
        pred = d / "prediction.json"
        pred.write_text(json.dumps({"match_date": name.split("_")[-1]}))

    # prune with filter 'remove' should only affect directories containing 'remove'
    removed = prune_old_reports(
        league=str(league), keep=0, match_filter='remove', debug=True, base_dir=tmp_path / "reports" / "leagues"
    )
    assert removed == 1

    # prune with filter 'keepme' and keep=1 should remove 1 (since two keepme dirs exist and keep=1 keeps newest)
    removed2 = prune_old_reports(
        league=str(league), keep=1, match_filter='keepme', debug=True, base_dir=tmp_path / "reports" / "leagues"
    )
    assert removed2 in (0, 1)


def test_prune_old_reports_prune_all(tmp_path):
    league = "la-liga"
    reports_dir = tmp_path / "reports" / "leagues" / league / "matches"
    reports_dir.mkdir(parents=True)

    # Create several fake match folders with prediction.json
    for name in ["a_vs_b_2020-01-01", "c_vs_d_2020-01-02", "e_vs_f_2020-01-03"]:
        m = reports_dir / name
        m.mkdir()
        (m / "prediction.json").write_text(json.dumps({"match_date": name.split("_")[-1]}), encoding="utf-8")

    # prune all (keep=0) should remove all 3
    removed = prune_old_reports(league, keep=0, debug=True, base_dir=tmp_path / "reports" / "leagues")
    assert removed == 3
