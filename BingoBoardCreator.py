import argparse
import copy
import json
import os
import random
import datetime

def generate_category_lists(pool):
    category_dict = {}
    for entry in pool:
        category = entry["category"]
        if category not in category_dict:
            category_dict[category] = []
        category_dict[category].append(entry)
    return dict(sorted(category_dict.items()))


def show_all_in_category(category, catalog):
    for entry in catalog[category]:
        print(entry["name"])


# <param name="lockout_mode"  >If the card should be in Lockout mode or not</param>
# <param name="hide_card"     >If the card should be hidden and need revealing</param>
# <param name="cardIDs"       >The IDs of the game and variant to use</param>
# <param name="seed"          >The seed to use for the new card, where if -1, will use a random seed</param>
# <param name="custom_json"   >Custom JSON to pass for the boards creation, primarily used in Custom games</param>
# public async Task CreateNewCard(bool lockout_mode, bool hide_card, CardIDs cardIDs, int seed = -1, string custom_json = "")
# GetResponse(URL_API_NewCard, false, BingoSyncPost.NewCard(CurrentRoomInfo.RoomID, lockout_mode ? "2" : "1",
#                        hide_card, seed <= -1 ? "" : Math.Abs(seed).ToString(), custom_json, cardIDs.GameID.ToString(),
#                        cardIDs.VariantID.ToString()));
def generate_new_room(hide_card, game_type, variant_type, custom_json, lockout_mode, seed, room):
    request_json = json.dumps('''{
        {fHideCard},
        {fGameType},
        {fVariantType},
        {fCustomJSON},
        {fLockoutMode},
        {fSeed},
        {fRoom}
    '''.format(fHideCard=hide_card, fGameType=game_type, fVariantType=variant_type, fCustomJSON=custom_json,
               fLockoutMode=lockout_mode, fSeed=seed, fRoom=room), indent=2)
    print(request_json)


# *************** Utils *******************
def check_duplicants(pool):
    seen = set()
    counter = 0
    for entry in pool:
        counter += 1
        if entry["name"] in seen:
            print("Duplicate! |" + str(entry))
        else:
            seen.add(entry["name"])
    print("All done! " + str(counter) + " entries checked")

def check_uniqueness(pool):
    seen_categories = set()
    seen_regions = set()
    for entry in pool:
        seen_categories.add(entry["category"])
        seen_regions.add(entry["region"])

    print("\n Total category list looks like")
    for category in sorted(seen_categories):
        print("\t" + str(category))

    print("\n Total region list looks like")
    for region in sorted(seen_regions):
        print("\t" + str(region))


def audit_pool(category_dict):
    all_regions = set()
    for entries in category_dict.values():
        for entry in entries:
            if entry["region"] != "Singleton":
                for sub in entry["region"].split(" and "):
                    all_regions.add(sub.strip())

    print("=== Possible Region Mismatches ===")
    print("Entry name contains a known region keyword but region field doesn't include it.\n")
    found = False
    for category, entries in category_dict.items():
        for entry in entries:
            name_lower = entry["name"].lower()
            entry_sub_regions = (
                {sub.strip() for sub in entry["region"].split(" and ")}
                if entry["region"] != "Singleton" else set()
            )
            for region in all_regions:
                if region.lower() in name_lower and region not in entry_sub_regions:
                    print(f"  [{category}] '{entry['name']}' — suggests '{region}' but has region '{entry['region']}'")
                    found = True
    if not found:
        print("  None found.")

    print("\n=== Shared-Region Groups (Progressive Chain Candidates) ===")
    print("Multiple entries in the same category share a region — only one can appear per board.\n")
    found = False
    for category, entries in category_dict.items():
        region_groups = {}
        for entry in entries:
            if entry["region"] == "Singleton":
                continue
            region_groups.setdefault(entry["region"], []).append(entry["name"])
        for region, names in region_groups.items():
            if len(names) > 1:
                print(f"  [{category}] — '{region}':")
                for name in names:
                    print(f"    - {name}")
                found = True
    if not found:
        print("  None found.")

    print("\n=== Singleton / Non-Singleton Conflicts ===")
    print("Singleton entries that share name keywords with non-Singleton regions in the same category.\n")
    found = False
    for category, entries in category_dict.items():
        singletons = [e for e in entries if e["region"] == "Singleton"]
        non_singletons = [e for e in entries if e["region"] != "Singleton"]
        if not singletons or not non_singletons:
            continue
        for singleton in singletons:
            singleton_lower = singleton["name"].lower()
            for entry in non_singletons:
                for sub in entry["region"].split(" and "):
                    if sub.strip().lower() in singleton_lower:
                        print(f"  [{category}] Singleton '{singleton['name']}' may conflict with '{entry['name']}' (region: '{entry['region']}')")
                        found = True
    if not found:
        print("  None found.")


def filter_by_region(pool, removed_entry, split_compounded, exclusionary):
    if not exclusionary:
        return list(pool)
    picked_region = removed_entry["region"]
    if picked_region == "Singleton":
        return list(pool)
    if picked_region == "All":
        return [r for r in pool if r["region"] == "Singleton"]
    if split_compounded:
        eliminated_region = picked_region.split(" and ")
        return [
            r for r in pool
            if r["region"] != "All"
            and (r["region"] == "Singleton"
                 or len(set(r["region"].split(" and ")).intersection(eliminated_region)) < 1)
        ]
    else:
        return [
            r for r in pool
            if r["region"] != "All"
            and (r["region"] == "Singleton" or r["region"] != picked_region)
        ]


def purge_region(category_dict, exhausted_region, split_compounded):
    for cat in category_dict:
        if split_compounded:
            category_dict[cat] = [
                e for e in category_dict[cat]
                if e["region"] == "Singleton" or exhausted_region not in e["region"].split(" and ")
            ]
        else:
            category_dict[cat] = [
                e for e in category_dict[cat]
                if e["region"] == "Singleton" or e["region"] != exhausted_region
            ]


def update_region_counts(region_counts, removed_entry, guidance, category_dict):
    if removed_entry["region"] == "Singleton":
        return
    split_compounded = guidance["Split_Compounded_Regions"]
    sub_regions = removed_entry["region"].split(" and ") if split_compounded else [removed_entry["region"]]
    region_limit_overrides = guidance.get("Region_Limits", {})
    default_region_limit = guidance.get("Default_Region_Limit")
    for sub_region in sub_regions:
        region_counts[sub_region] = region_counts.get(sub_region, 0) + 1
        limit = region_limit_overrides.get(sub_region, default_region_limit)
        if limit is not None and region_counts[sub_region] == limit:
            purge_region(category_dict, sub_region, split_compounded)


def resolve_limits(guidance, category_dict):
    overrides = guidance.get("Category_Limits", {})
    default = guidance.get("Default_Category_Limit")
    limits = {}
    missing = []
    for cat in category_dict:
        if cat in overrides:
            limits[cat] = overrides[cat]
        elif default is not None:
            limits[cat] = default
        else:
            missing.append(cat)
    if missing:
        raise ValueError(f"Categories missing from Category_Limits and no Default_Category_Limit set: {missing}")
    return limits


def load_weights(guidance, category_dict):
    use_fixed_weights = guidance.get("Use_Fixed_Weights", False)
    category_weights = {}
    if use_fixed_weights:
        overrides = guidance.get("Category_Weights", {})
        default = guidance.get("Default_Category_Weight")
        missing = []
        for cat in category_dict:
            if cat in overrides:
                category_weights[cat] = overrides[cat]
            elif default is not None:
                category_weights[cat] = default
            else:
                missing.append(cat)
        if missing:
            raise ValueError(f"Categories missing from Category_Weights and no Default_Category_Weight set: {missing}")
    return use_fixed_weights, category_weights


def generate_board(category_dict, grid_guidance, guidance, use_fixed_weights, category_weights):
    category_dict = copy.deepcopy(category_dict)
    grid_guidance = copy.deepcopy(grid_guidance)

    # Guard: grid must be 5x5
    if len(grid_guidance) != 5 or any(len(row) != 5 for row in grid_guidance):
        raise ValueError(f"Grid_Guidance must be 5x5, got {len(grid_guidance)}x{len(grid_guidance[0]) if grid_guidance else 0}")

    # Guard: all category names in fixed cells must exist in the pool
    fixed_categories = set(
        cat.strip()
        for row in grid_guidance
        for entry in row if entry != "-"
        for cat in entry.split(",")
    )
    unknown = fixed_categories - category_dict.keys()
    if unknown:
        raise ValueError(f"Fixed cells reference categories not found in pool: {unknown}")

    # Guard: all categories must have a limit defined (via override or default)
    limits = resolve_limits(guidance, category_dict)
    region_counts = {}

    # First pass: fill fixed cells, category limits do not apply
    for y, row in enumerate(grid_guidance):
        for x, entry in enumerate(row):
            if entry == "-":
                continue
            chosen_category = random.choices([cat.strip() for cat in entry.split(",")])[0]
            pool_category = category_dict[chosen_category]
            removed_entry = pool_category.pop(random.randrange(len(pool_category)))
            grid_guidance[y][x] = removed_entry["name"]
            category_dict[chosen_category] = filter_by_region(
                pool_category, removed_entry,
                guidance["Split_Compounded_Regions"], guidance["Exclusionary_Regions"]
            )
            update_region_counts(region_counts, removed_entry, guidance, category_dict)

    # Apply initial limits: zero out pools for categories already at their limit
    for category, limit in limits.items():
        if limit == 0:
            category_dict[category] = []

    # Second pass: fill remaining "-" cells
    for y, row in enumerate(grid_guidance):
        for x, entry in enumerate(row):
            if entry == "-":
                categories = list(category_dict.keys())
                if use_fixed_weights:
                    effective_weights = [category_weights[c] if len(category_dict[c]) > 0 else 0 for c in categories]
                else:
                    effective_weights = [len(category_dict[c]) for c in categories]
                try:
                    chosen_category = random.choices(categories, weights=effective_weights)[0]
                except ValueError:
                    raise ValueError("Pool exhausted — not enough entries to fill the board. Check your limits, region limits, and pool size.")
                pool_category = category_dict[chosen_category]
                removed_entry = pool_category.pop(random.randrange(len(pool_category)))
                grid_guidance[y][x] = removed_entry["name"]
                category_dict[chosen_category] = filter_by_region(
                    pool_category, removed_entry,
                    guidance["Split_Compounded_Regions"], guidance["Exclusionary_Regions"]
                )
                update_region_counts(region_counts, removed_entry, guidance, category_dict)
                limits[chosen_category] -= 1
                if limits[chosen_category] == 0:
                    category_dict[chosen_category] = []

    return grid_guidance


# ************** Mandatory IF MAIN *****************
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a Bingo board.")
    parser.add_argument("--pool", default="Resources/CustomBingoCategorized.json", help="Path to the pool JSON file")
    parser.add_argument("--guidance", default="Resources/MetaRandomizer.json", help="Path to the guidance JSON file")
    parser.add_argument("--output", default="Output", help="Directory to write output files to")
    parser.add_argument("--audit", action="store_true", help="Run data audit instead of generating a board")
    args = parser.parse_args()

    with open(args.pool) as pool_file, open(args.guidance) as guidance_file:
        pool = json.load(pool_file)
        guidance = json.load(guidance_file)

    category_dict = generate_category_lists(pool)

    if args.audit:
        audit_pool(category_dict)
    else:
        seed = guidance.get("Seed") or random.randrange(2**32)
        print(f"Seed: {seed}")
        random.seed(seed)

        use_fixed_weights, category_weights = load_weights(guidance, category_dict)
        grid_guidance = generate_board(category_dict, guidance["Grid_Guidance"], guidance, use_fixed_weights, category_weights)

        flat_grid = [{"name": entry} for row in grid_guidance for entry in row]
        output_json = json.dumps(flat_grid, indent=2)
        if guidance["Write_To_File"]:
            os.makedirs(args.output, exist_ok=True)
            output_path = os.path.join(args.output, "Output_" + str(datetime.datetime.now()).split(".")[0].replace(":", "_") + ".json")
            print("Writing to file:", output_path)
            with open(output_path, "w") as output_file:
                output_file.write(output_json)
        else:
            print(output_json)
