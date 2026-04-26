from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from database import Base


class Teacher(Base):
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    color = Column(String, nullable=True)

    subject = relationship("Subject")


class ClassGroup(Base):
    __tablename__ = "class_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)


class TimeSlot(Base):
    __tablename__ = "time_slots"

    id = Column(Integer, primary_key=True, index=True)
    day = Column(String, nullable=False)
    start_time = Column(String, nullable=False)
    end_time = Column(String, nullable=False)

    __table_args__ = (
        UniqueConstraint("day", "start_time", "end_time", name="uq_time_slot"),
    )


class TeacherAvailability(Base):
    __tablename__ = "teacher_availability"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    time_slot_id = Column(Integer, ForeignKey("time_slots.id"), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "teacher_id", "time_slot_id", name="uq_teacher_availability"
        ),
    )


class CourseRequirement(Base):
    __tablename__ = "course_requirements"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("class_groups.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    weekly_hours = Column(Integer, nullable=False)

    class_group = relationship("ClassGroup")
    subject = relationship("Subject")
    teacher = relationship("Teacher")


class ScheduleEntry(Base):
    __tablename__ = "schedule_entries"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("class_groups.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    time_slot_id = Column(Integer, ForeignKey("time_slots.id"), nullable=False)

    class_group = relationship("ClassGroup")
    subject = relationship("Subject")
    teacher = relationship("Teacher")
    time_slot = relationship("TimeSlot")

    __table_args__ = (
        UniqueConstraint(
            "teacher_id", "time_slot_id", name="uq_teacher_slot_assignment"
        ),
        UniqueConstraint(
            "class_id", "time_slot_id", name="uq_class_slot_assignment"
        ),
    )
