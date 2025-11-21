from pathlib import Path

# Base directory = folder where this config.py is located
BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"

# Make sure output directory exists
OUTPUT_DIR.mkdir(exist_ok=True)