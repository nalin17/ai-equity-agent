# ADR-014 - Daily NSE prices from Zerodha's Kite Connect (Stage 6a)

- decision_id: ADR-014
- date: 2026-11-22
- problem: 40B step 6a - price history is the true bottleneck: 6 trading days of NSE bhavcopies, downloaded by
  hand (NSE forbids automated collection, ADR-004). The liquidity band of Stage 12A refuses every company from
  20-Dec-2026 without newer prices, and features, targets and validation (steps 12-16) need years of them.
- options: (1) a broker data API - Zerodha Kite Connect (Rs 500 for 30 days, history included) or Dhan (Rs 499
  a month); (2) TrueData's Market Data API (authorised vendor, price on request, asked 22-Nov); (3) NSE's own
  licence (about Rs 1 lakh a year) or NSE research data (request drafted); (4) keep downloading by hand.
- decision: (1) Kite Connect, bought by the owner on 22-Nov-2026, built as follows:
  - New host api.kite.trade in news_fetch.ALLOWED_HOSTS; only POST /session/token, GET /instruments/NSE and GET
    /instruments/historical/<token>/day (query keys from, to, continuous, oi only) are asked for; at most 3
    historical requests a second (Kite's published limit); any refusal stops the run. A dropped connection (no
    answer at all - the owner's first full run was reset after about 2 minutes on 22-Nov-2026) is not a refusal:
    a download is asked again after 5, 20 and 60 seconds, then the run stops; the login is never repeated. Kite's
    server errors 500/502/503/504 (the second run met a 502 after 900 companies) are asked again the same way;
    every other status (400, 403, 429 ...) is a refusal and stops the run at once.
  - The owner's KITE_API_KEY and KITE_API_SECRET are read only in news_fetch.py. The owner logs in each day in
    their own browser (Kite's access token ends at 6 AM - a regulatory requirement; automating the login is not
    allowed) and pastes the redirect address; the request token, the access token and the login answer (it
    carries the owner's name and email) live in memory for one run only and are scrubbed from every message.
  - Kite's instrument list has no ISIN: an NSE EQ instrument reaches a company only through its NSE symbol in the
    registry on the day, or that symbol with -BE or -BZ (NSE's trade-for-trade series of the same shares: 206
    registry companies on 22-Nov-2026); others are recorded as unmapped; two Kite symbols for one company are
    both refused.
  - Two faults found in old SME-period history on the live run - a day candle stamped 10:00 instead of 00:00,
    and two candles for one day - are set aside candle by candle (kt_problems, schema 23; both candles of a
    doubled day, never chosen between) and the day stays missing; any other fault still refuses the whole answer.
    Each refused company is reported at once, not only at the end of a run.
  - Kite's day candles are adjusted by Zerodha for corporate actions and the whole history is re-adjusted after
    each split or bonus. They never enter trusted_prices (raw, as traded). Every answer is a vintage in kt_*;
    a daily fetch overlaps the last 10 stored days, and a changed day triggers a full re-fetch ('readjusted'), so
    a series is never stitched from two adjustments. An answer is used whole or not at all.
  - Availability (5B): known from our retrieval; under historical replay the vendor's values are
    AVAILABILITY_REVIEW (they were never public as such on the trade date) - withheld and counted.
  - The hub (hub-3) gives Kite candles as 'vendor_daily_price' for days NSE's own files lack, labelled as the
    vendor's adjusted series; missing trading days are judged over both. The liquidity band becomes rule
    se-liquidity-2: NSE's files first, then Kite's days (close x volume survives split adjustment).
- terms (kite.trade/terms, read 22-Nov-2026): personal use by the account holder; live data never displayed to the
  public; no virtual or mock trading apps; no redistribution; 4(b): unless expressly permitted by Zerodha, no
  databases or permanent copies of API content; 9(b): on ending the terms, delete stored content; charges are
  non-refundable. Zerodha's permission to store was asked by the owner on 22-Nov-2026 (kiteconnect@zerodha.com).
  OWNER'S DECISION 22-Nov-2026: store meanwhile ("proceed with the api and data storage for time being"). The
  assistant advised waiting and recorded the risk (termination of API access; Zerodha may audit, 5). Safeguard:
  purge-kite removes ALL Kite data at once (tables dropped and made again) if Zerodha refuses or the terms end;
  the reply is to be saved in data\handover\research\permissions\.
- consequences: automated daily prices for every listed NSE company that maps, back to 2015 by default (about
  6,000 requests, 35-40 minutes, once); about 2,100 requests a day after that. Survivorship: Kite has no delisted
  companies, so its history flatters any back-test - NSE research data or NSE's licence is still needed for that.
  Adjusted, not as traded: level-based features must use returns; raw prices stay NSE's bhavcopies.
- not decided here: intraday candles, indices (NIFTY, India VIX) and F&O open interest; TrueData (answers awaited).
