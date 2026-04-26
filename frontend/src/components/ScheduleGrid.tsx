"use client";

import { useDraggable, useDroppable } from "@dnd-kit/core";
import { ScheduleEntry, TimeSlot } from "@/lib/types";

const DAY_ORDER = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];

const FALLBACK_TEACHER_COLOR = "#e2e8f0";

// Any inter-lesson gap longer than this is treated as a lunch break
// (and rendered as a non-droppable row). Below this threshold the gap
// is considered a normal between-lesson break and stays implicit.
const LUNCH_THRESHOLD_MINUTES = 20;

function sortDays(days: string[]) {
  return [...days].sort(
    (a, b) => DAY_ORDER.indexOf(a) - DAY_ORDER.indexOf(b)
  );
}

function timeToMinutes(t: string): number {
  const [h, m] = t.split(":").map(Number);
  return h * 60 + m;
}

export function ScheduleGrid({
  schedule,
  timeSlots,
}: {
  schedule: ScheduleEntry[];
  timeSlots: TimeSlot[];
}) {
  const days = sortDays(Array.from(new Set(timeSlots.map((s) => s.day))));
  const periods = Array.from(
    new Map(
      timeSlots.map((s) => [`${s.start_time}-${s.end_time}`, s])
    ).values()
  ).sort((a, b) => a.start_time.localeCompare(b.start_time));

  // Detect the lunch break dynamically: it is the longest gap between
  // consecutive lesson periods, provided that gap is large enough to
  // qualify as more than a normal between-lesson break.
  type RowItem =
    | { kind: "slot"; start_time: string; end_time: string }
    | { kind: "lunch"; start_time: string; end_time: string };

  let lunchGap: { start_time: string; end_time: string } | null = null;
  let longestGap = 0;
  for (let i = 0; i < periods.length - 1; i += 1) {
    const gap =
      timeToMinutes(periods[i + 1].start_time) -
      timeToMinutes(periods[i].end_time);
    if (gap > longestGap) {
      longestGap = gap;
      lunchGap = {
        start_time: periods[i].end_time,
        end_time: periods[i + 1].start_time,
      };
    }
  }
  if (longestGap < LUNCH_THRESHOLD_MINUTES) {
    lunchGap = null;
  }

  const rows: RowItem[] = [];
  for (const p of periods) {
    if (lunchGap && p.start_time === lunchGap.end_time) {
      rows.push({ kind: "lunch", ...lunchGap });
    }
    rows.push({
      kind: "slot",
      start_time: p.start_time,
      end_time: p.end_time,
    });
  }

  const lookup = new Map<string, ScheduleEntry[]>();
  for (const entry of schedule) {
    const key = `${entry.day}|${entry.start_time}-${entry.end_time}`;
    const list = lookup.get(key) ?? [];
    list.push(entry);
    lookup.set(key, list);
  }

  const teacherLegend = Array.from(
    new Map(
      schedule.map((e) => [
        e.teacher_id,
        {
          id: e.teacher_id,
          name: e.teacher_name,
          color: e.teacher_color ?? FALLBACK_TEACHER_COLOR,
        },
      ])
    ).values()
  ).sort((a, b) => a.name.localeCompare(b.name));

  return (
    <div className="space-y-3">
      {teacherLegend.length > 0 && (
        <div className="flex flex-wrap items-center gap-3 rounded-lg border border-slate-200 bg-white p-3 text-xs">
          <span className="font-medium text-slate-600">Teachers:</span>
          {teacherLegend.map((t) => (
            <span key={t.id} className="flex items-center gap-1.5">
              <span
                className="inline-block h-3 w-3 rounded-sm border border-slate-300"
                style={{ backgroundColor: t.color }}
              />
              <span>{t.name}</span>
            </span>
          ))}
        </div>
      )}
      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr>
            <th className="w-32 border-b border-slate-200 bg-slate-50 px-3 py-2 text-left font-medium text-slate-600">
              Time
            </th>
            {days.map((day) => (
              <th
                key={day}
                className="border-b border-l border-slate-200 bg-slate-50 px-3 py-2 text-left font-medium text-slate-600"
              >
                {day}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => {
            if (row.kind === "lunch") {
              return (
                <tr key={`lunch-${idx}`}>
                  <td className="border-b border-slate-200 bg-slate-50 px-3 py-2 align-top text-slate-500">
                    {row.start_time}–{row.end_time}
                  </td>
                  <td
                    colSpan={days.length}
                    className="border-b border-l border-slate-200 bg-slate-100 px-3 py-2 text-center text-xs font-medium uppercase tracking-wide text-slate-500"
                  >
                    Lunch break · no lessons
                  </td>
                </tr>
              );
            }
            const p = row;
            return (
              <tr key={`${p.start_time}-${p.end_time}`}>
                <td className="border-b border-slate-200 px-3 py-2 align-top text-slate-500">
                  {p.start_time}–{p.end_time}
                </td>
                {days.map((day) => {
                  const key = `${day}|${p.start_time}-${p.end_time}`;
                  const cells = lookup.get(key) ?? [];
                  const slot = timeSlots.find(
                    (s) =>
                      s.day === day &&
                      s.start_time === p.start_time &&
                      s.end_time === p.end_time
                  );
                  return (
                    <DroppableCell key={day + key} slotId={slot?.id}>
                      <div className="flex flex-col gap-1">
                        {cells.map((entry) => {
                          const color =
                            entry.teacher_color ?? FALLBACK_TEACHER_COLOR;
                          return (
                            <DraggableEntry
                              key={entry.id}
                              entry={entry}
                              className="rounded-md border px-2 py-1 text-slate-900"
                              style={{
                                backgroundColor: color,
                                borderColor: color,
                              }}
                            >
                              <div className="font-medium">
                                {entry.class_name} — {entry.subject_name}
                              </div>
                              <div className="text-xs opacity-80">
                                {entry.teacher_name}
                              </div>
                            </DraggableEntry>
                          );
                        })}
                      </div>
                    </DroppableCell>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
      </div>
    </div>
  );
}

function DroppableCell({
  slotId,
  children,
}: {
  slotId?: number;
  children: React.ReactNode;
}) {
  const { isOver, setNodeRef } = useDroppable({
    id: slotId ? `slot-${slotId}` : "slot-unknown",
    data: { slotId },
  });

  return (
    <td
      ref={setNodeRef}
      className={`border-b border-l border-slate-200 px-2 py-2 align-top ${
        isOver ? "bg-slate-100" : ""
      }`}
    >
      {children}
    </td>
  );
}

function DraggableEntry({
  entry,
  className,
  style: extraStyle,
  children,
}: {
  entry: ScheduleEntry;
  className: string;
  style?: React.CSSProperties;
  children: React.ReactNode;
}) {
  const { attributes, listeners, setNodeRef, transform, isDragging } =
    useDraggable({
      id: `entry-${entry.id}`,
      data: { entryId: entry.id },
    });

  const style: React.CSSProperties = {
    ...(extraStyle ?? {}),
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
      className={className}
      {...listeners}
      {...attributes}
    >
      {children}
    </div>
  );
}
