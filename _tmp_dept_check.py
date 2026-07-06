import json
from collections import Counter

with open("work_orders_scheduled.json", encoding="utf-8") as f:
    sch = json.load(f)
with open("work_orders_unscheduled.json", encoding="utf-8") as f:
    uns = json.load(f)

all_records = sch + uns

dept_counts = Counter((r.get("department") or "").strip() for r in all_records)
print("=== Departments in combined files ===")
for dept, count in sorted(dept_counts.items(), key=lambda x: -x[1]):
    print(f"  {count:>5}  {dept!r}")

print()
# Check specific departments of interest
for dept in ["Machine Shop", "Assembly", "Shipping", "Mfg Engineering", "Quality Assurance"]:
    recs = [r for r in all_records if (r.get("department") or "").strip() == dept]
    s = sum(1 for r in recs if r.get("wo_type") == "scheduled" or r in sch)
    print(f"{dept}: {len(recs)} total records")
    # Show sample equipment names
    equip = list({(r.get("equipment_name") or "").strip() for r in recs})[:8]
    for e in equip:
        print(f"    {e!r}")
