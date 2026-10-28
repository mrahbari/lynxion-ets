#!/usr/bin/env python3
"""Outcome-blind qualification of explicit vendor book/trade inputs; no network."""
import argparse
import collections
import csv
from decimal import Decimal, InvalidOperation
import gzip
import hashlib
import json
from pathlib import Path

MINUTE = 60_000_000
FIVE = 5 * MINUTE
MAX_QUOTE_AGE = 1_000_000
VERSION = 'OBSERVED_TOP5_MTF_V1'


def numeric(value, *, zero=False):
    value = Decimal(value)
    if not value.is_finite() or value < 0 or (value == 0 and not zero):
        raise ValueError('invalid finite market value')
    return value


def rows(path, required):
    with gzip.open(path, 'rt', newline='') as source:
        reader = csv.DictReader(source)
        if not required.issubset(reader.fieldnames or []):
            raise ValueError('source schema does not satisfy declared contract')
        yield from enumerate(reader, 2)


def book_features(path, symbol='BTCUSDT'):
    required = {'exchange', 'symbol', 'timestamp', 'local_timestamp'}
    required |= {f'{side}[{i}].{field}' for side in ('bids', 'asks') for i in range(5) for field in ('price', 'amount')}
    minutes = {}
    stats = collections.Counter()
    previous_local = None
    max_gap = 0
    first = last = None
    for line, row in rows(path, required):
        stats['raw_rows'] += 1
        try:
            if row['exchange'] != 'binance-futures' or row['symbol'] != symbol:
                raise ValueError('source identity mismatch')
            event, local = int(row['timestamp']), int(row['local_timestamp'])
            if event <= 0 or local <= 0 or (previous_local is not None and local < previous_local):
                raise ValueError('invalid or out-of-order receive clock')
            if previous_local is not None:
                max_gap = max(max_gap, local - previous_local)
            previous_local = local
            first = local if first is None else first
            last = local
            available = max(event, local)
            levels = {side: [(numeric(row[f'{side}[{i}].price']), numeric(row[f'{side}[{i}].amount'], zero=True)) for i in range(5)] for side in ('bids', 'asks')}
            bid_prices = [p for p, _ in levels['bids']]
            ask_prices = [p for p, _ in levels['asks']]
            if any(bid_prices[i] <= bid_prices[i+1] or ask_prices[i] >= ask_prices[i+1] for i in range(4)) or bid_prices[0] >= ask_prices[0]:
                raise ValueError('unordered/crossed price levels')
            bid_amount = sum(q for _, q in levels['bids'])
            ask_amount = sum(q for _, q in levels['asks'])
            if bid_amount + ask_amount <= 0:
                raise ValueError('empty book cannot supply OBI')
            close = (available // MINUTE + 1) * MINUTE
            quote = {'source_row': line, 'exchange_timestamp_us': event,
                     'receipt_timestamp_us': local, 'available_at_us': available,
                     'best_bid': str(bid_prices[0]), 'best_ask': str(ask_prices[0]),
                     'best_bid_amount': str(levels['bids'][0][1]), 'best_ask_amount': str(levels['asks'][0][1]),
                     'obi_ratio': str((bid_amount - ask_amount) / (bid_amount + ask_amount))}
            if close not in minutes or available >= minutes[close]['available_at_us']:
                minutes[close] = quote
        except (KeyError, ValueError, InvalidOperation):
            stats['invalid_rows'] += 1
    stats.update({'first_receipt_us': first or 0, 'last_receipt_us': last or 0,
                  'max_receive_gap_us': max_gap, 'observed_minute_buckets': len(minutes)})
    return minutes, dict(stats)


def trade_features(path, symbol='BTCUSDT'):
    required = {'exchange', 'symbol', 'timestamp', 'local_timestamp', 'id', 'side', 'price', 'amount'}
    buckets = {}
    late = collections.Counter()
    stats = collections.Counter()
    seen = {}
    previous_local = None
    first = last = None
    for line, row in rows(path, required):
        stats['raw_rows'] += 1
        try:
            if row['exchange'] != 'binance-futures' or row['symbol'] != symbol or row['side'] not in ('buy', 'sell') or not row['id']:
                raise ValueError('trade identity/side missing')
            event, local = int(row['timestamp']), int(row['local_timestamp'])
            if event <= 0 or local <= 0 or (previous_local is not None and local < previous_local):
                raise ValueError('invalid or out-of-order receive clock')
            previous_local = local
            first = local if first is None else first
            last = local
            amount = numeric(row['amount'])
            price = numeric(row['price'])
            identity = row['id']
            fingerprint = (event, row['side'], price, amount)
            if identity in seen:
                if seen[identity] != fingerprint:
                    raise ValueError('conflicting duplicate trade')
                stats['exact_duplicate_trades'] += 1
                continue
            seen[identity] = fingerprint
            close = (event // FIVE + 1) * FIVE
            if max(event, local) > close:
                late[close] += 1
                stats['late_trades'] += 1
                continue
            bucket = buckets.setdefault(close, {'delta': Decimal(0), 'trade_count': 0})
            bucket['delta'] += amount if row['side'] == 'buy' else -amount
            bucket['trade_count'] += 1
        except (KeyError, ValueError, InvalidOperation):
            stats['invalid_rows'] += 1
    stats.update({'first_receipt_us': first or 0, 'last_receipt_us': last or 0,
                  'observed_five_minute_buckets': len(buckets), 'late_five_minute_buckets': len(late)})
    return buckets, late, dict(stats)


def combine(books, trades, late, start_us, stop_us, symbol='BTCUSDT'):
    for close in range(start_us + MINUTE, stop_us + 1, MINUTE):
        record = {'version': VERSION, 'symbol': symbol, 'available_at_us': close,
                  'source_class': 'DERIVED_FROM_VENDOR_NORMALIZED_OBSERVED',
                  'quote_status': 'UNAVAILABLE', 'flow_status': 'NOT_A_FIVE_MINUTE_CLOSE'}
        quote = books.get(close)
        if quote and 0 <= close - quote['available_at_us'] <= MAX_QUOTE_AGE:
            record.update(quote_status='OBSERVED_ASOF', quote={k:v for k,v in quote.items() if k!='obi_ratio'})
        if close % FIVE == 0:
            if record['quote_status'] != 'OBSERVED_ASOF':
                record['flow_status'] = 'MISSING_FRESH_BOOK'
            elif late.get(close):
                record['flow_status'] = 'LATE_TRADES_EXCLUDED'
            elif close not in trades:
                record['flow_status'] = 'TRADE_STREAM_UNAVAILABLE'
            else:
                record.update(flow_status='OBSERVED_ASOF', obi_ratio=quote['obi_ratio'],
                              cvd=str(trades[close]['delta']), trade_count=trades[close]['trade_count'])
        yield record


def qualify(root, output):
    manifest = json.loads((root/'acquisition_manifest.json').read_text())
    sources = {}
    for item in manifest['raw_files']:
        path = root/'raw'/item['filename']
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if item.get('acquisition') != 'COMPLETE_BYTES_ONLY_NOT_QUALIFIED' or digest != item['sha256']:
            raise ValueError('incomplete acquisition or raw SHA mismatch')
        sources[item['kind']] = path
    if set(sources) != {'book_snapshot_5', 'trades'}:
        raise ValueError('explicit book and trade inputs required')
    books, book_stats = book_features(sources['book_snapshot_5'])
    trades, late, trade_stats = trade_features(sources['trades'])
    start_us = 1704067200 * 1_000_000
    output.mkdir(parents=True, exist_ok=True)
    records = list(combine(books, trades, late, start_us, start_us + 24*60*MINUTE))
    features = ''.join(json.dumps(row, sort_keys=True, separators=(',', ':'))+'\n' for row in records)
    with (output/'observed_mtf.jsonl').open('x') as f:
        f.write(features)
    report = {'contract_commit': '7eab7ae', 'version': VERSION, 'outcomes_opened': False,
              'full_baseline_admitted': False, 'book': book_stats, 'trades': trade_stats,
              'minute_rows': len(records), 'quote_status_counts': dict(collections.Counter(r['quote_status'] for r in records)),
              'flow_status_counts': dict(collections.Counter(r['flow_status'] for r in records)),
              'feature_sha256': hashlib.sha256(features.encode()).hexdigest(),
              'raw_sha256': {i['kind']:i['sha256'] for i in manifest['raw_files']},
              'limits': ['Vendor-normalized top-five, not raw exchange depth/queue',
                         'CSV disconnect markers absent; stale/gap masks do not establish continuous capture',
                         'One selected development day, not independent OOS or market-wide cohort',
                         'Actual composed strategy/cost/funding/execution acceptance still required']}
    report['integrity_status'] = 'PASS_STRUCTURAL_ONLY' if not book_stats.get('invalid_rows') and not trade_stats.get('invalid_rows') else 'FAIL_SOURCE_ROWS'
    with (output/'qualification_report.json').open('x') as f:
        json.dump(report,f,indent=2);f.write('\n')
    return report


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args=parser.parse_args()
    result=qualify(args.data_root,args.output_dir)
    print(json.dumps(result,sort_keys=True))
    raise SystemExit(0 if result['integrity_status']=='PASS_STRUCTURAL_ONLY' else 2)
