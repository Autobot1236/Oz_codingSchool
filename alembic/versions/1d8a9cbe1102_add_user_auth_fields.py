"""add user authentication and profile fields

Revision ID: 1d8a9cbe1102
Revises: 4f7d2a647e31
"""
from alembic import op
import sqlalchemy as sa

revision = "1d8a9cbe1102"
down_revision = "4f7d2a647e31"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("department", sa.Enum("research", "medical", "development", name="department"), nullable=True))
    op.add_column("users", sa.Column("gender", sa.Enum("M", "F", name="gender"), nullable=True))
    op.add_column("users", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    # Preserve deployments that already have the previous doctor/nurse values.
    op.execute("ALTER TABLE users MODIFY role ENUM('doctor', 'nurse', 'pending', 'staff', 'admin') NOT NULL DEFAULT 'pending'")
    op.execute("UPDATE users SET role = 'staff' WHERE role IN ('doctor', 'nurse')")
    op.execute("ALTER TABLE users MODIFY role ENUM('pending', 'staff', 'admin') NOT NULL DEFAULT 'pending'")
    # Existing development data predates authentication; force an explicit reset instead of storing a known password.
    op.execute("UPDATE users SET password_hash = 'UNUSABLE', department = 'development', gender = 'M' WHERE password_hash IS NULL")
    op.alter_column("users", "password_hash", nullable=False)
    op.alter_column("users", "department", nullable=False)
    op.alter_column("users", "gender", nullable=False)


def downgrade() -> None:
    op.execute("ALTER TABLE users MODIFY role ENUM('doctor', 'nurse', 'pending', 'staff', 'admin') NOT NULL")
    op.execute("UPDATE users SET role = 'doctor' WHERE role IN ('pending', 'staff')")
    op.execute("ALTER TABLE users MODIFY role ENUM('doctor', 'nurse', 'admin') NOT NULL")
    op.drop_column("users", "is_active")
    op.drop_column("users", "gender")
    op.drop_column("users", "department")
    op.drop_column("users", "password_hash")
