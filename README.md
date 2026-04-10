# Reno Rennsport Porsche MCP Server

**The most comprehensive Porsche technical database as an MCP server.**

Built by [Reno Rennsport](https://renorennsport.com) — Porsche specialists serving enthusiasts, technicians, and collectors.

---

## What Is This?

`reno-porsche-mcp` is a [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that gives AI assistants access to an extensive Porsche technical database. It covers every generation from the 356 to the current 992, Taycan, and beyond.

When connected to an MCP-compatible client (Claude Desktop, Hermes Agent, or any MCP client), your AI assistant gains instant access to:

- **Model specifications** — Every production Porsche, all variants, full specs
- **Torque values** — Every bolt, every component, factory-correct values
- **Fluid capacities** — Oil, coolant, brake fluid, transmission, differential
- **Maintenance schedules** — Factory service intervals with mileage tracking
- **Known issues** — Common failures, symptoms, severity, and repair costs
- **VIN decoding** — Full breakdown of any Porsche VIN
- **Paint & option codes** — Complete code lookup from sticker or COA
- **Recalls & TSBs** — NHTSA recalls and Technical Service Bulletins
- **Fault codes** — Diagnostic trouble codes with causes and solutions
- **Brake, suspension, tire specs** — Complete chassis data
- **Fuse layouts** — Every fuse position and circuit assignment
- **Gear ratios** — All transmission options, all ratios
- **Performance data** — 0-60, quarter mile, top speed, Ring times
- **Market values** — Current pricing trends and historical values
- **Production numbers** — How many were built, by year and variant
- **Engine specs** — Deep technical data by engine code
- **DIY guides** — Step-by-step repair and maintenance procedures
- **Model comparison** — Side-by-side spec comparison of any two models

---

## Installation

### From PyPI (recommended)

```bash
pip install reno-porsche-mcp
```

### From Source

```bash
git clone https://github.com/reno-rennsport/reno-porsche-mcp.git
cd reno-porsche-mcp
pip install -e .
```

---

## Usage

### With Claude Desktop

Add to your Claude Desktop MCP configuration (`~/.config/claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "reno-porsche": {
      "command": "reno-porsche-mcp"
    }
  }
}
```

### With Hermes Agent

```json
{
  "mcpServers": {
    "reno-porsche": {
      "command": "reno-porsche-mcp"
    }
  }
}
```

### Standalone

```bash
reno-porsche-mcp
```

The server communicates over stdio using the MCP protocol.

### Custom Data Directory

By default, the server looks for data in the `data/` directory relative to the package. Override with:

```bash
export RENO_PORSCHE_DATA_DIR=/path/to/your/data
reno-porsche-mcp
```

---

## All 24 Tools

| # | Tool | Description |
|---|------|-------------|
| 1 | `lookup_model` | Full specs for any Porsche model |
| 2 | `search_tech` | Full-text search across all data |
| 3 | `get_torque_specs` | Torque values by model and system |
| 4 | `get_fluid_specs` | Fluids and capacities |
| 5 | `get_maintenance_schedule` | Service intervals with mileage tracking |
| 6 | `get_common_issues` | Known problems and failure points |
| 7 | `decode_vin` | Full VIN breakdown |
| 8 | `lookup_paint_code` | Paint color lookup |
| 9 | `lookup_option_code` | Option code meaning |
| 10 | `get_recalls` | NHTSA recall information |
| 11 | `get_tsbs` | Technical Service Bulletins |
| 12 | `get_fault_codes` | Diagnostic trouble codes |
| 13 | `get_brake_specs` | Brake data (rotors, pads, calipers) |
| 14 | `get_suspension_specs` | Alignment and spring data |
| 15 | `get_tire_specs` | Wheels, tires, and pressures |
| 16 | `get_fuse_layout` | Fuse box assignments |
| 17 | `get_gear_ratios` | Transmission ratios |
| 18 | `get_performance_data` | 0-60, quarter mile, top speed |
| 19 | `get_market_value` | Current pricing trends |
| 20 | `get_production_numbers` | Build numbers by year/variant |
| 21 | `get_engine_specs` | Deep engine data by code |
| 22 | `get_diy_guide` | Step-by-step repair guides |
| 23 | `compare_models` | Side-by-side model comparison |
| 24 | `list_models` | Browse all models with filters |

---

## Data Coverage

The database covers Porsche models across all eras:

**Classic (pre-1989):** 356, 911 (901), 912, 914, 924, 928, 944, 959

**Modern (1989-2010):** 964, 993, 996, 997, 986 Boxster, 987 Cayman, Cayenne (955/957), first-gen Panamera

**Current (2011+):** 991, 992, 718 Boxster/Cayman, Cayenne (958/9YA), Macan, Panamera (971), Taycan, 918 Spyder

### Data Directory Structure

```
data/
  models/          Model specifications
  specs/           Torque, fluid, brake, suspension, tire, gear ratio specs
  maintenance/     Service schedules
  issues/          Common issues and known problems
  safety/          Recalls and TSBs
  diagnostics/     Fault codes
  electrical/      Fuse layouts, wiring
  engines/         Engine specifications by code
  performance/     Performance testing data
  market/          Market values and trends
  history/         Production numbers, historical data
  reference/       VIN decoder, paint codes, option codes
  guides/          DIY repair and maintenance guides
```

---

## Requirements

- Python 3.10+
- `mcp` >= 1.0.0

---

## License

MIT License. Copyright (c) Reno Rennsport.

---

*Built with passion for Porsche by the Reno Rennsport team.*
