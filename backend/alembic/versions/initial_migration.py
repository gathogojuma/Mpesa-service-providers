from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid

revision = 'initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create businesses table
    op.create_table(
        'businesses',
        sa.Column('id', sa.String(), primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('phone', sa.String(), unique=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # Create staff table
    op.create_table(
        'staff',
        sa.Column('id', sa.String(), primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('phone', sa.String(), unique=True, nullable=False),
        sa.Column('pin_hash', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('business_id', sa.String(), sa.ForeignKey('businesses.id')),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # Create transactions table
    op.create_table(
        'transactions',
        sa.Column('id', sa.String(), primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('staff_id', sa.String(), sa.ForeignKey('staff.id')),
        sa.Column('business_id', sa.String(), sa.ForeignKey('businesses.id')),
        sa.Column('mpesa_transaction_id', sa.String(), unique=True),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('customer_phone', sa.String(), nullable=False),
        sa.Column('status', sa.Enum('pending', 'confirmed', 'failed', 'flagged', name='transactionstatus')),
        sa.Column('initiated_at', sa.DateTime(), nullable=False),
        sa.Column('confirmed_at', sa.DateTime()),
        sa.Column('table_number', sa.String()),
    )

    # Create reconciliation_logs table
    op.create_table(
        'reconciliation_logs',
        sa.Column('id', sa.String(), primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('transaction_id', sa.String(), sa.ForeignKey('transactions.id')),
        sa.Column('matched_by', sa.String()),
        sa.Column('manager_id', sa.String(), sa.ForeignKey('staff.id')),
        sa.Column('notes', sa.Text()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

def downgrade():
    op.drop_table('reconciliation_logs')
    op.drop_table('transactions')
    op.drop_table('staff')
    op.drop_table('businesses')
    op.execute('DROP TYPE transactionstatus')
