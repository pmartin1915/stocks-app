# Color Conventions

This document explains the intentional color scheme differences between the CLI and Dashboard interfaces.

## CLI (Rich Library)

The CLI uses [Rich](https://rich.readthedocs.io/)'s built-in terminal color palette. Terminal colors are limited and "yellow" is a standard ANSI color that renders consistently.

| Semantic Meaning | Color Name | Usage |
|-----------------|------------|-------|
| Positive/Safe | `green` | Safe zone, strong scores, buy signals |
| Warning/Uncertain | `yellow` | Grey zone, moderate scores, hold signals |
| Danger/Critical | `red` | Distress zone, weak scores, sell signals |
| Inactive/Neutral | `dim` | Pass decisions, disabled items |

### Files Using This Convention

- `asymmetric/cli/formatting.py`
- `asymmetric/cli/commands/decision.py`
- `asymmetric/cli/commands/alerts.py`
- `asymmetric/cli/commands/sectors.py`

## Dashboard (Streamlit)

The Dashboard uses web-standard CSS colors. In web contexts, "orange" is more visually distinct than yellow and better represents the "caution/warning" semantic.

| Semantic Meaning | Color Name | Hex Value | Usage |
|-----------------|------------|-----------|-------|
| Positive/Safe | `green` | `#22c55e` | Safe zone, strong scores, buy signals |
| Warning/Uncertain | `orange` | `#f97316` | Grey zone, moderate scores, hold signals |
| Danger/Critical | `red` | `#ef4444` | Distress zone, weak scores, sell signals |
| Inactive/Neutral | `gray` | `#6b7280` | Pass decisions, archived items |

### Files Using This Convention

- `dashboard/config.py`
- `dashboard/pages/*.py`
- `dashboard/utils/scoring.py`
- `dashboard/components/icons.py`

## Rationale

Both "yellow" (CLI) and "orange" (Dashboard) represent the same semantic meaning: **warning/uncertain/moderate**. The different color names are intentional:

1. **Terminal compatibility**: Rich's "yellow" is a standard ANSI color that works across all terminals
2. **Web visibility**: CSS "orange" stands out better against white backgrounds in browsers
3. **Semantic consistency**: Both map to the same meaning in the Asymmetric color system

## Adding New Colors

When adding new UI elements:

- **CLI**: Use Rich color names (`green`, `yellow`, `red`, `dim`, `white`)
- **Dashboard**: Use CSS color names (`green`, `orange`, `red`, `gray`)

Always ensure the semantic meaning is consistent across both interfaces.

## CLI Panel Border Styles

Panels in the CLI use border colors to convey meaning. These styles are defined in `asymmetric/cli/formatting.py`:

| Style | Constant | Usage |
| ----- | -------- | ----- |
| `blue` | `BORDER_PRIMARY` | Primary content panels (scores, analysis) |
| `green` | `BORDER_SUCCESS` | Success/confirmation panels (created thesis, recorded decision) |
| `dim` | `BORDER_METADATA` | Secondary/metadata panels (cost info, timestamps) |
| `yellow` | `BORDER_WARNING` | Warning panels (caution messages) |
| `red` | `BORDER_ERROR` | Error/alert panels (failures, triggered alerts) |

### Standard Padding

- `PANEL_PADDING = (1, 2)` - Standard panel padding
- `TABLE_PADDING = (0, 2)` - Standard table padding

### Missing Value Display

Use the `MISSING` constant (`"-"`) for consistent missing value display across all commands.
