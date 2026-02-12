"""allow_multiple_staff_profiles

Revision ID: 45e97532de7a
Revises: 10bc03c03f33
Create Date: 2026-02-11 03:09:30.847040

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


"""allow_multiple_staff_profiles

Revision ID: 45e97532de7a
Revises: 10bc03c03f33
Create Date: 2026-02-11 03:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '45e97532de7a'
down_revision: Union[str, Sequence[str], None] = '10bc03c03f33'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop unique constraint on userId in staff_profiles
    # Constraint name is likely 'staff_profiles_userId_key'
    op.drop_constraint('staff_profiles_userId_key', 'staff_profiles', type_='unique')


def downgrade() -> None:
    # Restore unique constraint
    op.create_unique_constraint('staff_profiles_userId_key', 'staff_profiles', ['userId'])
