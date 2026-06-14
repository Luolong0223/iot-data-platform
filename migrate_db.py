"""
数据库迁移脚本 v2 - 模型自动扫描
从 SQLAlchemy 模型自动发现所有列,与现有数据库对比,补全缺失列。

使用: python migrate_db.py
或: 在 create_app() 中自动调用
"""
import sys
import os
from sqlalchemy import inspect, text

os.environ.setdefault('DATABASE_URL', 'sqlite:///iot_platform.db')

from app import create_app
from models.database import db


def is_sqlite():
    return 'sqlite' in str(db.engine.url).lower()


def get_existing_columns(conn, table_name):
    """获取表的现有列"""
    try:
        cols = inspect(conn).get_columns(table_name)
        return {c['name'] for c in cols}
    except Exception:
        return set()


def get_all_tables(conn):
    return set(inspect(conn).get_table_names())


def get_model_columns(model_class):
    """从 SQLAlchemy 模型中提取所有列名"""
    return {c.name for c in model_class.__table__.columns}


def col_definition(col):
    """从 SQLAlchemy Column 对象生成 MySQL 列定义字符串"""
    col_type = col.type
    type_name = type(col_type).__name__.upper()

    # 类型映射
    type_map = {
        'INTEGER': 'INT',
        'BIGINTEGER': 'BIGINT',
        'SMALLINTEGER': 'SMALLINT',
        'STRING': f'VARCHAR({col_type.length})' if col_type.length else 'VARCHAR(255)',
        'TEXT': 'TEXT',
        'FLOAT': 'FLOAT',
        'NUMERIC': 'DECIMAL',
        'BOOLEAN': 'TINYINT(1)',
        'DATETIME': 'DATETIME',
        'DATE': 'DATE',
        'TIME': 'TIME',
        'JSON': 'JSON',
    }
    sql_type = type_map.get(type_name, 'VARCHAR(255)')

    # 默认值
    default = ''
    if col.default is not None and col.default.arg is not None:
        val = col.default.arg
        if isinstance(val, str):
            default = f" DEFAULT '{val}'"
        elif isinstance(val, bool):
            default = f" DEFAULT {1 if val else 0}"
        elif val is not None:
            default = f" DEFAULT {val}"
    elif col.nullable:
        default = ''  # NULL 列不需要显式 default
    else:
        # NOT NULL 但没默认值 - 给他一个安全默认值防止 INSERT 失败
        if 'INT' in sql_type:
            default = ' DEFAULT 0'
        elif 'VARCHAR' in sql_type or 'TEXT' in sql_type:
            default = " DEFAULT ''"
        elif 'FLOAT' in sql_type or 'DOUBLE' in sql_type or 'DECIMAL' in sql_type:
            default = ' DEFAULT 0.0'
        elif 'TINYINT' in sql_type:
            default = ' DEFAULT 0'
        elif 'DATETIME' in sql_type:
            default = ' NULL'

    nullable = 'NULL' if col.nullable else 'NOT NULL'
    return f"{sql_type}{default} {nullable}"


def auto_migrate():
    """从模型自动发现所有列,与数据库对比,补全缺失列"""
    print('=' * 60)
    print('🔧 [数据库迁移] v2 - 模型自动扫描模式')
    print('=' * 60)

    from models.database import db
    # 收集所有模型类
    models = []
    for cls in db.Model.__subclasses__():
        models.append(cls)
    # 包含 db.Model 自身
    if db.Model not in models:
        for cls in db.Model.__subclasses__():
            for sub in cls.__subclasses__():
                if sub not in models:
                    models.append(sub)

    print(f'📋 发现 {len(models)} 个模型: {[m.__tablename__ for m in models if hasattr(m, "__tablename__")]}\n')

    total_added = 0
    total_failed = 0

    with db.engine.connect() as conn:
        existing_tables = get_all_tables(conn)

        for model in models:
            table_name = getattr(model, '__tablename__', None)
            if not table_name:
                continue

            if table_name not in existing_tables:
                print(f'⏭️  表 {table_name} 不存在,跳过 (db.create_all() 会创建)')
                continue

            existing_cols = get_existing_columns(conn, table_name)
            model_cols = get_model_columns(model)
            missing_cols = model_cols - existing_cols

            if not missing_cols:
                print(f'✅ {table_name}: 已同步')
                continue

            print(f'🔍 {table_name}: 缺少 {len(missing_cols)} 列: {missing_cols}')

            for col_name in missing_cols:
                col = model.__table__.columns[col_name]
                col_def = col_definition(col)

                if is_sqlite():
                    sql = f'ALTER TABLE {table_name} ADD COLUMN {col_name} NULL'
                else:
                    sql = f'ALTER TABLE `{table_name}` ADD COLUMN `{col_name}` {col_def}'

                try:
                    conn.execute(text(sql))
                    conn.commit()
                    print(f'   ➕ {col_name} ({col_def}) ... ✅')
                    total_added += 1
                except Exception as e:
                    print(f'   ❌ {col_name} 失败: {str(e)[:100]}')
                    total_failed += 1
                    try:
                        conn.rollback()
                    except Exception:
                        pass

    print('\n' + '=' * 60)
    if total_failed == 0:
        print(f'✅ [数据库迁移] 完成!新增 {total_added} 列,失败 0')
    else:
        print(f'⚠️  [数据库迁移] 新增 {total_added} 列,失败 {total_failed} 列')
        print('⚠️  失败原因通常是 MySQL 用户缺少 ALTER 权限')
        print('⚠️  请参考 migration_manual.sql 手动执行,或联系 DBA 授权')
    print('=' * 60)


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        auto_migrate()
