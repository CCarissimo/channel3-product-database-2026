## Channel3 Take Home Assignment

# System Design
Getting this system to web-scale will require identifying the biggest bottlenecks, and trying to find the most general fixes. LLM APIs are very good at extracting hetereogenous text, but can become expensive over time. The biggest savings comes from sending fewer input tokens to the LLM, and requesting the least output tokens. I would spend a lot of time optimizing these dimensions. For example, different pages stored their images in different parts of the code, which means that we need a way to quickly detect these kinds of design choices. This can be done with some simple scripts that help to determine the html that can be stripped. I would approach this similarly as a tree-like tool, where given an html file we first process it with some rule based analysis to determine its structure and contents, and create the best possible pre-processing before we pass any of it to large language models. I would also consider fine-tuning a model on the desired outputs so that over time we can get more and more self-similar and user preferred PDPs.

I would change the frontend with React, where now it is just a python setup. I would look into making sure that we only display the correct images, as right now it seems we are fetching more images that may not pertain to the specific product. I would work on making the individual React components modular so that they can easily be fit into any structure. Ideally, you can pass an object that has a standardized form and function to any application, it will be easily displayed, and it can be easily manipulated irrespective of its context. That would be the end goal I'd strive for, and I would set myself to study how to achieve that. 

# Setup

## Prerequisites
- Python 3.12+
- An OpenRouter API key

## Installation

```bash
pip install openai python-dotenv pydantic
```

Create a `.env` file in the root directory:

```
OPEN_ROUTER_API_KEY=your_key_here
```

# Usage

## Product Extraction (Backend)

Extract product data from HTML files using LLM-powered extraction with automatic category classification via Google Product Taxonomy.

### Single file
```bash
python main.py data/ace.html --name "single_product"
```

### Directory of HTML files
```bash
python main.py data/ --name "full_batch"
```

### Quick test (all files in data/)
```bash
python test.py
```

Results are saved to `experiments/<timestamp>_<name>/` with per-product JSON files containing extracted product schemas and token usage metrics.

## Dashboard (Frontend)

View extracted products, compare experiments, and track optimization metrics.

```bash
python serve.py
```

Opens `http://localhost:8000/frontend/` with:
- **Overview tab** — charts comparing cost, tokens, and extraction vs taxonomy breakdown across experiments
- **Experiment tabs** — product grid with images, click any product to open a detail page (PDP) with images, description, features, variants, colors, and category
- **Cost bar** — per-experiment token usage and cost summary

## Other Tools

### Taxonomy CLI
Browse the Google Product Taxonomy tree interactively:
```bash
python taxonomy.py                                    # top-level categories
python taxonomy.py --subcat "Hardware"                 # subcategories
python taxonomy.py --subcat "Hardware" --subcat "Tools" --subcat "Drills"
```

### HTML Analysis
Analyze HTML file composition (scripts, styles, attributes, etc.):
```bash
python html_analysis.py
```

### HTML Preprocessing
Preview the preprocessed HTML that gets sent to the model:
```bash
python html_preprocessing.py data/ace.html
python html_preprocessing.py data/ace.html -o cleaned.html
```

# Project Structure

```
main.py                 # CLI entry point for product extraction
test.py                 # Quick test runner for all data/ files
extraction.py           # Core extraction + category discovery logic
experiment.py           # Experiment orchestration + metrics tracking
ai.py                   # OpenRouter API wrapper with token tracking
models.py               # Pydantic models (Product, Category, Price, SingleVariant)
taxonomy.py             # Google Product Taxonomy tree CLI + loader
html_preprocessing.py   # HTML preprocessing pipeline
html_analysis.py        # HTML content breakdown analysis
serve.py                # Local dev server for the dashboard
frontend/index.html     # Dashboard UI
categories.txt          # Google Product Taxonomy (source)
data/                   # Input HTML product pages
experiments/            # Output: experiment results + summary
```
