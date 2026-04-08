import argparse
import json
import re


def extract_and_preserve_images(html: str) -> str:
    """Extract image URLs from JSON-LD, meta tags, and data attributes before stripping."""
    urls = set()

    # 1. JSON-LD blocks
    for match in re.finditer(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>([\s\S]*?)</script>', html):
        try:
            data = json.loads(match.group(1))
            _extract_json_images(data, urls)
        except json.JSONDecodeError:
            pass

    # 2. Meta tags (og:image, twitter:image)
    for match in re.finditer(r'<meta[^>]*(?:property|name)=["\'](?:og:image|twitter:image)["\'][^>]*content=["\']([^"\']+)["\']', html):
        urls.add(match.group(1))
    # Also match reversed attribute order
    for match in re.finditer(r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*(?:property|name)=["\'](?:og:image|twitter:image)["\']', html):
        urls.add(match.group(1))

    # 3. data-src and data-srcset attributes
    for match in re.finditer(r'data-src\s*=\s*["\']([^"\']+)["\']', html):
        url = match.group(1).strip()
        if url and not url.startswith('data:'):
            urls.add(url)
    for match in re.finditer(r'data-srcset\s*=\s*["\']([^"\']+)["\']', html):
        # srcset has format "url1 1x, url2 2x"
        for part in match.group(1).split(','):
            url = part.strip().split()[0] if part.strip() else ''
            if url and not url.startswith('data:'):
                urls.add(url)

    # Normalize protocol-relative URLs
    urls = {f'https:{u}' if u.startswith('//') else u for u in urls}
    # Filter to likely image URLs
    urls = {u for u in urls if re.search(r'\.(jpg|jpeg|png|gif|webp|svg|avif)|/image', u, re.IGNORECASE)}

    if not urls:
        return html

    # Inject preserved image URLs as img tags at the end of body
    img_block = '\n<!-- preserved-images -->\n'
    for url in sorted(urls):
        img_block += f'<img src="{url}">\n'
    img_block += '<!-- /preserved-images -->\n'

    # Insert before </body> or append
    if '</body>' in html:
        html = html.replace('</body>', img_block + '</body>', 1)
    else:
        html += img_block

    return html


def _extract_json_images(data, urls):
    """Recursively extract image URLs from JSON-LD data."""
    if isinstance(data, dict):
        for key, value in data.items():
            if key.lower() == 'image':
                if isinstance(value, str):
                    urls.add(value)
                elif isinstance(value, list):
                    for v in value:
                        if isinstance(v, str):
                            urls.add(v)
            else:
                _extract_json_images(value, urls)
    elif isinstance(data, list):
        for item in data:
            _extract_json_images(item, urls)


def strip_scripts_and_styles(html: str) -> str:
    """Remove all <script> and <style> tags and their contents."""
    html = re.sub(r"<script[\s\S]*?</script>", "", html)
    html = re.sub(r"<style[\s\S]*?</style>", "", html)
    return html


def strip_non_product_content(html: str) -> str:
    """Remove site chrome, SVGs, comments, data URIs, and other non-product elements."""
    # HTML comments (but preserve our injected image block)
    html = re.sub(r"<!--(?!\s*/?preserved-images)[\s\S]*?-->", "", html)
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
    # HTML attributes (strip all except src and href which contain URLs)
    def _strip_attributes_keep_urls(match):
        tag = match.group(1)
        attrs = match.group(2)
        kept = []
        for m in re.finditer(r'(src)\s*=\s*("[^"]*"|\'[^\']*\')', attrs):
            kept.append(f'{m.group(1)}={m.group(2)}')
        if kept:
            return f'<{tag} {" ".join(kept)}>'
        return f'<{tag}>'
    html = re.sub(r"<([a-zA-Z][a-zA-Z0-9-]*)\s([^>]*?)>", _strip_attributes_keep_urls, html)
    # Collapse whitespace: multiple blank lines -> single newline
    html = re.sub(r"\n\s*\n", "\n", html)
    # Strip leading whitespace on each line
    html = re.sub(r"(?m)^[ \t]+", "", html)
    return html


def preprocess(html: str) -> str:
    """Apply all preprocessing steps."""
    html = extract_and_preserve_images(html)
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
