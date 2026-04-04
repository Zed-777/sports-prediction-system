from pathlib import Path

from app.utils import state_sync


def test_list_and_clear_file_flags(tmp_path: Path):
    # Ensure clean starting state
    state_sync.clear_all_disabled_flags()
    host = "listclear.example"
    path = "/v1/x"
    state_sync.set_disabled_flag(host, path, 9999999999)
    flags = state_sync.list_disabled_flags()
    assert host in flags
    assert path in flags[host]
    # Clear it
    state_sync.clear_disabled_flag(host, path)
    flags = state_sync.list_disabled_flags()
    assert host not in flags or path not in flags.get(host, {})

    # Clear all
    state_sync.set_disabled_flag(host, path, 9999999999)
    state_sync.clear_all_disabled_flags()
    flags = state_sync.list_disabled_flags()
    assert flags == {}
