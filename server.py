"""
BLA Maintenance Dashboard - Backend
===================================
Flask server powering a local web UI with a three-level drill-down:

    BLA Division  ->  Department  ->  Machine (EQ ID)  ->  4 tabs
        (dashboard)     (dashboard)     1. Dashboard
                        + machines      2. AI Troubleshooting Checklist (Ollama)
                                        3. Unscheduled work orders
                                        4. Scheduled work orders

Only two departments are surfaced: "Soap Dispenser Assembly" (Soap & Assembly)
and "Toilet Partitions".

It reuses the stats / prompt / Ollama logic from analyze_equipment.py (including
the Windows-TLS PowerShell transport, since the corporate network blocks the
OpenSSL-based TLS that Python would otherwise use).

Run:
    python server.py
Then open http://127.0.0.1:5000 in your browser.

Per-machine troubleshooting checklists are cached as Markdown in
./guides/<equipment_id>.md and only regenerated when explicitly requested.
"""

import os
from collections import Counter

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

import analyze_equipment as ae

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
WEBAPP_DIR = os.path.join(OUTPUT_DIR, "webapp")
GUIDES_DIR = os.path.join(OUTPUT_DIR, "guides")

# Gemini model name (only used if LLM_PROVIDER=gemini). Checklists default to
# Ollama Cloud because OLLAMA_API_KEY is present in the .env file.
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# Ollama Cloud model. The default in analyze_equipment.py ("gemma4:31b") is not
# a real cloud model, so pin a valid one here unless the user overrides it.
ae.OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gpt-oss:120b")

os.makedirs(GUIDES_DIR, exist_ok=True)

app = Flask(__name__, static_folder=WEBAPP_DIR, static_url_path="")
CORS(app)

# --------------------------------------------------------------------------- #
# Division / department configuration
# --------------------------------------------------------------------------- #
DIVISION = {"key": "bla", "name": "BLA"}

DEPARTMENTS = {
    "soap": {
        "key": "soap",
        "name": "Soap Dispenser Assembly",
        "label": "Soap & Assembly",
        "unscheduled": "work_orders_unscheduled_soap_dispenser_assembly.json",
        "scheduled": "work_orders_scheduled_soap_dispenser_assembly.json",
    },
    "toilet": {
        "key": "toilet",
        "name": "Toilet Partitions",
        "label": "Toilet Partitions",
        "unscheduled": "work_orders_unscheduled_toilet_partitions.json",
        "scheduled": "work_orders_scheduled_toilet_partitions.json",
    },
}


# --------------------------------------------------------------------------- #
# Machine grouping (within a department)
# --------------------------------------------------------------------------- #
# Ordered groups for the Toilet Partitions department. Names are the ACTUAL
# equipment_name strings as they appear in the scraped data (matched after
# light normalization), so minor spacing/quote differences still line up.
TOILET_GROUP_ORDER = [
    "Machines", "Vehicles", "General", "Equipment", "Gages and Jigs",
    "Carts", "Tools",
]

TOILET_GROUPS = {
    "Machines": [
        '1/2 " Edge Finisher, Solid, Technolegno/ Universal 280',
        '3/4 " Edge Finisher, Solid, Technolegno/ Universal 280',
        'CNC Drilling Machine, Automatic Leveling Bar',
        'Chop Saw (corner guard pack out Lam.)',
        'Chop saw by Holzma Saw',
        'Drill Press (Stile Building Cell)',
        'Drilling Machine CNC, 1040 Laminate',
        'Edge Finisher Laminate',
        'Edgebander Homag 2520 Servo 6 Coil',
        'Evolve Double Head Drilling Machine',
        'Gannomat Index 330 Trend/PRO (Solid)',
        'Insert 1 Screwdriver, Auto Reverse, Lever',
        'Insert Screwdriver, 1080 -1',
        'Laminate Slitter',
        'Notching machine, 1540 Door',
        'O-Sama (Joos) Glue Spreader',
        'Pinch Roller (Heated)',
        'Router Station (Stile Building cell)',
        'Router, CNC, Anderson Stratos/Nest TC+D',
        "Saw, 10' Panel, Laminate Line",
        'Saw, Horizontal, Holzma',
        'Saw,Horizontal, Holz-Her',
        'Screwdriver, Insert, 1080-2',
        'Step Drill 1080/1090 CNC Drilling Machine',
        'TLF Intellistore (Rainbow Stacking System)- TLF211',
        'Tenoner A 517 Single End',
        'VLM Storage Lift -Small Hardware',
    ],
    "Vehicles": [
        'Forklift # T20',
        'Forklift # T4',
        'Forklift # T5',
        'Scissor Lift #1 (small) Holz-Her Saw',
        'Scissor Lift Holz-Her Edge Bander',
        'Scissor Lift Holzma Saw',
        'Sissors Lift, HolzHer Saw',
        'Stacker R-19',
    ],
    "General": [
        'Concrete floor',
        'Flamex spark detection and extinguishing system',
        'General Maintenance',
        'Laminate Cell',
        'Solid Cell',
        'TPF',
    ],
    "Equipment": [
        '1/2 Pop-up table made in house',
        '2 gallon glue tank with hand held glue nozzle gun',
        '3/4 Thomas return system',
        'Dust Collector, Donaldson Downflo Oval',
        'Edge finisher Pop UP table',
        'Edgebander Pop up table',
        'Evolve cell Pop UP table',
        'FLIP TABLE',
        'POP UP Table, 3/4" Edge Finisher',
        'Return System, Thomas, 1/2" Solid Panels',
        'Return System, Thomas, 1040 Edgebander',
        'Return System, Thomas, Laminate Trimmer',
        'Return system,Thomas,Evolve cell',
        'Vacuum Lift (Anderson CNC)',
        'Vacuum Lift 1/2" panels packout',
        'Vacuum Lift 1080 Line packout',
        'Vacuum Lift Evolve Cell',
        'Vacuum Lift Holz-Her Saw',
        'Vacuum Lift Laminate Pack Out',
        'Vacuum Lift System (Glue Line )',
    ],
    "Gages and Jigs": [
        'CNC Drill Setup Gage-1040',
        'CNC Drill Setup Gage-1080',
        'Cutout Jig B3471/B3571',
        'Cutout Jig B357, B347',
        'Drill Jig - OS Door Hinge',
        'Drill Jig, 1080/ 1090 Leveling Bar',
        'Gage (Go/No Go), Drill Diameter, Laminate',
        'Gage (Go/No Go), Drill Diameter, Solid',
        'Jig, Drill, T-203040 ECOR T-Nut Drill, Laminate',
        'Laminate Drill Hole Depth Gage',
        'TPT CL 1005 ANDY',
    ],
    "Carts": [
        'Drywall Carts 1-15',
        'Job Carts 1-6',
        'Materal Carts 1-2',
        'Pack out Carts 1-6',
    ],
    "Tools": [
        'Driver, Pulse Tool, 1080 Leveling Bar',
        'Driver, Pulse Tool, 1080 Leveling Bar,Desoutter model PTF022-T6500-S4Q',
        'Shaper, Single Spindle, Northfield',
        'Step Drill & Stop Phenolic Series Insert',
    ],
}

OTHER_GROUP = "Other"


def _norm_name(name: str) -> str:
    """Normalize an equipment name for tolerant matching."""
    s = (name or "").lower().strip()
    for ch in ('"', "'", "\u201c", "\u201d", "\u2018", "\u2019"):
        s = s.replace(ch, "")
    return " ".join(s.split())


# group config per department key -> (ordered group names, {normalized name: group})
def _build_group_lookup(groups: dict) -> tuple[list, dict]:
    lookup = {}
    for grp, names in groups.items():
        for n in names:
            lookup[_norm_name(n)] = grp
    return list(groups.keys()), lookup


_DEPT_GROUPS = {
    "toilet": _build_group_lookup(TOILET_GROUPS),
}


def _group_for(dept_key: str, name: str) -> str | None:
    cfg = _DEPT_GROUPS.get(dept_key)
    if not cfg:
        return None
    return cfg[1].get(_norm_name(name), OTHER_GROUP)


def _group_order(dept_key: str) -> list:
    cfg = _DEPT_GROUPS.get(dept_key)
    if not cfg:
        return []
    return cfg[0] + [OTHER_GROUP]


def _load(filename: str) -> list[dict]:
    path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(path):
        return []
    return ae.load_work_orders(path)


# Loaded once at startup; restart the server to pick up new scrapes.
_DEPT_DATA: dict[str, dict[str, list[dict]]] = {}
for _key, _cfg in DEPARTMENTS.items():
    _uns = _load(_cfg["unscheduled"])
    _sch = _load(_cfg["scheduled"])
    for _r in _uns:
        _r["wo_type"] = "unscheduled"
        _r["department_key"] = _key
    for _r in _sch:
        _r["wo_type"] = "scheduled"
        _r["department_key"] = _key
    _DEPT_DATA[_key] = {"unscheduled": _uns, "scheduled": _sch}

# Flat index for fast single work-order lookup (wo_id -> record).
_WO_INDEX: dict[str, dict] = {}
for _data in _DEPT_DATA.values():
    for _kind in ("unscheduled", "scheduled"):
        for _r in _data[_kind]:
            _wid = str(_r.get("wo_id") or "").strip()
            if _wid and _wid not in _WO_INDEX:
                _WO_INDEX[_wid] = _r


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _totals(records: list[dict]) -> dict:
    """Sum the three numeric KPI fields across a list of records."""
    return {
        "labor_time": round(sum(ae._to_float(r.get("labor_time")) for r in records), 2),
        "material_cost": round(sum(ae._to_float(r.get("material_cost")) for r in records), 2),
        "downtime_hours": round(sum(ae._to_float(r.get("downtime_hours")) for r in records), 2),
    }


def _stats(unscheduled: list[dict], scheduled: list[dict]) -> dict:
    allr = unscheduled + scheduled
    t = _totals(allr)
    t["unscheduled_count"] = len(unscheduled)
    t["scheduled_count"] = len(scheduled)
    return t


def _machine_groups(dept_key: str) -> dict[str, dict[str, list[dict]]]:
    """Group a department's work orders by equipment_id (the EQ ID)."""
    data = _DEPT_DATA.get(dept_key)
    if data is None:
        return {}
    groups: dict[str, dict[str, list[dict]]] = {}
    for kind in ("unscheduled", "scheduled"):
        for r in data[kind]:
            eq = (r.get("equipment_id") or "").strip()
            if not eq:
                continue
            groups.setdefault(eq, {"unscheduled": [], "scheduled": []})[kind].append(r)
    return groups


def _machine_name(records: list[dict]) -> str:
    names = [(r.get("equipment_name") or "").strip() for r in records if r.get("equipment_name")]
    if not names:
        return "Unknown"
    return Counter(names).most_common(1)[0][0]


def _eq_label(records: list[dict], eq_id: str) -> str:
    for r in records:
        lbl = (r.get("equipment_eq_id") or "").strip()
        if lbl:
            return lbl
    return f"EQ ID {eq_id}"


def _guide_path(eq_id: str) -> str:
    safe = "".join(c for c in str(eq_id) if c.isalnum() or c in ("-", "_"))
    return os.path.join(GUIDES_DIR, f"{safe}.md")


# --------------------------------------------------------------------------- #
# Static
# --------------------------------------------------------------------------- #
@app.route("/")
def index():
    return send_from_directory(WEBAPP_DIR, "index.html")


# --------------------------------------------------------------------------- #
# Division
# --------------------------------------------------------------------------- #
@app.route("/api/division")
def api_division():
    depts = []
    all_uns: list[dict] = []
    all_sch: list[dict] = []
    for key, cfg in DEPARTMENTS.items():
        data = _DEPT_DATA[key]
        uns, sch = data["unscheduled"], data["scheduled"]
        all_uns += uns
        all_sch += sch
        stats = _stats(uns, sch)
        stats.update({
            "key": key,
            "name": cfg["name"],
            "label": cfg["label"],
            "machine_count": len(_machine_groups(key)),
        })
        depts.append(stats)
    return jsonify({
        "key": DIVISION["key"],
        "name": DIVISION["name"],
        "departments": depts,
        "totals": _stats(all_uns, all_sch),
    })


# --------------------------------------------------------------------------- #
# Department
# --------------------------------------------------------------------------- #
@app.route("/api/departments/<dept_key>")
def api_department(dept_key):
    cfg = DEPARTMENTS.get(dept_key)
    if not cfg:
        return jsonify({"error": "department not found"}), 404

    data = _DEPT_DATA[dept_key]
    groups = _machine_groups(dept_key)

    machines = []
    for eq_id, recs in groups.items():
        uns, sch = recs["unscheduled"], recs["scheduled"]
        combined = uns + sch
        stats = _stats(uns, sch)
        name = _machine_name(combined)
        stats.update({
            "eq_id": eq_id,
            "eq_label": _eq_label(combined, eq_id),
            "name": name,
            "group": _group_for(dept_key, name),
            "has_guide": os.path.exists(_guide_path(eq_id)),
        })
        machines.append(stats)

    # Sort machines by most unscheduled work orders (most troublesome first).
    machines.sort(key=lambda m: (-m["unscheduled_count"], m["name"]))

    # Only advertise groups that actually contain machines, preserving order.
    present = {m["group"] for m in machines if m.get("group")}
    groups = [g for g in _group_order(dept_key) if g in present]

    return jsonify({
        "key": dept_key,
        "name": cfg["name"],
        "label": cfg["label"],
        "stats": _stats(data["unscheduled"], data["scheduled"]),
        "machines": machines,
        "groups": groups,
    })


# --------------------------------------------------------------------------- #
# Machine
# --------------------------------------------------------------------------- #
@app.route("/api/departments/<dept_key>/machines/<eq_id>")
def api_machine(dept_key, eq_id):
    if dept_key not in DEPARTMENTS:
        return jsonify({"error": "department not found"}), 404
    groups = _machine_groups(dept_key)
    recs = groups.get(eq_id)
    if recs is None:
        return jsonify({"error": "machine not found"}), 404

    uns, sch = recs["unscheduled"], recs["scheduled"]
    combined = uns + sch
    return jsonify({
        "machine": {
            "eq_id": eq_id,
            "eq_label": _eq_label(combined, eq_id),
            "name": _machine_name(combined),
            "department": DEPARTMENTS[dept_key]["name"],
            "department_key": dept_key,
            "has_guide": os.path.exists(_guide_path(eq_id)),
        },
        "stats": _stats(uns, sch),
        "unscheduled": uns,
        "scheduled": sch,
    })


# --------------------------------------------------------------------------- #
# Work order detail
# --------------------------------------------------------------------------- #
@app.route("/api/workorder/<wo_id>")
def api_workorder(wo_id):
    rec = _WO_INDEX.get(str(wo_id).strip())
    if rec is None:
        return jsonify({"error": "work order not found"}), 404
    return jsonify(rec)


# --------------------------------------------------------------------------- #
# Per-machine troubleshooting checklist (Ollama)
# --------------------------------------------------------------------------- #
@app.route("/api/departments/<dept_key>/machines/<eq_id>/guide")
def api_get_guide(dept_key, eq_id):
    path = _guide_path(eq_id)
    if not os.path.exists(path):
        return jsonify({"exists": False, "markdown": None})
    with open(path, encoding="utf-8") as f:
        return jsonify({
            "exists": True,
            "markdown": f.read(),
            "generated_at": os.path.getmtime(path),
        })


@app.route("/api/departments/<dept_key>/machines/<eq_id>/guide", methods=["POST"])
def api_generate_guide(dept_key, eq_id):
    if dept_key not in DEPARTMENTS:
        return jsonify({"error": "department not found"}), 404
    groups = _machine_groups(dept_key)
    recs = groups.get(eq_id)
    if recs is None:
        return jsonify({"error": "machine not found"}), 404

    # Checklist is built ENTIRELY from the machine's unscheduled (breakdown)
    # work orders, per the requirements.
    unscheduled = recs["unscheduled"]
    if not unscheduled:
        return jsonify({"error": "no unscheduled work orders to analyze for this machine"}), 400

    label = f"{_machine_name(unscheduled)} ({_eq_label(unscheduled, eq_id)})"
    stats = ae.build_stats(unscheduled)
    prompt = ae.build_troubleshoot_prompt(unscheduled, stats, label)

    try:
        markdown = ae.analyze(prompt, MODEL)
    except SystemExit as e:  # analyze() calls sys.exit on failure
        return jsonify({"error": str(e)}), 502

    path = _guide_path(eq_id)
    with open(path, "w", encoding="utf-8") as f:
        f.write(markdown)

    return jsonify({
        "exists": True,
        "markdown": markdown,
        "generated_at": os.path.getmtime(path),
    })


if __name__ == "__main__":
    print("BLA Maintenance Dashboard running at http://127.0.0.1:5000")
    print(f"  Checklist provider: {'ollama' if os.environ.get('OLLAMA_API_KEY') else 'gemini'} "
          f"(model: {ae.OLLAMA_MODEL})")
    app.run(host="127.0.0.1", port=5000, threaded=True, debug=False)
