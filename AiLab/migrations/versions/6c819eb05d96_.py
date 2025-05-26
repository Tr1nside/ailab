"""Add ai_chat_id to Message

Revision ID: 6c819eb05d96
Revises: 432fceb10a2b
Create Date: 2025-05-25 16:30:50.609918

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '6c819eb05d96'
down_revision = '432fceb10a2b'
branch_labels = None
depends_on = None

def upgrade():
    # Обновление таблицы message
    with op.batch_alter_table('message', schema=None) as batch_op:
        batch_op.add_column(sa.Column('ai_chat_id', sa.Integer(), nullable=True))
        batch_op.alter_column('sender_id', existing_type=sa.INTEGER(), nullable=True)
        batch_op.alter_column('recipient_id', existing_type=sa.INTEGER(), nullable=True)
        batch_op.create_foreign_key('fk_message_ai_chat_id', 'ai_chat', ['ai_chat_id'], ['id'])

def downgrade():
    # Удаление изменений в таблице message
    with op.batch_alter_table('message', schema=None) as batch_op:
        batch_op.drop_constraint('fk_message_ai_chat_id', type_='foreignkey')
        batch_op.alter_column('recipient_id', existing_type=sa.INTEGER(), nullable=False)
        batch_op.alter_column('sender_id', existing_type=sa.INTEGER(), nullable=False)
        batch_op.drop_column('ai_chat_id')
