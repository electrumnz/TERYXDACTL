"""Toyota EPS spoof frames (docs/power-steering-wrecker.md)."""

from teryx.eps_toyota import (MAX_ASSIST_KMH, RPM_ID, SPEED_ID, assist_speed_kmh, frames,
                              rpm_frame, speed_frame, toyota_checksum)


def test_frames_match_the_working_retrofit():
    # Exact bytes from the Carloop thread that woke a 2008 Prius EPS.
    assert rpm_frame(1674).hex(" ").upper() == "06 8A 00 19 00 00 92 09"
    assert speed_frame(16.38).hex(" ").upper() == "00 00 00 00 8D 06 66 B5"


def test_checksum_is_last_byte():
    for can_id, data in ((RPM_ID, rpm_frame(900)), (SPEED_ID, speed_frame(37.5))):
        assert data[-1] == toyota_checksum(can_id, data)


def test_low_speed_gets_full_assist():
    assert assist_speed_kmh(0) == MAX_ASSIST_KMH
    assert assist_speed_kmh(None) == MAX_ASSIST_KMH
    assert assist_speed_kmh(40) == 40


def test_silent_when_not_ready():
    assert frames(10, engine_ready=False) == []
    ids = [i for i, _ in frames(10, engine_ready=True)]
    assert ids == [RPM_ID, SPEED_ID]
