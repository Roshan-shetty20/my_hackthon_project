# Crisis Command - Demo Script (3 minutes)

## Setup
```bash
streamlit run app.py
```

## Step 1: Initialize (15s)
- Click "Initialize Crisis" in sidebar
- Show 3 incidents with severity badges on map
- Show 5 available units on map
- Point out: "3 incidents, 5 units, all in Surat"

## Step 2: Generate Plans (30s)
- Click "Generate Plans"
- Show Plan Comparison tab: 3 strategies side by side
- Point out: NEAREST and SEVERITY are INVALID (reserve violation)
- Only BALANCED maintains reserve
- Show resilience score and single points of failure

## Step 3: Approve (10s)
- Click "Approve Recommended Plan"
- Show green "APPROVED" badge
- Show assignment lines on map

## Step 4: Break AMB-01 (30s)
- Select AMB-01 in sidebar dropdown
- Click "Simulate Breakdown"
- Show map update: AMB-01 turns red
- Show Plan Diff tab: what changed and why
- Show new recommendation with lower score

## Step 5: Add Road Block (20s)
- Select a road, click "Simulate Road Block"
- Show ETA changes in Plan Diff
- Show replanning with road blocked on map

## Step 6: New Critical Incident (30s)
- Click "Add Gas Leak Incident"
- Show new red marker on map
- Show replanning under maximum stress
- Point out coverage trade-offs

## Step 7: Conclusion (15s)
- Show Action Log tab: full timeline
- Show Agent Activity: every agent action timestamped
- Key message: "We don't just find a plan. We find a plan that survives the next surprise."

## Key Talking Points
- Deterministic safety: LLM never allocates resources
- 3 strategies compared transparently
- Resilience engine: stress-test before approval
- Plan diff: see exactly what changed
- Human in the loop: approve/reject/override
