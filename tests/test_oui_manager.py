"""Deterministic coverage of the current cache API, including older disk formats."""
import json
from unittest.mock import Mock

import pytest
from shadowvendor.core.oui_manager import OUIManager

MAC = "E0:FE:ED:00:00:01"
OUI = "E0:FE:ED"


def test_legacy_failed_list_is_expired(monkeypatch):
    manager = OUIManager()
    manager.failed_lookups_file.write_text(json.dumps([OUI]))
    response = Mock(return_value=Mock(status_code=200, text="Recovered"))
    monkeypatch.setattr("requests.get", response)
    assert OUIManager().get_vendor(MAC) == "Recovered"
    assert response.call_count == 1
    assert MAC not in response.call_args.args[0]
    assert response.call_args.args[0].endswith(OUI)


def test_recent_negative_cache_survives_restart_and_expires(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr("shadowvendor.core.oui_manager.time.time", lambda: now[0])
    response = Mock(return_value=Mock(status_code=404))
    monkeypatch.setattr("requests.get", response)
    first = OUIManager()
    assert first.get_vendor(MAC) is None
    second = OUIManager()
    assert second.get_vendor(MAC) is None
    assert response.call_count == 1
    assert json.loads(first.failed_lookups_file.read_text()) == {OUI: 1000.0}
    now[0] += second.FAILED_LOOKUP_TTL
    response.return_value = Mock(status_code=200, text="Recovered")
    assert second.get_vendor(MAC) == "Recovered"
    assert response.call_count == 2


def test_positive_cache_wins_over_recent_failure(monkeypatch):
    monkeypatch.setattr("requests.get", Mock(return_value=Mock(status_code=404)))
    first = OUIManager()
    assert first.get_vendor(MAC) is None
    first.cache_file.write_text(json.dumps({OUI.lower(): "Added Vendor"}))
    assert OUIManager(offline=True).get_vendor(MAC) == "Added Vendor"


def test_offline_miss_never_writes_negative_cache():
    manager = OUIManager(offline=True)
    for _ in range(10):
        assert manager.get_vendor(MAC) is None
    assert not manager.failed_lookups_file.exists()
    assert not manager.failed_lookups


def test_cache_key_spellings_are_normalized():
    manager = OUIManager(offline=True)
    manager.cache_file.write_text(json.dumps({"e0-feed": "Normalized"}))
    assert OUIManager(offline=True).get_vendor(MAC) == "Normalized"


def test_batch_progress_is_optional_and_cache_avoids_extra_requests(monkeypatch):
    response = Mock(return_value=Mock(status_code=200, text="Mock Vendor"))
    monkeypatch.setattr("requests.get", response)
    manager = OUIManager()
    expected = {MAC: "Mock Vendor", "E0:FE:ED:00:00:02": "Mock Vendor"}
    assert manager.batch_lookup_vendors(list(expected)) == expected
    assert response.call_count == 1
    progress = Mock()
    assert manager.batch_lookup_vendors(list(expected), progress) == expected
    progress.add_task.assert_not_called()
    assert response.call_count == 1


def test_batch_progress_tracks_actual_work(monkeypatch):
    response = Mock(return_value=Mock(status_code=200, text="Mock Vendor"))
    monkeypatch.setattr("requests.get", response)
    progress = Mock()
    progress.add_task.return_value = 0
    assert OUIManager().batch_lookup_vendors([MAC], progress) == {MAC: "Mock Vendor"}
    progress.advance.assert_called_once_with(0)


@pytest.mark.parametrize("content", ['["E0:FE:ED"]', '{"E0:FE:ED":"bad timestamp"}', 'not json'])
def test_bad_or_old_failure_records_do_not_block_cache(content):
    manager = OUIManager(offline=True)
    manager.failed_lookups_file.write_text(content)
    manager.cache_file.write_text(json.dumps({OUI: "Valid"}))
    assert OUIManager(offline=True).get_vendor(MAC) == "Valid"


def test_clear_cache_resets_timed_failures(monkeypatch):
    monkeypatch.setattr("requests.get", Mock(return_value=Mock(status_code=404)))
    manager = OUIManager()
    manager.get_vendor(MAC)
    manager.clear_cache()
    assert manager.failed_lookups == set()
    assert manager._failed_at == {}


def test_invalid_mac_never_reaches_vendor_service():
    manager = OUIManager()
    assert manager.get_vendor("zzzz.zzzz.zzzz") is None
    assert manager.get_vendor("00112233445566") is None


def test_normalization_does_not_discard_extended_cache_records():
    manager = OUIManager(offline=True)
    original = {"e0:fe:ed": "Normalized", "00:1B:C5:00:00/36": "Extended Vendor"}
    manager.cache_file.write_text(json.dumps(original))
    restored = OUIManager(offline=True)
    assert restored.get_vendor(MAC) == "Normalized"
    restored.save_cache()
    persisted = json.loads(restored.cache_file.read_text())
    assert all(persisted[key] == value for key, value in original.items())
