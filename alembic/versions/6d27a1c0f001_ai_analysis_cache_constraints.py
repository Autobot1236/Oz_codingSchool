"""add ai analysis cache constraints

Revision ID: 6d27a1c0f001
Revises: c5439fa798f8
Create Date: 2026-07-27

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6d27a1c0f001"
down_revision: Union[str, Sequence[str], None] = "c5439fa798f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "ai_analysis_results",
        "heatmap_url",
        existing_type=sa.String(length=255),
        nullable=True,
    )
    op.create_unique_constraint(
        "uq_ai_analysis_results_record_model",
        "ai_analysis_results",
        ["record_id", "ai_model"],
    )
    op.create_index(
        "ix_ai_analysis_results_record_created_at",
        "ai_analysis_results",
        ["record_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ai_analysis_results_record_created_at",
        table_name="ai_analysis_results",
    )
    op.drop_constraint(
        "uq_ai_analysis_results_record_model",
        "ai_analysis_results",
        type_="unique",
    )
    op.execute(
        sa.text(
            "UPDATE ai_analysis_results "
            "SET heatmap_url = '' "
            "WHERE heatmap_url IS NULL"
        )
    )
    op.alter_column(
        "ai_analysis_results",
        "heatmap_url",
        existing_type=sa.String(length=255),
        nullable=False,
    )
