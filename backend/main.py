from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="School Scheduler API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Teacher(BaseModel):
    id: int
    name: str


class ClassGroup(BaseModel):
    id: int
    name: str


class Subject(BaseModel):
    id: int
    name: str


class TimeSlot(BaseModel):
    id: int
    day: str
    start_time: str
    end_time: str


class TeacherAvailability(BaseModel):
    teacher_id: int
    time_slot_id: int


class CourseRequirement(BaseModel):
    id: int
    class_id: int
    subject_id: int
    teacher_id: int
    weekly_hours: int


class ScheduleEntry(BaseModel):
    id: int
    class_id: int
    class_name: str
    subject_id: int
    subject_name: str
    teacher_id: int
    teacher_name: str
    time_slot_id: int
    day: str
    start_time: str
    end_time: str


class UnassignedLesson(BaseModel):
    class_name: str
    subject_name: str
    teacher_name: str
    reason: str


teachers: List[Teacher] = []
classes: List[ClassGroup] = []
subjects: List[Subject] = []
time_slots: List[TimeSlot] = []
teacher_availability: List[TeacherAvailability] = []
course_requirements: List[CourseRequirement] = []
schedule: List[ScheduleEntry] = []


@app.get("/")
def root():
    return {"message": "School Scheduler API is running"}


@app.post("/seed")
def seed_data():
    teachers.clear()
    classes.clear()
    subjects.clear()
    time_slots.clear()
    teacher_availability.clear()
    course_requirements.clear()
    schedule.clear()

    teachers.extend([
        Teacher(id=1, name="Ayşe Yılmaz"),
        Teacher(id=2, name="Mehmet Demir"),
        Teacher(id=3, name="Zeynep Kaya"),
    ])

    classes.extend([
        ClassGroup(id=1, name="9A"),
        ClassGroup(id=2, name="10A"),
    ])

    subjects.extend([
        Subject(id=1, name="Mathematics"),
        Subject(id=2, name="Physics"),
        Subject(id=3, name="Chemistry"),
    ])

    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    hours = [
        ("09:00", "10:00"),
        ("10:00", "11:00"),
        ("11:00", "12:00"),
        ("13:00", "14:00"),
        ("14:00", "15:00"),
    ]

    slot_id = 1
    for day in days:
        for start, end in hours:
            time_slots.append(
                TimeSlot(
                    id=slot_id,
                    day=day,
                    start_time=start,
                    end_time=end,
                )
            )
            slot_id += 1

    # For MVP, all teachers are available for most slots.
    for teacher in teachers:
        for slot in time_slots:
            teacher_availability.append(
                TeacherAvailability(
                    teacher_id=teacher.id,
                    time_slot_id=slot.id,
                )
            )

    course_requirements.extend([
        CourseRequirement(
            id=1,
            class_id=1,
            subject_id=1,
            teacher_id=1,
            weekly_hours=4,
        ),
        CourseRequirement(
            id=2,
            class_id=1,
            subject_id=2,
            teacher_id=2,
            weekly_hours=3,
        ),
        CourseRequirement(
            id=3,
            class_id=1,
            subject_id=3,
            teacher_id=3,
            weekly_hours=2,
        ),
        CourseRequirement(
            id=4,
            class_id=2,
            subject_id=1,
            teacher_id=1,
            weekly_hours=4,
        ),
        CourseRequirement(
            id=5,
            class_id=2,
            subject_id=2,
            teacher_id=2,
            weekly_hours=3,
        ),
    ])

    return {"message": "Sample data loaded successfully"}


@app.get("/teachers")
def get_teachers():
    return teachers


@app.get("/classes")
def get_classes():
    return classes


@app.get("/subjects")
def get_subjects():
    return subjects


@app.get("/time-slots")
def get_time_slots():
    return time_slots


@app.get("/course-requirements")
def get_course_requirements():
    return course_requirements


@app.get("/schedule")
def get_schedule():
    return schedule


def find_teacher(teacher_id: int) -> Optional[Teacher]:
    return next((teacher for teacher in teachers if teacher.id == teacher_id), None)


def find_class(class_id: int) -> Optional[ClassGroup]:
    return next((class_group for class_group in classes if class_group.id == class_id), None)


def find_subject(subject_id: int) -> Optional[Subject]:
    return next((subject for subject in subjects if subject.id == subject_id), None)


def find_time_slot(time_slot_id: int) -> Optional[TimeSlot]:
    return next((slot for slot in time_slots if slot.id == time_slot_id), None)


def is_teacher_available(teacher_id: int, time_slot_id: int) -> bool:
    return any(
        availability.teacher_id == teacher_id
        and availability.time_slot_id == time_slot_id
        for availability in teacher_availability
    )


def is_teacher_busy(teacher_id: int, time_slot_id: int) -> bool:
    return any(
        entry.teacher_id == teacher_id
        and entry.time_slot_id == time_slot_id
        for entry in schedule
    )


def is_class_busy(class_id: int, time_slot_id: int) -> bool:
    return any(
        entry.class_id == class_id
        and entry.time_slot_id == time_slot_id
        for entry in schedule
    )


@app.post("/generate-schedule")
def generate_schedule():
    schedule.clear()
    unassigned: List[UnassignedLesson] = []
    schedule_entry_id = 1

    for requirement in course_requirements:
        teacher = find_teacher(requirement.teacher_id)
        class_group = find_class(requirement.class_id)
        subject = find_subject(requirement.subject_id)

        if not teacher or not class_group or not subject:
            continue

        for _ in range(requirement.weekly_hours):
            assigned = False

            for slot in time_slots:
                if not is_teacher_available(teacher.id, slot.id):
                    continue

                if is_teacher_busy(teacher.id, slot.id):
                    continue

                if is_class_busy(class_group.id, slot.id):
                    continue

                schedule.append(
                    ScheduleEntry(
                        id=schedule_entry_id,
                        class_id=class_group.id,
                        class_name=class_group.name,
                        subject_id=subject.id,
                        subject_name=subject.name,
                        teacher_id=teacher.id,
                        teacher_name=teacher.name,
                        time_slot_id=slot.id,
                        day=slot.day,
                        start_time=slot.start_time,
                        end_time=slot.end_time,
                    )
                )

                schedule_entry_id += 1
                assigned = True
                break

            if not assigned:
                unassigned.append(
                    UnassignedLesson(
                        class_name=class_group.name,
                        subject_name=subject.name,
                        teacher_name=teacher.name,
                        reason="No available time slot found for this lesson.",
                    )
                )

    return {
        "schedule": schedule,
        "unassigned": unassigned,
    }