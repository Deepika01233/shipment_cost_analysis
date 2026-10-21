import pandas as pd
from pathlib import Path

# 1. File paths
BASE_DIR = Path(__file__).resolve().parent
SHIPMENTS_FILE = BASE_DIR / "shipment_records.csv"
NOTES_FILE = BASE_DIR / "context_notes.csv"
OUTPUT_FILE = BASE_DIR / "shipment_cost_analysis.csv"

# 2. Load input files
shipments = pd.read_csv(SHIPMENTS_FILE)
notes = pd.read_csv(NOTES_FILE)

shipments.columns = shipments.columns.str.strip()
notes.columns = notes.columns.str.strip()

shipments["shipment_date"] = pd.to_datetime(shipments["shipment_date"])
notes["date"] = pd.to_datetime(notes["date"])

print("Shipments loaded:", len(shipments))
print("Context notes loaded:", len(notes))

# 3. Calculate tonne-kilometres
shipments["tonne_km"] = (
    shipments["quantity_tonnes"] * shipments["distance_km"]
)

# 4. Assign each shipment to its week's Monday
shipments["week_of"] = (
    shipments["shipment_date"]
    - pd.to_timedelta(shipments["shipment_date"].dt.weekday, unit="D")
).dt.strftime("%Y-%m-%d")

# 5. Aggregate shipments by route and week
weekly = shipments.groupby(
    ["origin", "destination", "route_type", "week_of"],
    as_index=False
).agg(
    total_freight_cost=("freight_cost_inr", "sum"),
    total_tonne_km=("tonne_km", "sum"),
    shipment_count=("shipment_id", "count")
)

# 6. Calculate cost per tonne-kilometre
weekly["cost_per_tonne_km"] = (
    weekly["total_freight_cost"] / weekly["total_tonne_km"]
)

weekly = weekly.sort_values(
    ["origin", "destination", "route_type", "week_of"]
).reset_index(drop=True)

# 7. Compare with the previous eight weeks
weekly["vs_own_history"] = weekly.groupby(
    ["origin", "destination", "route_type"]
)["cost_per_tonne_km"].transform(
    lambda costs: costs.shift(1).rolling(window=8, min_periods=1).mean()
)

# 8. Compare with other routes of the same type and week
route_group = weekly.groupby(["route_type", "week_of"])
route_count = route_group["cost_per_tonne_km"].transform("count")
route_total = route_group["cost_per_tonne_km"].transform("sum")

weekly["vs_similar_routes"] = (
    (route_total - weekly["cost_per_tonne_km"])
    / (route_count - 1).where(route_count > 1)
)

# 9. Flag costs at least 10% above either baseline
weekly["flagged"] = (
    (
        weekly["vs_own_history"].notna()
        & (weekly["cost_per_tonne_km"] >= weekly["vs_own_history"] * 1.10)
    )
    |
    (
        weekly["vs_similar_routes"].notna()
        & (
            weekly["cost_per_tonne_km"]
            >= weekly["vs_similar_routes"] * 1.10
        )
    )
)

# 10. Create route labels
weekly["route"] = weekly["origin"] + "-" + weekly["destination"]


# 11. Match context notes
def match_note(row):
    week_start = pd.to_datetime(row["week_of"])
    week_end = week_start + pd.Timedelta(days=6)
    route_name = row["route"]

    applicable = (
        (notes["date"] <= week_end)
        & (
            notes["applies_to"].str.strip().str.lower().eq("all routes")
            | notes["applies_to"].eq(route_name)
        )
    )

    candidates = notes.loc[applicable].copy()

    irrelevant_phrases = [
        "returned to normal",
        "no significant disruptions",
        "costs were not significantly affected",
        "without a rate change",
        "affected routes are not part of this dataset",
        "stable demand",
    ]

    candidates = candidates[
        ~candidates["note"].str.lower().apply(
            lambda note: any(phrase in note for phrase in irrelevant_phrases)
        )
    ]

    def note_is_relevant(note_row):
        note_date = pd.to_datetime(note_row["date"])

        # Chennai-Bangalore flooding: Feb 24 to Mar 8, 2025
        if note_row["note_id"] == "N001":
            event_start = pd.Timestamp("2025-02-24")
            event_end = pd.Timestamp("2025-03-08")
            return (
                route_name == "Chennai-Bangalore"
                and week_start <= event_end
                and week_end >= event_start
            )

        # Nationwide diesel-price increase from May 5, 2025
        if note_row["note_id"] == "N003":
            return week_end >= note_date

        # Other notes apply only to their recorded week
        return week_start <= note_date <= week_end

    candidates = candidates[
        candidates.apply(note_is_relevant, axis=1)
    ]

    if candidates.empty:
        return pd.Series({
            "matched_note_id": "",
            "reason": (
                "Unusual cost detected; no matching context note found."
                if row["flagged"]
                else "No unusual cost detected."
            ),
        })

    specific = candidates[candidates["applies_to"].eq(route_name)]
    if not specific.empty:
        candidates = specific

    note = candidates.sort_values("date").iloc[-1]

    if row["flagged"]:
        return pd.Series({
            "matched_note_id": note["note_id"],
            "reason": f'Unusual cost detected. Context: {note["note"]}',
        })

    return pd.Series({
        "matched_note_id": "",
        "reason": "No unusual cost detected.",
    })


matched = weekly.apply(match_note, axis=1)
weekly[["matched_note_id", "reason"]] = matched

# 12. Create the required output
output = weekly[
    [
        "route",
        "week_of",
        "cost_per_tonne_km",
        "vs_own_history",
        "vs_similar_routes",
        "flagged",
        "matched_note_id",
        "reason",
    ]
].copy()

# 13. Save output
output.to_csv(OUTPUT_FILE, index=False)

# 14. Display summary
print("\nWeekly route records:", len(output))
print("Flagged records:", int(output["flagged"].sum()))
print("Records with matched notes:", int(output["matched_note_id"].ne("").sum()))
print("\nFlagged records (first 10):")
print(output.loc[output["flagged"]].head(10).to_string(index=False))
print("\nFirst 10 output records:")
print(output.head(10).to_string(index=False))
print(f"\nOutput saved to: {OUTPUT_FILE}")
