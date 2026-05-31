"""create rag evidence chunks

Revision ID: 20260531_0012
Revises: 20260531_0011
Create Date: 2026-05-31 18:00:00.000000
"""

from typing import Any, Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260531_0012"
down_revision: Union[str, None] = "20260531_0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


class VectorType(sa.types.UserDefinedType):
    cache_ok = True

    def get_col_spec(self, **kw: Any) -> str:
        return "vector"


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "rag_evidence_chunks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.Uuid(), nullable=False),
        sa.Column("research_task_id", sa.Integer(), nullable=False),
        sa.Column("opportunity_id", sa.Integer(), nullable=True),
        sa.Column("research_source_id", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("support_level", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column("publisher", sa.String(length=200), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("embedding", VectorType(), nullable=False),
        sa.Column("embedding_model", sa.String(length=160), nullable=False),
        sa.Column("embedding_dimension", sa.Integer(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("raw_metadata", sa.JSON(), nullable=False),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"]),
        sa.ForeignKeyConstraint(["research_source_id"], ["research_sources.id"]),
        sa.ForeignKeyConstraint(["research_task_id"], ["research_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    )
    op.create_index(
        "ix_rag_evidence_chunks_task_deleted_at",
        "rag_evidence_chunks",
        ["research_task_id", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_rag_evidence_chunks_opportunity_deleted_at",
        "rag_evidence_chunks",
        ["opportunity_id", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_rag_evidence_chunks_source_deleted_at",
        "rag_evidence_chunks",
        ["research_source_id", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_rag_evidence_chunks_task_type_deleted_at",
        "rag_evidence_chunks",
        ["research_task_id", "source_type", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_rag_evidence_chunks_task_hash_deleted_at",
        "rag_evidence_chunks",
        ["research_task_id", "content_hash", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_rag_evidence_chunks_deleted_at",
        "rag_evidence_chunks",
        ["deleted_at"],
        unique=False,
    )
    op.execute(
        """
        CREATE INDEX ix_rag_evidence_chunks_embedding_hnsw_1536
        ON rag_evidence_chunks
        USING hnsw ((embedding::vector(1536)) vector_cosine_ops)
        WHERE deleted_at IS NULL AND embedding_dimension = 1536
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_rag_evidence_chunks_embedding_hnsw_1536")
    op.drop_index("ix_rag_evidence_chunks_deleted_at", table_name="rag_evidence_chunks")
    op.drop_index(
        "ix_rag_evidence_chunks_task_hash_deleted_at",
        table_name="rag_evidence_chunks",
    )
    op.drop_index(
        "ix_rag_evidence_chunks_task_type_deleted_at",
        table_name="rag_evidence_chunks",
    )
    op.drop_index(
        "ix_rag_evidence_chunks_source_deleted_at",
        table_name="rag_evidence_chunks",
    )
    op.drop_index(
        "ix_rag_evidence_chunks_opportunity_deleted_at",
        table_name="rag_evidence_chunks",
    )
    op.drop_index(
        "ix_rag_evidence_chunks_task_deleted_at",
        table_name="rag_evidence_chunks",
    )
    op.drop_table("rag_evidence_chunks")
