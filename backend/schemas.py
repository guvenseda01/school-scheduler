from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TeacherIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    subject_id: int
    color: Optional[str] = Field(
        default=None,
        pattern=r"^#([0-9a-fA-F]{6})$",
    )


class TeacherOut(BaseModel):
    id: int
    name: str
    subject_id: Optional[int] = None
    color: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ClassGroupIn(BaseModel):
    name: str = Field(min_length=1, max_length=50)


class ClassGroupOut(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class SubjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class SubjectOut(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class TimeSlotIn(BaseModel):
    day: str = Field(min_length=1)
    start_time: str = Field(min_length=1)
    end_time: str = Field(min_length=1)


class TimeSlotOut(BaseModel):
    id: int
    day: str
    start_time: str
    end_time: str

    model_config = ConfigDict(from_attributes=True)


class CourseRequirementIn(BaseModel):
    class_id: int
    subject_id: int
    teacher_id: int
    weekly_hours: int = Field(ge=1, le=40)


class CourseRequirementOut(BaseModel):
    id: int
    class_id: int
    subject_id: int
    teacher_id: int
    weekly_hours: int

    model_config = ConfigDict(from_attributes=True)


class TeacherAvailabilityIn(BaseModel):
    teacher_id: int
    time_slot_id: int


class TeacherAvailabilityOut(BaseModel):
    id: int
    teacher_id: int
    time_slot_id: int

    model_config = ConfigDict(from_attributes=True)


class ScheduleEntryOut(BaseModel):
    id: int
    class_id: int
    class_name: str
    subject_id: int
    subject_name: str
    teacher_id: int
    teacher_name: str
    teacher_color: Optional[str] = None
    time_slot_id: int
    day: str
    start_time: str
    end_time: str


class ScheduleMoveIn(BaseModel):
    target_time_slot_id: int


class ScheduleCreateIn(BaseModel):
    class_id: int
    subject_id: int
    teacher_id: int
    target_time_slot_id: int


class UnassignedLesson(BaseModel):
    class_id: int
    class_name: str
    subject_id: int
    subject_name: str
    teacher_id: int
    teacher_name: str
    teacher_color: Optional[str] = None
    reason: str


class GenerateScheduleResponse(BaseModel):
    schedule: List[ScheduleEntryOut]
    unassigned: List[UnassignedLesson]


VALID_DAYS = {
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
}


class ScheduleSettingsIn(BaseModel):
    """Configuration that the backend turns into a full week of lesson slots."""

    first_lesson_start: str = Field(
        description="Start time of lesson 1 in HH:MM (24h)."
    )
    lesson_duration_minutes: int = Field(ge=5, le=240)
    break_duration_minutes: int = Field(ge=0, le=120)
    lessons_per_day: int = Field(ge=1, le=15)
    lunch_after_lesson: int = Field(
        ge=0,
        description=(
            "Insert the lunch break after the lesson with this 1-based number."
            " Use 0 to disable the lunch break."
        ),
    )
    lunch_duration_minutes: int = Field(ge=0, le=240)
    school_days: List[str] = Field(min_length=1, max_length=7)

    @field_validator("first_lesson_start")
    @classmethod
    def _validate_time(cls, v: str) -> str:
        try:
            hh, mm = v.split(":")
            h, m = int(hh), int(mm)
        except Exception as exc:
            raise ValueError("first_lesson_start must be in HH:MM format") from exc
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError("first_lesson_start must be a valid clock time")
        return f"{h:02d}:{m:02d}"

    @field_validator("school_days")
    @classmethod
    def _validate_days(cls, v: List[str]) -> List[str]:
        cleaned = []
        for day in v:
            if day not in VALID_DAYS:
                raise ValueError(
                    f"school_days entries must be one of {sorted(VALID_DAYS)}"
                )
            if day not in cleaned:
                cleaned.append(day)
        return cleaned


class GeneratedScheduleSettingsResponse(BaseModel):
    time_slots: List[TimeSlotOut]
    lessons_per_day: int
    school_days: List[str]
