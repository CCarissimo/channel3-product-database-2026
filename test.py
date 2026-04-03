import ai
import asyncio
import logging
from pydantic import BaseModel
from models import FirstQueryProduct, Product, Category
from taxonomy import load_or_build_tree

CATEGORY_MODEL = "google/gemini-2.0-flash-lite-001"
MAX_RETRIES = 3


class CategorySelection(BaseModel):
    category: str


async def find_category(name: str, description: str) -> str:
    """Walk the taxonomy tree by asking the model to pick categories until a leaf is reached."""
    tree = load_or_build_tree()
    node = tree
    path = []

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
            result = await ai.responses(
                model=CATEGORY_MODEL,
                input=[{"role": "user", "content": prompt}],
                text_format=CategorySelection,
            )
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
    return full_category


async def test_ace():
    with open("./data/ace.html", "r") as f:
        html_content = f.read()

    product = await ai.responses(
        model="google/gemini-2.5-flash-lite",
        input=[
            {"role": "system", "content": "Extract the product information from the following HTML page."},
            {"role": "user", "content": html_content},
        ],
        text_format=FirstQueryProduct,
    )

    print(f"\nProduct: {product.name}")
    print(f"Description: {product.description[:100]}...")
    print(f"\nFinding category...")
    category = await find_category(product.name, product.description)

    final_product = Product(
        **product.model_dump(),
        category=Category(name=category),
    )

    print(f"\nFinal category: {category}")
    print(f"\n{final_product.model_dump_json(indent=2)}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_ace())
    