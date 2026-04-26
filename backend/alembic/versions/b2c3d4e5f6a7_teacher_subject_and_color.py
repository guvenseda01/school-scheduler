"""teacher subject and color

Revision ID: b2c3d4e5f6a7
Revises: a1b38490cf06
Create Date: 2026-04-26 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b38490cf06"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PALETTE = [
    "#fde68a",
    "#bbf7d0",
    "#bfdbfe",
    "#fbcfe8",
    "#ddd6fe",
    "#fed7aa",
    "#a5f3fc",
    "#fecaca",
    "#bae6fd",
    "#d9f99d",
]


def upgrade() -> None:
    with op.batch_alter_table("teachers") as batch_op:
        batch_op.add_column(sa.Column("subject_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("color", sa.String(), nullable=True))
        batch_op.create_foreign_key(
            "fk_teachers_subject_id", "subjects", ["subject_id"], ["id"]
        )

    bind = op.get_bind()
    teachers = bind.execute(
        sa.text("SELECT id FROM teachers ORDER BY id")
    ).fetchall()
    for index, row in enumerate(teachers):
        teacher_id = row[0]
        majority = bind.execute(
            sa.text(
                "SELECT subject_id FROM course_requirements "
                "WHERE teacher_id = :tid "
                "GROUP BY subject_id ORDER BY COUNT(*) DESC LIMIT 1"
            ),
            {"tid": teacher_id},
        ).fetchone()
        subject_id = majority[0] if majority else None
        color = PALETTE[index % len(PALETTE)]
        bind.execute(
            sa.text(
                "UPDATE teachers SET subject_id = :sid, color = :c "
                "WHERE id = :tid"
            ),
            {"sid": subject_id, "c": color, "tid": teacher_id},
        )


def downgrade() -> None:
    with op.batch_alter_table("teachers") as batch_op:
        batch_op.drop_constraint("fk_teachers_subject_id", type_="foreignkey")
        batch_op.drop_column("color")
        batch_op.drop_column("subject_id")
