"""initial schema: itineraries + outbox_events

Revision ID: 0001
Revises:
Create Date: 2026-09-09

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "itineraries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_name", sa.String(length=255), nullable=False),
        sa.Column("origin_airport_id", sa.Integer(), nullable=False),
        sa.Column("origin_airport_code", sa.String(length=10), nullable=False),
        sa.Column("origin_airport_name", sa.String(length=255), nullable=False),
        sa.Column("destination_airport_id", sa.Integer(), nullable=False),
        sa.Column("destination_airport_code", sa.String(length=10), nullable=False),
        sa.Column("destination_airport_name", sa.String(length=255), nullable=False),
        sa.Column("travel_date", sa.Date(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_itineraries_travel_date", "itineraries", ["travel_date"])
    op.create_index("ix_itineraries_origin_airport_id", "itineraries", ["origin_airport_id"])
    op.create_index("ix_itineraries_destination_airport_id", "itineraries", ["destination_airport_id"])
    op.create_index("ix_itineraries_created_at", "itineraries", ["created_at"])

    op.create_table(
        "outbox_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("aggregate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=255), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_outbox_events_aggregate_id", "outbox_events", ["aggregate_id"])
    # Indice clave para el polling del OutboxRelay (`WHERE published_at IS NULL`).
    op.create_index("ix_outbox_events_published_at", "outbox_events", ["published_at"])
    op.create_index("ix_outbox_events_created_at", "outbox_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_outbox_events_created_at", table_name="outbox_events")
    op.drop_index("ix_outbox_events_published_at", table_name="outbox_events")
    op.drop_index("ix_outbox_events_aggregate_id", table_name="outbox_events")
    op.drop_table("outbox_events")

    op.drop_index("ix_itineraries_created_at", table_name="itineraries")
    op.drop_index("ix_itineraries_destination_airport_id", table_name="itineraries")
    op.drop_index("ix_itineraries_origin_airport_id", table_name="itineraries")
    op.drop_index("ix_itineraries_travel_date", table_name="itineraries")
    op.drop_table("itineraries")
