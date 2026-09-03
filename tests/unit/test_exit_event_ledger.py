from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import pytest

from infrastructure.observability.exit_event_ledger import ExitEventLedger,LedgerValidationError


def event(event_id="e1",event_type="POSITION_OBSERVED",seconds=0):
    return {"schema_version":1,"event_id":event_id,"event_type":event_type,
      "event_time_utc":f"2026-09-03T00:00:{seconds:02d}+00:00","run_id":"r1","evaluation_id":"v1",
      "position_key":"BTCUSDT:LONG:1","symbol":"BTCUSDT","side":"LONG","quantity":1.0,
      "entry_price":100.0,"current_price":101.0,"price_source":"MARK","configured_leverage":5.0,
      "requested_leverage":5.0,"exchange_leverage":5.0,"roe_pct":5.0,"peak_price":101.0,
      "peak_roe_pct":5.0,"manager_state_before":{},"manager_state_after":{},"error":None}


def test_append_and_deterministic_validation(tmp_path):
    ledger=ExitEventLedger(tmp_path);path=ledger.append(event());a=ledger.validate_file(path);b=ledger.validate_file(path)
    assert a==b and a["events"]==1 and len(a["sha256"])==64


def test_duplicate_corruption_and_timestamp_order_fail(tmp_path):
    ledger=ExitEventLedger(tmp_path);path=ledger.append(event())
    with pytest.raises(LedgerValidationError,match="duplicate"):ledger.append(event())
    path.write_text(path.read_text()+"not-json\n")
    with pytest.raises(LedgerValidationError,match="invalid JSON"):ledger.validate_file(path)
    path.write_text(json.dumps(event("e2",seconds=2))+"\n"+json.dumps(event("e3",seconds=1))+"\n")
    with pytest.raises(LedgerValidationError,match="out of order"):ledger.validate_file(path)


def test_required_fields_sensitive_keys_and_nonfinite_fail():
    broken=event();del broken["exchange_leverage"]
    with pytest.raises(LedgerValidationError,match="missing common"):ExitEventLedger.validate_event(broken,set())
    broken=event();broken["metadata"]={"api_key":"bad"}
    with pytest.raises(LedgerValidationError,match="sensitive"):ExitEventLedger.validate_event(broken,set())
    broken=event();broken["roe_pct"]=float("nan")
    with pytest.raises(LedgerValidationError,match="finite"):ExitEventLedger.validate_event(broken,set())


def test_causal_reference_and_state_commit_invariant(tmp_path):
    ledger=ExitEventLedger(tmp_path)
    ledger.append(event("request","STOP_REPLACE_REQUESTED",0)|{"requested_stop_price":99.0,"attempt":1})
    ledger.append(event("response","STOP_REPLACE_RESPONDED",1)|{"causal_event_id":"request","accepted":True})
    ledger.append(event("verify","STOP_VISIBILITY_VERIFIED",2)|{"causal_event_id":"response","visible_stop_price":99.0})
    path=ledger.append(event("commit","STATE_COMMITTED",3)|{"causal_event_id":"verify","causal_event_type":"STOP_VISIBILITY_VERIFIED"})
    assert ledger.validate_file(path)["events"]==4


def test_invalid_causal_reference_is_rejected():
    response=event("response","STOP_REPLACE_RESPONDED")|{"causal_event_id":"request","accepted":True}
    with pytest.raises(LedgerValidationError,match="earlier event"):ExitEventLedger.validate_event(response,set())
    committed=event("commit","STATE_COMMITTED")|{"causal_event_id":"verify","causal_event_type":"STOP_VISIBILITY_FAILED"}
    with pytest.raises(LedgerValidationError,match="verified visibility"):ExitEventLedger.validate_event(committed,{"verify"})


def test_concurrent_append_preserves_unique_events(tmp_path):
    ledger=ExitEventLedger(tmp_path)
    with ThreadPoolExecutor(max_workers=8) as pool:
        paths=list(pool.map(lambda i:ledger.append(event(f"e{i}")),range(20)))
    assert len(set(paths))==1 and ledger.validate_file(paths[0])["events"]==20
