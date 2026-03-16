"""
dataset_agent.py — Real file writes for training dataset collection.
Saves annotated frames + metadata JSON to dataset/{category}/ directory.
"""
import os
import json
import base64
from datetime import datetime
from pathlib import Path
from config import DATASET_DIR


def save_to_dataset(
    image_b64: str,
    label: str,
    confidence: float,
    bbox: list,
    category: str,
    metadata: dict,
) -> bool:
    """
    Saves a detection to the training dataset.

    Directory layout:
        dataset/
          confirmed_threat/
            2024-01-20_14-30-00_elephant_0.92.jpg
            2024-01-20_14-30-00_elephant_0.92.json
          non_threat/
            ...
          nova_rejected/
            ...
          false_positive_human_verified/
            ...

    Returns True if saved successfully.
    """
    try:
        ts = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
        safe_label = label.replace(" ", "_").lower()
        stem = f"{ts}_{safe_label}_{confidence:.2f}"

        # Ensure directory exists
        save_dir = Path(DATASET_DIR) / category
        save_dir.mkdir(parents=True, exist_ok=True)

        # Save image
        if image_b64:
            img_path = save_dir / f"{stem}.jpg"
            # Strip data-URI prefix if present
            b64_data = image_b64
            if "," in b64_data:
                b64_data = b64_data.split(",", 1)[1]
            # Handle truncated b64 gracefully
            try:
                img_bytes = base64.b64decode(b64_data + "==")
                with open(img_path, "wb") as f:
                    f.write(img_bytes)
            except Exception as img_err:
                print(f"[Dataset] Image save failed (skipping image): {img_err}")

        # Save metadata JSON
        meta_path = save_dir / f"{stem}.json"
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "label": label,
            "confidence": confidence,
            "bbox": bbox,
            "category": category,
            **metadata,
        }
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2, default=str)

        print(f"[Dataset] Saved {category}/{stem}")
        return True

    except Exception as e:
        print(f"[Dataset] save_to_dataset failed: {e}")
        return False


def update_frame_metadata(animal: str, created_at, new_label: str) -> bool:
    """
    Updates the category metadata JSON for a frame that was relabeled
    by human feedback (confirmed_threat → confirmed_threat_human_verified,
    or false_positive_human_verified).

    Searches dataset/ recursively for a JSON file matching the animal
    and approximate timestamp, then rewrites the category field.
    """
    try:
        if not created_at:
            return False

        # Convert datetime to string prefix for lookup
        if hasattr(created_at, "strftime"):
            ts_prefix = created_at.strftime("%Y-%m-%d_%H-%M")
        else:
            ts_prefix = str(created_at)[:16].replace(" ", "_").replace(":", "-")

        safe_animal = animal.replace(" ", "_").lower()
        dataset_root = Path(DATASET_DIR)

        matched = False
        for json_file in dataset_root.rglob("*.json"):
            name = json_file.stem
            if ts_prefix in name and safe_animal in name:
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    data["category"] = new_label
                    data["human_relabeled_at"] = datetime.utcnow().isoformat()

                    with open(json_file, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2, default=str)

                    # Move image + json to the new category folder
                    new_dir = dataset_root / new_label
                    new_dir.mkdir(parents=True, exist_ok=True)

                    for suffix in [json_file, json_file.with_suffix(".jpg")]:
                        if suffix.exists():
                            suffix.rename(new_dir / suffix.name)

                    print(f"[Dataset] Relabeled {json_file.name} → {new_label}")
                    matched = True
                    break
                except Exception as inner_err:
                    print(f"[Dataset] Failed to relabel {json_file}: {inner_err}")

        return matched

    except Exception as e:
        print(f"[Dataset] update_frame_metadata failed: {e}")
        return False
