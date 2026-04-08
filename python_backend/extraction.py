from . import ai
from pydantic import BaseModel
from .models import FirstQueryProduct, Product, Category
from .taxonomy import load_or_build_tree
from .html_preprocessing import preprocess

CATEGORY_MODEL = "google/gemini-2.0-flash-lite-001"
EXTRACTION_MODEL = "google/gemini-2.5-flash-lite"
MAX_RETRIES = 3


class CategorySelection(BaseModel):
    category: str


async def find_category(name: str, description: str) -> tuple[str, list[dict]]:
    """Walk the taxonomy tree by asking the model to pick categories until a leaf is reached.
    Returns (full_category_path, list_of_usage_dicts)."""
    tree = load_or_build_tree()
    usage_log = []

    for full_attempt in range(MAX_RETRIES):
        node = tree
        path = []
        failed = False

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
            else:
                print(f"  '{selected}' not in valid options at level: {' > '.join(path) or 'root'}, restarting ({full_attempt + 1}/{MAX_RETRIES})")
                failed = True
                break

        if not failed:
            full_category = " > ".join(path)
            print(f"  Leaf reached: {full_category}")
            return full_category, usage_log

    raise ValueError(f"Model failed to find a valid category after {MAX_RETRIES} full attempts")


async def extract_product(html_path: str) -> tuple[Product, list[dict]]:
    """Extract a Product from an HTML file, including category discovery.
    Returns (product, list_of_all_usage_dicts)."""
    with open(html_path, "r") as f:
        html_content = preprocess(f.read())

    schema_description = FirstQueryProduct.model_json_schema()

    messages = [
        {"role": "system", "content": (
            "Extract the product information from the following HTML page.\n\n"
            "Output must conform to this schema:\n"
            f"{schema_description}\n\n"
            "Important:\n"
            "- All numeric fields (price, compare_at_price) must be plain numbers, not strings. "
            "Do not include currency symbols or text in numeric fields. "
            "Currency should be a separate string field (e.g. 'USD', 'EUR').\n"
            "- Variants represent product options a customer can choose from, such as sizes, colors, or fits. "
            "Each variant has a 'name' (e.g. 'Size', 'Color', 'Fit') and 'options' (e.g. ['S', 'M', 'L', 'XL']). "
            "Only include variants that are explicitly present on the product page. "
            "If no variants are found, return an empty list.\n"
            "- Keep the description concise (under 500 characters).\n"
            "- Keep key_features to at most 5 items, each under 100 characters."
        )},
        {"role": "user", "content": html_content},
    ]

    from pydantic import ValidationError as PydanticValidationError
    from pydantic_core import ValidationError as PydanticCoreValidationError
    for attempt in range(MAX_RETRIES):
        try:
            product, extraction_usage = await ai.responses(
                model=EXTRACTION_MODEL,
                input=messages,
                text_format=FirstQueryProduct,
                max_output_tokens=16384,
            )
            break
        except (PydanticValidationError, PydanticCoreValidationError) as e:
            if attempt < MAX_RETRIES - 1:
                print(f"  Extraction attempt {attempt + 1} failed (truncated output), retrying...")
                continue
            raise
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
