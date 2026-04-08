import json
from datetime import datetime
from pathlib import Path

from extraction import extract_product, EXTRACTION_MODEL, CATEGORY_MODEL

EXPERIMENTS_DIR = Path("./experiments")
SUMMARY_FILE = EXPERIMENTS_DIR / "summary.json"


async def run_experiment(html_files: list[Path], name: str | None = None) -> Path:
    """Run extraction on a list of HTML files and save results as an experiment.
    Returns the experiment directory path."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    folder_name = f"{timestamp}_{name}" if name else timestamp
    experiment_dir = EXPERIMENTS_DIR / folder_name
    experiment_dir.mkdir(parents=True, exist_ok=True)

    print(f"Experiment: {folder_name}")
    print(f"Found {len(html_files)} HTML file(s) to process")
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
        "name": name,
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
        "name": name,
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

    return experiment_dir
