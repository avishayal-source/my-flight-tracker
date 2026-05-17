"""Google Flights via Playwright — parse real result cards only (no junk fallback)."""
from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from fast_flights import FlightData, Passengers, TFSData

from flights.config import AppConfig, departure_dates
from flights.models import FlightOffer

if TYPE_CHECKING:
    from playwright.sync_api import Page

ROOT = Path(__file__).resolve().parents[1]
DEBUG_DIR = ROOT / "data" / "debug"

# TLV-VIE economy ~2 pax rough bounds (reject UI noise like repeated $296 chips)
MIN_PRICE_USD = 80.0
MAX_PRICE_USD = 3500.0


class GooglePlaywrightError(RuntimeError):
    pass


def _build_url(origin: str, destination: str, dep_date: date, adults: int, currency: str) -> str:
    tfs = TFSData.from_interface(
        flight_data=[
            FlightData(
                date=dep_date.isoformat(),
                from_airport=origin,
                to_airport=destination,
                max_stops=0,
            )
        ],
        trip="one-way",
        passengers=Passengers(adults=adults),
        seat="economy",
        max_stops=0,
    )
    from urllib.parse import urlencode

    params = {
        "tfs": tfs.as_b64().decode("utf-8"),
        "hl": "en",
        "tfu": "EgQIABABIgA",
        "curr": currency,
    }
    return "https://www.google.com/travel/flights?" + urlencode(params)


def _accept_consent(page: Page) -> None:
    for label in ("Accept all", "Accepteer alles", "I agree", "Accept"):
        try:
            btn = page.get_by_role("button", name=re.compile(label, re.I))
            if btn.count() > 0:
                btn.first.click(timeout=3000)
                page.wait_for_timeout(1000)
                return
        except Exception:
            continue


def _wait_for_results(page: Page, timeout_ms: int = 120000) -> None:
    """Poll until result rows appear or empty-state / timeout."""
    import time as time_mod

    try:
        page.wait_for_selector('[role="main"]', timeout=30000)
    except Exception as e:
        raise GooglePlaywrightError(f"No main content: {e}") from e

    page.wait_for_timeout(4000)

    selectors = (
        'div[jsname="IWWDBc"] li',
        "ul.Rk10dc li",
        'motionless.EqeGBc',
        'div[jsname="YdtKid"] li',
    )
    deadline = time_mod.time() + timeout_ms / 1000.0
    while time_mod.time() < deadline:
        html = page.content()
        if "No flights" in html or "No results" in html or "couldn't find" in html.lower():
            raise GooglePlaywrightError("Google shows no flights for this search (try other dates)")
        for sel in selectors:
            try:
                loc = page.locator(sel).first
                if loc.count() > 0:
                    loc.wait_for(state="visible", timeout=5000)
                    page.wait_for_timeout(2000)
                    return
            except Exception:
                continue
        page.mouse.wheel(0, 600)
        page.wait_for_timeout(800)

    raise GooglePlaywrightError(
        "Results list did not appear in time (try --headful, different dates, or non-direct)"
    )


def _parse_results_html(html: str) -> list[dict]:
    from fast_flights.core import parse_response

    class _R:
        text = html
        text_markdown = html

    result = parse_response(_R())
    rows: list[dict] = []
    for f in result.flights:
        if f.stops != 0:
            continue
        rows.append(
            {
                "name": f.name,
                "departure": f.departure,
                "arrival": f.arrival,
                "price": f.price,
            }
        )
    return rows


def _valid_price(price: float) -> bool:
    return MIN_PRICE_USD <= price <= MAX_PRICE_USD


def _parse_price(raw: str) -> float:
    m = re.search(r"([\d,]+(?:\.\d+)?)", raw.replace(",", ""))
    if not m:
        raise GooglePlaywrightError(f"Bad price: {raw!r}")
    return float(m.group(1))


def _carrier_from_name(name: str) -> tuple[str, str]:
    """Map airline label to short code + flight label."""
    n = (name or "").strip()
    if not n or n.lower() == "unknown":
        return "UNK", "UNKNOWN"
    primary = n.split(",")[0].strip()
    # Common carriers on TLV-VIE
    mapping = {
        "el al": "LY",
        "austrian": "OS",
        "wizz": "W6",
        "lufthansa": "LH",
        "swiss": "LX",
        "turkish": "TK",
        "pegasus": "PC",
        "blue bird": "BZ",
        "arkia": "IZ",
    }
    low = primary.lower()
    for key, code in mapping.items():
        if key in low:
            return code, primary[:40]
    code = re.sub(r"[^A-Za-z]", "", primary)[:3].upper() or "UNK"
    return code, primary[:40]


def _parse_time(dep_date: date, time_str: str) -> datetime:
    if not time_str or not time_str.strip():
        return datetime.combine(dep_date, datetime.min.time())
    for fmt in ("%I:%M %p", "%H:%M"):
        try:
            return datetime.combine(dep_date, datetime.strptime(time_str.strip(), fmt).time())
        except ValueError:
            continue
    return datetime.combine(dep_date, datetime.min.time())


def _save_debug(page: Page, tag: str) -> None:
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    path = DEBUG_DIR / f"{tag}.png"
    try:
        page.screenshot(path=str(path), full_page=True)
        print(f"  debug screenshot: {path}", flush=True)
    except Exception:
        pass


def _fetch_leg_playwright(
    page: Page,
    cfg: AppConfig,
    direction: str,
    origin: str,
    destination: str,
    dep_date: date,
    run_id: int,
) -> FlightOffer | None:
    url = _build_url(origin, destination, dep_date, cfg.adults, cfg.currency)
    print(f"  fetch {origin}->{destination} {dep_date} ...", flush=True)
    page.goto(url, wait_until="load", timeout=120000)
    _accept_consent(page)

    try:
        _wait_for_results(page)
    except GooglePlaywrightError as e:
        _save_debug(page, f"run{run_id}-{direction}-{dep_date}-nowait")
        print(f"  skip {origin}->{destination} {dep_date}: {e}", flush=True)
        return None

    rows = _parse_results_html(page.content())
    if not rows:
        _save_debug(page, f"run{run_id}-{direction}-{dep_date}-noparse")
        print(f"  skip {origin}->{destination} {dep_date}: parser found 0 flights", flush=True)
        return None

    priced = []
    for r in rows:
        try:
            p = _parse_price(r["price"])
            if _valid_price(p):
                priced.append((p, r))
        except GooglePlaywrightError:
            continue

    if not priced:
        _save_debug(page, f"run{run_id}-{direction}-{dep_date}-invalid")
        print(f"  skip {origin}->{destination} {dep_date}: no prices in ${MIN_PRICE_USD}-${MAX_PRICE_USD}", flush=True)
        return None

    best_price, best = min(priced, key=lambda x: x[0])
    carrier, flight_label = _carrier_from_name(best.get("name", ""))

    return FlightOffer(
        direction=direction,
        departure_date=dep_date,
        departure_at=_parse_time(dep_date, best.get("departure", "")),
        arrival_at=_parse_time(dep_date, best.get("arrival", "")),
        carrier_code=carrier,
        flight_number=flight_label,
        duration_minutes=0,
        stops=0,
        price_total_usd=best_price,
        adults=cfg.adults,
        cabin=cfg.cabin,
        external_id=f"google-{direction}-{dep_date}-{carrier}-{int(best_price)}",
    )


def fetch_google_playwright_offers(
    cfg: AppConfig,
    max_days: int | None,
    run_id: int,
    *,
    start_offset_days: int | None = None,
    headless: bool = True,
    pause_seconds: float = 3.0,
) -> list[FlightOffer]:
    from playwright.sync_api import sync_playwright

    offset = (
        start_offset_days
        if start_offset_days is not None
        else cfg.departure_start_offset_days
    )
    dates = departure_dates(cfg.horizon_days, max_days, offset)
    legs = [
        (f"{cfg.origin}_{cfg.destination}", cfg.origin, cfg.destination),
        (f"{cfg.destination}_{cfg.origin}", cfg.destination, cfg.origin),
    ]
    offers: list[FlightOffer] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(locale="en-US")
        page = context.new_page()
        try:
            for dep_date in dates:
                for direction, origin, destination in legs:
                    try:
                        offer = _fetch_leg_playwright(
                            page, cfg, direction, origin, destination, dep_date, run_id
                        )
                        if offer:
                            offers.append(offer)
                    except Exception as exc:
                        print(f"  error {origin}->{destination} {dep_date}: {exc}", flush=True)
                    if pause_seconds > 0:
                        page.wait_for_timeout(int(pause_seconds * 1000))
        finally:
            browser.close()

    if not offers:
        raise GooglePlaywrightError(
            "No valid offers parsed. Run once with --headful --max-days 1 and check data/debug/*.png"
        )
    return offers
