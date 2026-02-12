"""refine_auth_schema

Revision ID: 10bc03c03f33
Revises: 662a16abecb0
Create Date: 2026-02-11 02:57:02.003196

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


"""refine_auth_schema

Revision ID: 10bc03c03f33
Revises: 662a16abecb0
Create Date: 2026-02-11 02:56:55.772591

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid
from datetime import datetime

# revision identifiers, used by Alembic.
revision: str = '10bc03c03f33'
down_revision: Union[str, Sequence[str], None] = '662a16abecb0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- 1. Refine user_roles table ---
    
    # Add new columns
    op.add_column('user_roles', sa.Column('id', sa.String(), nullable=True)) # Temporary nullable
    op.add_column('user_roles', sa.Column('shop_id', sa.String(), sa.ForeignKey('shops.id', ondelete='CASCADE'), nullable=True))
    op.add_column('user_roles', sa.Column('active', sa.Boolean(), server_default='true', nullable=False))

    # Generate IDs for existing rows
    connection = op.get_bind()
    user_roles = connection.execute(sa.text("SELECT user_id, role_id FROM user_roles"))
    for row in user_roles:
        new_id = str(uuid.uuid4())
        connection.execute(
            sa.text("UPDATE user_roles SET id = :id WHERE user_id = :uid AND role_id = :rid"),
            {"id": new_id, "uid": row.user_id, "rid": row.role_id}
        )

    # Alter 'id' to not null
    op.alter_column('user_roles', 'id', nullable=False)

    # Drop old PK (user_id, role_id)
    # Hint: Primary key constraint name usually 'user_roles_pkey' or similar. 
    # But Alembic doesn't track names by default well. 
    # Standard postgres naming: table_pkey
    op.execute("ALTER TABLE user_roles DROP CONSTRAINT IF EXISTS user_roles_pkey")

    # Add new PK on 'id'
    op.create_primary_key("user_roles_pkey", "user_roles", ["id"])

    # Add Unique Constraint (user_id, role_id, shop_id)
    # Note: treating (user, role, NULL) as distinct from (user, role, shop)
    op.create_unique_constraint("uq_user_role_shop", "user_roles", ["user_id", "role_id", "shop_id"])


    # --- 2. Create staff_invites table ---
    op.create_table(
        'staff_invites',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('phone', sa.String(), nullable=False),
        sa.Column('shop_id', sa.String(), sa.ForeignKey('shops.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(), default='BARBER', nullable=False),
        sa.Column('status', sa.String(), default='PENDING', nullable=False), # PENDING, ACCEPTED, DECLINED, EXPIRED
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
        sa.Column('expires_at', sa.DateTime(), nullable=True)
    )
    op.create_index(op.f('ix_staff_invites_phone'), 'staff_invites', ['phone'], unique=False)


    # --- 3. Users Table Cleanup ---
    # Drop password column
    op.drop_column('users', 'password')
    
    # Ensure phone is unique if not already (it is index=True in model, but let's be safe)
    # Check if constraint exists? Or just try adding unique index.
    # op.create_unique_constraint("uq_users_phone", "users", ["phone"]) 
    # Assuming 'ix_users_phone' exists, we might want to drop and re-create as unique or leave it?
    # Models.py says unique=True usually implied? No, in models.py: phone = Column(String, index=True, nullable=False)
    # It does NOT say unique=True. 
    # WE MUST ADD UNIQUE CONSTRAINT to phone.
    # First, let's check duplicates? (Assuming none for now or we fail)
    op.drop_index('ix_users_phone', table_name='users')
    op.create_index('ix_users_phone', 'users', ['phone'], unique=True)


def downgrade() -> None:
    # --- 1. Revert Users Cleanup ---
    op.add_column('users', sa.Column('password', sa.VARCHAR(), nullable=True)) # Nullable because we can't restore passwords
    op.drop_index('ix_users_phone', table_name='users')
    op.create_index('ix_users_phone', 'users', ['phone'], unique=False)

    # --- 2. Drop staff_invites ---
    op.drop_table('staff_invites')

    # --- 3. Revert user_roles ---
    # Drop unique constraint
    op.drop_constraint("uq_user_role_shop", "user_roles", type_="unique")
    
    # Drop PK
    op.drop_constraint("user_roles_pkey", "user_roles", type_="primary")
    
    # Add old PK
    op.create_primary_key("user_roles_pkey", "user_roles", ["user_id", "role_id"])
    
    # Drop columns
    op.drop_column('user_roles', 'active')
    op.drop_column('user_roles', 'shop_id')
    op.drop_column('user_roles', 'id')
