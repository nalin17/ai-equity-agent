# ADR-008 - Macro context from FRED's API, with the owner's own key

- decision_id: ADR-008
- date: 2026-10-03
- problem: Stage 10C (architecture 40B step 9a, 3G, 5C) needs world and India macro context -
  rates and bonds, currencies, commodities, world equity indices, volatility, credit spreads and
  economic releases - as point-in-time evidence with every vintage. No source used so far carries
  any of it. Architecture 4G asks for official and free sources first, the terms checked before
  use, one network module with an allow-list, and secrets that never leave the owner's computer.
- research (2026-10-03, read in the browser; real answers fetched by the owner's own probe):
  - FRED API terms: free key per user; personal use allowed, including series owned by third
    parties ("before using data series owned by third parties for anything other than your own
    personal use, you must contact the data owner"); the notice "This product uses the FRED(R) API
    but is not endorsed or certified by the Federal Reserve Bank of St. Louis" must be shown; no
    concealed identity; up to 120 requests a minute (HTTP 429 beyond). No clause on storage or AI
    use; the data is stored privately and never redistributed.
  - Owners' notes on real series: Nikkei (downloading for research projects permitted), Cboe and
    IMF (reprinted with permission), ICE BofA (internal use only, no distribution), Nasdaq
    (copyright notice). S&P Dow Jones Indices: "Reproduction of S&P 500 in any form is prohibited
    except with the prior written permission" - and SP500 has no vintages in ALFRED. Its series are
    refused.
  - ALFRED keeps vintages (DGS10 since 2005). Real answers showed: daily series exceed FRED's
    2,000-vintage-date limit per answer; holidays are listed with no value ('.'); US payrolls and
    CPI carry many revisions; an ALFRED vintage date can precede FRED's actual update (ICE's credit
    spread for 1-Oct carries 1-Oct, loaded 2-Oct 09:12 Chicago time), so it is not proof of
    availability.
  - Publication times differ by publisher: US index closes reach FRED the same evening (before the
    next Indian session), H.15 Treasury yields the next business day afternoon (Chicago), H.10
    exchange rates and EIA oil prices once a week.
  - FRED's India series are weak (OECD India CPI ends Mar-2025, industrial production Jan-2023;
    India 10-year yield monthly, two months late). India's own sources come in Stage 10C-2: MoSPI's
    eSankhyiki API (official; reuse with attribution under GSDD 2026; needs a free registration and
    token) and NSE's India VIX and index files by hand (ADR-004). FBIL's reference rates are not
    used (all rights reserved, login required); niftyindices.com forbids automated collection and
    copying.
- options: (1) hand downloads from FRED's website; (2) FRED's API with the owner's key; (3) a paid
  vendor; (4) wait for India's sources first.
- decision: (2), approved by the owner on 2026-10-03, as a narrow addition to ADR-005/ADR-006:
  - src/ingestion/news_fetch.py, the only network module, may also ask api.stlouisfed.org for
    exactly /fred/series/observations and /fred/series - no other FRED address, https only, no
    redirects; at most one request a second; HTTP 429 stops all FRED requests for that run;
  - the key is read only by that module, from the environment variable FRED_API_KEY, which the
    owner sets on their own computer as a Windows user environment variable; it is never put in
    chat, the repository, a stored file or table, a log line or an error message, and an answer
    containing it is not stored;
  - every answer used is kept byte for byte as a raw file before it is read;
  - the series are declared by the owner in config/macro_series.yaml and recorded once, never
    silently changed; S&P Dow Jones Indices series are refused;
  - the notice is shown in README.md and by fetch-macro and show-macro.
  Enforced by tests: the allow-list, the two FRED addresses, the key never reaching the database,
  files, logs or messages, the request spacing and the stop on HTTP 429.
- reason: official, free, documented, with vintages (3G rule 1, 5A); the owner's rule "first check
  the free option".
- impact: fetch-macro fetches the 25 declared series (50 requests, about a minute). Run it daily.
  Historical replay of macro history before this system's first read stays unavailable
  (AVAILABILITY_REVIEW in effect): ALFRED's vintage dates are kept, and a later decision may admit
  them once their timing is measured against FRED's own update times. Python on Windows has no
  time-zone database, so session times are declared in src/core/sessions.py (US Eastern, Tokyo,
  India), checked against Windows' own rules for 2007-2040 - no new dependency.
- supersedes: none (adds to ADR-005 and ADR-006)
- owner: project owner
