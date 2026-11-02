from alembic import context
from alembic.autogenerate import rewriter
from alembic.operations import ops
from sqlalchemy import create_engine, pool

from app.core.config import get_settings
from app.models import Base

config = context.config
target_metadata = Base.metadata

# Supabase tự tạo các schema auth, storage, realtime, vault... Alembic chỉ quản lý schema public.
MANAGED_SCHEMAS = {None, "public"}


def include_object(obj, name, type_, reflected, compare_to):
    if type_ == "table":
        if obj.schema not in MANAGED_SCHEMAS:
            return False
        # Bảng có trong DB nhưng không có model (tạo từ Dashboard, extension...) -> KHÔNG tự sinh drop_table.
        # Muốn xóa bảng thật: `manage.py make --empty "..."` rồi tự viết op.drop_table(...).
        if reflected and compare_to is None:
            return False
    return True


# Bảng mới tạo từ Python: tự bật RLS và thu quyền của anon/authenticated.
# Supabase mặc định cho Data API (PostgREST) đọc/ghi mọi bảng mới trong public,
# nên thiếu bước này thì ai có anon key cũng đọc được bảng. Muốn mobile đọc
# trực tiếp thì tự viết thêm GRANT + POLICY trong file migration.
_writer = rewriter.Rewriter()


@_writer.rewrites(ops.CreateTableOp)
def _secure_new_table(context, revision, op):
    table = f'{op.schema or "public"}."{op.table_name}"'
    return [
        op,
        ops.ExecuteSQLOp(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"),
        ops.ExecuteSQLOp(f"REVOKE ALL ON {table} FROM anon, authenticated"),
    ]


def process_revision_directives(context, revision, directives):
    autogenerate = config.attributes.get("autogenerate") or getattr(config.cmd_opts, "autogenerate", False)
    if autogenerate:
        script = directives[0]
        if script.upgrade_ops.is_empty():
            directives[:] = []
            print("Models và database đã khớp, không có gì để tạo migration.")
            return
    _writer(context, revision, directives)


def run_migrations_offline() -> None:
    context.configure(
        url=get_settings().sqlalchemy_url.render_as_string(hide_password=False),
        target_metadata=target_metadata,
        literal_binds=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(get_settings().sqlalchemy_url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            process_revision_directives=process_revision_directives,
            compare_type=True,
            transaction_per_migration=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
