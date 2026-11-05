"""BIS WS_CBPOL event-path normalisation."""
from country_primer.bis_policy import BIS_REF_AREA, glitch_note, to_event_path


def test_event_path_keeps_confirmed_changes_and_as_of_row():
    daily = [
        ("2026-06-22", 6.25), ("2026-06-23", 6.25),
        ("2026-07-01", 6.0), ("2026-07-02", 6.0),
        ("2026-07-22", 5.75), ("2026-07-23", 5.75),
        ("2026-10-21", 5.75),
    ]
    events, glitches = to_event_path(daily)
    assert events == [
        ("2026-06-22", 6.25),
        ("2026-07-01", 6.0),
        ("2026-07-22", 5.75),
        ("2026-10-21", 5.75),
    ]
    assert glitches == []


def test_single_observation_reversal_is_excluded_and_disclosed():
    # Mirrors the BIS Hungary feed: one day at 6.00% between 6.25% prints.
    daily = [
        ("2026-06-23", 6.25), ("2026-06-24", 6.0), ("2026-06-25", 6.25),
        ("2026-06-26", 6.25), ("2026-07-01", 6.0), ("2026-07-02", 6.0),
    ]
    events, glitches = to_event_path(daily)
    assert events == [("2026-06-23", 6.25), ("2026-07-01", 6.0), ("2026-07-02", 6.0)]
    assert glitches == [("2026-06-24", 6.0)]
    assert "2026-06-24" in glitch_note(glitches)


def test_latest_unconfirmed_change_is_accepted():
    daily = [("2026-09-23", 1.0), ("2026-09-24", 1.25)]
    events, glitches = to_event_path(daily)
    assert events[-1] == ("2026-09-24", 1.25)
    assert glitches == []


def test_uncovered_scopes_are_not_mapped():
    for code in ("TW", "KZ", "UZ", "EG", "NG"):
        assert code not in BIS_REF_AREA
    assert BIS_REF_AREA["EA"] == "XM"
    assert BIS_REF_AREA["UK"] == "GB"
