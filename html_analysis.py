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


if __name__ == "__main__":
    data_dir = Path("./data")
    for html_file in sorted(data_dir.glob("*.html")):
        html = load_html(str(html_file))
        breakdown = measure_content_breakdown(html)
        print_breakdown(html_file.name, breakdown)
