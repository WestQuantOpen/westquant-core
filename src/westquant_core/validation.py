from __future__ import annotations
from typing import Any

POLICY_REQUIRED = {
    "schema_version", "framework", "challenge_id", "state_id", "next_state_id",
    "step_index", "stage", "action", "success", "selectable", "verification",
    "metrics_before", "metrics_after", "kept_in_beam", "terminal",
}


def validate_policy_record(record: dict[str, Any]) -> list[str]:
    errors=[]
    missing=sorted(POLICY_REQUIRED-set(record))
    if missing: errors.append(f"missing fields: {missing}")
    if record.get("schema_version") != "wqt-policy-v0.1": errors.append("schema_version must be wqt-policy-v0.1")
    if not isinstance(record.get("action"),dict): errors.append("action must be an object")
    else:
        for key in ("stage","name","parameters"):
            if key not in record["action"]: errors.append(f"action missing {key}")
    for key in ("success","selectable","kept_in_beam","terminal"):
        if key in record and not isinstance(record[key],bool): errors.append(f"{key} must be boolean")
    if isinstance(record.get("step_index"),int) and record["step_index"]<0: errors.append("step_index must be >= 0")
    return errors
