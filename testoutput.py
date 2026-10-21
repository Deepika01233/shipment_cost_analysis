
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = BASE_DIR / "shipment_cost_analysis.csv"

# Load the generated output
df = pd.read_csv(OUTPUT_FILE)

# Required output columns
expected_columns = [
    "route",
    "week_of",
    "cost_per_tonne_km",
    "vs_own_history",
    "vs_similar_routes",
    "flagged",
    "matched_note_id",
    "reason",
]

# Run checks
assert list(df.columns) == expected_columns, "Output columns do not match!"
assert len(df) > 0, "Output file is empty!"
assert df["route"].notna().all(), "Some routes are missing!"
assert df["week_of"].notna().all(), "Some week dates are missing!"
assert df["cost_per_tonne_km"].notna().all(), "Some costs are missing!"
assert df["flagged"].notna().all(), "Some flag values are missing!"
assert df["flagged"].isin([True, False]).all(), "Invalid flag values found!"

print("All basic output checks passed!")
print("Total output records:", len(df))
print("Flagged records:", int(df["flagged"].sum()))
print("Output columns:", len(df.columns))
