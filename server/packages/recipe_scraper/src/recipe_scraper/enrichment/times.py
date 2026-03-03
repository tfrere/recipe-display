"""DAG-based time calculation for recipe step graphs."""

import logging
from graphlib import TopologicalSorter, CycleError
from typing import Dict, Any, Optional
from recipe_structurer.shared import parse_iso8601_minutes, EQUIPMENT_KEYWORDS

logger = logging.getLogger(__name__)

_FALLBACK_DURATION_MIN = 5.0


def _parse_time_to_minutes(time_str: str) -> float:
    """
    Convert a time string to minutes.

    Supports ISO 8601 (PT30M, PT1H30M) and legacy formats (1h30min, 5min).
    """
    if not time_str:
        return 0.0

    time_str = str(time_str).strip()
    original_str = time_str

    if time_str.upper().startswith("PT"):
        parsed = parse_iso8601_minutes(time_str)
        return parsed if parsed is not None else 0.0

    time_str = time_str.lower()
    total_minutes = 0.0

    if "h" in time_str:
        hour_match = time_str.find("h")
        try:
            hours = float(time_str[:hour_match].strip())
            total_minutes += hours * 60
            time_str = time_str[hour_match + 1:]
        except ValueError:
            logger.warning(f"Could not parse hours from time string: {time_str}")
    elif "hour" in time_str:
        hour_match = time_str.find("hour")
        try:
            hours = float(time_str[:hour_match].strip())
            total_minutes += hours * 60
            time_str = time_str[hour_match + len("hour"):]
            if time_str.startswith("s"):
                time_str = time_str[1:]
            time_str = time_str.strip()
        except ValueError:
            logger.warning(f"Could not parse hours from time string: {original_str}")

    if "min" in time_str:
        min_match = time_str.find("min")
        try:
            min_start = 0
            if total_minutes > 0:
                for i, char in enumerate(time_str):
                    if char.isdigit():
                        min_start = i
                        break
            min_part = time_str[min_start:min_match].strip()
            if min_part:
                total_minutes += float(min_part)
        except ValueError:
            logger.warning(f"Could not parse minutes from time string: {time_str}")
    elif "minute" in time_str:
        minute_match = time_str.find("minute")
        try:
            min_start = 0
            if total_minutes > 0:
                for i, char in enumerate(time_str):
                    if char.isdigit():
                        min_start = i
                        break
            min_part = time_str[min_start:minute_match].strip()
            if min_part:
                total_minutes += float(min_part)
        except ValueError:
            logger.warning(f"Could not parse minutes from time string: {time_str}")

    if "sec" in time_str or "second" in time_str or (total_minutes == 0 and time_str.endswith("s") and time_str[-2:-1].isdigit()):
        sec_match = -1
        if "sec" in time_str:
            sec_match = time_str.find("sec")
        elif "second" in time_str:
            sec_match = time_str.find("second")
        if sec_match != -1:
            try:
                sec_start = 0
                if total_minutes > 0:
                    for i, char in enumerate(time_str):
                        if char.isdigit():
                            sec_start = i
                            break
                sec_part = time_str[sec_start:sec_match].strip()
                if sec_part:
                    total_minutes += float(sec_part) / 60
            except ValueError:
                logger.warning(f"Could not parse seconds from time string: {time_str}")

    if total_minutes == 0 and time_str.strip().replace('.', '', 1).isdigit():
        try:
            total_minutes = float(time_str.strip())
        except ValueError:
            pass

    return total_minutes


def _minutes_to_iso8601(minutes: float) -> str:
    """Convert minutes to ISO 8601 duration string (e.g. PT1H30M)."""
    if minutes <= 0:
        return "PT0M"
    total_min = round(minutes)
    hours = total_min // 60
    mins = total_min % 60
    if hours and mins:
        return f"PT{hours}H{mins}M"
    elif hours:
        return f"PT{hours}H"
    else:
        return f"PT{mins}M"


def _calculate_times_linear_fallback(recipe_data: Dict[str, Any]) -> Dict[str, Any]:
    """Fallback: simply sums all step durations linearly."""
    total_minutes = 0.0
    active_minutes = 0.0
    for step in recipe_data.get("steps", []):
        time_str = step.get("duration") or step.get("time")
        if time_str:
            mins = _parse_time_to_minutes(time_str)
            total_minutes += mins
            is_pass = step.get("isPassive", False) or step.get("stepMode") == "passive"
            if not is_pass:
                active_minutes += mins
    passive_minutes = total_minutes - active_minutes
    return {
        "totalTime": _minutes_to_iso8601(total_minutes),
        "totalActiveTime": _minutes_to_iso8601(active_minutes),
        "totalPassiveTime": _minutes_to_iso8601(passive_minutes),
        "totalTimeMinutes": round(total_minutes, 1),
        "totalActiveTimeMinutes": round(active_minutes, 1),
        "totalPassiveTimeMinutes": round(passive_minutes, 1),
    }


def calculate_times_from_dag(recipe_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate recipe times using the critical path through the step DAG.

    Returns dict with ISO 8601 strings + float minutes.
    """
    steps = recipe_data.get("steps", [])
    recipe_title = recipe_data.get("metadata", {}).get("title", "?")

    if not steps or not isinstance(steps, list):
        logger.warning(f"No steps list found for '{recipe_title}', falling back to linear sum")
        return _calculate_times_linear_fallback(recipe_data)

    step_by_id: Dict[str, Dict] = {}
    duration_min: Dict[str, float] = {}
    is_passive: Dict[str, bool] = {}

    for step in steps:
        sid = step.get("id", "")
        step_by_id[sid] = step
        dur_str = step.get("duration") or step.get("time")
        if dur_str:
            duration_min[sid] = _parse_time_to_minutes(dur_str)
        else:
            action_lower = step.get("action", "").lower()
            is_equipment = any(kw in action_lower for kw in EQUIPMENT_KEYWORDS)
            duration_min[sid] = 0.0 if is_equipment else _FALLBACK_DURATION_MIN
        is_passive[sid] = bool(step.get("isPassive", False))

    state_producer: Dict[str, str] = {}
    for step in steps:
        prod = step.get("produces", "")
        if prod:
            state_producer[prod] = step["id"]

    ingredient_ids = {ing.get("id", "") for ing in recipe_data.get("ingredients", [])}

    predecessors: Dict[str, set] = {s["id"]: set() for s in steps}
    for step in steps:
        sid = step["id"]
        refs = list(step.get("uses", [])) + list(step.get("requires", []))
        for ref in refs:
            if ref in ingredient_ids:
                continue
            if ref in state_producer:
                pred_id = state_producer[ref]
                if pred_id != sid:
                    predecessors[sid].add(pred_id)

    earliest_finish: Dict[str, float] = {}
    critical_pred: Dict[str, Optional[str]] = {}

    try:
        sorted_ids = list(TopologicalSorter(predecessors).static_order())
    except CycleError:
        logger.warning(f"[{recipe_title}] Cycle detected in step DAG, falling back to JSON order")
        sorted_ids = [s["id"] for s in steps]

    for sid in sorted_ids:
        max_pred_finish = 0.0
        best_pred = None
        for pred in predecessors.get(sid, set()):
            pf = earliest_finish.get(pred, 0.0)
            if pf > max_pred_finish:
                max_pred_finish = pf
                best_pred = pred
        earliest_finish[sid] = max_pred_finish + duration_min.get(sid, 0.0)
        critical_pred[sid] = best_pred

    final_state = recipe_data.get("finalState", "")
    if final_state and final_state in state_producer:
        critical_end = state_producer[final_state]
    else:
        critical_end = max(earliest_finish, key=earliest_finish.get) if earliest_finish else None

    total_time_min = earliest_finish.get(critical_end, 0.0) if critical_end else 0.0

    critical_path_active = 0.0
    critical_path_passive = 0.0
    path_ids = []
    current = critical_end
    while current:
        path_ids.append(current)
        dur = duration_min.get(current, 0.0)
        if is_passive.get(current, False):
            critical_path_passive += dur
        else:
            critical_path_active += dur
        current = critical_pred.get(current)
    path_ids.reverse()

    linear_total = sum(duration_min.values())
    logger.info(
        f"[{recipe_title}] DAG critical path: {total_time_min:.0f}min "
        f"(active={critical_path_active:.0f}min + passive={critical_path_passive:.0f}min) | "
        f"Linear sum would be: {linear_total:.0f}min | "
        f"Path: {' → '.join(path_ids)}"
    )

    return {
        "totalTime": _minutes_to_iso8601(total_time_min),
        "totalActiveTime": _minutes_to_iso8601(critical_path_active),
        "totalPassiveTime": _minutes_to_iso8601(critical_path_passive),
        "totalTimeMinutes": round(total_time_min, 1),
        "totalActiveTimeMinutes": round(critical_path_active, 1),
        "totalPassiveTimeMinutes": round(critical_path_passive, 1),
    }
