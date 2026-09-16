# TASK-0368 — A1 exploratory mean-reversion plus aggressive-flow contract

## خلاصه ساده فارسی

قبل از دیدن نتیجه، آزمون اکتشافی اول محدود شد: ابتدا حرکت شدید ۱۵‌دقیقه‌ای را با تاریخچه ۳۰ روزه
تشخیص می‌دهیم و خلاف جهت آن برای یک ساعت بررسی می‌کنیم. سپس می‌سنجیم آیا فشار taker شدید و هم‌جهت
با حرکت، subset بهتری برای برگشت قیمت می‌سازد یا نه. کارمزد، slippage، funding، folds زمانی و
هم‌بستگی رویدادهای یک روز لحاظ می‌شوند. این آزمون فقط می‌تواند مجوز preregistration بدهد، نه edge.

## Label and question

`EXPLORATORY — NOT CONFIRMATORY`

Does a causal aggressive-flow exhaustion condition add stable net information to the identical
15-minute extreme-return mean-reversion baseline?

## Frozen exploratory construction

- Universe: ADAUSDT, BNBUSDT, BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT.
- Source: `data/research/taker_flow/normalized`, exact native 15-minute futures bars.
- Formation return: completed-bar close divided by the immediately preceding close minus one.
- Baseline event: absolute formation return strictly exceeds its prior 2,880-bar (30-day) causal
  p90, excluding current. Positive move implies SHORT; negative move implies LONG.
- Flow score: `(2 * taker_buy_quote_volume - quote_volume) / quote_volume` on the completed
  formation bar.
- Primary flow condition: score sign matches formation-return sign and absolute score strictly
  exceeds its prior 2,880-bar causal p75, excluding current.
- Entry: exact next 15-minute open. Exit: exact open four complete bars after entry (one hour).
- Reject missing/non-finite bars and overlapping positions per symbol.
- Include actual funding settlements strictly after entry and at or before exit with correct side
  sign.
- Primary round-trip friction: 0.30%; stress: 0.50%.

## Reports

- Compare identical baseline and conditioned samples using N, unique UTC-day clusters, expectancy,
  PF, win rate, folds, symbol/side breadth, funding, and positive-PnL concentration.
- Use four chronological folds and UTC-entry-day clustered bootstrap with fixed seed `360368`.
- Perturb only the flow percentile to p70 and p80 as fragility diagnostics; do not select either as
  a replacement winner.

## Fast falsification

Park/reject A1 if the p75 conditioned sample has non-positive primary net expectancy, fails to
improve over baseline, has fewer than three positive/improved chronological folds, fails 0.50%
stress, depends on fewer than four positive symbols, has bootstrap lower bound at or below zero, or
has more than 35% positive-PnL concentration in one symbol.

Survival only means `PREREGISTRATION_JUSTIFIED`. It cannot alter production or prove edge; a fresh
independent confirmatory boundary remains mandatory.

## Engineering budget

One disposable research script, one machine-readable report, one focused test file, no download,
no new dependency/service/runtime, and no production code.
