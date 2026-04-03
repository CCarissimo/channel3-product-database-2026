import ai
import asyncio
import logging
from models import Product

async def test_ace():
    with open("./data/ace.html", "r") as f:
        html_content = f.read()

    product = await ai.responses(
        model="google/gemini-2.5-flash-lite",
        input=[
            {"role": "system", "content": "Extract the product information from the following HTML page."},
            {"role": "user", "content": html_content},
        ],
        text_format=None,
    )
    print(product.model_dump_json(indent=2))

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_ace())
    