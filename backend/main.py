import os
from typing import List

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import crud
import models
import scheduler
from database import get_db
from schemas import (
    ClassGroupIn,
    ClassGroupOut,
    CourseRequirementIn,
    CourseRequirementOut,
    GeneratedScheduleSettingsResponse,
    GenerateScheduleResponse,
    ScheduleCreateIn,
    ScheduleMoveIn,
    ScheduleEntryOut,
    ScheduleSettingsIn,
    SubjectIn,
    SubjectOut,
    TeacherAvailabilityIn,
    TeacherAvailabilityOut,
    TeacherIn,
    TeacherOut,
    TimeSlotIn,
    TimeSlotOut,
    UnassignedLesson,
)

app = FastAPI(title="School Scheduler API")

# Comma-separated list of allowed origins, e.g.
#   CORS_ORIGINS="https://my-frontend.vercel.app,https://staging.example.com"
# Falls back to "*" so local development still works out of the box.
_cors_env = os.environ.get("CORS_ORIGINS", "*").strip()
_cors_origins = (
    ["*"]
    if _cors_env in ("", "*")
    else [o.strip() for o in _cors_env.split(",") if o.strip()]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False if _cors_origins == ["*"] else True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "School Scheduler API is running"}


@app.post("/seed")
def seed_data(db: Session = Depends(get_db)):
    crud.seed_sample_data(db)
    return {"message": "Sample data loaded successfully"}


@app.get("/teachers", response_model=List[TeacherOut])
def list_teachers(db: Session = Depends(get_db)):
    return crud.get_teachers(db)


@app.post(
    "/teachers", response_model=TeacherOut, status_code=status.HTTP_201_CREATED
)
def create_teacher(payload: TeacherIn, db: Session = Depends(get_db)):
    if not crud.get_subject_by_id(db, payload.subject_id):
        raise HTTPException(status_code=404, detail="Subject not found.")
    return crud.create_teacher(
        db,
        name=payload.name.strip(),
        subject_id=payload.subject_id,
        color=payload.color,
    )


@app.delete("/teachers/{teacher_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_teacher(teacher_id: int, db: Session = Depends(get_db)):
    if not crud.get_teacher_by_id(db, teacher_id):
        raise HTTPException(status_code=404, detail="Teacher not found.")
    crud.delete_teacher(db, teacher_id)


@app.get("/classes", response_model=List[ClassGroupOut])
def list_classes(db: Session = Depends(get_db)):
    return crud.get_classes(db)


@app.post(
    "/classes",
    response_model=ClassGroupOut,
    status_code=status.HTTP_201_CREATED,
)
def create_class(payload: ClassGroupIn, db: Session = Depends(get_db)):
    try:
        return crud.create_class(db, name=payload.name.strip())
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="A class with this name already exists."
        )


@app.delete("/classes/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_class(class_id: int, db: Session = Depends(get_db)):
    if not crud.get_class_by_id(db, class_id):
        raise HTTPException(status_code=404, detail="Class not found.")
    crud.delete_class(db, class_id)


@app.get("/subjects", response_model=List[SubjectOut])
def list_subjects(db: Session = Depends(get_db)):
    return crud.get_subjects(db)


@app.post(
    "/subjects", response_model=SubjectOut, status_code=status.HTTP_201_CREATED
)
def create_subject(payload: SubjectIn, db: Session = Depends(get_db)):
    try:
        return crud.create_subject(db, name=payload.name.strip())
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="A subject with this name already exists."
        )


@app.delete("/subjects/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subject(subject_id: int, db: Session = Depends(get_db)):
    if not crud.get_subject_by_id(db, subject_id):
        raise HTTPException(status_code=404, detail="Subject not found.")
    crud.delete_subject(db, subject_id)


@app.get("/time-slots", response_model=List[TimeSlotOut])
def list_time_slots(db: Session = Depends(get_db)):
    return crud.get_time_slots(db)


@app.post(
    "/time-slots",
    response_model=TimeSlotOut,
    status_code=status.HTTP_201_CREATED,
)
def create_time_slot(payload: TimeSlotIn, db: Session = Depends(get_db)):
    try:
        return crud.create_time_slot(
            db,
            day=payload.day,
            start_time=payload.start_time,
            end_time=payload.end_time,
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="An identical time slot already exists."
        )


@app.delete(
    "/time-slots/{time_slot_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_time_slot(time_slot_id: int, db: Session = Depends(get_db)):
    if not crud.get_time_slot_by_id(db, time_slot_id):
        raise HTTPException(status_code=404, detail="Time slot not found.")
    crud.delete_time_slot(db, time_slot_id)


@app.post(
    "/schedule-settings",
    response_model=GeneratedScheduleSettingsResponse,
)
def apply_schedule_settings(
    payload: ScheduleSettingsIn, db: Session = Depends(get_db)
):
    """Replace the entire week of time slots with one generated from settings.

    This wipes existing time slots, teacher availability rows, and any
    schedule entries (they reference the old slots). Teacher and class
    definitions are kept.
    """
    if payload.lunch_after_lesson > payload.lessons_per_day:
        raise HTTPException(
            status_code=400,
            detail=(
                "lunch_after_lesson must be 0 (disabled) or between 1 and "
                "lessons_per_day."
            ),
        )

    created = crud.regenerate_time_slots_from_settings(
        db,
        first_lesson_start=payload.first_lesson_start,
        lesson_duration_minutes=payload.lesson_duration_minutes,
        break_duration_minutes=payload.break_duration_minutes,
        lessons_per_day=payload.lessons_per_day,
        lunch_after_lesson=payload.lunch_after_lesson,
        lunch_duration_minutes=payload.lunch_duration_minutes,
        school_days=payload.school_days,
    )
    return GeneratedScheduleSettingsResponse(
        time_slots=[
            TimeSlotOut.model_validate(slot, from_attributes=True)
            for slot in created
        ],
        lessons_per_day=payload.lessons_per_day,
        school_days=list(payload.school_days),
    )


@app.get("/course-requirements", response_model=List[CourseRequirementOut])
def list_course_requirements(db: Session = Depends(get_db)):
    return crud.get_course_requirements(db)


@app.post(
    "/course-requirements",
    response_model=CourseRequirementOut,
    status_code=status.HTTP_201_CREATED,
)
def create_course_requirement(
    payload: CourseRequirementIn, db: Session = Depends(get_db)
):
    if not crud.get_class_by_id(db, payload.class_id):
        raise HTTPException(status_code=404, detail="Class not found.")
    if not crud.get_subject_by_id(db, payload.subject_id):
        raise HTTPException(status_code=404, detail="Subject not found.")
    teacher = crud.get_teacher_by_id(db, payload.teacher_id)
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found.")
    if teacher.subject_id is not None and teacher.subject_id != payload.subject_id:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Teacher '{teacher.name}' does not teach this subject. "
                "Each teacher is assigned to one subject (their major)."
            ),
        )

    return crud.create_course_requirement(
        db,
        class_id=payload.class_id,
        subject_id=payload.subject_id,
        teacher_id=payload.teacher_id,
        weekly_hours=payload.weekly_hours,
    )


@app.delete(
    "/course-requirements/{requirement_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_course_requirement(
    requirement_id: int, db: Session = Depends(get_db)
):
    if not crud.get_course_requirement_by_id(db, requirement_id):
        raise HTTPException(
            status_code=404, detail="Course requirement not found."
        )
    crud.delete_course_requirement(db, requirement_id)


@app.get("/teacher-availability", response_model=List[TeacherAvailabilityOut])
def list_teacher_availability(db: Session = Depends(get_db)):
    return crud.get_teacher_availability(db)


@app.post(
    "/teacher-availability",
    response_model=TeacherAvailabilityOut,
    status_code=status.HTTP_201_CREATED,
)
def add_teacher_availability(
    payload: TeacherAvailabilityIn, db: Session = Depends(get_db)
):
    if not crud.get_teacher_by_id(db, payload.teacher_id):
        raise HTTPException(status_code=404, detail="Teacher not found.")
    if not crud.get_time_slot_by_id(db, payload.time_slot_id):
        raise HTTPException(status_code=404, detail="Time slot not found.")
    return crud.set_teacher_availability(
        db,
        teacher_id=payload.teacher_id,
        time_slot_id=payload.time_slot_id,
    )


@app.delete(
    "/teacher-availability", status_code=status.HTTP_204_NO_CONTENT
)
def remove_teacher_availability(
    teacher_id: int, time_slot_id: int, db: Session = Depends(get_db)
):
    crud.unset_teacher_availability(
        db, teacher_id=teacher_id, time_slot_id=time_slot_id
    )


@app.get("/schedule", response_model=List[ScheduleEntryOut])
def list_schedule(db: Session = Depends(get_db)):
    entries = crud.get_schedule(db)
    return [_serialize_entry(e) for e in entries]


@app.patch("/schedule/{entry_id}", response_model=ScheduleEntryOut)
def move_schedule_entry(
    entry_id: int, payload: ScheduleMoveIn, db: Session = Depends(get_db)
):
    entry = crud.get_schedule_entry_by_id(db, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Schedule entry not found.")
    if not crud.get_time_slot_by_id(db, payload.target_time_slot_id):
        raise HTTPException(status_code=404, detail="Target time slot not found.")
    if not crud.can_move_schedule_entry(db, entry, payload.target_time_slot_id):
        raise HTTPException(
            status_code=409,
            detail=(
                "Move violates constraints "
                "(teacher availability or class/teacher conflict)."
            ),
        )
    moved = crud.move_schedule_entry(db, entry, payload.target_time_slot_id)
    return _serialize_entry(moved)


@app.post(
    "/schedule/manual",
    response_model=ScheduleEntryOut,
    status_code=status.HTTP_201_CREATED,
)
def create_schedule_entry_manual(
    payload: ScheduleCreateIn, db: Session = Depends(get_db)
):
    if not crud.get_class_by_id(db, payload.class_id):
        raise HTTPException(status_code=404, detail="Class not found.")
    if not crud.get_subject_by_id(db, payload.subject_id):
        raise HTTPException(status_code=404, detail="Subject not found.")
    teacher = crud.get_teacher_by_id(db, payload.teacher_id)
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found.")
    if not crud.get_time_slot_by_id(db, payload.target_time_slot_id):
        raise HTTPException(status_code=404, detail="Target time slot not found.")
    if teacher.subject_id is not None and teacher.subject_id != payload.subject_id:
        raise HTTPException(
            status_code=409,
            detail="Teacher major does not match selected subject.",
        )
    if not crud.can_place_schedule_entry(
        db,
        class_id=payload.class_id,
        teacher_id=payload.teacher_id,
        target_time_slot_id=payload.target_time_slot_id,
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Cannot place lesson in that slot "
                "(teacher availability or class/teacher conflict)."
            ),
        )
    created = crud.create_schedule_entry(
        db,
        class_id=payload.class_id,
        subject_id=payload.subject_id,
        teacher_id=payload.teacher_id,
        time_slot_id=payload.target_time_slot_id,
    )
    return _serialize_entry(created)


@app.post("/generate-schedule", response_model=GenerateScheduleResponse)
def generate_schedule(db: Session = Depends(get_db)):
    requirements = crud.get_course_requirements(db)
    time_slots = crud.get_time_slots(db)
    availability = crud.get_teacher_availability(db)

    if not requirements or not time_slots:
        raise HTTPException(
            status_code=400,
            detail="Missing course requirements or time slots. Run POST /seed first.",
        )

    planned, unassigned = scheduler.generate_schedule(
        requirements=requirements,
        time_slots=time_slots,
        availability=availability,
    )

    crud.clear_schedule(db)
    new_entries = [
        models.ScheduleEntry(
            class_id=p.class_id,
            subject_id=p.subject_id,
            teacher_id=p.teacher_id,
            time_slot_id=p.time_slot_id,
        )
        for p in planned
    ]
    saved = crud.save_schedule(db, new_entries)

    teacher_map = {t.id: t.name for t in crud.get_teachers(db)}
    teacher_color_map = {t.id: t.color for t in crud.get_teachers(db)}
    class_map = {c.id: c.name for c in crud.get_classes(db)}
    subject_map = {s.id: s.name for s in crud.get_subjects(db)}

    return GenerateScheduleResponse(
        schedule=[_serialize_entry(e) for e in saved],
        unassigned=[
            UnassignedLesson(
                class_id=u.class_id,
                class_name=class_map.get(u.class_id, "?"),
                subject_id=u.subject_id,
                subject_name=subject_map.get(u.subject_id, "?"),
                teacher_id=u.teacher_id,
                teacher_name=teacher_map.get(u.teacher_id, "?"),
                teacher_color=teacher_color_map.get(u.teacher_id),
                reason=u.reason,
            )
            for u in unassigned
        ],
    )


def _serialize_entry(entry: models.ScheduleEntry) -> ScheduleEntryOut:
    return ScheduleEntryOut(
        id=entry.id,
        class_id=entry.class_id,
        class_name=entry.class_group.name,
        subject_id=entry.subject_id,
        subject_name=entry.subject.name,
        teacher_id=entry.teacher_id,
        teacher_name=entry.teacher.name,
        teacher_color=entry.teacher.color,
        time_slot_id=entry.time_slot_id,
        day=entry.time_slot.day,
        start_time=entry.time_slot.start_time,
        end_time=entry.time_slot.end_time,
    )
