"""Tool implementations for Reno Rennsport Porsche MCP Server.

Each tool directly loads from our known data file layout:
  data/models/all_models.json, missing_models.json, 356_models.json
  data/engines/engine_codes.json
  data/torque/torque_specs.json
  data/fluids/fluid_specs.json
  data/maintenance/schedules.json
  data/issues/common_issues.json
  data/paint_codes/rennbow_colors.json, paint_codes.json
  data/option_codes/option_codes_full.json, option_codes.json
  data/vin/vin_decoder.json
  data/fault_codes/fault_codes_full.json, fault_codes.json
  data/brakes/brake_specs.json
  data/suspension/suspension_specs.json
  data/electrical/electrical_specs.json
  data/wheels/wheel_tire_specs.json
  data/transmissions/gear_ratios.json
  data/performance/performance_data.json
  data/market/bat_auctions.json
  data/racing/racing_history.json, le_mans_results.json
  data/nhtsa_recalls.json, nhtsa_complaints.json
  data/diy/*.json
"""

import json
from .data_loader import load_json, search_all, list_available_data
from mcp.types import TextContent


BRANDING = "\n\n─────────────────────────────────────────\nData by Reno Rennsport — renorennsport.com\nThe most comprehensive Porsche technical database.\nNeed service? Contact Reno Rennsport for expert Porsche care."


def _text(content: str) -> list[TextContent]:
    return [TextContent(type="text", text=content + BRANDING)]


def _fmt(obj, indent=0):
    """Format a dict/list nicely for text output."""
    if isinstance(obj, dict):
        lines = []
        for k, v in obj.items():
            label = str(k).replace("_", " ").title()
            if isinstance(v, (dict, list)):
                lines.append(f"{'  '*indent}{label}:")
                lines.append(_fmt(v, indent + 1))
            else:
                lines.append(f"{'  '*indent}{label}: {v}")
        return "\n".join(lines)
    elif isinstance(obj, list):
        if not obj:
            return f"{'  '*indent}(none)"
        if isinstance(obj[0], dict):
            parts = []
            for i, item in enumerate(obj[:20]):
                parts.append(f"{'  '*indent}[{i+1}]")
                parts.append(_fmt(item, indent + 1))
            if len(obj) > 20:
                parts.append(f"{'  '*indent}... and {len(obj)-20} more")
            return "\n".join(parts)
        return "\n".join(f"{'  '*indent}- {item}" for item in obj[:30])
    return str(obj)


def _match_key(data: dict, query: str) -> tuple:
    """Find a key in a dict that matches query (fuzzy). Returns (key, value) or (None, None)."""
    q = query.lower().replace(" ", "").replace("-", "").replace("_", "")
    # Exact match first
    if query in data:
        return query, data[query]
    # Normalized match
    for k, v in data.items():
        kn = k.lower().replace(" ", "").replace("-", "").replace("_", "")
        if q == kn or q in kn or kn in q:
            return k, v
    # Partial match on values
    for k, v in data.items():
        if isinstance(v, dict):
            name = str(v.get("name", "")).lower()
            if q in name.replace(" ", ""):
                return k, v
    return None, None


def _load_all_models():
    """Load and merge all model files."""
    all_m = load_json("all_models.json", "models") or {}
    missing = load_json("missing_models.json", "models") or {}
    m356 = load_json("356_models.json", "models") or {}
    merged = {}
    merged.update(all_m)
    merged.update(missing)
    merged.update(m356)
    return merged


# --- Tool implementations ---

async def lookup_model(args: dict) -> list[TextContent]:
    model_q = args["model"]
    year = args.get("year")
    models = _load_all_models()
    if not models:
        return _text("Model database not loaded.")
    key, data = _match_key(models, model_q)
    if data:
        if year and isinstance(data, dict):
            vs = data.get("variants", [])
            filtered = [v for v in vs if str(year) in str(v.get("years", ""))]
            if filtered:
                data = {**data, "variants": filtered}
        return _text(f"=== Porsche {data.get('name', key)} ===\n\n{_fmt(data)}")
    return _text(f"Model '{model_q}' not found. Use list_models to see available models.")


async def search_tech(args: dict) -> list[TextContent]:
    query = args["query"]
    results = search_all(query, max_results=25)
    if not results:
        return _text(f"No results for '{query}'.")
    lines = [f"Search: '{query}' ({len(results)} results)\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"  {i}. [{r.get('source','')}] {r.get('match','')}")
        lines.append(f"     Path: {r.get('path','')}  (score: {r.get('score',0):.1f})\n")
    return _text("\n".join(lines))


async def get_torque_specs(args: dict) -> list[TextContent]:
    model_q = args["model"]
    system = args.get("system")
    data = load_json("torque_specs.json", "torque") or {}
    key, specs = _match_key(data, model_q)
    if specs:
        if system and isinstance(specs, dict) and system.lower() in specs:
            specs = {system: specs[system.lower()]}
        return _text(f"=== Torque Specs: {key} ===\n\n{_fmt(specs)}")
    return _text(f"No torque specs for '{model_q}'. Available: {', '.join(data.keys())}")


async def get_fluid_specs(args: dict) -> list[TextContent]:
    model_q = args["model"]
    data = load_json("fluid_specs.json", "fluids") or {}
    key, specs = _match_key(data, model_q)
    if specs:
        return _text(f"=== Fluid Specs: {key} ===\n\n{_fmt(specs)}")
    return _text(f"No fluid specs for '{model_q}'. Available: {', '.join(data.keys())}")


async def get_maintenance_schedule(args: dict) -> list[TextContent]:
    model_q = args["model"]
    mileage = args.get("mileage")
    data = load_json("schedules.json", "maintenance") or {}
    key, sched = _match_key(data, model_q)
    if sched:
        if mileage and isinstance(sched, dict):
            intervals = sched.get("intervals", {})
            due = []
            for mi_str, info in sorted(intervals.items(), key=lambda x: int(x[0])):
                mi = int(mi_str)
                if mileage >= mi:
                    due.append(f"\n  At {mi:,} miles: {info.get('note','')}\n  " + "\n  ".join(info.get("services", [])))
            if due:
                return _text(f"=== Maintenance Due at {mileage:,} mi ({key}) ===\n" + "\n".join(due))
        return _text(f"=== Maintenance: {key} ===\n\n{_fmt(sched)}")
    return _text(f"No maintenance schedule for '{model_q}'. Available: {', '.join(data.keys())}")


async def get_common_issues(args: dict) -> list[TextContent]:
    model_q = args["model"]
    data = load_json("common_issues.json", "issues") or {}
    key, issues = _match_key(data, model_q)
    if issues:
        return _text(f"=== Common Issues: {key} ({len(issues)} known) ===\n\n{_fmt(issues)}")
    return _text(f"No issues data for '{model_q}'. Available: {', '.join(data.keys())}")


async def decode_vin(args: dict) -> list[TextContent]:
    vin = args["vin"].upper().strip()
    if len(vin) != 17:
        return _text(f"Invalid VIN length: {len(vin)} (need 17). VIN: {vin}")
    vin_data = load_json("vin_decoder.json", "vin") or {}
    year_codes = vin_data.get("position_10_year", {})
    plant_codes = vin_data.get("position_11_plant", {})
    model_codes = vin_data.get("position_4_model", {})
    lines = [f"=== VIN Decode: {vin} ===\n"]
    wmi = vin[0:3]
    wmi_desc = vin_data.get("wmi_codes", {}).get(wmi, "Unknown manufacturer")
    lines.append(f"  Manufacturer (WMI):  {wmi} = {wmi_desc}")
    lines.append(f"  Model Code:          {vin[3]} = {model_codes.get(vin[3], 'Unknown')}")
    lines.append(f"  Engine Code:         {vin[4]} = {vin_data.get('position_5_engine', {}).get(vin[4], 'Unknown')}")
    lines.append(f"  Restraint:           {vin[5]} = {vin_data.get('position_6_restraint', {}).get(vin[5], 'Unknown')}")
    lines.append(f"  Body Type:           {vin[6]} = {vin_data.get('position_7_body', {}).get(vin[6], 'Unknown')}")
    lines.append(f"  Check Digit:         {vin[8]}")
    year = year_codes.get(vin[9], "Unknown")
    lines.append(f"  Model Year:          {vin[9]} = {year}")
    lines.append(f"  Assembly Plant:      {vin[10]} = {plant_codes.get(vin[10], 'Unknown')}")
    lines.append(f"  Serial Number:       {vin[11:17]}")
    return _text("\n".join(lines))


async def lookup_paint_code(args: dict) -> list[TextContent]:
    code_q = args["code"].strip()
    # Check curated paint codes
    curated = load_json("paint_codes.json", "paint_codes") or {}
    if code_q in curated:
        return _text(f"=== Paint Code: {code_q} ===\n\n{_fmt(curated[code_q])}")
    # Check Rennbow
    rennbow = load_json("rennbow_colors.json", "paint_codes") or []
    for color in rennbow:
        codes = color.get("code", [])
        if isinstance(codes, list) and code_q in codes:
            return _text(f"=== Paint Code: {code_q} ===\n\n{_fmt(color)}")
        if isinstance(codes, str) and code_q == codes:
            return _text(f"=== Paint Code: {code_q} ===\n\n{_fmt(color)}")
    # Search by name
    q_lower = code_q.lower()
    for color in rennbow:
        if q_lower in str(color.get("name", "")).lower():
            return _text(f"=== Paint: {color.get('name','')} ===\n\n{_fmt(color)}")
    return _text(f"Paint code '{code_q}' not found. We have {len(rennbow)} colors in the Rennbow database.")


async def lookup_option_code(args: dict) -> list[TextContent]:
    code_q = args["code"].strip().upper()
    full = load_json("option_codes_full.json", "option_codes") or {}
    basic = load_json("option_codes.json", "option_codes") or {}
    merged = {**basic, **full}
    if code_q in merged:
        return _text(f"=== Option Code: {code_q} ===\n\n{_fmt(merged[code_q])}")
    # Partial match
    matches = {k: v for k, v in merged.items() if code_q in k}
    if matches:
        return _text(f"=== Option Codes matching '{code_q}' ===\n\n{_fmt(matches)}")
    return _text(f"Option code '{code_q}' not found. {len(merged)} codes in database.")


async def get_recalls(args: dict) -> list[TextContent]:
    model_q = args["model"].lower()
    year = args.get("year")
    data = load_json("nhtsa_recalls.json") or []
    matches = [r for r in data if model_q in str(r.get("model", "")).lower()]
    if year:
        matches = [r for r in matches if r.get("year") == year]
    if matches:
        return _text(f"=== NHTSA Recalls: Porsche {args['model']} ({len(matches)} found) ===\n\n{_fmt(matches)}")
    return _text(f"No recalls found for '{args['model']}'" + (f" ({year})" if year else ""))


async def get_tsbs(args: dict) -> list[TextContent]:
    # TSBs not separately scraped — point to recalls + complaints
    return _text("TSBs are not separately available via NHTSA API. Use get_recalls() for recall data and search_tech() for forum-reported technical issues.")


async def get_fault_codes(args: dict) -> list[TextContent]:
    code_q = args.get("code", "").strip().upper()
    full = load_json("fault_codes_full.json", "fault_codes") or {}
    basic = load_json("fault_codes.json", "fault_codes") or {}
    merged = {**basic, **full}
    if not code_q:
        lines = [f"=== Porsche Fault Codes ({len(merged)} in database) ===\n"]
        for k, v in list(merged.items())[:30]:
            desc = v.get("desc", v.get("description", ""))
            lines.append(f"  {k}: {desc}")
        lines.append(f"\n  ... {len(merged)} total. Use get_fault_codes(code='P0XXX') for details.")
        return _text("\n".join(lines))
    if code_q in merged:
        return _text(f"=== Fault Code: {code_q} ===\n\n{_fmt(merged[code_q])}")
    matches = {k: v for k, v in merged.items() if code_q in k}
    if matches:
        return _text(f"=== Codes matching '{code_q}' ===\n\n{_fmt(matches)}")
    return _text(f"Code '{code_q}' not found. {len(merged)} codes in database.")


async def get_brake_specs(args: dict) -> list[TextContent]:
    model_q = args["model"]
    data = load_json("brake_specs.json", "brakes") or {}
    key, specs = _match_key(data, model_q)
    if specs:
        return _text(f"=== Brake Specs: {key} ===\n\n{_fmt(specs)}")
    return _text(f"No brake specs for '{model_q}'. Available: {', '.join(data.keys())}")


async def get_suspension_specs(args: dict) -> list[TextContent]:
    model_q = args["model"]
    data = load_json("suspension_specs.json", "suspension") or {}
    key, specs = _match_key(data, model_q)
    if specs:
        return _text(f"=== Suspension: {key} ===\n\n{_fmt(specs)}")
    return _text(f"No suspension data for '{model_q}'. Available: {', '.join(data.keys())}")


async def get_tire_specs(args: dict) -> list[TextContent]:
    model_q = args["model"]
    data = load_json("wheel_tire_specs.json", "wheels") or {}
    key, specs = _match_key(data, model_q)
    if specs:
        return _text(f"=== Wheels & Tires: {key} ===\n\n{_fmt(specs)}")
    return _text(f"No wheel/tire data for '{model_q}'. Available: {', '.join(data.keys())}")


async def get_fuse_layout(args: dict) -> list[TextContent]:
    model_q = args["model"]
    data = load_json("electrical_specs.json", "electrical") or {}
    key, specs = _match_key(data, model_q)
    if specs:
        return _text(f"=== Electrical / Fuse Layout: {key} ===\n\n{_fmt(specs)}")
    return _text(f"No electrical data for '{model_q}'. Available: {', '.join(data.keys())}")


async def get_gear_ratios(args: dict) -> list[TextContent]:
    model_q = args["model"]
    data = load_json("gear_ratios.json", "transmissions") or {}
    key, specs = _match_key(data, model_q)
    if specs:
        return _text(f"=== Gear Ratios: {key} ===\n\n{_fmt(specs)}")
    return _text(f"No gear ratio data for '{model_q}'. Available: {', '.join(data.keys())}")


async def get_performance_data(args: dict) -> list[TextContent]:
    model_q = args["model"]
    data = load_json("performance_data.json", "performance") or {}
    key, specs = _match_key(data, model_q)
    if specs:
        return _text(f"=== Performance: {specs.get('name', key)} ===\n\n{_fmt(specs)}")
    return _text(f"No performance data for '{model_q}'. Available: {', '.join(data.keys())}")


async def get_market_value(args: dict) -> list[TextContent]:
    model_q = args["model"].lower()
    data = load_json("bat_auctions.json", "market") or {}
    key, specs = _match_key(data, model_q)
    if specs:
        return _text(f"=== Market Value: {key} (Bring a Trailer) ===\n\n{_fmt(specs)}")
    return _text(f"No market data for '{model_q}'. Available: {', '.join(data.keys())}")


async def get_production_numbers(args: dict) -> list[TextContent]:
    model_q = args["model"]
    models = _load_all_models()
    key, data = _match_key(models, model_q)
    if data and isinstance(data, dict):
        lines = [f"=== Production: {data.get('name', key)} ===\n"]
        if "production_total" in data:
            lines.append(f"  Total Production: {data['production_total']:,}")
        for v in data.get("variants", []):
            if "production_numbers" in v:
                lines.append(f"  {v.get('name','?')}: {v['production_numbers']:,}")
        if len(lines) == 1:
            lines.append("  Production numbers not available for individual variants.")
        return _text("\n".join(lines))
    return _text(f"No production data for '{model_q}'.")


async def get_engine_specs(args: dict) -> list[TextContent]:
    code_q = args.get("engine_code", "").strip()
    data = load_json("engine_codes.json", "engines") or {}
    if not code_q:
        lines = [f"=== Porsche Engine Codes ({len(data)} engines) ===\n"]
        for k, v in data.items():
            lines.append(f"  {k}: {v.get('name','')} — {v.get('displacement_cc','')}cc, {v.get('hp','')}hp")
        return _text("\n".join(lines))
    if code_q in data:
        return _text(f"=== Engine: {code_q} ===\n\n{_fmt(data[code_q])}")
    key, specs = _match_key(data, code_q)
    if specs:
        return _text(f"=== Engine: {key} ===\n\n{_fmt(specs)}")
    return _text(f"Engine code '{code_q}' not found. {len(data)} codes in database.")


async def get_diy_guide(args: dict) -> list[TextContent]:
    topic = args["topic"]
    model = args.get("model", "")
    # Search across all DIY files
    results = search_all(f"{topic} {model}".strip(), max_results=15)
    if results:
        lines = [f"=== DIY: {topic}" + (f" ({model})" if model else "") + f" — {len(results)} results ===\n"]
        for i, r in enumerate(results, 1):
            lines.append(f"  {i}. [{r.get('source','')}] {r.get('match','')}")
        return _text("\n".join(lines))
    return _text(f"No DIY guides found for '{topic}'.")


async def compare_models(args: dict) -> list[TextContent]:
    m1, m2 = args["model1"], args["model2"]
    models = _load_all_models()
    k1, d1 = _match_key(models, m1)
    k2, d2 = _match_key(models, m2)
    if not d1 and not d2:
        return _text(f"Neither '{m1}' nor '{m2}' found.")
    lines = [f"{'':30} {'Model 1':30} {'Model 2':30}"]
    lines.append(f"{'':30} {(d1 or {}).get('name',m1):30} {(d2 or {}).get('name',m2):30}")
    lines.append("=" * 90)
    compare_keys = ["years", "era", "layout", "wheelbase_in", "length_in", "width_in", "height_in", "fuel_tank_gal"]
    for ck in compare_keys:
        v1 = str((d1 or {}).get(ck, "N/A"))
        v2 = str((d2 or {}).get(ck, "N/A"))
        lines.append(f"  {ck.replace('_',' ').title():28} {v1:30} {v2:30}")
    return _text("\n".join(lines))


async def list_models(args: dict) -> list[TextContent]:
    era = args.get("era", "")
    mtype = args.get("type", "")
    models = _load_all_models()
    lines = [f"=== Porsche Models ({len(models)} in database) ===\n"]
    for k, v in models.items():
        name = v.get("name", k)
        years = v.get("years", "")
        model_era = v.get("era", "")
        nvars = len(v.get("variants", []))
        if era and era.lower() not in model_era.lower():
            continue
        if mtype and mtype.lower() not in name.lower():
            continue
        lines.append(f"  {name} ({years}) — {nvars} variants [{model_era}]")
    lines.append(f"\n  Use lookup_model(model='...') for full specs.")
    return _text("\n".join(lines))
