import re
from pathlib import Path


def load_html(filepath: str) -> str:
    with open(filepath, "r") as f:
        return f.read()


def measure_content_breakdown(html: str) -> dict:
    """Break down HTML file into scripts, styles, and remaining HTML/text."""
    script_matches = re.findall(r"<script[\s\S]*?</script>", html)
    style_matches = re.findall(r"<style[\s\S]*?</style>", html)

    script_bytes = sum(len(m) for m in script_matches)
    style_bytes = sum(len(m) for m in style_matches)
    total = len(html)
    rest = total - script_bytes - style_bytes

    return {
        "total_bytes": total,
        "scripts": {"count": len(script_matches), "bytes": script_bytes, "pct": round(script_bytes * 100 / total, 1)},
        "styles": {"count": len(style_matches), "bytes": style_bytes, "pct": round(style_bytes * 100 / total, 1)},
        "html_text": {"bytes": rest, "pct": round(rest * 100 / total, 1)},
    }


def print_breakdown(name: str, breakdown: dict):
    total = breakdown["total_bytes"]
    s = breakdown["scripts"]
    st = breakdown["styles"]
    h = breakdown["html_text"]
    print(f"{name}: {total:,} bytes total")
    print(f"  Scripts: {s['count']} tags, {s['bytes']:,} bytes ({s['pct']}%)")
    print(f"  Styles:  {st['count']} tags, {st['bytes']:,} bytes ({st['pct']}%)")
    print(f"  HTML/text: {h['bytes']:,} bytes ({h['pct']}%)")
    print()


def deep_analysis(html: str) -> dict:
    """Analyse what remains after stripping scripts and styles."""
    from .html_preprocessing import strip_scripts_and_styles
    cleaned = strip_scripts_and_styles(html)

    # HTML comments
    comments = re.findall(r"<!--[\s\S]*?-->", cleaned)
    comment_bytes = sum(len(c) for c in comments)

    # SVG elements
    svgs = re.findall(r"<svg[\s\S]*?</svg>", cleaned)
    svg_bytes = sum(len(s) for s in svgs)

    # HTML attributes (class, id, data-*, style, aria-*, etc.)
    attr_bytes = 0
    for match in re.finditer(r"<[a-zA-Z][^>]*>", cleaned):
        tag = match.group()
        # Extract tag name
        tag_name_match = re.match(r"<([a-zA-Z][a-zA-Z0-9-]*)", tag)
        if tag_name_match:
            minimal = f"<{tag_name_match.group(1)}>"
            attr_bytes += len(tag) - len(minimal)

    # Hidden/metadata elements (noscript, meta, link, head content)
    noscripts = re.findall(r"<noscript[\s\S]*?</noscript>", cleaned)
    noscript_bytes = sum(len(n) for n in noscripts)

    # Data URIs and base64 encoded content
    data_uris = re.findall(r'data:[^"\')\s]+', cleaned)
    data_uri_bytes = sum(len(d) for d in data_uris)

    # Whitespace (consecutive spaces, blank lines)
    lines = cleaned.split("\n")
    blank_line_bytes = sum(len(l) + 1 for l in lines if not l.strip())
    leading_whitespace_bytes = sum(len(l) - len(l.lstrip()) for l in lines if l.strip())

    # Nav, footer, header elements (non-product content)
    navs = re.findall(r"<nav[\s\S]*?</nav>", cleaned)
    nav_bytes = sum(len(n) for n in navs)
    footers = re.findall(r"<footer[\s\S]*?</footer>", cleaned)
    footer_bytes = sum(len(f) for f in footers)
    headers = re.findall(r"<header[\s\S]*?</header>", cleaned)
    header_bytes = sum(len(h) for h in headers)

    # Iframes
    iframes = re.findall(r"<iframe[\s\S]*?</iframe>", cleaned)
    iframe_bytes = sum(len(i) for i in iframes)

    # Visible text only (strip all tags)
    text_only = re.sub(r"<[^>]+>", "", cleaned)
    text_only = re.sub(r"\s+", " ", text_only).strip()

    return {
        "after_strip_bytes": len(cleaned),
        "comments": {"count": len(comments), "bytes": comment_bytes},
        "svgs": {"count": len(svgs), "bytes": svg_bytes},
        "html_attributes": {"bytes": attr_bytes},
        "noscript": {"count": len(noscripts), "bytes": noscript_bytes},
        "data_uris": {"count": len(data_uris), "bytes": data_uri_bytes},
        "whitespace": {"blank_lines_bytes": blank_line_bytes, "leading_whitespace_bytes": leading_whitespace_bytes},
        "nav": {"count": len(navs), "bytes": nav_bytes},
        "footer": {"count": len(footers), "bytes": footer_bytes},
        "header": {"count": len(headers), "bytes": header_bytes},
        "iframes": {"count": len(iframes), "bytes": iframe_bytes},
        "text_only_bytes": len(text_only),
    }


def print_deep_analysis(name: str, analysis: dict):
    total = analysis["after_strip_bytes"]
    print(f"{name} (after script/style strip): {total:,} bytes")
    for key in ["comments", "svgs", "noscript", "nav", "header", "footer", "iframes"]:
        item = analysis[key]
        if item["bytes"] > 0:
            print(f"  {key}: {item['count']} elements, {item['bytes']:,} bytes ({item['bytes']*100/total:.1f}%)")
    print(f"  html_attributes: {analysis['html_attributes']['bytes']:,} bytes ({analysis['html_attributes']['bytes']*100/total:.1f}%)")
    print(f"  data_uris: {analysis['data_uris']['count']} found, {analysis['data_uris']['bytes']:,} bytes ({analysis['data_uris']['bytes']*100/total:.1f}%)")
    ws = analysis["whitespace"]
    ws_total = ws["blank_lines_bytes"] + ws["leading_whitespace_bytes"]
    print(f"  whitespace: {ws_total:,} bytes ({ws_total*100/total:.1f}%) (blank lines: {ws['blank_lines_bytes']:,}, indentation: {ws['leading_whitespace_bytes']:,})")
    print(f"  text only: {analysis['text_only_bytes']:,} bytes ({analysis['text_only_bytes']*100/total:.1f}%)")
    print()


if __name__ == "__main__":
    data_dir = Path("./data")
    for html_file in sorted(data_dir.glob("*.html")):
        html = load_html(str(html_file))
        breakdown = measure_content_breakdown(html)
        print_breakdown(html_file.name, breakdown)

    print("=" * 60)
    print("DEEP ANALYSIS (after stripping scripts & styles)")
    print("=" * 60 + "\n")

    for html_file in sorted(data_dir.glob("*.html")):
        html = load_html(str(html_file))
        analysis = deep_analysis(html)
        print_deep_analysis(html_file.name, analysis)
