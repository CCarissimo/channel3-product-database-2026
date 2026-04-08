import asyncio
import logging
from pathlib import Path

from experiment import run_experiment


async def main():
    data_dir = Path("./data")
    html_files = sorted(data_dir.glob("*.html"))
    await run_experiment(html_files, name="test")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
