"""Esquema inicial: users, matches, predictions, top8_picks

Revision ID: 0001
Revises:
Create Date: 2026-06-09
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

match_phase_enum = sa.Enum(
    "GROUP_STAGE", "ROUND_OF_32", "ROUND_OF_16",
    "QUARTER_FINALS", "SEMI_FINALS", "THIRD_PLACE", "FINAL",
    name="matchphase",
)
match_status_enum = sa.Enum(
    "SCHEDULED", "LIVE", "FINISHED", "POSTPONED",
    name="matchstatus",
)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("team_name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"])
    op.create_index(op.f("ix_users_team_name"), "users", ["team_name"], unique=True)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "matches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("api_fixture_id", sa.Integer(), nullable=False),
        sa.Column("home_team", sa.String(length=100), nullable=False),
        sa.Column("away_team", sa.String(length=100), nullable=False),
        sa.Column("home_team_logo", sa.String(length=255), nullable=True),
        sa.Column("away_team_logo", sa.String(length=255), nullable=True),
        sa.Column("home_score", sa.Integer(), nullable=True),
        sa.Column("away_score", sa.Integer(), nullable=True),
        sa.Column("first_goal_team", sa.String(length=100), nullable=True),
        sa.Column("phase", match_phase_enum, nullable=False),
        sa.Column("status", match_status_enum, nullable=False),
        sa.Column("match_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f("ix_matches_id"), "matches", ["id"])
    op.create_index(op.f("ix_matches_api_fixture_id"), "matches", ["api_fixture_id"], unique=True)

    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matches.id"), nullable=False),
        sa.Column("predicted_home", sa.Integer(), nullable=False),
        sa.Column("predicted_away", sa.Integer(), nullable=False),
        sa.Column("first_goal_team", sa.String(length=100), nullable=True),
        sa.Column("points_earned", sa.Integer(), nullable=False),
        sa.Column("is_calculated", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "match_id", name="uq_prediction_user_match"),
    )
    op.create_index(op.f("ix_predictions_id"), "predictions", ["id"])
    op.create_index(op.f("ix_predictions_user_id"), "predictions", ["user_id"])
    op.create_index(op.f("ix_predictions_match_id"), "predictions", ["match_id"])

    op.create_table(
        "top8_picks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("team_name", sa.String(length=100), nullable=False),
        sa.Column("points_earned", sa.Integer(), nullable=False),
        sa.Column("is_calculated", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "position", name="uq_top8_user_position"),
        sa.UniqueConstraint("user_id", "team_name", name="uq_top8_user_team"),
    )
    op.create_index(op.f("ix_top8_picks_id"), "top8_picks", ["id"])
    op.create_index(op.f("ix_top8_picks_user_id"), "top8_picks", ["user_id"])


def downgrade() -> None:
    op.drop_table("top8_picks")
    op.drop_table("predictions")
    op.drop_table("matches")
    op.drop_table("users")
    match_status_enum.drop(op.get_bind(), checkfirst=True)
    match_phase_enum.drop(op.get_bind(), checkfirst=True)
