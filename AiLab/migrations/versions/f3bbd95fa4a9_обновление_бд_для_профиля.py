"""Обновление бд для профиля

Revision ID: f3bbd95fa4a9
Revises: 5e0500df559b
Create Date: 2025-03-22 13:24:54.513149

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f3bbd95fa4a9"
down_revision = "5e0500df559b"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("user_profile", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("media_type", sa.String(length=10), nullable=True)
        )

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("user_profile", schema=None) as batch_op:
        batch_op.drop_column("media_type")

    # ### end Alembic commands ###
