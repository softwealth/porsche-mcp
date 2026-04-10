"""Reno Rennsport Porsche MCP Server.

The most comprehensive Porsche technical database as an MCP server.
Provides 24 tools covering every aspect of Porsche technical data from
model specs to DIY guides, VIN decoding, and market values.

Usage:
    reno-porsche-mcp          # Run via entry point
    python -m reno_porsche_mcp.server   # Run as module
"""

import asyncio
import json
from typing import Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from . import __version__
from .data_loader import (
    find_in_data,
    format_record,
    format_records,
    load_json,
    search_all,
    list_available_data,
    get_data_dir,
)

# ---------------------------------------------------------------------------
# Server instance
# ---------------------------------------------------------------------------

app = Server("reno-porsche-mcp")

BANNER = (
    "Reno Rennsport Porsche Technical Database v{ver}\n"
    "The most comprehensive Porsche technical data, served over MCP."
).format(ver=__version__)

DATA_MISSING_MSG = (
    "Data for '{category}' is currently being compiled by the Reno Rennsport team. "
    "Check back soon or set the RENO_PORSCHE_DATA_DIR environment variable to point "
    "to your own data directory."
)


def _no_data(category: str) -> str:
    return DATA_MISSING_MSG.format(category=category)


def _text(content: str) -> list[TextContent]:
    return [TextContent(type="text", text=content)]


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS = [
    Tool(
        name="lookup_model",
        description="Look up full specifications for a Porsche model. Returns engine, dimensions, weight, performance figures, production years, and all known variants.",
        inputSchema={
            "type": "object",
            "properties": {
                "model": {"type": "string", "description": "Model name, e.g. '911 Carrera', '964 Turbo', 'Cayenne Turbo GT'"},
                "year": {"type": "integer", "description": "Optional model year to narrow results"},
            },
            "required": ["model"],
        },
    ),
    Tool(
        name="search_tech",
        description="Full-text search across the entire Porsche technical database. Searches model specs, torque values, fault codes, TSBs, DIY guides, and every other dataset.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query, e.g. 'IMS bearing', 'rear main seal', 'M96 coolant'"},
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="get_torque_specs",
        description="Get torque specifications for a Porsche model. Returns bolt torque values for engine, suspension, brakes, wheels, and drivetrain components.",
        inputSchema={
            "type": "object",
            "properties": {
                "model": {"type": "string", "description": "Model name, e.g. '996 Carrera'"},
                "system": {"type": "string", "description": "Optional system filter: 'engine', 'suspension', 'brakes', 'wheels', 'drivetrain'"},
            },
            "required": ["model"],
        },
    ),
    Tool(
        name="get_fluid_specs",
        description="Get fluid specifications and capacities for a Porsche model. Returns oil type/capacity, coolant, brake fluid, transmission fluid, and differential fluid specs.",
        inputSchema={
            "type": "object",
            "properties": {
                "model": {"type": "string", "description": "Model name, e.g. '997.2 Carrera S'"},
            },
            "required": ["model"],
        },
    ),
    Tool(
        name="get_maintenance_schedule",
        description="Get the maintenance schedule and service intervals for a Porsche model. Returns what service is due at each mileage interval.",
        inputSchema={
            "type": "object",
            "properties": {
                "model": {"type": "string", "description": "Model name, e.g. '991 GT3'"},
                "mileage": {"type": "integer", "description": "Optional current mileage to show what is due now"},
            },
            "required": ["model"],
        },
    ),
    Tool(
        name="get_common_issues",
        description="Get known common issues and failure points for a Porsche model. Includes severity, symptoms, typical mileage of failure, and repair cost estimates.",
        inputSchema={
            "type": "object",
            "properties": {
                "model": {"type": "string", "description": "Model name, e.g. '986 Boxster'"},
            },
            "required": ["model"],
        },
    ),
    Tool(
        name="decode_vin",
        description="Decode a Porsche VIN (Vehicle Identification Number). Returns model, year, engine, transmission, market, assembly plant, and equipment details.",
        inputSchema={
            "type": "object",
            "properties": {
                "vin": {"type": "string", "description": "Full 17-character Porsche VIN"},
            },
            "required": ["vin"],
        },
    ),
    Tool(
        name="lookup_paint_code",
        description="Look up a Porsche paint code. Returns color name, years offered, which models used it, color type (metallic/solid/special), and any notes.",
        inputSchema={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Paint code, e.g. 'L3AZ', '1G1', 'Guards Red'"},
            },
            "required": ["code"],
        },
    ),
    Tool(
        name="lookup_option_code",
        description="Look up a Porsche option code from the vehicle sticker or COA (Certificate of Authenticity). Returns the option description, category, and availability.",
        inputSchema={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Option code, e.g. 'P77', 'XME', '220'"},
            },
            "required": ["code"],
        },
    ),
    Tool(
        name="get_recalls",
        description="Get NHTSA recall information for a Porsche model. Returns recall campaigns, descriptions, affected VIN ranges, and remedy details.",
        inputSchema={
            "type": "object",
            "properties": {
                "model": {"type": "string", "description": "Model name, e.g. '718 Cayman'"},
                "year": {"type": "integer", "description": "Optional model year filter"},
            },
            "required": ["model"],
        },
    ),
    Tool(
        name="get_tsbs",
        description="Get Technical Service Bulletins (TSBs) for a Porsche model. Returns bulletin numbers, descriptions, affected systems, and repair procedures.",
        inputSchema={
            "type": "object",
            "properties": {
                "model": {"type": "string", "description": "Model name, e.g. 'Macan S'"},
                "year": {"type": "integer", "description": "Optional model year filter"},
            },
            "required": ["model"],
        },
    ),
    Tool(
        name="get_fault_codes",
        description="Look up Porsche diagnostic fault codes (DTCs). Returns code meaning, affected system, common causes, and diagnostic steps.",
        inputSchema={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Fault code, e.g. 'P0300', 'P1128', 'U0100'. Omit to list common codes."},
            },
        },
    ),
    Tool(
        name="get_brake_specs",
        description="Get brake specifications for a Porsche model. Returns rotor sizes, pad types, caliper info, brake fluid spec, and wear limits.",
        inputSchema={
            "type": "object",
            "properties": {
                "model": {"type": "string", "description": "Model name, e.g. '993 Turbo'"},
            },
            "required": ["model"],
        },
    ),
    Tool(
        name="get_suspension_specs",
        description="Get suspension and alignment specifications for a Porsche model. Returns spring rates, damper specs, ride height, camber/caster/toe settings.",
        inputSchema={
            "type": "object",
            "properties": {
                "model": {"type": "string", "description": "Model name, e.g. '987 Cayman S'"},
            },
            "required": ["model"],
        },
    ),
    Tool(
        name="get_tire_specs",
        description="Get tire and wheel specifications for a Porsche model. Returns OEM tire sizes, wheel dimensions, tire pressures, and compatible alternatives.",
        inputSchema={
            "type": "object",
            "properties": {
                "model": {"type": "string", "description": "Model name, e.g. '992 Turbo S'"},
            },
            "required": ["model"],
        },
    ),
    Tool(
        name="get_fuse_layout",
        description="Get fuse box layout and assignments for a Porsche model. Returns fuse positions, amperage ratings, and which circuits they protect.",
        inputSchema={
            "type": "object",
            "properties": {
                "model": {"type": "string", "description": "Model name, e.g. '996 Carrera 4S'"},
            },
            "required": ["model"],
        },
    ),
    Tool(
        name="get_gear_ratios",
        description="Get transmission gear ratios for a Porsche model. Returns individual gear ratios, final drive ratio, and available transmission options.",
        inputSchema={
            "type": "object",
            "properties": {
                "model": {"type": "string", "description": "Model name, e.g. '911 GT3 RS'"},
            },
            "required": ["model"],
        },
    ),
    Tool(
        name="get_performance_data",
        description="Get performance data for a Porsche model. Returns 0-60 mph, 0-100 mph, quarter mile, top speed, Nurburgring time, and braking distances.",
        inputSchema={
            "type": "object",
            "properties": {
                "model": {"type": "string", "description": "Model name, e.g. '918 Spyder'"},
            },
            "required": ["model"],
        },
    ),
    Tool(
        name="get_market_value",
        description="Get current market value and pricing trends for a Porsche model. Returns price ranges, value trends, and what affects pricing.",
        inputSchema={
            "type": "object",
            "properties": {
                "model": {"type": "string", "description": "Model name, e.g. '993 Carrera'"},
                "year": {"type": "integer", "description": "Optional model year"},
            },
            "required": ["model"],
        },
    ),
    Tool(
        name="get_production_numbers",
        description="Get production numbers and statistics for a Porsche model. Returns total units built, breakdown by year, market, and variant.",
        inputSchema={
            "type": "object",
            "properties": {
                "model": {"type": "string", "description": "Model name, e.g. '964 RS America'"},
                "year": {"type": "integer", "description": "Optional model year"},
            },
            "required": ["model"],
        },
    ),
    Tool(
        name="get_engine_specs",
        description="Get deep technical specifications for a Porsche engine. Returns displacement, bore/stroke, compression ratio, valve train, fuel system, and all technical details.",
        inputSchema={
            "type": "object",
            "properties": {
                "engine_code": {"type": "string", "description": "Engine code, e.g. 'M96.01', 'M64/21', 'MA1.02'. Omit to list all known engine codes."},
            },
        },
    ),
    Tool(
        name="get_diy_guide",
        description="Get a DIY repair or maintenance guide for a specific topic and Porsche model. Returns step-by-step procedures, tools needed, parts list, and tips.",
        inputSchema={
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Repair or maintenance topic, e.g. 'oil change', 'brake pad replacement', 'IMS bearing'"},
                "model": {"type": "string", "description": "Optional model to get model-specific instructions"},
            },
            "required": ["topic"],
        },
    ),
    Tool(
        name="compare_models",
        description="Compare two Porsche models side by side. Returns a detailed comparison of specs, performance, dimensions, pricing, and key differences.",
        inputSchema={
            "type": "object",
            "properties": {
                "model1": {"type": "string", "description": "First model, e.g. '991 GT3'"},
                "model2": {"type": "string", "description": "Second model, e.g. '992 GT3'"},
            },
            "required": ["model1", "model2"],
        },
    ),
    Tool(
        name="list_models",
        description="Browse all Porsche models in the database. Optionally filter by era or type. Returns model names, years, and basic info.",
        inputSchema={
            "type": "object",
            "properties": {
                "era": {"type": "string", "description": "Optional era filter: 'classic' (pre-1989), 'modern' (1989-2010), 'current' (2011+)"},
                "type": {"type": "string", "description": "Optional type filter: '911', 'boxster/cayman', 'cayenne', 'macan', 'panamera', 'taycan', '944/968', '928', '356'"},
            },
        },
    ),
]


# ---------------------------------------------------------------------------
# Tool list handler
# ---------------------------------------------------------------------------

@app.list_tools()
async def handle_list_tools() -> list[Tool]:
    """Return the full list of available tools."""
    return TOOLS


# ---------------------------------------------------------------------------
# Tool dispatch handler
# ---------------------------------------------------------------------------

@app.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Dispatch tool calls to the appropriate handler."""
    from . import tools as T
    handlers = {
        "lookup_model": T.lookup_model,
        "search_tech": T.search_tech,
        "get_torque_specs": T.get_torque_specs,
        "get_fluid_specs": T.get_fluid_specs,
        "get_maintenance_schedule": T.get_maintenance_schedule,
        "get_common_issues": T.get_common_issues,
        "decode_vin": T.decode_vin,
        "lookup_paint_code": T.lookup_paint_code,
        "lookup_option_code": T.lookup_option_code,
        "get_recalls": T.get_recalls,
        "get_tsbs": T.get_tsbs,
        "get_fault_codes": T.get_fault_codes,
        "get_brake_specs": T.get_brake_specs,
        "get_suspension_specs": T.get_suspension_specs,
        "get_tire_specs": T.get_tire_specs,
        "get_fuse_layout": T.get_fuse_layout,
        "get_gear_ratios": T.get_gear_ratios,
        "get_performance_data": T.get_performance_data,
        "get_market_value": T.get_market_value,
        "get_production_numbers": T.get_production_numbers,
        "get_engine_specs": T.get_engine_specs,
        "get_diy_guide": T.get_diy_guide,
        "compare_models": T.compare_models,
        "list_models": T.list_models,
    }

    handler = handlers.get(name)
    if handler is None:
        return _text(f"Unknown tool: {name}. Use list_tools to see available tools.")

    try:
        return await handler(arguments)
    except Exception as e:
        return _text(f"Error executing {name}: {e}")


# ---------------------------------------------------------------------------
# Individual tool implementations
# ---------------------------------------------------------------------------

async def _tool_lookup_model(args: dict) -> list[TextContent]:
    """Look up full specifications for a Porsche model."""
    model = args["model"]
    year = args.get("year")

    results = find_in_data("models.json", "model", model, subdirectory="models", year=year)
    if not results:
        # Try top-level models.json
        results = find_in_data("models.json", "model", model, year=year)
    if not results:
        results = find_in_data("models.json", "name", model, subdirectory="models", year=year)

    if results:
        title = f"Porsche {model}" + (f" ({year})" if year else "")
        return _text(format_records(results, title=title))

    return _text(_no_data(f"model specs for '{model}'"))


async def _tool_search_tech(args: dict) -> list[TextContent]:
    """Full-text search across all data."""
    query = args["query"]
    results = search_all(query, max_results=25)

    if not results:
        available = list_available_data()
        if not available:
            return _text(
                f"No results for '{query}'.\n\n"
                "The data directory appears to be empty. Data files are being compiled by the "
                "Reno Rennsport team. Set RENO_PORSCHE_DATA_DIR to point to your data directory."
            )
        return _text(f"No results found for '{query}' across {sum(len(v) for v in available.values())} data files.")

    lines = [f"Search results for '{query}' ({len(results)} matches):", ""]
    for i, r in enumerate(results, 1):
        lines.append(f"  {i}. [{r['source']}] {r['match']}")
        lines.append(f"     Path: {r['path']}  (score: {r['score']:.1f})")
        lines.append("")

    return _text("\n".join(lines))


async def _tool_get_torque_specs(args: dict) -> list[TextContent]:
    """Get torque specifications for a model."""
    model = args["model"]
    system = args.get("system")

    results = find_in_data("torque_specs.json", "model", model, subdirectory="specs")
    if not results:
        results = find_in_data("torque_specs.json", "model", model)

    if results:
        if system:
            filtered = []
            for r in results:
                sys_val = r.get("system", "").lower()
                cat_val = r.get("category", "").lower()
                if system.lower() in sys_val or system.lower() in cat_val:
                    filtered.append(r)
            if filtered:
                results = filtered

        title = f"Torque Specs: Porsche {model}" + (f" ({system})" if system else "")
        return _text(format_records(results, title=title))

    return _text(_no_data(f"torque specs for '{model}'"))


async def _tool_get_fluid_specs(args: dict) -> list[TextContent]:
    """Get fluid specs and capacities."""
    model = args["model"]

    results = find_in_data("fluid_specs.json", "model", model, subdirectory="specs")
    if not results:
        results = find_in_data("fluid_specs.json", "model", model)

    if results:
        return _text(format_records(results, title=f"Fluid Specs: Porsche {model}"))

    return _text(_no_data(f"fluid specs for '{model}'"))


async def _tool_get_maintenance_schedule(args: dict) -> list[TextContent]:
    """Get maintenance schedule."""
    model = args["model"]
    mileage = args.get("mileage")

    results = find_in_data("maintenance.json", "model", model, subdirectory="maintenance")
    if not results:
        results = find_in_data("maintenance.json", "model", model)

    if results:
        if mileage is not None:
            lines = [f"Maintenance for Porsche {model} at {mileage:,} miles:", ""]
            for r in results:
                interval = r.get("interval_miles") or r.get("interval", 0)
                try:
                    interval = int(interval)
                except (ValueError, TypeError):
                    continue
                if interval > 0 and mileage >= interval:
                    due = "OVERDUE" if (mileage % interval) > (interval * 0.9) else "DUE"
                    lines.append(f"  [{due}] {r.get('service', r.get('description', 'Service'))} (every {interval:,} mi)")
            if len(lines) == 2:
                lines.append("  No specific services matched the mileage filter.")
            return _text("\n".join(lines))

        return _text(format_records(results, title=f"Maintenance Schedule: Porsche {model}"))

    return _text(_no_data(f"maintenance schedule for '{model}'"))


async def _tool_get_common_issues(args: dict) -> list[TextContent]:
    """Get common issues and known problems."""
    model = args["model"]

    results = find_in_data("common_issues.json", "model", model, subdirectory="issues")
    if not results:
        results = find_in_data("common_issues.json", "model", model)

    if results:
        return _text(format_records(results, title=f"Common Issues: Porsche {model}"))

    return _text(_no_data(f"common issues for '{model}'"))


async def _tool_decode_vin(args: dict) -> list[TextContent]:
    """Decode a Porsche VIN."""
    vin = args["vin"].upper().strip()

    if len(vin) != 17:
        return _text(f"Invalid VIN length: {len(vin)} characters (expected 17).\nVIN provided: {vin}")

    # Load VIN decoding tables
    vin_data = load_json("vin_decoder.json", subdirectory="reference")
    if not vin_data:
        vin_data = load_json("vin_decoder.json")

    lines = [f"VIN Decode: {vin}", ""]

    # Basic positional decode (Porsche VIN structure)
    lines.append(f"  WMI (World Manufacturer): {vin[0:3]}")
    if vin[0:3] == "WP0":
        lines.append("    -> Porsche AG, Stuttgart, Germany")
    elif vin[0:3] == "WP1":
        lines.append("    -> Porsche (SUV line)")

    lines.append(f"  Model Identifier: {vin[3:6]}")
    lines.append(f"  Restraint System: {vin[6]}")
    lines.append(f"  Check Digit: {vin[8]}")

    year_codes = {
        "R": 1994, "S": 1995, "T": 1996, "V": 1997, "W": 1998,
        "X": 1999, "Y": 2000, "1": 2001, "2": 2002, "3": 2003,
        "4": 2004, "5": 2005, "6": 2006, "7": 2007, "8": 2008,
        "9": 2009, "A": 2010, "B": 2011, "C": 2012, "D": 2013,
        "E": 2014, "F": 2015, "G": 2016, "H": 2017, "J": 2018,
        "K": 2019, "L": 2020, "M": 2021, "N": 2022, "P": 2023,
        "R2": 2024, "S2": 2025,
    }
    year_char = vin[9]
    model_year = year_codes.get(year_char, "Unknown")
    lines.append(f"  Model Year Code: {year_char} -> {model_year}")
    lines.append(f"  Assembly Plant: {vin[10]}")
    lines.append(f"  Serial Number: {vin[11:17]}")

    if vin_data and isinstance(vin_data, dict):
        # Cross-reference with detailed decode tables if available
        model_codes = vin_data.get("model_codes", {})
        model_id = vin[3:6]
        if model_id in model_codes:
            lines.append(f"\n  Model: {model_codes[model_id]}")

    lines.append("")
    lines.append("Note: For a complete factory spec sheet, use lookup_model with the decoded model name.")

    return _text("\n".join(lines))


async def _tool_lookup_paint_code(args: dict) -> list[TextContent]:
    """Look up a Porsche paint code."""
    code = args["code"].strip()

    results = find_in_data("paint_codes.json", "code", code, subdirectory="reference")
    if not results:
        # Try matching by color name
        results = find_in_data("paint_codes.json", "name", code, subdirectory="reference")
    if not results:
        results = find_in_data("paint_codes.json", "code", code)

    if results:
        return _text(format_records(results, title=f"Paint Code: {code}"))

    return _text(_no_data(f"paint code '{code}'"))


async def _tool_lookup_option_code(args: dict) -> list[TextContent]:
    """Look up a Porsche option code."""
    code = args["code"].strip().upper()

    results = find_in_data("option_codes.json", "code", code, subdirectory="reference")
    if not results:
        results = find_in_data("option_codes.json", "code", code)

    if results:
        return _text(format_records(results, title=f"Option Code: {code}"))

    return _text(_no_data(f"option code '{code}'"))


async def _tool_get_recalls(args: dict) -> list[TextContent]:
    """Get NHTSA recall information."""
    model = args["model"]
    year = args.get("year")

    results = find_in_data("recalls.json", "model", model, subdirectory="safety", year=year)
    if not results:
        results = find_in_data("recalls.json", "model", model, year=year)

    if results:
        title = f"Recalls: Porsche {model}" + (f" ({year})" if year else "")
        return _text(format_records(results, title=title))

    return _text(_no_data(f"recalls for '{model}'"))


async def _tool_get_tsbs(args: dict) -> list[TextContent]:
    """Get Technical Service Bulletins."""
    model = args["model"]
    year = args.get("year")

    results = find_in_data("tsbs.json", "model", model, subdirectory="safety", year=year)
    if not results:
        results = find_in_data("tsbs.json", "model", model, year=year)

    if results:
        title = f"TSBs: Porsche {model}" + (f" ({year})" if year else "")
        return _text(format_records(results, title=title))

    return _text(_no_data(f"TSBs for '{model}'"))


async def _tool_get_fault_codes(args: dict) -> list[TextContent]:
    """Look up diagnostic fault codes."""
    code = args.get("code", "").strip().upper()

    data = load_json("fault_codes.json", subdirectory="diagnostics")
    if data is None:
        data = load_json("fault_codes.json")

    if data is None:
        if code:
            return _text(_no_data(f"fault code '{code}'"))
        return _text(_no_data("fault codes"))

    if not code:
        # List common codes
        if isinstance(data, list):
            sample = data[:30]
        elif isinstance(data, dict):
            sample = [{"code": k, **v} if isinstance(v, dict) else {"code": k, "description": v} for k, v in list(data.items())[:30]]
        else:
            sample = []
        return _text(format_records(sample, title="Common Porsche Fault Codes"))

    results = find_in_data("fault_codes.json", "code", code, subdirectory="diagnostics")
    if not results:
        results = find_in_data("fault_codes.json", "code", code)

    if results:
        return _text(format_records(results, title=f"Fault Code: {code}"))

    return _text(f"Fault code '{code}' not found in the database. It may be a manufacturer-specific code.")


async def _tool_get_brake_specs(args: dict) -> list[TextContent]:
    """Get brake specifications."""
    model = args["model"]

    results = find_in_data("brake_specs.json", "model", model, subdirectory="specs")
    if not results:
        results = find_in_data("brake_specs.json", "model", model)

    if results:
        return _text(format_records(results, title=f"Brake Specs: Porsche {model}"))

    return _text(_no_data(f"brake specs for '{model}'"))


async def _tool_get_suspension_specs(args: dict) -> list[TextContent]:
    """Get suspension and alignment specs."""
    model = args["model"]

    results = find_in_data("suspension_specs.json", "model", model, subdirectory="specs")
    if not results:
        results = find_in_data("suspension_specs.json", "model", model)

    if results:
        return _text(format_records(results, title=f"Suspension Specs: Porsche {model}"))

    return _text(_no_data(f"suspension specs for '{model}'"))


async def _tool_get_tire_specs(args: dict) -> list[TextContent]:
    """Get tire and wheel specifications."""
    model = args["model"]

    results = find_in_data("tire_specs.json", "model", model, subdirectory="specs")
    if not results:
        results = find_in_data("tire_specs.json", "model", model)

    if results:
        return _text(format_records(results, title=f"Tire & Wheel Specs: Porsche {model}"))

    return _text(_no_data(f"tire specs for '{model}'"))


async def _tool_get_fuse_layout(args: dict) -> list[TextContent]:
    """Get fuse box layout."""
    model = args["model"]

    results = find_in_data("fuse_layout.json", "model", model, subdirectory="electrical")
    if not results:
        results = find_in_data("fuse_layout.json", "model", model)

    if results:
        return _text(format_records(results, title=f"Fuse Layout: Porsche {model}"))

    return _text(_no_data(f"fuse layout for '{model}'"))


async def _tool_get_gear_ratios(args: dict) -> list[TextContent]:
    """Get transmission gear ratios."""
    model = args["model"]

    results = find_in_data("gear_ratios.json", "model", model, subdirectory="specs")
    if not results:
        results = find_in_data("gear_ratios.json", "model", model)

    if results:
        return _text(format_records(results, title=f"Gear Ratios: Porsche {model}"))

    return _text(_no_data(f"gear ratios for '{model}'"))


async def _tool_get_performance_data(args: dict) -> list[TextContent]:
    """Get performance data."""
    model = args["model"]

    results = find_in_data("performance.json", "model", model, subdirectory="performance")
    if not results:
        results = find_in_data("performance.json", "model", model)

    if results:
        return _text(format_records(results, title=f"Performance: Porsche {model}"))

    return _text(_no_data(f"performance data for '{model}'"))


async def _tool_get_market_value(args: dict) -> list[TextContent]:
    """Get market value and pricing trends."""
    model = args["model"]
    year = args.get("year")

    results = find_in_data("market_values.json", "model", model, subdirectory="market", year=year)
    if not results:
        results = find_in_data("market_values.json", "model", model, year=year)

    if results:
        title = f"Market Value: Porsche {model}" + (f" ({year})" if year else "")
        return _text(format_records(results, title=title))

    return _text(_no_data(f"market values for '{model}'"))


async def _tool_get_production_numbers(args: dict) -> list[TextContent]:
    """Get production numbers."""
    model = args["model"]
    year = args.get("year")

    results = find_in_data("production_numbers.json", "model", model, subdirectory="history", year=year)
    if not results:
        results = find_in_data("production_numbers.json", "model", model, year=year)

    if results:
        title = f"Production Numbers: Porsche {model}" + (f" ({year})" if year else "")
        return _text(format_records(results, title=title))

    return _text(_no_data(f"production numbers for '{model}'"))


async def _tool_get_engine_specs(args: dict) -> list[TextContent]:
    """Get deep engine specifications."""
    engine_code = args.get("engine_code", "").strip()

    data = load_json("engines.json", subdirectory="engines")
    if data is None:
        data = load_json("engines.json")

    if data is None:
        if engine_code:
            return _text(_no_data(f"engine code '{engine_code}'"))
        return _text(_no_data("engine specifications"))

    if not engine_code:
        # List all engine codes
        if isinstance(data, list):
            codes = [e.get("engine_code") or e.get("code", "?") for e in data if isinstance(e, dict)]
        elif isinstance(data, dict):
            codes = list(data.keys())
        else:
            codes = []
        lines = ["Known Porsche Engine Codes:", ""]
        for c in codes[:50]:
            lines.append(f"  {c}")
        lines.append(f"\n{len(codes)} engine codes in database. Use get_engine_specs(engine_code='...') for details.")
        return _text("\n".join(lines))

    results = find_in_data("engines.json", "engine_code", engine_code, subdirectory="engines")
    if not results:
        results = find_in_data("engines.json", "code", engine_code, subdirectory="engines")
    if not results:
        results = find_in_data("engines.json", "engine_code", engine_code)

    if results:
        return _text(format_records(results, title=f"Engine: {engine_code}"))

    return _text(f"Engine code '{engine_code}' not found. Use get_engine_specs() with no arguments to list all codes.")


async def _tool_get_diy_guide(args: dict) -> list[TextContent]:
    """Get DIY repair/maintenance guide."""
    topic = args["topic"]
    model = args.get("model")

    # Try topic-specific file first
    topic_slug = topic.lower().replace(" ", "_").replace("/", "_")
    results = find_in_data(f"{topic_slug}.json", "topic", topic, subdirectory="guides")

    if not results:
        # Try general guides file
        results = find_in_data("diy_guides.json", "topic", topic, subdirectory="guides")
    if not results:
        results = find_in_data("diy_guides.json", "title", topic, subdirectory="guides")
    if not results:
        results = find_in_data("diy_guides.json", "topic", topic)

    if results:
        if model:
            model_filtered = [r for r in results if model.lower() in str(r.get("model", "")).lower() or model.lower() in str(r.get("models", "")).lower()]
            if model_filtered:
                results = model_filtered

        title = f"DIY Guide: {topic}" + (f" ({model})" if model else "")
        return _text(format_records(results, title=title))

    return _text(_no_data(f"DIY guide for '{topic}'"))


async def _tool_compare_models(args: dict) -> list[TextContent]:
    """Compare two Porsche models side by side."""
    model1 = args["model1"]
    model2 = args["model2"]

    specs1 = find_in_data("models.json", "model", model1, subdirectory="models")
    if not specs1:
        specs1 = find_in_data("models.json", "model", model1)
    specs2 = find_in_data("models.json", "model", model2, subdirectory="models")
    if not specs2:
        specs2 = find_in_data("models.json", "model", model2)

    if not specs1 and not specs2:
        return _text(_no_data(f"model comparison between '{model1}' and '{model2}'"))

    lines = [f"Model Comparison: {model1} vs {model2}", "=" * 50, ""]

    s1 = specs1[0] if specs1 else {}
    s2 = specs2[0] if specs2 else {}

    all_keys = list(dict.fromkeys(list(s1.keys()) + list(s2.keys())))

    for key in all_keys:
        label = str(key).replace("_", " ").title()
        v1 = s1.get(key, "N/A")
        v2 = s2.get(key, "N/A")

        if isinstance(v1, (dict, list)) or isinstance(v2, (dict, list)):
            continue

        lines.append(f"  {label:<25} {str(v1):<25} {str(v2):<25}")

    if not specs1:
        lines.append(f"\nNote: No data found for '{model1}' - data may still be compiling.")
    if not specs2:
        lines.append(f"\nNote: No data found for '{model2}' - data may still be compiling.")

    return _text("\n".join(lines))


async def _tool_list_models(args: dict) -> list[TextContent]:
    """Browse all models in the database."""
    era = args.get("era")
    model_type = args.get("type")

    data = load_json("models.json", subdirectory="models")
    if data is None:
        data = load_json("models.json")

    if data is None:
        return _text(_no_data("model listing"))

    records: list[dict] = []
    if isinstance(data, list):
        records = [r for r in data if isinstance(r, dict)]
    elif isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, dict):
                rec = {**v}
                if "model" not in rec:
                    rec["model"] = k
                records.append(rec)
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        rec = {**item}
                        if "model" not in rec:
                            rec["model"] = k
                        records.append(rec)

    # Filter by era
    if era:
        era_lower = era.lower()
        filtered = []
        for r in records:
            year_val = r.get("year") or r.get("year_start") or r.get("years", "")
            year_str = str(year_val)
            try:
                # Extract first year number from the string
                import re
                year_match = re.search(r'\d{4}', year_str)
                if year_match:
                    y = int(year_match.group())
                    if era_lower == "classic" and y < 1989:
                        filtered.append(r)
                    elif era_lower == "modern" and 1989 <= y <= 2010:
                        filtered.append(r)
                    elif era_lower == "current" and y > 2010:
                        filtered.append(r)
            except (ValueError, TypeError):
                pass
        records = filtered

    # Filter by type
    if model_type:
        type_lower = model_type.lower()
        filtered = []
        for r in records:
            model_name = str(r.get("model", "") or r.get("name", "")).lower()
            model_cat = str(r.get("type", "") or r.get("category", "")).lower()
            if type_lower in model_name or type_lower in model_cat:
                filtered.append(r)
        records = filtered

    if not records:
        filter_desc = ""
        if era:
            filter_desc += f" era='{era}'"
        if model_type:
            filter_desc += f" type='{model_type}'"
        return _text(f"No models found matching filters:{filter_desc}")

    lines = ["Porsche Models in Database", "=" * 40, ""]
    for r in records:
        name = r.get("model") or r.get("name", "Unknown")
        years = r.get("years") or r.get("year") or r.get("year_start", "")
        engine = r.get("engine") or r.get("engine_type", "")
        hp = r.get("horsepower") or r.get("hp", "")
        line = f"  {name}"
        if years:
            line += f" ({years})"
        if engine:
            line += f" - {engine}"
        if hp:
            line += f", {hp} hp"
        lines.append(line)

    lines.append(f"\n{len(records)} models listed. Use lookup_model for full specs.")
    return _text("\n".join(lines))


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def _run():
    """Run the MCP server with stdio transport."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def main():
    """Entry point for the reno-porsche-mcp command."""
    asyncio.run(_run())


if __name__ == "__main__":
    main()
