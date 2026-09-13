# xoomar

Python client for the [XOOMAR](https://xoomar.com/markets) free market data API: 29 datasets from primary sources (SEC EDGAR and XBRL, FINRA, CFTC, the Federal Reserve, USAspending, exchange APIs) as clean JSON, no key needed to start.

```bash
pip install xoomar
```

```python
from xoomar import Xoomar

x = Xoomar()                          # 30 requests a minute; Xoomar(api_key="...") for 120 with a free key

x.short_interest("GME")[-1]           # FINRA short interest, latest settlement
x.short_volume("GME", days=30)        # FINRA daily short sale volume
x.fails_to_deliver("GME")             # SEC fails to deliver
x.insiders("NVDA")                    # SEC Form 4 trades
x.large_holders("HIMS")               # Schedule 13D and 13G holders
x.financials("AAPL")["quarterly"]     # XBRL income statement by quarter
x.fund_holders("AMZN")                # which tracked 13F managers hold it
x.cot("gold")                         # CFTC positioning history
x.fed_liquidity()[-1]                 # net liquidity, this week
x.funding_rates()                     # perpetual funding on three exchanges
x.bitcoin_treasuries()                # bitcoin on public balance sheets
x.form_d(days=7)                      # private placements filed this week
x.federal_contracts(ticker="LMT")     # federal contract actions
```

Every method returns the `data` part of the response; `x.last_meta` holds `updatedAt`, `source`, `license` and `attribution` from the last call. `x.get("short-interest", symbol="TSLA")` calls any endpoint directly and `x.csv("short-interest/csv")` fetches a CSV download.

Full endpoint reference, fields and limits: https://xoomar.com/markets/api

## Datasets

Short interest, daily short volume, fails to deliver, insider trades (Form 4), planned sales (Form 144), large holders (13D/13G), 13F fund holdings, company financials and buybacks (XBRL), 8-K events, structured products, federal contracts, Form D private placements, the IPO pipeline, bitcoin treasuries, CFTC COT, funding rates, open interest, liquidations, options, whale positions, sentiment, signals, ETF flows, prediction markets, Fed liquidity, macro, policy rates, economic calendar.

## Rate limits and keys

30 requests a minute per IP without a key. A free account at https://xoomar.com/signup gives a key for 120 a minute; pass it as `Xoomar(api_key=...)`. A 429 raises `XoomarRateLimited` with `retry_after`.

## Attribution

The data is free to use, including commercially. When you republish it, on a site, in an app, in an article, in a dataset or a chart, credit XOOMAR with a visible link to the dataset page on xoomar.com. Terms: https://xoomar.com/terms

## License

MIT, XOOMAR.
