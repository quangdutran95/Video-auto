import os
import shutil
import re

watch_dir = r"C:\Users\Home\Downloads\tobyflow_output\tobyflow_bot"
dest_dir = r"E:\Video-Auto\jobs\2026-07-05_001_suc-khoe-la-vo-gia\input\raw_assets\images"
os.makedirs(dest_dir, exist_ok=True)

# Map of prefix words to scene IDs
mappings = {
    "a_young_scholar_standing_joyfully": "SC_01",
    "a_fragile_shadow_figure_leaning": "SC_02",
    "a_massive_pile_of_shiny_gold": "SC_03",
    "a_person_standing_peacefully": "SC_04",
    "a_traveler_sitting_down_exhausted": "SC_05",
    "a_wooden_desk_containing_a_small": "SC_06",
    "a_single_dewdrop_resting": "SC_07",
    "a_candle_burning_brightly": "SC_08",
    "a_candle_burnt_down_to_the_bottom": "SC_09",
    "a_single_autumn_leaf_falling": "SC_10",
    "a_pair_of_worn_straw_sandals": "SC_11",
    "a_hand_gently_placing": "SC_12",
    "a_young_scholar_looking_determinedly": "SC_13",
    "a_simple_wooden_bowl_filled": "SC_14",
    "a_vibrant_green_bamboo_shoot": "SC_15",
    "the_young_scholar_climbing_actively": "SC_16"
}

files = os.listdir(watch_dir)
copied = 0

for file in files:
    if "2026-07-05" in file and file.lower().endswith(".jpeg"):
        file_lower = file.lower()
        for prefix, scene_id in mappings.items():
            if file_lower.startswith(prefix):
                src_path = os.path.join(watch_dir, file)
                dest_path = os.path.join(dest_dir, f"{scene_id}.jpeg")
                print(f"Copying {file} -> {scene_id}.jpeg")
                shutil.copy2(src_path, dest_path)
                copied += 1
                break

print(f"Copied {copied} files successfully!")
