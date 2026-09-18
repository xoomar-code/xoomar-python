"""Client for the XOOMAR free market data API (https://xoomar.com/markets/api).

Every method returns the ``data`` part of the JSON response as plain Python
objects (lists or dicts). The full envelope of the last call, with
``updatedAt``, ``source``, ``license`` and ``attribution``, is on
``client.last_meta``.

When you republish the data, link to the dataset page on xoomar.com; the terms
of use are at https://xoomar.com/terms.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

__version__ = "0.1.7"
__all__ = ["Xoomar", "XoomarError", "XoomarRateLimited"]

DEFAULT_BASE_URL = "https://xoomar.com"


class XoomarError(Exception):
    """An HTTP or API error. ``status`` is the HTTP status, ``body`` the response text."""

    def __init__(self, status: int, body: str, url: str):
        super().__init__(f"HTTP {status} from {url}: {body[:200]}")
        self.status = status
        self.body = body
        self.url = url


class XoomarRateLimited(XoomarError):
    """429: 30 requests a minute without a key, 120 with a free key from https://xoomar.com/signup."""

    def __init__(self, status: int, body: str, url: str, retry_after: Optional[int]):
        super().__init__(status, body, url)
        self.retry_after = retry_after


class Xoomar:
    """
    >>> from xoomar import Xoomar
    >>> x = Xoomar()                      # or Xoomar(api_key="...") for 120 requests a minute
    >>> x.short_interest("GME")[0]
    {'settlementDate': '2026-08-14', 'symbol': 'GME', 'shortQty': 54036583, ...}
    """

    def __init__(self, api_key: Optional[str] = None, base_url: str = DEFAULT_BASE_URL, timeout: float = 30.0, user_agent: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.user_agent = user_agent or f"xoomar-python/{__version__}"
        self.last_meta: Dict[str, Any] = {}

    # ── transport ──

    def get(self, path: str, **params: Any) -> Any:
        """GET ``/api/markets/<path>`` with query parameters; returns the ``data`` field."""
        query = {k: v for k, v in params.items() if v is not None}
        url = f"{self.base_url}/api/markets/{path.lstrip('/')}"
        if query:
            url += "?" + urllib.parse.urlencode(query)
        headers = {"Accept": "application/json", "User-Agent": self.user_agent}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as res:
                payload = json.loads(res.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace") if e.fp else ""
            if e.code == 429:
                ra = e.headers.get("Retry-After") if e.headers else None
                raise XoomarRateLimited(e.code, body, url, int(ra) if ra and ra.isdigit() else None) from None
            raise XoomarError(e.code, body, url) from None
        if isinstance(payload, dict) and "data" in payload:
            self.last_meta = {k: v for k, v in payload.items() if k != "data"}
            return payload["data"]
        self.last_meta = {}
        return payload

    def csv(self, path: str, **params: Any) -> str:
        """The CSV download for a dataset, e.g. ``csv("short-interest/csv")``, as text."""
        query = {k: v for k, v in params.items() if v is not None}
        url = f"{self.base_url}/api/markets/{path.lstrip('/')}"
        if query:
            url += "?" + urllib.parse.urlencode(query)
        headers = {"Accept": "text/csv", "User-Agent": self.user_agent}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as res:
                return res.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            raise XoomarError(e.code, e.read().decode("utf-8", "replace") if e.fp else "", url) from None

    # ── companies (SEC and FINRA) ──

    def short_interest(self, symbol: Optional[str] = None) -> Any:
        """FINRA short interest: a symbol's history newest first, or the latest settlement's highest days to cover."""
        return self.get("short-interest", symbol=symbol)

    def short_volume(self, symbol: Optional[str] = None, days: Optional[int] = None, sort: Optional[str] = None, from_: Optional[str] = None, to: Optional[str] = None, limit: Optional[int] = None) -> Any:
        """FINRA daily short sale volume since August 2021: a symbol's history oldest first (from_/to ISO dates, limit up to 5,000), or the latest day (sort="shares" for largest volumes)."""
        return self.get("short-volume", symbol=symbol, days=days, sort=sort, **{"from": from_, "to": to, "limit": limit})

    def fails_to_deliver(self, symbol: Optional[str] = None, from_: Optional[str] = None, to: Optional[str] = None, limit: Optional[int] = None) -> Any:
        """SEC fails to deliver since January 2010: a symbol's history oldest first (from_/to ISO dates, limit up to 5,000), or the latest settlement date's largest fails."""
        return self.get("fails-to-deliver", symbol=symbol, **{"from": from_, "to": to, "limit": limit})

    def insiders(self, ticker: Optional[str] = None, type: Optional[str] = None, window: Optional[str] = None, from_: Optional[str] = None, to: Optional[str] = None, limit: Optional[int] = None) -> Any:
        """SEC Form 4 trades: a ticker's history from filings since 2020 (from_/to ISO dates, limit up to 2,000), or the latest across companies (type="buys", window="7d")."""
        if ticker:
            return self.get(f"insiders/{ticker.lower()}", **{"from": from_, "to": to, "limit": limit})
        return self.get("insiders", type=type, window=window)

    def insider_clusters(self, days: Optional[int] = None, min_insiders: Optional[int] = None, min_usd: Optional[float] = None, ticker: Optional[str] = None, limit: Optional[int] = None) -> Any:
        """Cluster buying: companies where several different insiders bought on the open market in the window (min_insiders default 3), buyers and combined value per row."""
        return self.get("insiders/clusters", days=days, minInsiders=min_insiders, minUsd=min_usd, ticker=ticker, limit=limit)

    def threshold_list(self, date: Optional[str] = None, symbol: Optional[str] = None, market: Optional[str] = None, limit: Optional[int] = None) -> Any:
        """Regulation SHO threshold securities lists (Nasdaq and Cboe daily files since 2022): one date, one symbol's days on the list, or one market."""
        return self.get("threshold-list", date=date, symbol=symbol, market=market, limit=limit)

    def planned_sales(self, symbol: Optional[str] = None, days: Optional[int] = None) -> Any:
        """SEC Form 144 notices of proposed sale."""
        return self.get("planned-sales", symbol=symbol, days=days)

    def large_holders(self, symbol: Optional[str] = None, form: Optional[str] = None, days: Optional[int] = None, new: Optional[bool] = None, sort: Optional[str] = None) -> Any:
        """Schedule 13D and 13G cover pages (form="13D" or "13G")."""
        return self.get("large-holders", symbol=symbol, form=form, days=days, new=1 if new else None, sort=sort)

    def financials(self, symbol: str) -> Any:
        """XBRL quarterly income, annual statements and latest balance sheet for a ticker."""
        return self.get("financials", symbol=symbol)

    def buybacks(self) -> Any:
        """Largest share repurchases per company in its latest fiscal year."""
        return self.get("buybacks")

    def fund_holders(self, ticker: str) -> Any:
        """Tracked 13F managers holding a ticker at their latest filing."""
        return self.get("funds", ticker=ticker)

    def fund(self, slug: str) -> Any:
        """One tracked manager's latest 13F portfolio (e.g. "berkshire-hathaway")."""
        return self.get(f"funds/{slug}")

    def events(self, ticker: Optional[str] = None, item: Optional[str] = None, days: Optional[int] = None) -> Any:
        """SEC 8-K material events."""
        return self.get("events", ticker=ticker, item=item, days=days)

    def earnings(self, ticker: Optional[str] = None, from_: Optional[str] = None, to: Optional[str] = None, status: Optional[str] = None, limit: Optional[int] = None) -> Any:
        """Earnings calendar from 8-K Item 2.02 filings. With a ticker: that company's reported dates since 2023 and the next estimate (an object). Without: the window's rows (default today to +14 days; status="reported" or "estimated")."""
        if ticker and from_ is None and to is None and status is None and limit is None:
            return self.get(f"earnings/{ticker.lower()}")
        return self.get("earnings", ticker=ticker, status=status, limit=limit, **{"from": from_, "to": to})

    def structured_products(self, **params: Any) -> Any:
        """Bank structured notes from 424B2 and FWP filings (issuer=, underlying=, noteType=, days=, cursor=)."""
        return self.get("structured-products", **params)

    def federal_contracts(self, ticker: Optional[str] = None, days: Optional[int] = None, by: Optional[str] = None, listed: Optional[bool] = None) -> Any:
        """Largest US federal contract actions (by="ticker" sums by listed parent)."""
        return self.get("federal-contracts", ticker=ticker, days=days, by=by, listed=1 if listed else None)

    # ── markets ──

    def funding_rates(self, slug: Optional[str] = None) -> Any:
        """Perpetual futures funding on Binance, Bybit and OKX; a symbol slug (e.g. "btc") gives its history."""
        return self.get(f"funding-rates/{slug}") if slug else self.get("funding-rates")

    def open_interest(self, slug: str) -> Any:
        """Hourly open interest history for a symbol slug."""
        return self.get(f"open-interest/{slug}")

    def liquidations(self) -> Any:
        """24-hour liquidation summary: totals, long/short split, hourly buckets, top contracts."""
        return self.get("liquidations")

    def liquidation_events(self, symbol: Optional[str] = None, exchange: Optional[str] = None, side: Optional[str] = None, min_usd: Optional[float] = None, limit: Optional[int] = None) -> Any:
        """Individual liquidation events, newest first (up to 500); filter by contract (BTC or BTCUSDT), exchange (okx, gate, htx), side and minimum notional."""
        return self.get("liquidations/recent", symbol=symbol, exchange=exchange, side=side, minUsd=min_usd, limit=limit)

    def liquidation_history(self, symbol: Optional[str] = None, from_: Optional[str] = None, to: Optional[str] = None, limit: Optional[int] = None) -> Any:
        """Hourly liquidation totals kept permanently (from 15 June 2026), oldest first; one contract with symbol, a window with from_/to, up to 5,000 hours."""
        return self.get("liquidations/history", symbol=symbol, **{"from": from_, "to": to, "limit": limit})

    def options(self, currency: str = "BTC") -> Any:
        """Deribit options: put/call, max pain, DVOL for BTC or ETH."""
        return self.get(f"options/{currency}")

    def whales(self, coin: Optional[str] = None) -> Any:
        """Hyperliquid whale positions, all or for one coin."""
        return self.get(f"whales/{coin}") if coin else self.get("whales")

    def cot(self, market: Optional[str] = None) -> Any:
        """CFTC Commitments of Traders: the latest report across markets, or one market's history (e.g. "gold")."""
        return self.get(f"cot/{market}") if market else self.get("cot")

    def sentiment(self, asset: Optional[str] = None, kind: Optional[str] = None, window: Optional[str] = None) -> Any:
        """Composite sentiment scores, all assets or one asset slug."""
        return self.get(f"sentiment/{asset}") if asset else self.get("sentiment", kind=kind, window=window)

    def signals(self, asset: Optional[str] = None) -> Any:
        """Rules-based composite signals."""
        return self.get(f"signals/{asset}") if asset else self.get("signals")

    def etf_flows(self, asset: Optional[str] = None, days: Optional[int] = None) -> Any:
        """Spot bitcoin and ether ETF flows."""
        return self.get("etf-flows", asset=asset, days=days)

    def bitcoin_treasuries(self) -> Any:
        """Bitcoin held by public companies from their SEC filings."""
        return self.get("bitcoin-treasuries")

    # ── macro ──

    def macro(self, series: Optional[str] = None, from_: Optional[str] = None, to: Optional[str] = None) -> Any:
        """US Treasury yield curve, spreads, stablecoin supply (series=, from=, to=)."""
        return self.get("macro", series=series, **{"from": from_, "to": to})

    def fed_liquidity(self, series: Optional[str] = None, limit: Optional[int] = None) -> Any:
        """Weekly net liquidity with components, or one FRED series (WALCL, WRESBAL, RRPONTSYD, WTREGEN, SOFR, EFFR, IORB, WSHOSHO)."""
        return self.get("fed-liquidity", series=series, limit=limit)

    def rates(self, country: Optional[str] = None) -> Any:
        """Central bank policy rates: all economies, or one country code's history (e.g. "us")."""
        return self.get(f"rates/{country}") if country else self.get("rates")

    def treasury_auctions(self, type: Optional[str] = None, term: Optional[str] = None, from_: Optional[str] = None, to: Optional[str] = None, upcoming: Optional[bool] = None, limit: Optional[int] = None) -> Any:
        """US Treasury auction results and calendar since 2010 (type="Note", "Bond", "TIPS", "FRN", "Bill", "CMB" or "all"; term="10-Year"; upcoming=True for announced auctions)."""
        return self.get("treasury-auctions", type=type, term=term, upcoming=1 if upcoming else None, limit=limit, **{"from": from_, "to": to})

    def calendar(self, from_: Optional[str] = None, to: Optional[str] = None, importance: Optional[str] = None) -> Any:
        """US economic calendar with consensus and actuals."""
        return self.get("calendar", importance=importance, **{"from": from_, "to": to})

    # ── filings and offerings ──

    def form_d(self, days: Optional[int] = None, funds: Optional[bool] = None, cik: Optional[str] = None, sort: Optional[str] = None, amendments: Optional[bool] = None) -> Any:
        """SEC Form D private placements: largest raises in a window, one issuer by CIK, or sort="recent"."""
        return self.get("startup-funding", days=days, funds=1 if funds else None, cik=cik, sort=sort, amendments=1 if amendments else None)

    def ipos(self, form: Optional[str] = None, days: Optional[int] = None, new: Optional[bool] = None) -> Any:
        """IPO pipeline filings (form="S-1,F-1", "424B4", "RW", "EFFECT"; new=True for filers not yet listed)."""
        return self.get("ipos", form=form, days=days, new=1 if new else None)
