import argparse
import re


def strip_scripts_and_styles(html: str) -> str:
    """Remove all <script> and <style> tags and their contents."""
    html = re.sub(r"<script[\s\S]*?</script>", "", html)
    html = re.sub(r"<style[\s\S]*?</style>", "", html)
    return html


def strip_non_product_content(html: str) -> str:
    """Remove site chrome, SVGs, comments, data URIs, and other non-product elements."""
    # HTML comments
    html = re.sub(r"<!--[\s\S]*?-->", "", html)
    # SVGs
    html = re.sub(r"<svg[\s\S]*?</svg>", "", html)
    # Navigation, header, footer (site chrome)
    html = re.sub(r"<nav[\s\S]*?</nav>", "", html)
    html = re.sub(r"<header[\s\S]*?</header>", "", html)
    html = re.sub(r"<footer[\s\S]*?</footer>", "", html)
    # Noscript, iframes
    html = re.sub(r"<noscript[\s\S]*?</noscript>", "", html)
    html = re.sub(r"<iframe[\s\S]*?</iframe>", "", html)
    # Data URIs (base64-encoded content in attributes)
    html = re.sub(r'data:[^"\')\s]+', "", html)
    # HTML attributes (keep tag names, strip everything else)
    html = re.sub(r"<([a-zA-Z][a-zA-Z0-9-]*)\s[^>]*?>", r"<\1>", html)
    # Collapse whitespace: multiple blank lines -> single newline
    html = re.sub(r"\n\s*\n", "\n", html)
    # Strip leading whitespace on each line
    html = re.sub(r"(?m)^[ \t]+", "", html)
    return html


def preprocess(html: str) -> str:
    """Apply all preprocessing steps."""
    html = strip_scripts_and_styles(html)
    html = strip_non_product_content(html)
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
