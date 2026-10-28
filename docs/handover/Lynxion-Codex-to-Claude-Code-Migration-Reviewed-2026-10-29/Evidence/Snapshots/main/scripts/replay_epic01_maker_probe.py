#!/usr/bin/env python3
"""Fixed actual-tape maker mechanism probe, not strategy economics or broker fills."""
import argparse
import csv
from datetime import datetime, timedelta, timezone
import gzip
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from infrastructure.backtest.maker_execution import MakerQuote, MakerTrade, PendingMakerOrder

EPOCH=datetime(1970,1,1,tzinfo=timezone.utc)
DECISION_US=1704067500*1_000_000  # First completed five-minute boundary, not result-selected.


def clock(us):
    return EPOCH+timedelta(microseconds=us)


def replay(root):
    manifest=json.loads((root/'acquisition_manifest.json').read_text())
    paths={}
    for item in manifest['raw_files']:
        path=root/'raw'/item['filename']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError('raw input hash changed')
        paths[item['kind']]=path
    decision_quote=arrival_quote=None
    arrival_us=DECISION_US+100_000
    with gzip.open(paths['book_snapshot_5'],'rt',newline='') as f:
        for number,row in enumerate(csv.DictReader(f),2):
            local=int(row['local_timestamp'])
            if local>arrival_us:break
            available=max(int(row['timestamp']),local)
            if available>arrival_us:continue
            current=MakerQuote(row['symbol'],clock(available),row['bids[0].price'],row['asks[0].price'],
                               row['bids[0].amount'],row['asks[0].amount'],f'book:{number}')
            if available<=DECISION_US and (decision_quote is None or current.available_at>=decision_quote.available_at):
                decision_quote=current
            if arrival_quote is None or current.available_at>=arrival_quote.available_at:arrival_quote=current
    if decision_quote is None or arrival_quote is None:
        raise ValueError('actual decision/arrival quote unavailable')
    if clock(DECISION_US)-decision_quote.available_at>timedelta(seconds=1):
        raise ValueError('stale decision quote')
    orders=[PendingMakerOrder(order_id=f'probe-{side}',symbol='BTCUSDT',side=side,
                quantity='0.001',limit_price=decision_quote.bid if side=='BUY' else decision_quote.ask,
                decision_at=clock(DECISION_US),quote=arrival_quote) for side in ('BUY','SELL')]
    with gzip.open(paths['trades'],'rt',newline='') as f:
        for row in csv.DictReader(f):
            local=int(row['local_timestamp'])
            if local>arrival_us+60_000_000:break
            available=max(int(row['timestamp']),local)
            if available<=arrival_us:continue
            event=MakerTrade(row['symbol'],clock(available),row['price'],row['amount'],row['side'].upper(),row['id'])
            for order in orders:order.on_trade(event)
    for order in orders:
        if order.active:order.expire(order.expires_at)
    return {'classification':'ACTUAL_TAPE_MODELED_EXECUTION_PROBE_ONLY',
            'strategy_economics_run':False,'broker_orders':False,
            'simultaneous_portfolio':False,'contract_commit':'7eab7ae',
            'decision_at':clock(DECISION_US).isoformat(),'quantity_per_independent_probe':'0.001',
            'arrival_quote_source':arrival_quote.source_id,
            'orders':[{'side':o.side,'status':o.status,'filled_quantity':str(o.quantity-o.remaining),
                       'remaining':str(o.remaining),'modeled_fees':str(sum(f.fee for f in o.fills)),
                       'fills':[{'time':f.available_at.isoformat(),'price':str(f.price),'quantity':str(f.quantity),
                                 'source_trade_id':f.source_trade_id} for f in o.fills]} for o in orders],
            'limits':['Two separate directional execution probes, not a trading strategy',
                      'Queue/latency/participation are declared assumptions',
                      'No PnL, expectancy, OOS, funding or full baseline admission']}


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--data-root',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();result=replay(args.data_root)
    with args.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result,sort_keys=True))
