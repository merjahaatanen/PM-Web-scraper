import json

with open("equipment_data.json", encoding="utf-8") as f:
    records = json.load(f)

toilet = [r for r in records if (r.get("dept") or "").strip() == "Toilet Partitions"]
print(f"Total toilet machines: {len(toilet)}")

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
        'Step Drill 1040 CNC Drilling Machine',
        'Step Drill 1080/1090 CNC Drilling Machine',
        'TLF Intellistore (Rainbow Stacking System)- TLF211',
        'Tenoner A 517 Single End',
        'VLM Storage Lift -Small Hardware',
    ],
    "Vehicles": [
        'Forklift # T20', 'Forklift # T4', 'Forklift # T5',
        'Scissor Lift #1 (small) Holz-Her Saw',
        'Scissor Lift Holz-Her Edge Bander',
        'Scissor Lift # 2 (large) Holz-Her Saw',
        'Scissor Lift 1/2" Edge Finisher',
        'Scissor Lift 3/4" solid Edge Finisher',
        'Scissor Lift Holzma Saw',
        'Sissors Lift, HolzHer Saw',
        'Stacker R-19',
    ],
    "General": [
        'Concrete floor', 'Flamex spark detection and extinguishing system',
        'General Maintenance', 'Laminate Cell', 'Solid Cell', 'TPF',
    ],
    "Equipment": [
        '1/2 Pop-up table made in house',
        '2 gallon glue tank with hand held glue nozzle gun',
        '3/4 Thomas return system',
        'Dust Collector, Donaldson Downflo Oval',
        'FRL - Filter, Regulator, Lubricator',
        'Meyer rotary airlock (dust collector)',
        'Panel Handler - 4ft',
        'Rework Station (Laminate Cell)',
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
        'CNC Drill Setup Gage-1040', 'CNC Drill Setup Gage-1080',
        'Cutout Jig B3471/B3571', 'Cutout Jig B357, B347',
        'Drill Jig - OS Door Hinge',
        'Drill Jig - for Door Hinges ( 3 Hinges) Laminate',
        'Drill Jig - for Door Hinges Laminate',
        'Drill Jig - for Hinges Stile -I/S-O/S FC For Laminate',
        'Drill Jig - for Hinges for O/S Stile Hinges',
        'Drill Jig, 1080/ 1090 Leveling Bar',
        'Gage (Go/No Go), Drill Diameter, Laminate',
        'Gage (Go/No Go), Drill Diameter, Solid',
        'Jig, Drill, T-203040 ECOR T-Nut Drill, Laminate',
        'Laminate Drill Hole Depth Gage', 'TPT CL 1005 ANDY', 'TPT CL 1005 TENO',
    ],
    "Carts": [
        'Cart - TPF Finish Goods',
        'Drywall Carts 1-15', 'Job Carts 1-6',
        'Materal Carts 1-2', 'Pack out Carts 1-6',
    ],
    "Tools": [
        'Driver, Pulse Tool, 1080 Leveling Bar',
        'Driver, Pulse Tool, 1080 Leveling Bar,Desoutter model PTF022-T6500-S4Q',
        'Shaper, Single Spindle, Northfield',
        'Step Drill & Stop Phenolic Series Insert',
    ],
}


def norm(s):
    s = (s or "").lower().strip()
    for ch in ('"', "'", "\u201c", "\u201d", "\u2018", "\u2019"):
        s = s.replace(ch, "")
    return " ".join(s.split())


lookup = {}
for grp, names in TOILET_GROUPS.items():
    for n in names:
        lookup[norm(n)] = grp

unmatched = []
for r in toilet:
    name = (r.get("equipment_name") or "").strip()
    if norm(name) not in lookup:
        unmatched.append(name)

print(f"Unmatched: {len(unmatched)}")
for n in sorted(unmatched):
    print(" -", repr(n))
