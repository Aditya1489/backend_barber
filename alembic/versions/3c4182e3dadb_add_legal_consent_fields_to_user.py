"""add_legal_consent_fields_to_user

Revision ID: 3c4182e3dadb
Revises: 45e97532de7a
Create Date: 2026-02-12 03:50:37.006470

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3c4182e3dadb'
down_revision: Union[str, Sequence[str], None] = '45e97532de7a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('agreed_to_privacy', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('users', sa.Column('agreed_to_terms', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('users', sa.Column('legal_consent_name', sa.String(), nullable=True))
    op.add_column('users', sa.Column('legal_consent_place', sa.String(), nullable=True))
    op.add_column('users', sa.Column('legal_consent_timestamp', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'legal_consent_timestamp')
    op.drop_column('users', 'legal_consent_place')
    op.drop_column('users', 'legal_consent_name')
    op.drop_column('users', 'agreed_to_terms')
    op.drop_column('users', 'agreed_to_privacy')
