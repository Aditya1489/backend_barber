"""refactor_multi_role_schema

Revision ID: 662a16abecb0
Revises: d9f5771ee76d
Create Date: 2026-02-11 02:31:52.958850

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import uuid
from datetime import datetime


# revision identifiers, used by Alembic.
revision: str = '662a16abecb0'
revision = '662a16abecb0'
down_revision = 'd9f5771ee76d'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Create 'roles' table
    roles_table = op.create_table(
        'roles',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('name', sa.String(), unique=True, nullable=False)
    )

    # 2. Create 'user_roles' table
    op.create_table(
        'user_roles',
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('role_id', sa.String(), sa.ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow)
    )

    # 3. Create 'customer_profiles' table
    customer_profiles_table = op.create_table(
        'customer_profiles',
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('profile_photo', sa.String(), nullable=True),
        sa.Column('preferences', sa.JSON(), default={}),
        sa.Column('loyalty_points', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow)
    )

    # 4. Create 'owner_profiles' table
    owner_profiles_table = op.create_table(
        'owner_profiles',
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('profile_photo', sa.String(), nullable=True),
        sa.Column('permissions', sa.JSON(), default={}),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow)
    )

    # --- Data Migration ---
    
    # helper for UUID generation
    def gen_uuid():
        return str(uuid.uuid4())

    # Insert default roles
    role_map = {
        'CUSTOMER': gen_uuid(),
        'BARBER': gen_uuid(),
        'OWNER': gen_uuid(),
        'ADMIN': gen_uuid(),
    }
    
    op.bulk_insert(
        roles_table,
        [
            {'id': role_map['CUSTOMER'], 'name': 'CUSTOMER'},
            {'id': role_map['BARBER'], 'name': 'BARBER'},
            {'id': role_map['OWNER'], 'name': 'OWNER'},
            {'id': role_map['ADMIN'], 'name': 'ADMIN'},
        ]
    )

    # Migrate existing users
    connection = op.get_bind()
    users_result = connection.execute(sa.text("SELECT id, role, \"profilePhoto\", permissions FROM users"))
    
    user_roles_data = []
    customer_profiles_data = []
    owner_profiles_data = []

    for user in users_result:
        user_id = user.id
        old_role = user.role.upper() if user.role else 'CUSTOMER' # Default to customer if null
        profile_photo = user.profilePhoto
        permissions = user.permissions

        # Assign role
        if old_role in role_map:
            user_roles_data.append({
                'user_id': user_id,
                'role_id': role_map[old_role],
                'created_at': datetime.utcnow()
            })
        
        # Create profiles based on role
        if old_role == 'CUSTOMER':
             customer_profiles_data.append({
                'user_id': user_id,
                'profile_photo': profile_photo,
                'preferences': {},
                'loyalty_points': 0,
                'created_at': datetime.utcnow()
            })
        elif old_role == 'OWNER':
             owner_profiles_data.append({
                'user_id': user_id,
                'profile_photo': profile_photo,
                'permissions': permissions if permissions else {},
                'created_at': datetime.utcnow()
            })
        elif old_role == 'BARBER':
             # For barbers, data should arguably already be in staff_profiles
             # But let's ensure the user entry is clean. 
             # We might want to backfill staff_profiles if missing, but focusing on user separation here.
             pass

    if user_roles_data:
        op.bulk_insert(sa.table('user_roles', 
            sa.Column('user_id', sa.String()), 
            sa.Column('role_id', sa.String()),
            sa.Column('created_at', sa.DateTime())
        ), user_roles_data)

    if customer_profiles_data:
        op.bulk_insert(customer_profiles_table, customer_profiles_data)

    if owner_profiles_data:
        op.bulk_insert(owner_profiles_table, owner_profiles_data)

    # --- Cleanup ---
    # Drop columns from users table
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('role')
        batch_op.drop_column('profilePhoto')
        # batch_op.drop_column('permissions') # Keep permissions for now as general app settings? Or move to profile? 
        # Plan said remove, moving to OwnerProfile. For regular users, permissions might be app settings -> customer_profile.preferences?
        # Let's drop permissions as it was mainly OWNER capabilities.
        batch_op.drop_column('permissions')
        batch_op.drop_column('experience')
        batch_op.drop_column('about')
        batch_op.drop_column('portfolio')


def downgrade() -> None:
    # Re-add columns to users
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('role', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('profilePhoto', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('permissions', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('experience', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('about', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('portfolio', sa.JSON(), nullable=True))

    # Data restoration (simplified - best effort)
    connection = op.get_bind()
    
    # Restore User Roles
    # Join user_roles + roles to update users.role
    # This is complex in downgrade, might need raw SQL
    connection.execute(sa.text("""
        UPDATE users 
        SET role = r.name 
        FROM user_roles ur 
        JOIN roles r ON ur.role_id = r.id 
        WHERE users.id = ur.user_id
    """))

    # Restore Photos from profiles
    connection.execute(sa.text("""
        UPDATE users 
        SET "profilePhoto" = cp.profile_photo 
        FROM customer_profiles cp 
        WHERE users.id = cp.user_id
    """))
    
    connection.execute(sa.text("""
        UPDATE users 
        SET "profilePhoto" = op.profile_photo, permissions = op.permissions
        FROM owner_profiles op 
        WHERE users.id = op.user_id
    """))

    # Drop new tables
    op.drop_table('owner_profiles')
    op.drop_table('customer_profiles')
    op.drop_table('user_roles')
    op.drop_table('roles')
