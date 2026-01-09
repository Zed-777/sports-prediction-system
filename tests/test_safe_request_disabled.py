from app.utils.http import safe_request_get
from app.utils.state_sync import set_disabled_flag
import time


def test_safe_request_get_respects_disabled_flag():
    # set disabled for injuries-like path
    set_disabled_flag("/v3/injuries", time.time() + 5)
    # sanity check: the flag is set
    from app.utils.state_sync import get_disabled_flag

    assert get_disabled_flag("/v3/injuries") is not None
    resp = safe_request_get(
        "https://api-football-v1.p.rapidapi.com/v3/injuries",
        headers={},
        params={"team": 61},
    )
    assert resp.status_code == 429
