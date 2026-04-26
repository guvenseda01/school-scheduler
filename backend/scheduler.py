from dataclasses import dataclass
from math import ceil
from typing import Dict, List, Set, Tuple

import models


@dataclass
class PlannedAssignment:
    class_id: int
    subject_id: int
    teacher_id: int
    time_slot_id: int


@dataclass
class UnassignedAssignment:
    class_id: int
    subject_id: int
    teacher_id: int
    reason: str


def generate_schedule(
    requirements: List[models.CourseRequirement],
    time_slots: List[models.TimeSlot],
    availability: List[models.TeacherAvailability],
) -> Tuple[List[PlannedAssignment], List[UnassignedAssignment]]:
    """Optimization-based scheduler.

    This solver performs a bounded branch-and-bound search (instead of
    first-fit greedy) with two goals:
      1) maximize number of assigned lessons (minimize unassigned),
      2) spread each class+subject across multiple days whenever possible.
    """
    if not requirements or not time_slots:
        return [], []

    slot_by_id: Dict[int, models.TimeSlot] = {s.id: s for s in time_slots}
    day_by_slot_id: Dict[int, str] = {s.id: s.day for s in time_slots}
    available_pairs: Set[Tuple[int, int]] = {
        (a.teacher_id, a.time_slot_id) for a in availability
    }
    # Teachers that have at least one explicit availability row.
    # Convention: teachers without any rows are treated as available
    # everywhere. This matches the manual-placement validation in crud.py
    # and keeps newly created teachers schedulable by default.
    teachers_with_availability: Set[int] = {a.teacher_id for a in availability}

    lesson_instances: List[models.CourseRequirement] = []
    for req in sorted(requirements, key=lambda r: r.weekly_hours, reverse=True):
        lesson_instances.extend([req] * req.weekly_hours)

    all_slot_ids: List[int] = [s.id for s in time_slots]

    candidate_slots: List[List[int]] = []
    for req in lesson_instances:
        if req.teacher_id in teachers_with_availability:
            slots = [
                s.id
                for s in time_slots
                if (req.teacher_id, s.id) in available_pairs
            ]
        else:
            slots = list(all_slot_ids)
        candidate_slots.append(slots)

    # Fail-fast order (MRV): place lessons with fewer options first.
    order = sorted(range(len(lesson_instances)), key=lambda i: len(candidate_slots[i]))
    ordered_lessons = [lesson_instances[i] for i in order]
    ordered_candidates = [candidate_slots[i] for i in order]

    teacher_busy: Set[Tuple[int, int]] = set()
    class_busy: Set[Tuple[int, int]] = set()
    key_day_counts: Dict[Tuple[int, int], Dict[str, int]] = {}
    global_day_counts: Dict[str, int] = {}
    current_assignments: List[PlannedAssignment] = []
    current_unassigned: List[UnassignedAssignment] = []

    best_assignments: List[PlannedAssignment] = []
    best_unassigned: List[UnassignedAssignment] = []
    best_score = (-1, -10**9)  # (assigned_count, spread_score)

    # Search budget: enough for realistic test datasets but bounded.
    max_nodes = 150_000
    nodes_visited = 0

    target_days_by_key: Dict[Tuple[int, int], int] = {}
    all_days = {slot.day for slot in time_slots}
    max_days = max(1, len(all_days))
    for req in requirements:
        target_days_by_key[(req.class_id, req.subject_id)] = min(
            req.weekly_hours, max_days
        )

    def spread_score() -> int:
        score = 0
        for key, day_counts in key_day_counts.items():
            distinct_days = len(day_counts)
            target = target_days_by_key.get(key, 1)
            # Reward diversity, penalize concentration.
            score += min(distinct_days, target) * 3
            max_load = max(day_counts.values()) if day_counts else 0
            avg = ceil(sum(day_counts.values()) / max(1, distinct_days))
            score -= max(0, max_load - avg)

        # Global weekday usage: prefer timetables that do not leave
        # entire weekdays empty when feasible.
        if global_day_counts:
            distinct_global_days = len(global_day_counts)
            score += distinct_global_days * 2
            global_max = max(global_day_counts.values())
            global_min = min(global_day_counts.values())
            score -= max(0, global_max - global_min - 1)
        return score

    def can_place(req: models.CourseRequirement, slot_id: int) -> bool:
        if (req.teacher_id, slot_id) in teacher_busy:
            return False
        if (req.class_id, slot_id) in class_busy:
            return False
        return True

    def place(req: models.CourseRequirement, slot_id: int) -> None:
        teacher_busy.add((req.teacher_id, slot_id))
        class_busy.add((req.class_id, slot_id))
        current_assignments.append(
            PlannedAssignment(
                class_id=req.class_id,
                subject_id=req.subject_id,
                teacher_id=req.teacher_id,
                time_slot_id=slot_id,
            )
        )
        key = (req.class_id, req.subject_id)
        day = day_by_slot_id[slot_id]
        if key not in key_day_counts:
            key_day_counts[key] = {}
        key_day_counts[key][day] = key_day_counts[key].get(day, 0) + 1
        global_day_counts[day] = global_day_counts.get(day, 0) + 1

    def unplace(req: models.CourseRequirement, slot_id: int) -> None:
        teacher_busy.remove((req.teacher_id, slot_id))
        class_busy.remove((req.class_id, slot_id))
        current_assignments.pop()
        key = (req.class_id, req.subject_id)
        day = day_by_slot_id[slot_id]
        key_day_counts[key][day] -= 1
        if key_day_counts[key][day] == 0:
            del key_day_counts[key][day]
        if not key_day_counts[key]:
            del key_day_counts[key]
        global_day_counts[day] -= 1
        if global_day_counts[day] == 0:
            del global_day_counts[day]

    def dfs(idx: int) -> None:
        nonlocal nodes_visited, best_assignments, best_unassigned, best_score
        if nodes_visited >= max_nodes:
            return
        nodes_visited += 1

        assigned_count = len(current_assignments)
        remaining = len(ordered_lessons) - idx
        # Branch-and-bound prune: even best-case cannot beat current best.
        if assigned_count + remaining < best_score[0]:
            return

        if idx == len(ordered_lessons):
            score = (len(current_assignments), spread_score())
            if score > best_score:
                best_score = score
                best_assignments = list(current_assignments)
                best_unassigned = list(current_unassigned)
            return

        req = ordered_lessons[idx]
        slots = ordered_candidates[idx]

        # Prefer slots on currently less-used days for this class+subject.
        key = (req.class_id, req.subject_id)
        day_usage = key_day_counts.get(key, {})
        slots = sorted(
            slots,
            key=lambda sid: (
                day_usage.get(day_by_slot_id[sid], 0),
                slot_by_id[sid].day,
                slot_by_id[sid].start_time,
            ),
        )

        any_feasible = False
        for sid in slots:
            if not can_place(req, sid):
                continue
            any_feasible = True
            place(req, sid)
            dfs(idx + 1)
            unplace(req, sid)

        # Also allow this lesson to remain unassigned.
        # This makes the search complete for over-constrained datasets.
        if not any_feasible or len(current_assignments) + remaining - 1 >= best_score[0]:
            current_unassigned.append(
                UnassignedAssignment(
                    class_id=req.class_id,
                    subject_id=req.subject_id,
                    teacher_id=req.teacher_id,
                    reason="No feasible slot found under current constraints.",
                )
            )
            dfs(idx + 1)
            current_unassigned.pop()

    dfs(0)
    return best_assignments, best_unassigned
