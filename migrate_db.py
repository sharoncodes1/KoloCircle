# migrate_db.py
import os
from pkg import app, db
from sqlalchemy import inspect

def run_migrations():
    with app.app_context():
        print("🔄 Checking database...")
        
        # Check if tables exist
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        if tables:
            print(f"📊 Existing tables: {tables}")
            print("✅ Database already has tables. Skipping...")
        else:
            print("📊 No tables found. Creating...")
            db.create_all()
            print("✅ Tables created successfully!")
        
        # Check if admin user exists
        from pkg.models import User
        if User.query.count() == 0:
            print("👤 Creating admin user...")
            from werkzeug.security import generate_password_hash
            admin = User(
                fullname="System Administrator",
                username="admin",
                email="admin@kolocircle.com",
                password=generate_password_hash("admin"),
                is_admin=True,
                wallet_balance=1000000.0,
                total_saved=0.0
            )
            db.session.add(admin)
            db.session.commit()
            print("✅ Admin user created!")

if __name__ == "__main__":
    run_migrations()