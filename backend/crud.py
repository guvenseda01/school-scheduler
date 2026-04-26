from typing import List, Optional, Sequence

from sqlalchemy.orm import Session

import models

TEACHER_COLOR_PALETTE = [
    "#fde68a",
    "#bbf7d0",
    "#bfdbfe",
    "#fbcfe8",
    "#ddd6fe",
    "#fed7aa",
    "#a5f3fc",
    "#fecaca",
    "#bae6fd",
    "#d9f99d",
]


def _next_teacher_color(db: Session) -> str:
    count = db.query(models.Teacher).count()
    return TEACHER_COLOR_PALETTE[count % len(TEACHER_COLOR_PALETTE)]


def get_teachers(db: Session) -> List[models.Teacher]:
    return db.query(models.Teacher).order_by(models.Teacher.id).all()


def get_teacher_by_id(db: Session, teacher_id: int) -> Optional[models.Teacher]:
    return db.query(models.Teacher).filter(models.Teacher.id == teacher_id).first()


def create_teacher(
    db: Session,
    name: str,
    subject_id: int,
    color: Optional[str] = None,
) -> models.Teacher:
    teacher = models.Teacher(
        name=name,
        subject_id=subject_id,
        color=color or _next_teacher_color(db),
    )
    db.add(teacher)
    db.commit()
    db.refresh(teacher)

    # Convenience default: newly created teachers are available in all
    # currently defined time slots unless availability is edited later.
    slots = db.query(models.TimeSlot.id).all()
    if slots:
        db.add_all(
            [
                models.TeacherAvailability(
                    teacher_id=teacher.id,
                    time_slot_id=slot_id,
                )
                for (slot_id,) in slots
            ]
        )
        db.commit()

    return teacher


def delete_teacher(db: Session, teacher_id: int) -> None:
    db.query(models.ScheduleEntry).filter(
        models.ScheduleEntry.teacher_id == teacher_id
    ).delete()
    db.query(models.CourseRequirement).filter(
        models.CourseRequirement.teacher_id == teacher_id
    ).delete()
    db.query(models.TeacherAvailability).filter(
        models.TeacherAvailability.teacher_id == teacher_id
    ).delete()
    db.query(models.Teacher).filter(models.Teacher.id == teacher_id).delete()
    db.commit()


def get_classes(db: Session) -> List[models.ClassGroup]:
    return db.query(models.ClassGroup).order_by(models.ClassGroup.id).all()


def get_class_by_id(db: Session, class_id: int) -> Optional[models.ClassGroup]:
    return (
        db.query(models.ClassGroup)
        .filter(models.ClassGroup.id == class_id)
        .first()
    )


def create_class(db: Session, name: str) -> models.ClassGroup:
    class_group = models.ClassGroup(name=name)
    db.add(class_group)
    db.commit()
    db.refresh(class_group)
    return class_group


def delete_class(db: Session, class_id: int) -> None:
    db.query(models.ScheduleEntry).filter(
        models.ScheduleEntry.class_id == class_id
    ).delete()
    db.query(models.CourseRequirement).filter(
        models.CourseRequirement.class_id == class_id
    ).delete()
    db.query(models.ClassGroup).filter(
        models.ClassGroup.id == class_id
    ).delete()
    db.commit()


def get_subjects(db: Session) -> List[models.Subject]:
    return db.query(models.Subject).order_by(models.Subject.id).all()


def get_subject_by_id(db: Session, subject_id: int) -> Optional[models.Subject]:
    return (
        db.query(models.Subject).filter(models.Subject.id == subject_id).first()
    )


def create_subject(db: Session, name: str) -> models.Subject:
    subject = models.Subject(name=name)
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject


def delete_subject(db: Session, subject_id: int) -> None:
    db.query(models.ScheduleEntry).filter(
        models.ScheduleEntry.subject_id == subject_id
    ).delete()
    db.query(models.CourseRequirement).filter(
        models.CourseRequirement.subject_id == subject_id
    ).delete()
    # Teachers whose major is the subject being deleted must be detached,
    # otherwise their subject_id would point at a row that no longer exists
    # and the major-match validator would reject every new requirement for
    # them. The admin can pick a new major for them via the UI afterwards.
    db.query(models.Teacher).filter(
        models.Teacher.subject_id == subject_id
    ).update({models.Teacher.subject_id: None}, synchronize_session=False)
    db.query(models.Subject).filter(
        models.Subject.id == subject_id
    ).delete()
    db.commit()


def get_time_slots(db: Session) -> List[models.TimeSlot]:
    return db.query(models.TimeSlot).order_by(models.TimeSlot.id).all()


def get_time_slot_by_id(
    db: Session, time_slot_id: int
) -> Optional[models.TimeSlot]:
    return (
        db.query(models.TimeSlot)
        .filter(models.TimeSlot.id == time_slot_id)
        .first()
    )


def create_time_slot(
    db: Session, day: str, start_time: str, end_time: str
) -> models.TimeSlot:
    slot = models.TimeSlot(day=day, start_time=start_time, end_time=end_time)
    db.add(slot)
    db.commit()
    db.refresh(slot)

    # Whenever a new slot is added, grant availability for it to every
    # existing teacher. For teachers without any explicit availability
    # rows the "no rows = available everywhere" convention already
    # applies, but adding a row keeps the data consistent and prevents
    # restricted teachers from silently becoming unavailable for the
    # newly added slot.
    teacher_ids = [tid for (tid,) in db.query(models.Teacher.id).all()]
    if teacher_ids:
        db.add_all(
            [
                models.TeacherAvailability(
                    teacher_id=tid, time_slot_id=slot.id
                )
                for tid in teacher_ids
            ]
        )
        db.commit()
    return slot


def delete_time_slot(db: Session, time_slot_id: int) -> None:
    db.query(models.ScheduleEntry).filter(
        models.ScheduleEntry.time_slot_id == time_slot_id
    ).delete()
    db.query(models.TeacherAvailability).filter(
        models.TeacherAvailability.time_slot_id == time_slot_id
    ).delete()
    db.query(models.TimeSlot).filter(
        models.TimeSlot.id == time_slot_id
    ).delete()
    db.commit()


def _format_minutes(total_minutes: int) -> str:
    h = (total_minutes // 60) % 24
    m = total_minutes % 60
    return f"{h:02d}:{m:02d}"


def regenerate_time_slots_from_settings(
    db: Session,
    *,
    first_lesson_start: str,
    lesson_duration_minutes: int,
    break_duration_minutes: int,
    lessons_per_day: int,
    lunch_after_lesson: int,
    lunch_duration_minutes: int,
    school_days: Sequence[str],
) -> List[models.TimeSlot]:
    """Wipe all existing time slots and regenerate them from settings.

    The generated slots cover only the *teaching* periods. Breaks and the
    lunch break are intentionally not stored as rows: they are the gaps
    between consecutive lesson slots. The frontend renders the largest
    such gap as a labelled "Lunch break" row.
    """
    # Wipe slot-dependent rows first to avoid orphaned references.
    db.query(models.ScheduleEntry).delete()
    db.query(models.TeacherAvailability).delete()
    db.query(models.TimeSlot).delete()
    db.commit()

    hh, mm = first_lesson_start.split(":")
    cursor = int(hh) * 60 + int(mm)

    created: List[models.TimeSlot] = []
    for day in school_days:
        day_cursor = cursor
        for lesson_idx in range(lessons_per_day):
            start = day_cursor
            end = day_cursor + lesson_duration_minutes
            slot = models.TimeSlot(
                day=day,
                start_time=_format_minutes(start),
                end_time=_format_minutes(end),
            )
            db.add(slot)
            created.append(slot)
            day_cursor = end

            # Gap between this lesson and the next one (no gap after the
            # last lesson of the day).
            is_last = lesson_idx == lessons_per_day - 1
            if is_last:
                continue
            if (
                lunch_after_lesson
                and lesson_idx + 1 == lunch_after_lesson
                and lunch_duration_minutes > 0
            ):
                day_cursor += lunch_duration_minutes
            else:
                day_cursor += break_duration_minutes

    db.commit()
    for slot in created:
        db.refresh(slot)

    teacher_ids = [tid for (tid,) in db.query(models.Teacher.id).all()]
    if teacher_ids and created:
        db.add_all(
            [
                models.TeacherAvailability(
                    teacher_id=tid, time_slot_id=slot.id
                )
                for tid in teacher_ids
                for slot in created
            ]
        )
        db.commit()

    return created


def get_course_requirements(db: Session) -> List[models.CourseRequirement]:
    return (
        db.query(models.CourseRequirement)
        .order_by(models.CourseRequirement.id)
        .all()
    )


def get_course_requirement_by_id(
    db: Session, requirement_id: int
) -> Optional[models.CourseRequirement]:
    return (
        db.query(models.CourseRequirement)
        .filter(models.CourseRequirement.id == requirement_id)
        .first()
    )


def create_course_requirement(
    db: Session,
    class_id: int,
    subject_id: int,
    teacher_id: int,
    weekly_hours: int,
) -> models.CourseRequirement:
    requirement = models.CourseRequirement(
        class_id=class_id,
        subject_id=subject_id,
        teacher_id=teacher_id,
        weekly_hours=weekly_hours,
    )
    db.add(requirement)
    db.commit()
    db.refresh(requirement)
    return requirement


def delete_course_requirement(db: Session, requirement_id: int) -> None:
    db.query(models.CourseRequirement).filter(
        models.CourseRequirement.id == requirement_id
    ).delete()
    db.commit()


def get_teacher_availability(db: Session) -> List[models.TeacherAvailability]:
    return db.query(models.TeacherAvailability).all()


def set_teacher_availability(
    db: Session, teacher_id: int, time_slot_id: int
) -> models.TeacherAvailability:
    existing = (
        db.query(models.TeacherAvailability)
        .filter(
            models.TeacherAvailability.teacher_id == teacher_id,
            models.TeacherAvailability.time_slot_id == time_slot_id,
        )
        .first()
    )
    if existing:
        return existing
    availability = models.TeacherAvailability(
        teacher_id=teacher_id, time_slot_id=time_slot_id
    )
    db.add(availability)
    db.commit()
    db.refresh(availability)
    return availability


def unset_teacher_availability(
    db: Session, teacher_id: int, time_slot_id: int
) -> None:
    db.query(models.TeacherAvailability).filter(
        models.TeacherAvailability.teacher_id == teacher_id,
        models.TeacherAvailability.time_slot_id == time_slot_id,
    ).delete()
    db.commit()


def is_teacher_available_in_slot(
    db: Session, teacher_id: int, time_slot_id: int
) -> bool:
    """Treat a teacher with no availability rows as available everywhere.

    Otherwise the slot must be present in the teacher's availability list.
    """
    has_any = (
        db.query(models.TeacherAvailability)
        .filter(models.TeacherAvailability.teacher_id == teacher_id)
        .first()
        is not None
    )
    if not has_any:
        return True
    explicit = (
        db.query(models.TeacherAvailability)
        .filter(
            models.TeacherAvailability.teacher_id == teacher_id,
            models.TeacherAvailability.time_slot_id == time_slot_id,
        )
        .first()
    )
    return explicit is not None


def get_schedule(db: Session) -> List[models.ScheduleEntry]:
    return (
        db.query(models.ScheduleEntry)
        .order_by(models.ScheduleEntry.id)
        .all()
    )


def get_schedule_entry_by_id(
    db: Session, entry_id: int
) -> Optional[models.ScheduleEntry]:
    return (
        db.query(models.ScheduleEntry)
        .filter(models.ScheduleEntry.id == entry_id)
        .first()
    )


def can_move_schedule_entry(
    db: Session, entry: models.ScheduleEntry, target_time_slot_id: int
) -> bool:
    teacher_conflict = (
        db.query(models.ScheduleEntry)
        .filter(
            models.ScheduleEntry.id != entry.id,
            models.ScheduleEntry.teacher_id == entry.teacher_id,
            models.ScheduleEntry.time_slot_id == target_time_slot_id,
        )
        .first()
    )
    if teacher_conflict:
        return False

    class_conflict = (
        db.query(models.ScheduleEntry)
        .filter(
            models.ScheduleEntry.id != entry.id,
            models.ScheduleEntry.class_id == entry.class_id,
            models.ScheduleEntry.time_slot_id == target_time_slot_id,
        )
        .first()
    )
    if class_conflict:
        return False

    return is_teacher_available_in_slot(db, entry.teacher_id, target_time_slot_id)


def can_place_schedule_entry(
    db: Session,
    class_id: int,
    teacher_id: int,
    target_time_slot_id: int,
) -> bool:
    teacher_conflict = (
        db.query(models.ScheduleEntry)
        .filter(
            models.ScheduleEntry.teacher_id == teacher_id,
            models.ScheduleEntry.time_slot_id == target_time_slot_id,
        )
        .first()
    )
    if teacher_conflict:
        return False

    class_conflict = (
        db.query(models.ScheduleEntry)
        .filter(
            models.ScheduleEntry.class_id == class_id,
            models.ScheduleEntry.time_slot_id == target_time_slot_id,
        )
        .first()
    )
    if class_conflict:
        return False

    return is_teacher_available_in_slot(db, teacher_id, target_time_slot_id)


def create_schedule_entry(
    db: Session,
    class_id: int,
    subject_id: int,
    teacher_id: int,
    time_slot_id: int,
) -> models.ScheduleEntry:
    entry = models.ScheduleEntry(
        class_id=class_id,
        subject_id=subject_id,
        teacher_id=teacher_id,
        time_slot_id=time_slot_id,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def move_schedule_entry(
    db: Session, entry: models.ScheduleEntry, target_time_slot_id: int
) -> models.ScheduleEntry:
    entry.time_slot_id = target_time_slot_id
    db.commit()
    db.refresh(entry)
    return entry


def clear_schedule(db: Session) -> None:
    db.query(models.ScheduleEntry).delete()
    db.commit()


def reset_all(db: Session) -> None:
    db.query(models.ScheduleEntry).delete()
    db.query(models.TeacherAvailability).delete()
    db.query(models.CourseRequirement).delete()
    db.query(models.TimeSlot).delete()
    db.query(models.Subject).delete()
    db.query(models.ClassGroup).delete()
    db.query(models.Teacher).delete()
    db.commit()


def seed_sample_data(db: Session) -> None:
    """Insert a small, deterministic sample dataset for demos."""
    reset_all(db)

    classes = [
        models.ClassGroup(id=1, name="9A"),
        models.ClassGroup(id=2, name="10A"),
    ]
    subjects = [
        models.Subject(id=1, name="Mathematics"),
        models.Subject(id=2, name="Physics"),
        models.Subject(id=3, name="Chemistry"),
    ]
    db.add_all(classes + subjects)
    db.flush()

    teachers = [
        models.Teacher(
            id=1,
            name="Zeynep Kaya",
            subject_id=1,
            color=TEACHER_COLOR_PALETTE[0],
        ),
        models.Teacher(
            id=2,
            name="Mehmet Demir",
            subject_id=2,
            color=TEACHER_COLOR_PALETTE[1],
        ),
        models.Teacher(
            id=3,
            name="Ayşe Yılmaz",
            subject_id=3,
            color=TEACHER_COLOR_PALETTE[2],
        ),
    ]
    db.add_all(teachers)
    db.flush()

    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    hours = [
        ("09:00", "10:00"),
        ("10:00", "11:00"),
        ("11:00", "12:00"),
        ("13:00", "14:00"),
        ("14:00", "15:00"),
    ]
    slot_id = 1
    slots = []
    for day in days:
        for start, end in hours:
            slots.append(
                models.TimeSlot(
                    id=slot_id, day=day, start_time=start, end_time=end
                )
            )
            slot_id += 1
    db.add_all(slots)
    db.flush()

    availability = [
        models.TeacherAvailability(teacher_id=t.id, time_slot_id=s.id)
        for t in teachers
        for s in slots
    ]
    db.add_all(availability)

    requirements = [
        models.CourseRequirement(
            id=1, class_id=1, subject_id=1, teacher_id=1, weekly_hours=4
        ),
        models.CourseRequirement(
            id=2, class_id=1, subject_id=2, teacher_id=2, weekly_hours=3
        ),
        models.CourseRequirement(
            id=3, class_id=1, subject_id=3, teacher_id=3, weekly_hours=2
        ),
        models.CourseRequirement(
            id=4, class_id=2, subject_id=1, teacher_id=1, weekly_hours=4
        ),
        models.CourseRequirement(
            id=5, class_id=2, subject_id=2, teacher_id=2, weekly_hours=3
        ),
    ]
    db.add_all(requirements)

    db.commit()


def save_schedule(
    db: Session, entries: List[models.ScheduleEntry]
) -> List[models.ScheduleEntry]:
    db.add_all(entries)
    db.commit()
    for entry in entries:
        db.refresh(entry)
    return entries
