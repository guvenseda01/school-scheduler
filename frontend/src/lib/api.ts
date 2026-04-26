import {
  ClassGroup,
  CourseRequirement,
  GeneratedScheduleSettingsResponse,
  GenerateScheduleResponse,
  ScheduleEntry,
  ScheduleSettings,
  Subject,
  Teacher,
  TeacherAvailability,
  TimeSlot,
} from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";

async function request<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // ignore
    }
    throw new Error(`${res.status} ${detail}`);
  }

  if (res.status === 204) {
    return undefined as T;
  }
  return (await res.json()) as T;
}

export const api = {
  seed: () => request<{ message: string }>("/seed", { method: "POST" }),

  listTeachers: () => request<Teacher[]>("/teachers"),
  createTeacher: (input: {
    name: string;
    subject_id: number;
    color?: string;
  }) =>
    request<Teacher>("/teachers", {
      method: "POST",
      body: JSON.stringify(input),
    }),
  deleteTeacher: (id: number) =>
    request<void>(`/teachers/${id}`, { method: "DELETE" }),

  listClasses: () => request<ClassGroup[]>("/classes"),
  createClass: (name: string) =>
    request<ClassGroup>("/classes", {
      method: "POST",
      body: JSON.stringify({ name }),
    }),
  deleteClass: (id: number) =>
    request<void>(`/classes/${id}`, { method: "DELETE" }),

  listSubjects: () => request<Subject[]>("/subjects"),
  createSubject: (name: string) =>
    request<Subject>("/subjects", {
      method: "POST",
      body: JSON.stringify({ name }),
    }),
  deleteSubject: (id: number) =>
    request<void>(`/subjects/${id}`, { method: "DELETE" }),

  listTimeSlots: () => request<TimeSlot[]>("/time-slots"),
  createTimeSlot: (input: {
    day: string;
    start_time: string;
    end_time: string;
  }) =>
    request<TimeSlot>("/time-slots", {
      method: "POST",
      body: JSON.stringify(input),
    }),
  deleteTimeSlot: (id: number) =>
    request<void>(`/time-slots/${id}`, { method: "DELETE" }),

  listCourseRequirements: () =>
    request<CourseRequirement[]>("/course-requirements"),
  createCourseRequirement: (input: {
    class_id: number;
    subject_id: number;
    teacher_id: number;
    weekly_hours: number;
  }) =>
    request<CourseRequirement>("/course-requirements", {
      method: "POST",
      body: JSON.stringify(input),
    }),
  deleteCourseRequirement: (id: number) =>
    request<void>(`/course-requirements/${id}`, {
      method: "DELETE",
    }),

  listTeacherAvailability: () =>
    request<TeacherAvailability[]>("/teacher-availability"),
  addTeacherAvailability: (input: {
    teacher_id: number;
    time_slot_id: number;
  }) =>
    request<TeacherAvailability>("/teacher-availability", {
      method: "POST",
      body: JSON.stringify(input),
    }),
  removeTeacherAvailability: (input: {
    teacher_id: number;
    time_slot_id: number;
  }) =>
    request<void>(
      `/teacher-availability?teacher_id=${input.teacher_id}&time_slot_id=${input.time_slot_id}`,
      { method: "DELETE" }
    ),

  listSchedule: () => request<ScheduleEntry[]>("/schedule"),
  moveScheduleEntry: (entryId: number, targetTimeSlotId: number) =>
    request<ScheduleEntry>(`/schedule/${entryId}`, {
      method: "PATCH",
      body: JSON.stringify({ target_time_slot_id: targetTimeSlotId }),
    }),
  createScheduleEntryManual: (input: {
    class_id: number;
    subject_id: number;
    teacher_id: number;
    target_time_slot_id: number;
  }) =>
    request<ScheduleEntry>("/schedule/manual", {
      method: "POST",
      body: JSON.stringify(input),
    }),
  generateSchedule: () =>
    request<GenerateScheduleResponse>("/generate-schedule", {
      method: "POST",
    }),

  applyScheduleSettings: (settings: ScheduleSettings) =>
    request<GeneratedScheduleSettingsResponse>("/schedule-settings", {
      method: "POST",
      body: JSON.stringify(settings),
    }),
};
