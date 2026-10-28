"""Synthetic mechanism/accounting controls; no claim about real order fills or Edge."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
import pytest
from infrastructure.backtest.maker_execution import MakerQuote, MakerTrade, PendingMakerOrder

T = datetime(2024, 1, 1, tzinfo=timezone.utc)


def quote(**kw):
    data=dict(symbol='BTCUSDT', available_at=T, bid='100', ask='101',
              bid_quantity='5', ask_quantity='5', source_id='book:1')
    data.update(kw)
    return MakerQuote(**data)


def order(**kw):
    data=dict(order_id='o1', symbol='BTCUSDT', side='BUY', quantity='1',
              limit_price='100', decision_at=T, quote=quote())
    data.update(kw)
    return PendingMakerOrder(**data)


def trade(i, *, seconds=1, price='99', quantity='10', side='SELL'):
    return MakerTrade('BTCUSDT', T+timedelta(seconds=seconds), price, quantity, side, str(i))


@pytest.mark.parametrize('side,limit', [('BUY','101'),('SELL','100')])
def test_post_only_cross_at_arrival_rejects_without_fill(side,limit):
    pending=order(side=side,limit_price=limit)
    assert pending.status=='REJECTED_POST_ONLY'
    assert pending.on_trade(trade(1)) is None


@pytest.mark.parametrize('at', [T-timedelta(seconds=2), T+timedelta(seconds=1)])
def test_stale_or_future_arrival_quote_cannot_admit(at):
    with pytest.raises(ValueError):order(quote=quote(available_at=at))


def test_equal_price_consumes_queue_but_cannot_alone_fill():
    pending=order()
    assert pending.on_trade(trade(1,price='100',quantity='7')) is None
    assert pending.queue_ahead==0
    fill=pending.on_trade(trade(2,seconds=2,quantity='10'))
    assert fill.quantity==D('0.1') and fill.price==100
    assert fill.fee==D('0.002')


def test_queue_and_participation_bound_partial_fills_and_remaining():
    pending=order(quantity='0.2')
    first=pending.on_trade(trade(1,quantity='10'))
    assert first.quantity==D('0.05')  # five queue-ahead, one percent of remaining five
    assert pending.status=='PARTIALLY_FILLED'
    second=pending.on_trade(trade(2,seconds=2,quantity='100'))
    assert second.quantity==D('0.15')
    assert pending.remaining==0 and pending.status=='FILLED'
    assert pending.on_trade(trade(3,seconds=3)) is None


def test_arrival_expiry_and_wrong_aggressor_never_fabricate_fill():
    pending=order(quote=quote(bid_quantity=0))
    assert pending.on_trade(trade(1,seconds=.1)) is None
    assert pending.on_trade(trade(2,seconds=1,side='BUY')) is None
    assert pending.on_trade(trade(3,seconds=60.1)) is None
    assert pending.status=='EXPIRED'


def test_duplicate_conflict_and_out_of_order_events_fail_closed():
    pending=order()
    event=trade(1)
    fill=pending.on_trade(event)
    assert pending.on_trade(event) is None
    assert sum(f.quantity for f in pending.fills)==fill.quantity
    with pytest.raises(ValueError):pending.on_trade(replace(event,quantity=D(20)))
    with pytest.raises(ValueError):pending.on_trade(trade(2,seconds=.5))


def test_cancel_keeps_prior_partial_fill_and_denies_retroactive_clock():
    pending=order()
    first=pending.on_trade(trade(1))
    with pytest.raises(ValueError):pending.cancel(T)
    pending.cancel(T+timedelta(seconds=2))
    assert pending.status=='CANCELLED'
    assert pending.on_trade(trade(2,seconds=3)) is None
    assert pending.fills==[first]


def test_sell_side_is_symmetric_without_favorable_price_improvement():
    pending=order(side='SELL',limit_price='101')
    fill=pending.on_trade(trade(1,side='BUY',price='103'))
    assert fill.side=='SELL' and fill.price==D('101') and fill.quantity==D('.05')


@pytest.mark.parametrize('value', ['NaN','Infinity','-1',True])
def test_invalid_market_values_cannot_enter_queue(value):
    with pytest.raises((ValueError, ArithmeticError)):order(quantity=value)


def test_actual_backtester_ledger_uses_limit_maker_fee_and_single_application():
    from infrastructure.backtest.execution_intent import create_execution_intent
    from infrastructure.backtest.realistic_backtester import RealisticBacktester
    pending=order(quote=quote(bid_quantity=0))
    fill=pending.on_trade(trade(1,quantity='10'))
    intent=create_execution_intent('buy',1,100,T,stop_loss=90,take_profit=110,
                                   symbol='BTCUSDT',intent_id='o1')
    backtester=RealisticBacktester(fee_rate=.1,slippage_factor=.1,spread_bps=100)
    record=backtester.apply_modeled_maker_fill(intent,fill)
    assert record['price']==100 and record['fees']==pytest.approx(.002)
    assert record['simulated_fill'] is True
    assert backtester.position==pytest.approx(.1)
    assert backtester.cash==pytest.approx(9989.998)
    cash=backtester.cash
    with pytest.raises(ValueError):backtester.apply_modeled_maker_fill(intent,fill)
    assert backtester.cash==cash
    with pytest.raises(ValueError):backtester.apply_modeled_maker_fill(intent,replace(fill,source_trade_id='oversize',quantity=D('2')))
    backtester.reset()
    assert backtester.apply_modeled_maker_fill(intent,fill)['price']==100


def test_actual_ledger_accounts_subminimum_partial_of_admissible_original_order():
    from infrastructure.backtest.execution_intent import create_execution_intent
    from infrastructure.backtest.realistic_backtester import RealisticBacktester
    pending=order(quantity='0.001',quote=quote(bid_quantity=0))
    fill=pending.on_trade(trade(1,quantity='0.003'))
    assert fill.quantity==D('0.00003')
    intent=create_execution_intent('buy',.001,100,T,stop_loss=90,take_profit=110,
                                   symbol='BTCUSDT',intent_id='o1')
    backtester=RealisticBacktester()
    record=backtester.apply_modeled_maker_fill(intent,fill)
    assert record is not None
    assert backtester.position==pytest.approx(.00003)


@pytest.mark.parametrize('original_size',[.0005,1000])
def test_tiny_partial_cannot_bypass_original_submission_admission(original_size):
    from infrastructure.backtest.execution_intent import create_execution_intent
    from infrastructure.backtest.realistic_backtester import RealisticBacktester
    pending=order(quantity=original_size,quote=quote(bid_quantity=0))
    fill=pending.on_trade(trade(1,quantity='0.003'))
    intent=create_execution_intent('buy',original_size,100,T,stop_loss=90,take_profit=110,
                                   symbol='BTCUSDT',intent_id='o1')
    backtester=RealisticBacktester()
    assert backtester.apply_modeled_maker_fill(intent,fill) is None
    assert backtester.position==0 and backtester.cash==10000
