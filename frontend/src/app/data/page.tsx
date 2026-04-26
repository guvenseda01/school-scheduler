"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";

import { api } from "@/lib/api";
import {
  ClassGroup,
  CourseRequirement,
  Subject,
  Teacher,
} from "@/lib/types";

export default function DataPage() {
  return (
    <div className="space-y-12">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Manage data</h1>
          <p className="mt-1 text-sm text-slate-600">
            Add or remove the inputs that drive the scheduler.
          </p>
        </div>
        <SeedButton />
      </header>

      <div className="grid gap-8 md:grid-cols-2">
        <TeachersSection />
        <ClassesSection />
        <SubjectsSection />
        <RequirementsSection />
      </div>
    </div>
  );
}

function SeedButton() {
  const qc = useQueryClient();
  const mutation = useMutation({
    mutationFn: api.seed,
    onSuccess: () => qc.invalidateQueries(),
  });
  return (
    <button
      onClick={() => {
        if (
          confirm(
            "This wipes everything and loads sample data. Continue?"
          )
        ) {
          mutation.mutate();
        }
      }}
      className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-100"
      disabled={mutation.isPending}
    >
      {mutation.isPending ? "Seeding..." : "Reset & seed sample data"}
    </button>
  );
}

function Card({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5">
      <h2 className="mb-4 text-lg font-medium">{title}</h2>
      {children}
    </section>
  );
}

function TeachersSection() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery<Teacher[]>({
    queryKey: ["teachers"],
    queryFn: api.listTeachers,
  });
  const { data: subjects } = useQuery<Subject[]>({
    queryKey: ["subjects"],
    queryFn: api.listSubjects,
  });
  const create = useMutation({
    mutationFn: api.createTeacher,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["teachers"] }),
  });
  const remove = useMutation({
    mutationFn: (id: number) => api.deleteTeacher(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["teachers"] });
      qc.invalidateQueries({ queryKey: ["course-requirements"] });
    },
  });

  const [name, setName] = useState("");
  const [subjectId, setSubjectId] = useState<number | "">("");
  const [error, setError] = useState<string | null>(null);

  const subjectName = (id: number | null) =>
    id == null ? "—" : subjects?.find((s) => s.id === id)?.name ?? `#${id}`;

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!name.trim()) return;
    if (subjectId === "") {
      setError("Pick the teacher's subject (their major).");
      return;
    }
    create.mutate(
      { name: name.trim(), subject_id: Number(subjectId) },
      {
        onSuccess: () => {
          setName("");
          setSubjectId("");
        },
        onError: (err: Error) => setError(err.message),
      }
    );
  };

  return (
    <Card title="Teachers">
      <form
        onSubmit={onSubmit}
        className="mb-3 grid grid-cols-1 gap-2 sm:grid-cols-[1fr_1fr_auto]"
      >
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="New teacher name"
          className="rounded-md border border-slate-300 px-3 py-1.5 text-sm"
        />
        <select
          value={subjectId}
          onChange={(e) =>
            setSubjectId(e.target.value === "" ? "" : Number(e.target.value))
          }
          className="rounded-md border border-slate-300 px-2 py-1.5 text-sm"
        >
          <option value="">Major (subject)…</option>
          {subjects?.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
        <button
          type="submit"
          disabled={create.isPending}
          className="rounded-md bg-slate-900 px-3 py-1.5 text-sm text-white hover:bg-slate-700 disabled:opacity-50"
        >
          Add
        </button>
      </form>
      {error && <p className="mb-2 text-xs text-red-600">{error}</p>}
      {isLoading && <p className="text-sm text-slate-500">Loading...</p>}
      <ul className="divide-y divide-slate-100">
        {data?.map((t) => (
          <li
            key={t.id}
            className="flex items-center justify-between py-2 text-sm"
          >
            <span className="flex items-center gap-2">
              <span
                className="inline-block h-3 w-3 rounded-full border border-slate-300"
                style={{ backgroundColor: t.color ?? "#e2e8f0" }}
                title={t.color ?? "no color"}
              />
              <span>{t.name}</span>
              <span className="text-xs text-slate-500">
                — {subjectName(t.subject_id)}
              </span>
            </span>
            <button
              onClick={() => remove.mutate(t.id)}
              className="text-xs text-red-600 hover:underline"
            >
              Delete
            </button>
          </li>
        ))}
        {data && data.length === 0 && (
          <li className="py-2 text-sm text-slate-500">No teachers yet.</li>
        )}
      </ul>
    </Card>
  );
}

function ClassesSection() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery<ClassGroup[]>({
    queryKey: ["classes"],
    queryFn: api.listClasses,
  });
  const create = useMutation({
    mutationFn: (name: string) => api.createClass(name),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["classes"] }),
  });
  const remove = useMutation({
    mutationFn: (id: number) => api.deleteClass(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["classes"] });
      qc.invalidateQueries({ queryKey: ["course-requirements"] });
    },
  });

  const [name, setName] = useState("");
  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    create.mutate(name.trim(), { onSuccess: () => setName("") });
  };

  return (
    <Card title="Classes">
      <form onSubmit={onSubmit} className="mb-3 flex gap-2">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. 9A"
          className="flex-1 rounded-md border border-slate-300 px-3 py-1.5 text-sm"
        />
        <button
          type="submit"
          disabled={create.isPending}
          className="rounded-md bg-slate-900 px-3 py-1.5 text-sm text-white hover:bg-slate-700 disabled:opacity-50"
        >
          Add
        </button>
      </form>
      {isLoading && <p className="text-sm text-slate-500">Loading...</p>}
      <ul className="divide-y divide-slate-100">
        {data?.map((c) => (
          <li
            key={c.id}
            className="flex items-center justify-between py-2 text-sm"
          >
            <span>{c.name}</span>
            <button
              onClick={() => remove.mutate(c.id)}
              className="text-xs text-red-600 hover:underline"
            >
              Delete
            </button>
          </li>
        ))}
        {data && data.length === 0 && (
          <li className="py-2 text-sm text-slate-500">No classes yet.</li>
        )}
      </ul>
    </Card>
  );
}

function SubjectsSection() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery<Subject[]>({
    queryKey: ["subjects"],
    queryFn: api.listSubjects,
  });
  const create = useMutation({
    mutationFn: (name: string) => api.createSubject(name),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["subjects"] }),
  });
  const remove = useMutation({
    mutationFn: (id: number) => api.deleteSubject(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["subjects"] });
      qc.invalidateQueries({ queryKey: ["course-requirements"] });
    },
  });

  const [name, setName] = useState("");
  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    create.mutate(name.trim(), { onSuccess: () => setName("") });
  };

  return (
    <Card title="Subjects">
      <form onSubmit={onSubmit} className="mb-3 flex gap-2">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Mathematics"
          className="flex-1 rounded-md border border-slate-300 px-3 py-1.5 text-sm"
        />
        <button
          type="submit"
          disabled={create.isPending}
          className="rounded-md bg-slate-900 px-3 py-1.5 text-sm text-white hover:bg-slate-700 disabled:opacity-50"
        >
          Add
        </button>
      </form>
      {isLoading && <p className="text-sm text-slate-500">Loading...</p>}
      <ul className="divide-y divide-slate-100">
        {data?.map((s) => (
          <li
            key={s.id}
            className="flex items-center justify-between py-2 text-sm"
          >
            <span>{s.name}</span>
            <button
              onClick={() => remove.mutate(s.id)}
              className="text-xs text-red-600 hover:underline"
            >
              Delete
            </button>
          </li>
        ))}
        {data && data.length === 0 && (
          <li className="py-2 text-sm text-slate-500">No subjects yet.</li>
        )}
      </ul>
    </Card>
  );
}

function RequirementsSection() {
  const qc = useQueryClient();
  const { data: reqs, isLoading } = useQuery<CourseRequirement[]>({
    queryKey: ["course-requirements"],
    queryFn: api.listCourseRequirements,
  });
  const { data: teachers } = useQuery<Teacher[]>({
    queryKey: ["teachers"],
    queryFn: api.listTeachers,
  });
  const { data: classes } = useQuery<ClassGroup[]>({
    queryKey: ["classes"],
    queryFn: api.listClasses,
  });
  const { data: subjects } = useQuery<Subject[]>({
    queryKey: ["subjects"],
    queryFn: api.listSubjects,
  });

  const create = useMutation({
    mutationFn: api.createCourseRequirement,
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["course-requirements"] }),
  });
  const remove = useMutation({
    mutationFn: (id: number) => api.deleteCourseRequirement(id),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["course-requirements"] }),
  });

  const [classId, setClassId] = useState<number | "">("");
  const [subjectId, setSubjectId] = useState<number | "">("");
  const [teacherId, setTeacherId] = useState<number | "">("");
  const [hours, setHours] = useState<number>(1);
  const [error, setError] = useState<string | null>(null);

  const teacherById = (id: number) =>
    teachers?.find((t) => t.id === id)?.name ?? `#${id}`;
  const subjectById = (id: number) =>
    subjects?.find((s) => s.id === id)?.name ?? `#${id}`;

  const eligibleTeachers =
    subjectId === ""
      ? []
      : teachers?.filter((t) => t.subject_id === Number(subjectId)) ?? [];

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (classId === "" || subjectId === "" || teacherId === "") {
      setError("Please pick a class, a subject, and a teacher.");
      return;
    }
    create.mutate(
      {
        class_id: Number(classId),
        subject_id: Number(subjectId),
        teacher_id: Number(teacherId),
        weekly_hours: hours,
      },
      {
        onSuccess: () => {
          setClassId("");
          setSubjectId("");
          setTeacherId("");
          setHours(1);
        },
        onError: (err: Error) => setError(err.message),
      }
    );
  };

  return (
    <Card title="Course requirements">
      <form
        onSubmit={onSubmit}
        className="mb-4 grid grid-cols-2 gap-2 text-sm"
      >
        <select
          value={classId}
          onChange={(e) =>
            setClassId(e.target.value === "" ? "" : Number(e.target.value))
          }
          className="rounded-md border border-slate-300 px-2 py-1.5"
        >
          <option value="">Class…</option>
          {classes?.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <select
          value={subjectId}
          onChange={(e) => {
            setSubjectId(e.target.value === "" ? "" : Number(e.target.value));
            setTeacherId("");
          }}
          className="rounded-md border border-slate-300 px-2 py-1.5"
        >
          <option value="">Subject…</option>
          {subjects?.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
        <select
          value={teacherId}
          onChange={(e) =>
            setTeacherId(e.target.value === "" ? "" : Number(e.target.value))
          }
          className="rounded-md border border-slate-300 px-2 py-1.5 disabled:bg-slate-100 disabled:text-slate-400"
          disabled={subjectId === ""}
        >
          <option value="">
            {subjectId === ""
              ? "Pick a subject first…"
              : eligibleTeachers.length === 0
                ? "No teacher teaches this subject"
                : "Teacher…"}
          </option>
          {eligibleTeachers.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
        <input
          type="number"
          min={1}
          max={40}
          value={hours}
          onChange={(e) => setHours(Number(e.target.value))}
          className="rounded-md border border-slate-300 px-2 py-1.5"
          placeholder="Hours/week"
        />
        <button
          type="submit"
          disabled={create.isPending}
          className="col-span-2 rounded-md bg-slate-900 px-3 py-1.5 text-white hover:bg-slate-700 disabled:opacity-50"
        >
          Add requirement
        </button>
      </form>
      {error && <p className="mb-2 text-xs text-red-600">{error}</p>}
      {isLoading && <p className="text-sm text-slate-500">Loading...</p>}
      {reqs && reqs.length === 0 && (
        <p className="py-2 text-sm text-slate-500">
          No course requirements yet.
        </p>
      )}
      {reqs && reqs.length > 0 && (
        <div className="space-y-3">
          {groupRequirementsByClass(reqs, classes ?? []).map((group) => (
            <div
              key={group.classId}
              className="rounded-md border border-slate-200 bg-slate-50/60"
            >
              <div className="flex items-center justify-between border-b border-slate-200 bg-slate-100 px-3 py-1.5">
                <span className="text-sm font-medium text-slate-800">
                  {group.className}
                </span>
                <span className="text-xs text-slate-500">
                  {group.items.length}{" "}
                  {group.items.length === 1 ? "course" : "courses"} ·{" "}
                  {group.totalHours} h/week
                </span>
              </div>
              <ul className="divide-y divide-slate-100">
                {group.items.map((r) => (
                  <li
                    key={r.id}
                    className="flex items-center justify-between px-3 py-2 text-sm"
                  >
                    <span>
                      {subjectById(r.subject_id)} —{" "}
                      <span className="text-slate-700">
                        {teacherById(r.teacher_id)}
                      </span>{" "}
                      <span className="text-slate-500">
                        ({r.weekly_hours} h/week)
                      </span>
                    </span>
                    <button
                      onClick={() => remove.mutate(r.id)}
                      className="text-xs text-red-600 hover:underline"
                    >
                      Delete
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

type GroupedRequirements = {
  classId: number;
  className: string;
  items: CourseRequirement[];
  totalHours: number;
};

function groupRequirementsByClass(
  reqs: CourseRequirement[],
  classes: ClassGroup[]
): GroupedRequirements[] {
  const byId = new Map<number, GroupedRequirements>();
  const nameById = new Map(classes.map((c) => [c.id, c.name] as const));

  for (const r of reqs) {
    const existing = byId.get(r.class_id);
    if (existing) {
      existing.items.push(r);
      existing.totalHours += r.weekly_hours;
    } else {
      byId.set(r.class_id, {
        classId: r.class_id,
        className: nameById.get(r.class_id) ?? `#${r.class_id}`,
        items: [r],
        totalHours: r.weekly_hours,
      });
    }
  }

  // Stable, human-friendly ordering of class blocks: by class name
  // ("9A", "9B", "10A", …) using a natural sort so 9 comes before 10.
  const collator = new Intl.Collator(undefined, {
    numeric: true,
    sensitivity: "base",
  });
  return Array.from(byId.values())
    .map((g) => ({
      ...g,
      items: [...g.items].sort((a, b) => a.id - b.id),
    }))
    .sort((a, b) => collator.compare(a.className, b.className));
}
