import Link from "next/link";

export default function HomePage() {
  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-3xl font-semibold">School Scheduler</h1>
        <p className="mt-2 text-slate-600">
          Plan a weekly class schedule from your teachers, classes, subjects,
          and course requirements.
        </p>
      </header>

      <div className="grid gap-4 md:grid-cols-2">
        <Link
          href="/data"
          className="block rounded-lg border border-slate-200 bg-white p-6 transition hover:border-slate-400"
        >
          <h2 className="text-lg font-medium">Manage data</h2>
          <p className="mt-1 text-sm text-slate-600">
            Add or remove teachers, classes, subjects, and course requirements.
          </p>
        </Link>

        <Link
          href="/schedule"
          className="block rounded-lg border border-slate-200 bg-white p-6 transition hover:border-slate-400"
        >
          <h2 className="text-lg font-medium">View schedule</h2>
          <p className="mt-1 text-sm text-slate-600">
            Generate the timetable and inspect it as a weekly grid.
          </p>
        </Link>
      </div>
    </div>
  );
}
