# Freight Cost Smart Assistant

## Overview
This project analyzes shipment records to identify unusual weekly freight costs and provides relevant explanations from available context notes.

## Input Files
- `shipment_records.csv` — shipment details, route, quantity, distance, freight cost, and shipment date.
- `context_notes.csv` — notes about route disruptions, fuel prices, festivals, and other events.
- `sample_output_format_v2.csv` — reference for the required output columns.

## Methodology

### 1. Weekly aggregation
Shipments are grouped by origin, destination, route type, and week. Weeks start on Monday, and `week_of` contains the Monday date.

### 2. Cost per tonne-kilometre
Cost per tonne-kilometre is calculated as:

`Total freight cost / Total tonne-kilometres`

Total tonne-kilometres are calculated by summing `quantity_tonnes × distance_km`.

### 3. Historical comparison
Each route's weekly cost is compared with the average cost of its previous eight available weekly records. The current week is excluded. When fewer than eight prior records exist, all available prior records are used.

### 4. Similar-route comparison
Each route's cost is compared with the same-week average for other routes with the same route type. The route itself is excluded.

### 5. Anomaly rule
A record is flagged when its cost is at least 10% above either its historical average or its similar-route average, where that comparison is available.

The 10% threshold is a chosen heuristic because the case study does not specify a threshold.

### 6. Context matching
Context notes are matched using their dates and route applicability. Route-specific notes are preferred over notes applying to all routes. Notes that explicitly state that conditions returned to normal or that costs were unaffected are excluded from explanations.

A flagged record may have no matching note. In that case, the output states that no matching context note was found rather than inventing an explanation.

## Output
The program generates `shipment_cost_analysis.csv` with these columns:

`route, week_of, cost_per_tonne_km, vs_own_history, vs_similar_routes, flagged, matched_note_id, reason`

## How to Run
Install the dependency if needed:

`python -m pip install pandas`

Run the program from the project folder:

`python main.py`

## Current Run

- Shipment records loaded: 2,940
- Context notes loaded: 10
- Weekly route records generated: 728
- Flagged records: 90
- Records with matched notes: 35

## Validation

- Basic output checks passed.
- Output contains all 8 required columns.
- Reproducibility check passed: three consecutive runs produced identical SHA256 hashes.
- SHA256: `888BF39BB99874EEE40EA38DE83959D022DD9FD7B0EBA9EB20A3B715FED737F5`

## Limitations

The anomaly threshold is heuristic. Context matching uses the supplied notes and does not establish that a note caused a cost increase. Some flagged records have no matching context note. Results should be reviewed before making operational decisions.

No language-model API is used in the current implementation, so LLM token usage and API cost are zero.
