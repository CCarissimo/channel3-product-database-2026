import ai
import argparse
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel
from models import FirstQueryProduct, Product, Category
from taxonomy import load_or_build_tree
from html_preprocessing import preprocess

CATEGORY_MODEL = "google/gemini-2.0-flash-lite-001"
EXTRACTION_MODEL = "google/gemini-2.5-flash-lite"
MAX_RETRIES = 3
EXPERIMENTS_DIR = Path("./experiments")
SUMMARY_FILE = EXPERIMENTS_DIR / "summary.json"


class CategorySelection(BaseModel):
    category: str


async def find_category(name: str, description: str) -> tuple[str, list[dict]]:
    """Walk the taxonomy tree by asking the model to pick categories until a leaf is reached.
    Returns (full_category_path, list_of_usage_dicts)."""
    tree = load_or_build_tree()
    node = tree
    path = []
    usage_log = []

    while node:
        options = sorted(node.keys())
        options_str = "\n".join(f"- {o}" for o in options)
        level = "category" if not path else "subcategory"

        prompt = (
            f"Product: {name}\n"
            f"Description: {description}\n\n"
            f"Pick the most appropriate {level} from this list. "
            f"Reply with the EXACT name from the list, nothing else.\n\n"
            f"{options_str}"
        )

        for attempt in range(MAX_RETRIES):
            result, usage = await ai.responses(
                model=CATEGORY_MODEL,
                input=[{"role": "user", "content": prompt}],
                text_format=CategorySelection,
            )
            usage["step"] = f"category_level_{len(path)}"
            usage_log.append(usage)
            selected = result.category.strip()
            if selected in node:
                path.append(selected)
                node = node[selected]
                print(f"  Selected: {' > '.join(path)}")
                break
            else:
                print(f"  Retry ({attempt + 1}/{MAX_RETRIES}): '{selected}' not in valid options")
        else:
            raise ValueError(f"Model failed to pick a valid category after {MAX_RETRIES} retries at level: {' > '.join(path) or 'root'}")

    full_category = " > ".join(path)
    print(f"  Leaf reached: {full_category}")
    return full_category, usage_log


async def extract_product(html_path: str) -> tuple[Product, list[dict]]:
    """Extract a Product from an HTML file, including category discovery.
    Returns (product, list_of_all_usage_dicts)."""
    with open(html_path, "r") as f:
        html_content = preprocess(f.read())

    schema_description = FirstQueryProduct.model_json_schema()

    product, extraction_usage = await ai.responses(
        model=EXTRACTION_MODEL,
        input=[
            {"role": "system", "content": (
                "Extract the product information from the following HTML page.\n\n"
                "Output must conform to this schema:\n"
                f"{schema_description}\n\n"
                "Important: All numeric fields (price, compare_at_price) must be plain numbers, not strings. "
                "Do not include currency symbols or text in numeric fields. "
                "Currency should be a separate string field (e.g. 'USD', 'EUR')."
            )},
            {"role": "user", "content": html_content},
        ],
        text_format=FirstQueryProduct,
    )
    extraction_usage["step"] = "product_extraction"
    all_usage = [extraction_usage]

    print(f"\nProduct: {product.name}")
    print(f"Description: {product.description[:100]}...")
    print(f"\nFinding category...")
    category, category_usage = await find_category(product.name, product.description)
    all_usage.extend(category_usage)

    final_product = Product(
        **product.model_dump(),
        category=Category(name=category),
    )

    print(f"\nFinal category: {category}")
    print(f"\n{final_product.model_dump_json(indent=2)}")
    return final_product, all_usage


async def main():
    parser = argparse.ArgumentParser(description="Run product extraction experiment.")
    parser.add_argument("--name", type=str, default=None, help="Optional experiment name.")
    args = parser.parse_args()

    data_dir = Path("./data")
    html_files = sorted(data_dir.glob("*.html"))

    # Create experiment folder
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    folder_name = f"{timestamp}_{args.name}" if args.name else timestamp
    experiment_dir = EXPERIMENTS_DIR / folder_name
    experiment_dir.mkdir(parents=True, exist_ok=True)

    print(f"Experiment: {folder_name}")
    print(f"Found {len(html_files)} HTML files to process")
    print(f"Saving results to: {experiment_dir}\n")

    experiment_results = []

    for html_file in html_files:
        print(f"\n{'='*60}")
        print(f"Processing: {html_file.name}")
        print(f"{'='*60}")

        product, usage_log = await extract_product(str(html_file))

        product_name = html_file.stem

        # Split usage by query type
        extraction_calls = [u for u in usage_log if u["step"] == "product_extraction"]
        taxonomy_calls = [u for u in usage_log if u["step"].startswith("category_level_")]

        product_result = {
            "file": html_file.name,
            "product_name": product.name,
            "category": product.category.name,
            "num_api_calls": len(usage_log),
            "extraction": {
                "num_calls": len(extraction_calls),
                "input_tokens": sum(u["input_tokens"] for u in extraction_calls),
                "output_tokens": sum(u["output_tokens"] for u in extraction_calls),
                "cost": sum(u["cost"] for u in extraction_calls),
                "model": EXTRACTION_MODEL,
            },
            "taxonomy": {
                "num_calls": len(taxonomy_calls),
                "input_tokens": sum(u["input_tokens"] for u in taxonomy_calls),
                "output_tokens": sum(u["output_tokens"] for u in taxonomy_calls),
                "cost": sum(u["cost"] for u in taxonomy_calls),
                "model": CATEGORY_MODEL,
            },
            "total_input_tokens": sum(u["input_tokens"] for u in usage_log),
            "total_output_tokens": sum(u["output_tokens"] for u in usage_log),
            "total_cost": sum(u["cost"] for u in usage_log),
            "calls": usage_log,
        }
        # Save per-product JSON with product data and metrics
        product_file = experiment_dir / f"{product_name}.json"
        product_output = {
            "product": product.model_dump(),
            "metrics": {
                "extraction": product_result["extraction"],
                "taxonomy": product_result["taxonomy"],
                "total_input_tokens": product_result["total_input_tokens"],
                "total_output_tokens": product_result["total_output_tokens"],
                "total_cost": product_result["total_cost"],
                "num_api_calls": product_result["num_api_calls"],
                "calls": usage_log,
            },
        }
        with open(product_file, "w") as f:
            json.dump(product_output, f, indent=2)

        experiment_results.append(product_result)

        # Print per-product summary
        print(f"\n  --- {product_name} token usage ---")
        print(f"  Extraction: {product_result['extraction']['input_tokens']} in / {product_result['extraction']['output_tokens']} out / ${product_result['extraction']['cost']:.6f}")
        print(f"  Taxonomy:   {product_result['taxonomy']['input_tokens']} in / {product_result['taxonomy']['output_tokens']} out / ${product_result['taxonomy']['cost']:.6f} ({product_result['taxonomy']['num_calls']} calls)")
        print(f"  Total:      ${product_result['total_cost']:.6f}")

    # Compute aggregate breakdowns
    total_extraction_cost = sum(r["extraction"]["cost"] for r in experiment_results)
    total_taxonomy_cost = sum(r["taxonomy"]["cost"] for r in experiment_results)
    total_extraction_input = sum(r["extraction"]["input_tokens"] for r in experiment_results)
    total_taxonomy_input = sum(r["taxonomy"]["input_tokens"] for r in experiment_results)

    experiment_info = {
        "name": args.name,
        "timestamp": timestamp,
        "extraction_model": EXTRACTION_MODEL,
        "category_model": CATEGORY_MODEL,
        "num_products": len(experiment_results),
        "totals": {
            "api_calls": sum(r["num_api_calls"] for r in experiment_results),
            "input_tokens": sum(r["total_input_tokens"] for r in experiment_results),
            "output_tokens": sum(r["total_output_tokens"] for r in experiment_results),
            "cost": sum(r["total_cost"] for r in experiment_results),
        },
        "breakdown": {
            "extraction": {
                "input_tokens": total_extraction_input,
                "output_tokens": sum(r["extraction"]["output_tokens"] for r in experiment_results),
                "cost": total_extraction_cost,
            },
            "taxonomy": {
                "input_tokens": total_taxonomy_input,
                "output_tokens": sum(r["taxonomy"]["output_tokens"] for r in experiment_results),
                "cost": total_taxonomy_cost,
                "total_calls": sum(r["taxonomy"]["num_calls"] for r in experiment_results),
            },
        },
        "products": experiment_results,
    }

    with open(experiment_dir / "experiment.json", "w") as f:
        json.dump(experiment_info, f, indent=2)

    # Update aggregate summary
    summary = []
    if SUMMARY_FILE.exists():
        with open(SUMMARY_FILE, "r") as f:
            summary = json.load(f)

    total_cost = experiment_info["totals"]["cost"]
    num_products = len(experiment_results)

    summary.append({
        "name": args.name,
        "timestamp": timestamp,
        "extraction_model": EXTRACTION_MODEL,
        "category_model": CATEGORY_MODEL,
        "num_products": num_products,
        "total_input_tokens": experiment_info["totals"]["input_tokens"],
        "total_output_tokens": experiment_info["totals"]["output_tokens"],
        "total_cost": total_cost,
        "total_api_calls": experiment_info["totals"]["api_calls"],
        "cost_per_product": total_cost / num_products if num_products else 0,
        "extraction_cost": total_extraction_cost,
        "taxonomy_cost": total_taxonomy_cost,
    })

    with open(SUMMARY_FILE, "w") as f:
        json.dump(summary, f, indent=2)

    # Print summary
    print(f"\n{'='*60}")
    print(f"EXPERIMENT SUMMARY: {folder_name}")
    print(f"{'='*60}")
    print(f"  Extraction:  {total_extraction_input:>8} input tokens  ${total_extraction_cost:.6f}")
    print(f"  Taxonomy:    {total_taxonomy_input:>8} input tokens  ${total_taxonomy_cost:.6f}")
    print(f"  Total cost:         ${total_cost:.6f}")
    print(f"  Cost per product:   ${total_cost / num_products:.6f}")
    print(f"  Results saved to:   {experiment_dir}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
    