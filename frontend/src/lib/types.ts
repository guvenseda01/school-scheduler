export type Teacher = {
  id: number;
  name: string;
  subject_id: number | null;
  color: string | null;
};

export type ClassGroup = {
  id: number;
  name: string;
};

export type Subject = {
  id: number;
  name: string;
};

export type TimeSlot = {
  id: number;
  day: string;
  start_time: string;
  end_time: string;
};

export type CourseRequirement = {
  id: number;
  class_id: number;
  subject_id: number;
  teacher_id: number;
  weekly_hours: number;
};

export type TeacherAvailability = {
  id: number;
  teacher_id: number;
  time_slot_id: number;
};

export type ScheduleEntry = {
  id: number;
  class_id: number;
  class_name: string;
  subject_id: number;
  subject_name: string;
  teacher_id: number;
  teacher_name: string;
  teacher_color: string | null;
  time_slot_id: number;
  day: string;
  start_time: string;
  end_time: string;
};

export type UnassignedLesson = {
  class_id: number;
  class_name: string;
  subject_id: number;
  subject_name: string;
  teacher_id: number;
  teacher_name: string;
  teacher_color: string | null;
  reason: string;
};

export type GenerateScheduleResponse = {
  schedule: ScheduleEntry[];
  unassigned: UnassignedLesson[];
};

export type ScheduleSettings = {
  first_lesson_start: string;
  lesson_duration_minutes: number;
  break_duration_minutes: number;
  lessons_per_day: number;
  lunch_after_lesson: number;
  lunch_duration_minutes: number;
  school_days: string[];
};

export type GeneratedScheduleSettingsResponse = {
  time_slots: TimeSlot[];
  lessons_per_day: number;
  school_days: string[];
};
