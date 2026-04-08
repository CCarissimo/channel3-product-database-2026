import argparse
import asyncio
import logging
from pathlib import Path

from experiment import run_experiment


async def main():
    parser = argparse.ArgumentParser(description="Extract product data from HTML files.")
    parser.add_argument("input", type=str, help="Path to an HTML file or a directory containing HTML files.")
    parser.add_argument("--name", type=str, default=None, help="Optional experiment name.")
    args = parser.parse_args()

    input_path = Path(args.input)
    if input_path.is_file():
        html_files = [input_path]
    elif input_path.is_dir():
        html_files = sorted(input_path.glob("*.html"))
    else:
        print(f"Error: '{args.input}' is not a valid file or directory.")
        return

    if not html_files:
        print(f"No HTML files found in '{args.input}'.")
        return

    await run_experiment(html_files, name=args.name)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
