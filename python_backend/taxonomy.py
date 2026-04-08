import argparse
import json
import os
from pathlib import Path

CATEGORIES_FILE = Path(__file__).parent.parent / "categories.txt"
TREE_CACHE_FILE = Path(__file__).parent.parent / "taxonomy_tree.json"


def build_tree(filepath: Path) -> dict:
    """Parse categories.txt into a nested dict (trie)."""
    tree = {}
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split(" > ")]
            node = tree
            for part in parts:
                node = node.setdefault(part, {})
    return tree


def load_or_build_tree() -> dict:
    """Load cached tree if fresh, otherwise rebuild and cache."""
    if TREE_CACHE_FILE.exists():
        cache_mtime = os.path.getmtime(TREE_CACHE_FILE)
        source_mtime = os.path.getmtime(CATEGORIES_FILE)
        if cache_mtime > source_mtime:
            with open(TREE_CACHE_FILE, "r") as f:
                return json.load(f)

    tree = build_tree(CATEGORIES_FILE)
    with open(TREE_CACHE_FILE, "w") as f:
        json.dump(tree, f)
    return tree


def main():
    parser = argparse.ArgumentParser(description="Traverse the Google Product Taxonomy tree.")
    parser.add_argument("--subcat", action="append", default=[], help="Category level to drill into (repeatable).")
    args = parser.parse_args()

    tree = load_or_build_tree()
    node = tree
    path_so_far = []

    for cat in args.subcat:
        if cat not in node:
            print(f"Error: '{cat}' is not a valid category at level: {' > '.join(path_so_far) or 'root'}")
            print(f"Valid options: {', '.join(sorted(node.keys()))}")
            return
        path_so_far.append(cat)
        node = node[cat]

    if not node:
        print(f"Leaf category reached: {' > '.join(path_so_far)}")
    else:
        for child in sorted(node.keys()):
            print(child)


if __name__ == "__main__":
    main()
