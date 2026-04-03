import argparse
import re


def strip_scripts_and_styles(html: str) -> str:
    """Remove all <script> and <style> tags and their contents."""
    html = re.sub(r"<script[\s\S]*?</script>", "", html)
    html = re.sub(r"<style[\s\S]*?</style>", "", html)
    return html


def preprocess(html: str) -> str:
    """Apply all preprocessing steps."""
    html = strip_scripts_and_styles(html)
    return html


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Preprocess HTML files for product extraction.")
    parser.add_argument("file", help="Path to the HTML file to preprocess.")
    parser.add_argument("-o", "--output", help="Output file path. Defaults to stdout.")
    args = parser.parse_args()

    with open(args.file, "r") as f:
        html = f.read()

    result = preprocess(html)

    if args.output:
        with open(args.output, "w") as f:
            f.write(result)
        print(f"{args.file}: {len(html):,} -> {len(result):,} bytes ({100 - len(result) * 100 // len(html)}% reduction)")
    else:
        print(result)
