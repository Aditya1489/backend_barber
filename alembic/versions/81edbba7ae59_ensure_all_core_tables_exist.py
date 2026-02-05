"""ensure all core tables exist

Revision ID: 81edbba7ae59
Revises: d4eb1edab2b7
Create Date: 2026-02-05 05:39:06.050773

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '81edbba7ae59'
down_revision: Union[str, Sequence[str], None] = 'd4eb1edab2b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    IDEMPOTENT SCHEMA SYNC
    ---------------------
    This migration ensures that the core tables (users, shops, staff_profiles) 
    exist in the database. 
    
    Logic: It checks the information_schema for table existence 
    before attempting creation to avoid "already exists" errors.
    """
    conn = op.get_bind()
    
    # 1. Ensure users table exists
    if not conn.dialect.has_table(conn, "users"):
        op.create_table('users',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('name', sa.String(), nullable=False),
            sa.Column('email', sa.String(), nullable=False),
            sa.Column('phone', sa.String(), nullable=False),
            sa.Column('password', sa.String(), nullable=False),
            sa.Column('role', sa.String(), nullable=False),
            sa.Column('profilePhoto', sa.String(), nullable=True),
            sa.Column('permissions', sa.JSON(), nullable=True),
            sa.Column('createdAt', sa.DateTime(), nullable=True),
            sa.Column('experience', sa.Integer(), nullable=True),
            sa.Column('about', sa.String(), nullable=True),
            sa.Column('portfolio', sa.JSON(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
        op.create_index(op.f('ix_users_phone'), 'users', ['phone'], unique=False)

    # 2. Ensure shops table exists
    if not conn.dialect.has_table(conn, "shops"):
        op.create_table('shops',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('name', sa.String(), nullable=False),
            sa.Column('address', sa.String(), nullable=False),
            sa.Column('description', sa.String(), nullable=True),
            sa.Column('rating', sa.Float(), nullable=True),
            sa.Column('reviewsCount', sa.Integer(), nullable=True),
            sa.Column('coordinates', sa.JSON(), nullable=True),
            sa.Column('ownerId', sa.String(), nullable=True),
            sa.Column('phone', sa.String(), nullable=True),
            sa.Column('email', sa.String(), nullable=True),
            sa.Column('hours', sa.JSON(), nullable=True),
            sa.Column('amenities', sa.JSON(), nullable=True),
            sa.ForeignKeyConstraint(['ownerId'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )

    # 3. Ensure staff_profiles table exists
    if not conn.dialect.has_table(conn, "staff_profiles"):
        op.create_table('staff_profiles',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('userId', sa.String(), nullable=True),
            sa.Column('shopId', sa.String(), nullable=True),
            sa.Column('name', sa.String(), nullable=False),
            sa.Column('role', sa.String(), nullable=True),
            sa.Column('experience', sa.Integer(), nullable=True),
            sa.Column('rating', sa.Float(), nullable=True),
            sa.Column('reviewsCount', sa.Integer(), nullable=True),
            sa.Column('imageUrl', sa.String(), nullable=True),
            sa.Column('description', sa.String(), nullable=True),
            sa.Column('skills', sa.String(), nullable=True),
            sa.ForeignKeyConstraint(['shopId'], ['shops.id'], ),
            sa.ForeignKeyConstraint(['userId'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('userId')
        )

    # Clean up playing_with_neon if it exists
    if conn.dialect.has_table(conn, "playing_with_neon"):
        op.drop_table('playing_with_neon')


def downgrade() -> None:
    """Safety: downgrade logic omitted for idempotent fix migration to prevent accidental data loss"""
    pass
