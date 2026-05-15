# BingoBoardCreator

A randomized bingo board generator that produces [BingoSync](https://bingosync.com)-compatible output. Designed for OoT randomizer bingo, but the pool and guidance system is game-agnostic.

Rather than pulling blindly from a flat item list, BingoBoardCreator uses a **guidance file** to control category weights, region exclusions, limits, and fixed cell placement — giving you fine-grained control over board diversity and difficulty distribution.

---

## Requirements

Python 3.7+. No external dependencies.

---

## Usage

```bash
# Generate a board (output to terminal)
python BingoBoardCreator.py

# Generate a board with custom files
python BingoBoardCreator.py --pool Resources/MyPool.json --guidance Resources/MyGuidance.json

# Write output to a file instead of the terminal
# (set "Write_To_File": true in the guidance file)
python BingoBoardCreator.py --output MyOutputDir

# Audit the pool for region inconsistencies
python BingoBoardCreator.py --audit
```

### Arguments

| Argument | Default | Description |
|---|---|---|
| `--pool` | `Resources/CustomBingoCategorized.json` | Path to the item pool JSON |
| `--guidance` | `Resources/MetaRandomizer.json` | Path to the guidance JSON |
| `--output` | `Output` | Directory for output files (created if missing) |
| `--audit` | — | Run the data audit instead of generating a board |

The seed used for each run is always printed to the terminal. To reproduce a board, set `"Seed"` in the guidance file.

---

## Pool File

A JSON array of entries. Each entry requires three fields:

```json
[
    {
        "name": "Fairy Slingshot",
        "category": "Acquisitions",
        "region": "Slingshot"
    },
    {
        "name": "Bullet Bag 40 or Better",
        "category": "Acquisitions",
        "region": "Slingshot"
    }
]
```

| Field | Description |
|---|---|
| `name` | Display name shown on the bingo board |
| `category` | Groups entries for weighted selection and limit tracking |
| `region` | Controls diversity exclusion (see [Region System](#region-system)) |

---

## Guidance File

Controls all aspects of board generation. See `Resources/MetaRandomizer.json` for a working example.

### Flags

| Key | Type | Description |
|---|---|---|
| `Exclusionary_Regions` | bool | When an entry is picked, remove same-region entries from that category's pool |
| `Split_Compounded_Regions` | bool | Split compound regions (e.g. `"Swords and Tunics"`) on `" and "` for granular exclusion |
| `Write_To_File` | bool | Write output to a timestamped file instead of printing to terminal |

### Seeding

| Key | Type | Description |
|---|---|---|
| `Seed` | int (optional) | Fixed random seed for reproducibility. Omit or set to `null` for a random seed |

### Category Weights

Controls how likely each category is to be selected when filling random cells.

| Key | Type | Description |
|---|---|---|
| `Use_Fixed_Weights` | bool | `true` = use explicit weights; `false` = weight by pool size |
| `Default_Category_Weight` | number | Weight for any category not listed in `Category_Weights` |
| `Category_Weights` | object | Per-category weight overrides |

When `Use_Fixed_Weights` is `false`, categories are weighted proportionally to the number of remaining entries in their pool.

### Category Limits

Controls how many entries can be picked from each category per board.

| Key | Type | Description |
|---|---|---|
| `Default_Category_Limit` | int | Limit for any category not listed in `Category_Limits`. Use `-1` for unlimited, `0` to exclude entirely |
| `Category_Limits` | object | Per-category limit overrides. Same sentinel values apply |

### Region Limits

Controls how many times a region can appear across the whole board (cross-category).

| Key | Type | Description |
|---|---|---|
| `Default_Region_Limit` | int | Applies to any region not listed in `Region_Limits`. Omit, set to `null`, or set to `-1` for no limit |
| `Region_Limits` | object | Per-region limit overrides. Same sentinel values apply |

### Grid Guidance

A 5×5 array defining the board layout.

| Cell value | Behaviour |
|---|---|
| `"-"` | Filled randomly in the second pass using weights and limits |
| `"CategoryName"` | Fixed to that category, picked in the first pass (limits do not apply) |
| `"Cat1,Cat2"` | Randomly selects between the listed categories with equal probability |

```json
"Grid_Guidance": [
    [ "-",    "-",    "-",    "-", "-" ],
    [ "-",    "-",    "-",    "-", "-" ],
    [ "-",    "-",  "Meme",  "-", "-" ],
    [ "-",    "-",    "-",    "-", "-" ],
    [ "-",    "-",    "-",    "-", "-" ]
]
```

Fixed cells (non-`"-"`) are filled first and do not consume category limits. Region limits and exclusionary region logic still apply to fixed cells.

---

## Region System

Regions are the primary mechanism for ensuring board diversity within a category. When `Exclusionary_Regions` is enabled, picking an entry removes other entries sharing its region from that category's pool for the remainder of generation.

### Special Region Values

| Region | Behaviour |
|---|---|
| `"Singleton"` | Never excluded by any pick, and never excludes others. Use for entries that are truly one-of-a-kind with no related entries |
| `"All"` | Conflicts universally. Picking any other entry removes all `"All"` entries from the pool; picking an `"All"` entry clears everything except Singletons. Use for collection-count entries that overlap with all other entries in the category (e.g. `"10 Songs"`, `"Collect All 6 Warpsongs"`) |

### Compound Regions

Entries can belong to multiple regions by joining them with `" and "`:

```json
{ "name": "3 Swords & 3 Tunics", "region": "Swords and Tunics" }
```

When `Split_Compounded_Regions` is enabled, picking this entry eliminates all entries that share **any** of its sub-regions (`"Swords"` or `"Tunics"`). An entry with a compound region is also eliminated if **any** of its sub-regions has been exhausted by a previous pick or by a region limit.

### Region Limits vs. Exclusionary Regions

These two mechanisms are complementary but distinct:

- **Exclusionary Regions** — within a single category, prevents two entries from the same region appearing together
- **Region Limits** — across all categories, caps how many times a region appears on the entire board

---

## Generation Order

1. **First pass** — fixed cells in `Grid_Guidance` are filled in order. Category limits do not apply, but exclusionary region logic and region limit tracking do.
2. **Limit application** — any category with a limit of `0` has its pool cleared.
3. **Second pass** — remaining `"-"` cells are filled using weighted random selection, respecting all limits and exclusions.

---

## Data Utilities

Three diagnostic functions are available for validating and exploring the pool. Call them directly from a script or REPL after loading and categorising the pool.

### `audit_pool(category_dict)`

Runs three checks and prints a report:

- **Region Mismatches** — entries whose name contains a known region keyword but whose `region` field doesn't match. Useful for catching data entry errors like a progressive item assigned to the wrong region.
- **Shared-Region Groups** — all groups of 2+ entries sharing a region within a category. Lets you verify progressive item chains are correctly grouped.
- **Singleton / Non-Singleton Conflicts** — Singleton entries whose name keywords match non-Singleton region names in the same category. Flags cases where a Singleton and a non-Singleton entry could unintentionally coexist on the same board.

Run via the CLI:
```bash
python BingoBoardCreator.py --audit
```

### `check_duplicants(pool)`

Scans the raw pool for entries with duplicate `name` fields and reports the count checked.

### `check_uniqueness(pool)`

Prints all unique category and region names found in the pool. Useful for spotting typos in region names (e.g. `"Tunic"` vs `"Tunics"`).

---

## Output Format

BingoSync expects a flat JSON array of 25 objects in row-major order (top-left to bottom-right):

```json
[
  { "name": "Fairy Slingshot" },
  { "name": "Beat the Water Temple" },
  ...
]
```

This is the format produced by both the terminal output and file output modes.
