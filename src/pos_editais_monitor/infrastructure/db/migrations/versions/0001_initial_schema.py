"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-10

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PgUUID

revision: str = "0001_initial"
down_revision: str | Sequence[str] | None = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ies",
        sa.Column("id", PgUUID(as_uuid=True), primary_key=True),
        sa.Column("codigo_emec", sa.String(32), nullable=False, unique=True),
        sa.Column("sigla", sa.String(32), nullable=False, index=True),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("categoria_administrativa", sa.String(64), nullable=False, server_default=""),
        sa.Column("organizacao_academica", sa.String(64), nullable=False, server_default=""),
        sa.Column("uf", sa.String(4), nullable=False, server_default=""),
        sa.Column("municipio", sa.String(128), nullable=False, server_default=""),
        sa.Column("ativa", sa.Boolean, nullable=False, server_default=sa.text("true"), index=True),
        sa.Column("gratuita", sa.Boolean, nullable=False, server_default=sa.text("true"), index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "fontes",
        sa.Column("id", PgUUID(as_uuid=True), primary_key=True),
        sa.Column("codigo", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("tipo", sa.String(64), nullable=False, server_default="outro"),
        sa.Column("base_url", sa.String(512), nullable=False, server_default=""),
        sa.Column("ativa", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("intervalo_minutos", sa.Integer, nullable=False, server_default="180"),
        sa.Column("spider_class", sa.String(255), nullable=False, server_default=""),
        sa.Column("ultima_execucao", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ultima_execucao_status", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "editais",
        sa.Column("id", PgUUID(as_uuid=True), primary_key=True),
        sa.Column("titulo", sa.String(512), nullable=False),
        sa.Column("ies_id", PgUUID(as_uuid=True), sa.ForeignKey("ies.id"), nullable=True),
        sa.Column("fonte_id", PgUUID(as_uuid=True), sa.ForeignKey("fontes.id"), nullable=True),
        sa.Column("nivel", sa.String(32), nullable=False, server_default="desconhecido"),
        sa.Column("modalidade", sa.String(32), nullable=False, server_default="desconhecida"),
        sa.Column("area_cnpq_codigo", sa.String(16), nullable=True, index=True),
        sa.Column("is_gratuito", sa.Boolean, nullable=False, server_default=sa.text("false"), index=True),
        sa.Column("vagas", sa.Integer, nullable=True),
        sa.Column("inscricao_de", sa.Date, nullable=True),
        sa.Column("inscricao_ate", sa.Date, nullable=True, index=True),
        sa.Column("identificador_externo_valor", sa.String(128), nullable=True),
        sa.Column("identificador_externo_fonte", sa.String(64), nullable=True),
        sa.Column("url_origem", sa.String(1024), nullable=False, server_default=""),
        sa.Column("url_pdf", sa.String(1024), nullable=True),
        sa.Column("texto_resumo", sa.Text, nullable=True),
        sa.Column("canonical_hash", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("simhash", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("status", sa.String(32), nullable=False, server_default="descoberto", index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_editais_simhash", "editais", ["simhash"])
    op.create_index("ix_editais_fonte_status", "editais", ["fonte_id", "status"])

    op.create_table(
        "snapshots",
        sa.Column("id", PgUUID(as_uuid=True), primary_key=True),
        sa.Column("edital_id", PgUUID(as_uuid=True), sa.ForeignKey("editais.id"), nullable=True),
        sa.Column("fonte_id", PgUUID(as_uuid=True), sa.ForeignKey("fontes.id"), nullable=True),
        sa.Column("url", sa.String(1024), nullable=False),
        sa.Column("http_status", sa.Integer, nullable=False, server_default="0"),
        sa.Column("content_type", sa.String(128), nullable=False, server_default=""),
        sa.Column("sha256", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("bytes_size", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("storage_path", sa.String(512), nullable=False),
        sa.Column("parser_name", sa.String(64), nullable=True),
        sa.Column("parse_confidence", sa.Float, nullable=True),
        sa.Column("headers", sa.JSON, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "subscribers",
        sa.Column("id", PgUUID(as_uuid=True), primary_key=True),
        sa.Column("nome", sa.String(128), nullable=False, unique=True, index=True),
        sa.Column("email", sa.String(255), nullable=False, index=True),
        sa.Column("formacao", sa.String(128), nullable=False, server_default=""),
        sa.Column("profile_json", sa.JSON, nullable=False),
        sa.Column("score_minimo", sa.Float, nullable=False, server_default="0.70"),
        sa.Column("digest_cron", sa.String(64), nullable=False, server_default="0 7 * * *"),
        sa.Column("ativo", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "match_records",
        sa.Column("id", PgUUID(as_uuid=True), primary_key=True),
        sa.Column("subscriber_id", PgUUID(as_uuid=True), sa.ForeignKey("subscribers.id"), nullable=False),
        sa.Column("edital_id", PgUUID(as_uuid=True), sa.ForeignKey("editais.id"), nullable=False),
        sa.Column("score", sa.Float, nullable=False),
        sa.Column("notified", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("explanation_json", sa.JSON, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_match_subscriber_edital",
        "match_records",
        ["subscriber_id", "edital_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_match_subscriber_edital", table_name="match_records")
    op.drop_table("match_records")
    op.drop_table("subscribers")
    op.drop_table("snapshots")
    op.drop_index("ix_editais_fonte_status", table_name="editais")
    op.drop_index("ix_editais_simhash", table_name="editais")
    op.drop_table("editais")
    op.drop_table("fontes")
    op.drop_table("ies")
