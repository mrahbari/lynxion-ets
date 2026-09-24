from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

from infrastructure.orchestrators._auto_detection_execution import (
    IntentClaimStore, _AutoDetectionExecutionMixin,
)


class ClaimOwner(_AutoDetectionExecutionMixin):
    def __init__(self, store=None):
        self._intent_claim_store = store


def test_two_injected_claim_scopes_are_independent():
    intent = SimpleNamespace(intent_id="scoped-fixture")
    first = ClaimOwner(IntentClaimStore())
    second = ClaimOwner(IntentClaimStore())
    assert first._claim_execution_intent(intent)
    assert not first._claim_execution_intent(intent)
    assert second._claim_execution_intent(intent)
    assert not second._claim_execution_intent(intent)


def test_concurrent_claim_has_only_one_winner():
    owner = ClaimOwner(IntentClaimStore())
    intent = SimpleNamespace(intent_id="concurrent-fixture")
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(owner._claim_execution_intent, [intent] * 24))
    assert results.count(True) == 1


def test_live_default_remains_shared_across_owners():
    intent = SimpleNamespace(intent_id="live-default-fixture-unique")
    assert ClaimOwner()._claim_execution_intent(intent)
    assert not ClaimOwner()._claim_execution_intent(intent)


def test_empty_id_is_not_claimed():
    assert not ClaimOwner(IntentClaimStore())._claim_execution_intent(SimpleNamespace(intent_id=None))
