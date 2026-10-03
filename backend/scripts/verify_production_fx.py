"""Read-only provider acceptance: no database writes or financial data sent."""
import argparse
import asyncio
import sys
from datetime import date
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.providers.openexchangerates import OpenExchangeRatesProvider, RateSnapshot


async def verify(target: date | None) -> None:
    settings = get_settings()
    if not settings.is_production or settings.fx_allow_unsafe_1to1_fallback:
        raise ValueError("production configuration required")
    provider = OpenExchangeRatesProvider()
    rates = await provider.fetch_historical(target) if target else await provider.fetch_latest()
    expected = {code.strip().upper() for code in settings.supported_currencies.split(',')}
    if expected - rates.keys() or not isinstance(rates, RateSnapshot):
        raise ValueError("incomplete snapshot")
    print(f"FinCo-Pilot FX acceptance: PASS\nprovider={provider.name}\npublication_date={rates.published_date}\ncovered_currencies={len(expected)}\ndatabase_written=false")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--historical-date', type=date.fromisoformat)
    args = parser.parse_args(argv)
    try:
        asyncio.run(verify(args.historical_date))
        return 0
    except Exception:
        # Settings errors and HTTP exceptions can contain secrets. Never print them.
        print("FinCo-Pilot FX acceptance: FAIL (configuration/provider contract)", file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
