Stage 7 remediation #1 passed.

Heartbeat false-positive is fixed.
Risk engine protection is working.
Ledger attribution is working.

However Stage 7 requires one successful controlled VST execution path, not only blocked execution.

Perform minimal remediation only:

Problem:
Position sizing generated:
$50,005

Maximum allowed:
$50,000

Required:
Ensure final order quantity is capped below the configured maximum position limit before broker submission.

Rules:
- Architecture frozen.
- Do not disable risk checks.
- Do not increase limits.
- Do not bypass EnterpriseRiskManager.
- Only fix sizing boundary enforcement.

After fix run:

python run_trading_system.py --mode production --auto-detect --symbol XLMUSDT

Collect:

1. Order execution log.
2. Final approved quantity/notional.
3. BingX VST response.
4. execution_truth_ledger.jsonl entry.
5. real_sends_to_exchange.
6. ledger_verify_ok.
7. Any errors.

Pass condition:

Signal reaches broker adapter,
order is accepted in VST,
ledger records execution,
real_sends_to_exchange remains controlled.

Do not proceed to Stage 8 until Stage 7 is fully approved.