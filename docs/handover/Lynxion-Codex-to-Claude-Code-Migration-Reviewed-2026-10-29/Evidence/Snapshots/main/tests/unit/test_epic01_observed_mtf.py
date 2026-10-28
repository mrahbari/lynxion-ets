"""Causal observed-input qualification; synthetic rows, no future return labels."""
import csv
import gzip
import runpy
from pathlib import Path
from decimal import Decimal

module=runpy.run_path(str(Path(__file__).resolve().parents[2]/'scripts/qualify_epic01_mtf_data.py'))
M=module['MINUTE']; FIVE=module['FIVE']


def write(path,rows):
    with gzip.open(path,'wt',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)


def book(local):
    row=dict(exchange='binance-futures',symbol='BTCUSDT',timestamp=str(local-1),local_timestamp=str(local))
    for side in ['bids','asks']:
        for i in range(5):
            row[f'{side}[{i}].price']=str(100-i if side=='bids' else 101+i)
            row[f'{side}[{i}].amount']='2' if side=='bids' else '1'
    return row


def test_quote_and_top5_obi_are_available_only_after_actual_receive(tmp_path):
    path=tmp_path/'book.gz';write(path,[book(FIVE-100),book(FIVE+100)])
    books,stats=module['book_features'](path)
    rows=list(module['combine'](books,{FIVE:{'delta':Decimal(2),'trade_count':1}}, {},0,FIVE))
    last=rows[-1]
    assert last['quote']['receipt_timestamp_us']==FIVE-100
    assert last['obi_ratio']==str(Decimal(1)/3)
    assert last['cvd']=='2' and stats.get('invalid_rows',0)==0


def test_stale_or_missing_quotes_are_never_forward_filled_or_defaulted(tmp_path):
    path=tmp_path/'book.gz';write(path,[book(M+1)])
    books,_=module['book_features'](path)
    rows=list(module['combine'](books,{}, {},0,3*M))
    assert all(r['quote_status']=='UNAVAILABLE' for r in rows)
    assert all('quote' not in r for r in rows)


def test_late_and_duplicate_trades_cannot_manufacture_cvd(tmp_path):
    base=dict(exchange='binance-futures',symbol='BTCUSDT',timestamp='1',local_timestamp='2',id='1',side='buy',price='100',amount='3')
    late=dict(base,timestamp=str(FIVE-1),local_timestamp=str(FIVE+1),id='2',side='sell',amount='4')
    path=tmp_path/'trades.gz';write(path,[base,base,late])
    trades,late_rows,stats=module['trade_features'](path)
    assert trades[FIVE]['delta']==3 and trades[FIVE]['trade_count']==1
    assert stats['exact_duplicate_trades']==1 and late_rows[FIVE]==1
    quote={'source_row':2,'exchange_timestamp_us':FIVE-2,'receipt_timestamp_us':FIVE-1,
           'available_at_us':FIVE-1,'best_bid':'100','best_ask':'101','obi_ratio':'0.2'}
    row=list(module['combine']({FIVE:quote},trades,late_rows,0,FIVE))[-1]
    assert row['flow_status']=='LATE_TRADES_EXCLUDED' and 'cvd' not in row


def test_missing_trade_bucket_is_not_a_zero_delta():
    quote={'source_row':2,'available_at_us':FIVE-1,'obi_ratio':'0.2'}
    row=list(module['combine']({FIVE:quote},{},{},0,FIVE))[-1]
    assert row['flow_status']=='TRADE_STREAM_UNAVAILABLE' and 'cvd' not in row


def test_bad_book_identity_and_crossed_levels_are_reported_not_synthetic(tmp_path):
    bad=book(M-1);bad['asks[0].price']='99'
    wrong=dict(book(2*M-1),symbol='ETHUSDT')
    path=tmp_path/'book.gz';write(path,[bad,wrong])
    books,stats=module['book_features'](path)
    assert books=={} and stats['invalid_rows']==2
