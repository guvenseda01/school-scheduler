# School Scheduler

A small full-stack web application that helps a school administrator build and adjust a weekly class schedule from a list of teachers, classes, subjects, time slots and course requirements.

The app generates a conflict-free timetable automatically and lets the administrator drag and drop lessons to fine-tune the result.

> Status
> - Backend: FastAPI + SQLAlchemy + SQLite + Alembic — working
> - Scheduler: bounded branch-and-bound optimizer with spread heuristics — working
> - Frontend: Next.js (App Router) + Tailwind + React Query + dnd-kit — working
> - Live deploy: not deployed (optional in the brief)

---

## 1. How I defined the problem

I framed the task as a **constrained assignment problem**:

- **Inputs**
  - `teachers` (each with one major subject and a display color)
  - `classes` (e.g. *9A*, *10A*)
  - `subjects` (e.g. *Math*, *Physics*)
  - `time_slots` (a fixed weekly grid: `day` + `start_time` + `end_time`)
  - `teacher_availability` (which teacher can teach in which slots)
  - `course_requirements` of the form *"class X must have subject Y, taught by teacher Z, for N hours per week"*
- **Output**
  - a list of `(class, subject, teacher, time_slot)` rows that fills every requirement,
  - plus a list of any lessons that could not be placed under the current constraints.

The administrator then sees this output as a weekly timetable and can drag lessons around. Every drag is validated against the same constraints before it is accepted.

## 2. Assumptions I made

- Time slots are discrete fixed-length blocks (e.g. *Monday 09:00–10:00*). Each lesson occupies exactly one slot.
- A course requirement names exactly one teacher (no team-teaching, no automatic substitutes).
- A teacher has exactly **one major subject** and can only be assigned to course requirements of that subject. This is enforced both in the API and in the UI.
- A teacher with **no explicit availability rows** is treated as available for every slot. Availability rows are only used to *restrict* a teacher; this matches how a real school admin thinks ("I only need to mark Ahmet as unavailable on Friday afternoons").
- Authentication / multi-user accounts are explicitly out of scope per the brief.

## 3. Constraints I handled vs. did not handle

**Hard constraints (always enforced — in the optimizer, in the database, and in the manual drag-and-drop API):**

1. The teacher must be available for that slot (with the convention above).
2. A teacher cannot be in two different lessons in the same slot.
3. A class cannot be in two different lessons in the same slot.
4. A teacher can only teach the subject that matches their major.
5. Every requirement should be placed exactly `weekly_hours` times when feasible.

**Soft objectives (nudged by the optimizer, not strict rules):**

- Spread the lessons of one *(class, subject)* pair across multiple weekdays whenever possible (so all 4 math hours don't pile up on Monday).
- Use as many distinct weekdays as feasible across the whole timetable, so the schedule does not leave entire days like *Wednesday* completely empty.

**Out of scope in this version (intentional, listed in the presentation):**

- Room / classroom availability (no rooms are modelled).
- Daily maximum hours per class or per teacher.
- Lesson length variations and back-to-back / break preferences (within a single configured day, all lessons share the same length and break length).
- Soft preferences such as *"this teacher prefers mornings"*.

> Lunch breaks **are** modelled, but as a *gap in the time-slot grid*, not as a stored row. The admin configures *"lunch after lesson N for M minutes"* in the settings form and the backend simply omits a slot at that point. The frontend then renders that gap as a non-droppable *"Lunch break · no lessons"* row, so no lesson can ever be placed during lunch.

## 4. Alternative approaches I considered

| Approach | Pros | Cons | Decision |
|---|---|---|---|
| **Bounded branch-and-bound (chosen)** | Optimizes for two goals at once (max placements, then better spread); transparent and easy to explain; no extra dependencies. | Worst-case exponential, so I cap the search budget. | Picked. |
| Pure greedy first-fit | Simplest possible algorithm. | Quality is sensitive to input order; can leave many lessons unassigned even when a solution exists. | Used as the starting baseline, then replaced. |
| OR-Tools CP-SAT | Industrial-strength solver; perfect for soft constraints and large inputs. | Heavy dependency; harder to justify in a 2-day exercise where reviewers should be able to read the algorithm. | Considered as the natural next step. |
| Integer Linear Programming | Very expressive. | Overkill at this size; bigger setup cost. | Skipped. |

## 5. Why I chose this solution

For a 2-day exercise, the deciding factors were **explainability** and **a meaningful improvement over the trivial baseline**:

- A bounded branch-and-bound search is short enough to read in `backend/scheduler.py` and walk through in a presentation.
- It uses an **MRV (Minimum Remaining Values)** ordering — the lesson with the *fewest* candidate slots is placed first — which catches the hard cases early.
- It uses **branch-and-bound pruning** on the number of assigned lessons, so impossible branches are cut early.
- It scores partial schedules with a `spread_score` that rewards weekday diversity, both per *(class, subject)* and globally. This is what stops the optimizer from packing everything into Monday and Tuesday and leaving Wednesday empty.
- The search has a hard node budget so the API stays responsive even on adversarial inputs; if the budget is hit, the best solution found so far is returned.
- The hard constraints are *also* enforced by the database (unique constraints) and by the drag-and-drop API. The optimizer is therefore never the only line of defense.

The administrator can always override the optimizer by dragging lessons manually — including dragging *unassigned* lessons into empty slots — and every drag is validated against the same hard constraints before it is committed.

---

## 6. User experience

The UI is built around the two things a school administrator actually needs to do:

1. **Manage the data** (`/data` page)
   - Add and remove teachers, classes, subjects, course requirements.
   - When adding a teacher, the admin picks the teacher's *major subject*; a color is auto-assigned from a fixed palette so each teacher is visually distinguishable.
   - When adding a course requirement, the *Teacher* dropdown is filtered so only teachers whose major matches the selected subject appear. This makes the *"one teacher = one major"* rule unmissable.
   - Course requirements are **grouped by class** (all of *9A* in one card, all of *10A* in another, etc.) so the admin can see at a glance how many weekly hours each class has.
   - One-click *Reset & seed sample data* button to load a small realistic dataset.

2. **Configure the school's day** (`/schedule` page → *Schedule settings*)
   - The admin enters: first lesson start time, lesson duration, break duration, lessons per day, *"lunch break after lesson N"*, lunch duration, and which weekdays are school days.
   - The backend regenerates the entire weekly time-slot grid from these settings (existing lessons are cleared because their slots no longer exist).
   - The form shows a live text preview of the resulting daily schedule before the admin clicks *Apply*. This makes the app generic for any school: 8:45-start with 40-minute lessons, 9:00-start with 50-minute lessons, etc. all work with no code changes.

3. **Generate and adjust the schedule** (`/schedule` page)
   - One click on *Generate schedule* runs the optimizer and renders the weekly grid.
   - Each lesson card shows *class — subject* + *teacher name*, colored by the teacher's color. A small legend at the top maps teachers to colors.
   - The lunch break is rendered as a non-droppable row with the calculated start / end time, so the admin cannot accidentally schedule into it.
   - Lessons can be **dragged between slots**. The backend validates teacher/class conflicts and teacher availability before accepting.
   - Lessons that the optimizer could not place appear as **draggable cards in an "Unassigned lessons" panel**, also colored by teacher. The admin can drop them anywhere on the grid; placement is validated server-side and persisted.

If the backend is not reachable, the UI shows a clear red banner with the underlying error instead of a silent "Loading…".

---

## 7. Tech stack and why

| Layer | Choice | Why |
|---|---|---|
| Backend | **FastAPI** | Recommended in the brief; auto-generated `/docs`; type-safe with Pydantic. |
| ORM | **SQLAlchemy 2.x** | Standard Python ORM; lets me swap SQLite → Postgres later with a one-line config change. |
| DB | **SQLite** | Zero-config, file-based, reviewer can run the project locally with no extra services. |
| Migrations | **Alembic** | Versioned, incremental schema changes. I avoided `Base.metadata.create_all()` because it cannot evolve an existing database. |
| Validation | **Pydantic v2** | Single source of truth for request / response shapes. |
| Frontend | **Next.js (App Router) + TypeScript** | Recommended in the brief; fast to iterate; easy to deploy on Vercel. |
| Styling | **Tailwind CSS** | Lets me ship a clean, consistent UI quickly without a custom design system. |
| Server state | **TanStack Query (React Query)** | Caching, refetching, and invalidation around the FastAPI endpoints; keeps components free of manual fetch/effect glue. |
| Drag & drop | **@dnd-kit/core** | Modern, accessible, no big dependencies, works well with the React Query cache. |

I explicitly chose **not** to add authentication, per the brief.

---

## 8. Project structure

```
school-scheduler/
├── backend/
│   ├── main.py                   # FastAPI routes (HTTP layer only)
│   ├── database.py               # SQLAlchemy engine + Session + Base
│   ├── models.py                 # ORM models (DB tables)
│   ├── schemas.py                # Pydantic request / response shapes
│   ├── crud.py                   # All DB read / write logic + sample data
│   ├── scheduler.py              # Pure optimizer (no I/O, no FastAPI, no DB)
│   ├── alembic/                  # Migration scripts
│   ├── alembic.ini               # Alembic config
│   ├── requirements.txt          # Python dependencies
│   └── school_scheduler.db       # Created by the first migration (git-ignored)
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx          # Landing page
│   │   │   ├── data/page.tsx     # Manage teachers / classes / subjects / slots / requirements
│   │   │   └── schedule/page.tsx # Generate, view and drag-and-drop the timetable
│   │   ├── components/
│   │   │   ├── Nav.tsx
│   │   │   └── ScheduleGrid.tsx  # Weekly grid + draggable lesson cards + teacher legend
│   │   └── lib/
│   │       ├── api.ts            # Typed API client
│   │       ├── types.ts          # TypeScript mirrors of the Pydantic schemas
│   │       └── query-client.tsx  # React Query provider
│   ├── next.config.ts
│   └── package.json
├── .gitignore
└── README.md
```

### Why split it this way?

- `models.py` describes **how data is stored**.
- `schemas.py` describes **what the API sends and receives**. The two can differ (e.g. response objects expose `teacher_color` even though it lives on the teacher).
- `crud.py` is the only place that touches the DB. Everything else uses it as a small library.
- `scheduler.py` is **pure**: data in, data out. No FastAPI, no DB. This makes it trivial to unit-test and easy to swap out (e.g. replace branch-and-bound with OR-Tools CP-SAT later) without touching anything else.
- `main.py` is the thin HTTP layer: validate input → call `crud` and/or `scheduler` → return a Pydantic response.

---

## 9. Database schema (high level)

| Table | Purpose |
|---|---|
| `teachers` | name, `subject_id` (their major), `color` |
| `class_groups` | name (e.g. *9A*) |
| `subjects` | name (e.g. *Math*) |
| `time_slots` | `day`, `start_time`, `end_time` (one row per weekly slot) |
| `teacher_availability` | many-to-many `(teacher_id, time_slot_id)`; missing rows for a teacher mean *available everywhere* |
| `course_requirements` | `(class_id, subject_id, teacher_id, weekly_hours)` |
| `schedule_entries` | the generated/edited timetable: `(class_id, subject_id, teacher_id, time_slot_id)` |
| `alembic_version` | bookkeeping for migrations |

Unique constraints on `schedule_entries`:
- `(teacher_id, time_slot_id)` — a teacher can only be in one place at a time.
- `(class_id, time_slot_id)` — a class can only be in one place at a time.

These make the database itself reject conflicting writes, even if a future bug were to slip past the application logic.

---

## 10. API surface

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/seed` | Reset and load a small sample dataset. |
| `GET` / `POST` / `DELETE` | `/teachers`, `/teachers/{id}` | Manage teachers (with major subject + color). |
| `GET` / `POST` / `DELETE` | `/classes`, `/classes/{id}` | Manage classes. |
| `GET` / `POST` / `DELETE` | `/subjects`, `/subjects/{id}` | Manage subjects. |
| `GET` / `POST` / `DELETE` | `/time-slots`, `/time-slots/{id}` | Manage weekly time slots (mainly used internally by `/schedule-settings`). |
| `POST` | `/schedule-settings` | Regenerate the entire weekly time-slot grid from a settings payload (start time, lesson / break / lunch durations, lessons per day, school days). |
| `GET` / `POST` / `DELETE` | `/teacher-availability` | Restrict a teacher to specific slots. |
| `GET` / `POST` / `DELETE` | `/course-requirements`, `/course-requirements/{id}` | Manage *(class, subject, teacher, hours)* requirements. |
| `POST` | `/generate-schedule` | Run the optimizer and persist the result. Returns assigned + unassigned lessons. |
| `GET` | `/schedule` | Read the current timetable. |
| `PATCH` | `/schedule/{id}` | Drag-and-drop: move an existing entry to a new time slot, validated server-side. |
| `POST` | `/schedule/manual` | Drop an unassigned lesson into a slot, validated server-side. |

Full interactive docs are at `http://127.0.0.1:8000/docs` once the backend is running.

---

## 11. Setup

### 11.1 Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

alembic upgrade head        # creates / migrates the SQLite database
uvicorn main:app --reload --reload-exclude "venv/*"
```

The API is now at `http://127.0.0.1:8000`.
Interactive docs at `http://127.0.0.1:8000/docs`.

> The `--reload-exclude "venv/*"` flag prevents the file watcher from restarting the server every time pip writes inside `venv/`.

### 11.2 Frontend

```bash
cd frontend
npm install
npm run dev
```

The UI is at `http://127.0.0.1:3000` (Next.js will pick a different port if 3000 is in use).
The frontend assumes the backend is running at `http://127.0.0.1:8000`.

### 11.3 First-run smoke test

1. Open `http://127.0.0.1:3000/data` → click **Reset & seed sample data**.
2. Open `http://127.0.0.1:3000/schedule`.
3. (Optional) Click **Schedule settings**, change the start time / lesson length / lunch position, hit **Apply**, and confirm the grid redraws.
4. Click **Generate schedule**.
5. Drag any lesson around the grid. Drag any *Unassigned lesson* card onto a free slot.
6. Stop the backend, restart it, refresh the page — the schedule is still there (this is the proof that the data is persisted in the database, not in memory).

---

## 12. How I used AI tooling

I used an AI coding assistant throughout the build, primarily for:

- scaffolding the layered backend (`models / schemas / crud / scheduler / main`),
- drafting the Alembic migrations and the seed data,
- pair-debugging environment issues (uvicorn reload loops, Next.js Turbopack startup, CORS, port collisions),
- iterating on the optimizer (greedy → branch-and-bound)
- iterating on the UX (color-coding teachers, filtering teachers by subject in the requirement form, turning unassigned lessons into draggable cards).

Every architectural decision in this README — choosing SQLite + Alembic, splitting the codebase into layers, the constraint set, the optimizer's two-goal scoring, the drag-and-drop UX etc. was a decision I made and validated. The assistant accelerated the implementation; the framing, trade-offs and rejections were mine.

---

## 13. What I would do next given more time

- Replace the bounded branch-and-bound solver with an OR-Tools CP-SAT model and use it as a drop-in implementation behind the same `scheduler.py` interface, then compare both on the same input.
- Add **rooms** as a first-class entity with their own availability.
- Add daily / weekly **load caps** per teacher and per class.
- Add **soft preferences** (e.g. *"this teacher prefers mornings"*) and a tunable weight per preference.
- Add lightweight **import / export** (CSV or Excel) so a real administrator can bring their existing data.
- Add automated tests for the optimizer and the manual placement endpoints (currently verified manually via the smoke test in §11.3).
