"use client";

import { DndContext, DragEndEvent, useDraggable } from "@dnd-kit/core";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { ScheduleGrid } from "@/components/ScheduleGrid";
import { api } from "@/lib/api";
import {
  GenerateScheduleResponse,
  ScheduleEntry,
  ScheduleSettings,
  TimeSlot,
  UnassignedLesson,
} from "@/lib/types";

type UnassignedItem = UnassignedLesson & { _instanceId: string };

const ALL_DAYS = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
] as const;
type DayName = (typeof ALL_DAYS)[number];

const DEFAULT_SETTINGS: ScheduleSettings = {
  first_lesson_start: "08:45",
  lesson_duration_minutes: 40,
  break_duration_minutes: 10,
  lessons_per_day: 7,
  lunch_after_lesson: 4,
  lunch_duration_minutes: 45,
  school_days: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
};

function buildSettingsPreview(s: ScheduleSettings): string[] {
  const out: string[] = [];
  const [hh, mm] = s.first_lesson_start.split(":").map(Number);
  if (Number.isNaN(hh) || Number.isNaN(mm)) return out;
  let cursor = hh * 60 + mm;
  const fmt = (m: number) =>
    `${String(Math.floor(m / 60) % 24).padStart(2, "0")}:${String(
      m % 60
    ).padStart(2, "0")}`;
  for (let i = 0; i < s.lessons_per_day; i += 1) {
    const start = cursor;
    const end = cursor + s.lesson_duration_minutes;
    out.push(`Lesson ${i + 1}: ${fmt(start)} – ${fmt(end)}`);
    cursor = end;
    const isLast = i === s.lessons_per_day - 1;
    if (isLast) break;
    if (
      s.lunch_after_lesson &&
      i + 1 === s.lunch_after_lesson &&
      s.lunch_duration_minutes > 0
    ) {
      out.push(
        `Lunch:    ${fmt(cursor)} – ${fmt(cursor + s.lunch_duration_minutes)}`
      );
      cursor += s.lunch_duration_minutes;
    } else if (s.break_duration_minutes > 0) {
      out.push(
        `Break:    ${fmt(cursor)} – ${fmt(cursor + s.break_duration_minutes)}`
      );
      cursor += s.break_duration_minutes;
    }
  }
  return out;
}

export default function SchedulePage() {
  const qc = useQueryClient();
  const [unassigned, setUnassigned] = useState<UnassignedItem[]>([]);
  const [showSettings, setShowSettings] = useState(false);
  const [settings, setSettings] = useState<ScheduleSettings>(DEFAULT_SETTINGS);

  const {
    data: schedule,
    isLoading: loadingSchedule,
    error: scheduleError,
  } = useQuery<ScheduleEntry[]>({
    queryKey: ["schedule"],
    queryFn: api.listSchedule,
  });

  const {
    data: timeSlots,
    isLoading: loadingSlots,
    error: slotsError,
  } = useQuery<TimeSlot[]>({
    queryKey: ["time-slots"],
    queryFn: api.listTimeSlots,
  });

  const applySettings = useMutation({
    mutationFn: (s: ScheduleSettings) => api.applyScheduleSettings(s),
    onSuccess: () => {
      setUnassigned([]);
      qc.invalidateQueries({ queryKey: ["time-slots"] });
      qc.invalidateQueries({ queryKey: ["schedule"] });
    },
  });

  const settingsPreview = useMemo(
    () => buildSettingsPreview(settings),
    [settings]
  );

  const updateSetting = <K extends keyof ScheduleSettings>(
    key: K,
    value: ScheduleSettings[K]
  ) => setSettings((prev) => ({ ...prev, [key]: value }));

  const toggleSchoolDay = (day: string) => {
    setSettings((prev) => {
      const has = prev.school_days.includes(day);
      const next = has
        ? prev.school_days.filter((d) => d !== day)
        : [...prev.school_days, day];
      // Keep canonical week order so the API call is stable.
      next.sort(
        (a, b) =>
          ALL_DAYS.indexOf(a as DayName) - ALL_DAYS.indexOf(b as DayName)
      );
      return { ...prev, school_days: next };
    });
  };

  const generate = useMutation<GenerateScheduleResponse, Error>({
    mutationFn: api.generateSchedule,
    onSuccess: (result) => {
      setUnassigned(
        result.unassigned.map((u, i) => ({
          ...u,
          _instanceId: `${u.class_id}-${u.subject_id}-${u.teacher_id}-${i}-${Date.now()}`,
        }))
      );
      qc.invalidateQueries({ queryKey: ["schedule"] });
    },
  });
  const moveEntry = useMutation({
    mutationFn: ({
      entryId,
      targetTimeSlotId,
    }: {
      entryId: number;
      targetTimeSlotId: number;
    }) => api.moveScheduleEntry(entryId, targetTimeSlotId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["schedule"] }),
  });
  const placeUnassigned = useMutation({
    mutationFn: ({
      lesson,
      targetTimeSlotId,
    }: {
      lesson: UnassignedItem;
      targetTimeSlotId: number;
    }) =>
      api.createScheduleEntryManual({
        class_id: lesson.class_id,
        subject_id: lesson.subject_id,
        teacher_id: lesson.teacher_id,
        target_time_slot_id: targetTimeSlotId,
      }),
    onSuccess: (_created, vars) => {
      setUnassigned((prev) =>
        prev.filter((item) => item._instanceId !== vars.lesson._instanceId)
      );
      qc.invalidateQueries({ queryKey: ["schedule"] });
    },
  });

  const onDragEnd = (event: DragEndEvent) => {
    if (!event.over) return;
    const activeId = String(event.active.id);
    const overId = String(event.over.id);
    const targetTimeSlotId = Number(overId.replace("slot-", ""));
    if (!Number.isFinite(targetTimeSlotId)) return;

    if (activeId.startsWith("entry-")) {
      const entryId = Number(activeId.replace("entry-", ""));
      if (!Number.isFinite(entryId)) return;
      moveEntry.mutate({ entryId, targetTimeSlotId });
      return;
    }

    if (activeId.startsWith("unassigned-")) {
      const lesson = event.active.data.current?.lesson as
        | UnassignedItem
        | undefined;
      if (!lesson) return;
      placeUnassigned.mutate({ lesson, targetTimeSlotId });
    }
  };

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Weekly schedule</h1>
          <p className="mt-1 text-sm text-slate-600">
            The optimizer maximizes placed lessons and tries to distribute each
            course across the week. You can manually drag lessons to another
            slot; every move is validated on the backend.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setShowSettings((v) => !v)}
            className="rounded-md border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-100"
          >
            {showSettings ? "Close settings" : "Schedule settings"}
          </button>
          <button
            onClick={() => generate.mutate()}
            disabled={
              generate.isPending ||
              moveEntry.isPending ||
              placeUnassigned.isPending
            }
            className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-700 disabled:opacity-50"
          >
            {generate.isPending ? "Generating..." : "Generate schedule"}
          </button>
        </div>
      </header>

      {showSettings && (
        <section className="rounded-lg border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-medium text-slate-800">
            Schedule settings
          </h2>
          <p className="mt-1 text-xs text-slate-500">
            Define the school day once and the backend will generate the full
            week of time slots automatically. Applying these settings replaces
            the current time slots and clears the existing schedule.
          </p>

          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <label className="flex flex-col text-xs text-slate-600">
              <span className="mb-1">First lesson starts at</span>
              <input
                type="time"
                value={settings.first_lesson_start}
                onChange={(e) =>
                  updateSetting("first_lesson_start", e.target.value)
                }
                className="rounded-md border border-slate-300 px-3 py-2 text-sm"
              />
            </label>
            <label className="flex flex-col text-xs text-slate-600">
              <span className="mb-1">Lesson duration (minutes)</span>
              <input
                type="number"
                min={5}
                max={240}
                value={settings.lesson_duration_minutes}
                onChange={(e) =>
                  updateSetting(
                    "lesson_duration_minutes",
                    Number(e.target.value)
                  )
                }
                className="rounded-md border border-slate-300 px-3 py-2 text-sm"
              />
            </label>
            <label className="flex flex-col text-xs text-slate-600">
              <span className="mb-1">Break duration between lessons (min)</span>
              <input
                type="number"
                min={0}
                max={120}
                value={settings.break_duration_minutes}
                onChange={(e) =>
                  updateSetting(
                    "break_duration_minutes",
                    Number(e.target.value)
                  )
                }
                className="rounded-md border border-slate-300 px-3 py-2 text-sm"
              />
            </label>
            <label className="flex flex-col text-xs text-slate-600">
              <span className="mb-1">Lessons per day</span>
              <input
                type="number"
                min={1}
                max={15}
                value={settings.lessons_per_day}
                onChange={(e) =>
                  updateSetting("lessons_per_day", Number(e.target.value))
                }
                className="rounded-md border border-slate-300 px-3 py-2 text-sm"
              />
            </label>
            <label className="flex flex-col text-xs text-slate-600">
              <span className="mb-1">Lunch after lesson #</span>
              <input
                type="number"
                min={0}
                max={settings.lessons_per_day}
                value={settings.lunch_after_lesson}
                onChange={(e) =>
                  updateSetting("lunch_after_lesson", Number(e.target.value))
                }
                className="rounded-md border border-slate-300 px-3 py-2 text-sm"
              />
              <span className="mt-1 text-[11px] text-slate-400">
                Use 0 to disable the lunch break.
              </span>
            </label>
            <label className="flex flex-col text-xs text-slate-600">
              <span className="mb-1">Lunch duration (minutes)</span>
              <input
                type="number"
                min={0}
                max={240}
                value={settings.lunch_duration_minutes}
                onChange={(e) =>
                  updateSetting(
                    "lunch_duration_minutes",
                    Number(e.target.value)
                  )
                }
                className="rounded-md border border-slate-300 px-3 py-2 text-sm"
              />
            </label>
          </div>

          <div className="mt-4">
            <span className="text-xs text-slate-600">School days</span>
            <div className="mt-2 flex flex-wrap gap-2">
              {ALL_DAYS.map((d) => {
                const checked = settings.school_days.includes(d);
                return (
                  <button
                    key={d}
                    type="button"
                    onClick={() => toggleSchoolDay(d)}
                    className={`rounded-md border px-3 py-1.5 text-xs ${
                      checked
                        ? "border-slate-900 bg-slate-900 text-white"
                        : "border-slate-300 bg-white text-slate-700 hover:bg-slate-100"
                    }`}
                  >
                    {d}
                  </button>
                );
              })}
            </div>
          </div>

          {settingsPreview.length > 0 && (
            <div className="mt-4 rounded-md border border-slate-200 bg-slate-50 p-3">
              <p className="mb-2 text-xs font-medium text-slate-600">
                Preview (one day):
              </p>
              <pre className="whitespace-pre-wrap text-xs leading-5 text-slate-700">
                {settingsPreview.join("\n")}
              </pre>
            </div>
          )}

          <div className="mt-4 flex items-center gap-3">
            <button
              onClick={() => applySettings.mutate(settings)}
              disabled={
                applySettings.isPending || settings.school_days.length === 0
              }
              className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-700 disabled:opacity-50"
            >
              {applySettings.isPending
                ? "Applying..."
                : "Apply settings & regenerate slots"}
            </button>
            <button
              onClick={() => setSettings(DEFAULT_SETTINGS)}
              className="rounded-md border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-100"
            >
              Reset to defaults
            </button>
          </div>

          {applySettings.isError && (
            <p className="mt-3 text-sm text-red-700">
              {(applySettings.error as Error).message}
            </p>
          )}
          {applySettings.isSuccess && !applySettings.isPending && (
            <p className="mt-3 text-sm text-emerald-700">
              Time slots regenerated. Click <strong>Generate schedule</strong>{" "}
              above to fill them with lessons.
            </p>
          )}
        </section>
      )}

      {generate.isError && (
        <p className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {generate.error.message}
        </p>
      )}
      {moveEntry.isError && (
        <p className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {moveEntry.error.message}
        </p>
      )}
      {placeUnassigned.isError && (
        <p className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {placeUnassigned.error.message}
        </p>
      )}

      {(scheduleError || slotsError) && (
        <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          <p className="font-medium">Could not reach the backend.</p>
          <p className="mt-1">
            {(scheduleError ?? slotsError)?.message ?? "Unknown error"}
          </p>
          <p className="mt-1 text-xs opacity-80">
            Make sure the FastAPI server is running on{" "}
            <code>http://127.0.0.1:8000</code> (run{" "}
            <code>uvicorn main:app --reload</code> from the{" "}
            <code>backend/</code> folder).
          </p>
        </div>
      )}

      {(loadingSchedule || loadingSlots) &&
        !scheduleError &&
        !slotsError && (
          <p className="text-sm text-slate-500">Loading schedule...</p>
        )}

      {schedule && timeSlots && timeSlots.length > 0 && (
        <DndContext onDragEnd={onDragEnd}>
          <ScheduleGrid schedule={schedule} timeSlots={timeSlots} />

          {unassigned.length > 0 && (
            <section className="rounded-lg border border-amber-200 bg-amber-50 p-4">
              <h2 className="mb-2 text-sm font-medium text-amber-900">
                Unassigned lessons ({unassigned.length})
              </h2>
              <p className="mb-3 text-xs text-amber-900/80">
                Drag a card into the timetable to place it manually.
              </p>
              <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                {unassigned.map((u) => (
                  <UnassignedCard key={u._instanceId} lesson={u} />
                ))}
              </div>
            </section>
          )}
        </DndContext>
      )}

      {schedule && schedule.length === 0 && timeSlots && timeSlots.length > 0 && (
        <p className="text-sm text-slate-500">
          No schedule generated yet. Add some course requirements on the Data
          page and click Generate.
        </p>
      )}

      {timeSlots && timeSlots.length === 0 && (
        <p className="text-sm text-slate-500">
          No time slots in the database yet. Click{" "}
          <span className="font-medium">Reset &amp; seed sample data</span> on
          the Data page.
        </p>
      )}

    </div>
  );
}

function UnassignedCard({ lesson }: { lesson: UnassignedItem }) {
  const { attributes, listeners, setNodeRef, transform, isDragging } =
    useDraggable({
      id: `unassigned-${lesson._instanceId}`,
      data: { lesson },
    });

  const style: React.CSSProperties = {
    backgroundColor: lesson.teacher_color ?? "#fde68a",
    borderColor: lesson.teacher_color ?? "#f59e0b",
    transform: transform
      ? `translate3d(${transform.x}px, ${transform.y}px, 0)`
      : undefined,
    opacity: isDragging ? 0.6 : 1,
    cursor: "grab",
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="rounded-md border px-3 py-2 text-sm text-slate-900"
      {...listeners}
      {...attributes}
    >
      <div className="font-medium">
        {lesson.class_name} — {lesson.subject_name}
      </div>
      <div className="text-xs opacity-80">{lesson.teacher_name}</div>
      <div className="mt-1 text-[11px] opacity-70">{lesson.reason}</div>
    </div>
  );
}
