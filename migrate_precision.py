"""
数据库迁移脚本: 将 data_points.value / data_points.last_value / data_history.value
从 FLOAT 改为 DECIMAL(20,4)，支持高精度数值存储。
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models.database import db


def migrate():
    app = create_app()
    with app.app_context():
        engine = db.engine
        dialect = engine.dialect.name

        if dialect == 'mysql':
            alters = [
                "ALTER TABLE data_points MODIFY COLUMN value DECIMAL(20,4) DEFAULT 0.0",
                "ALTER TABLE data_points MODIFY COLUMN last_value DECIMAL(20,4) DEFAULT 0.0",
                "ALTER TABLE data_history MODIFY COLUMN value DECIMAL(20,4) DEFAULT 0.0",
            ]
        elif dialect == 'sqlite':
            print("SQLite detected — recreating tables with updated schema...")
            print("NOTE: This is a destructive migration for SQLite. Existing data will be lost.")
            print("For production MySQL, run the ALTER TABLE statements manually.")
            return
        else:
            print(f"Unsupported dialect: {dialect}")
            return

        with engine.begin() as conn:
            for sql in alters:
                print(f"Executing: {sql}")
                conn.execute(db.text(sql))
                print("  OK")

        print("\nMigration complete. All value columns now use DECIMAL(20,4).")


if __name__ == '__main__':
    migrate()
