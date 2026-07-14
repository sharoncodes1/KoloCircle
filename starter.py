from pkg import app, db
from flask_migrate import upgrade

def run_migrations():
    with app.app_context():
        try:
            print("🔄 Running migrations...")
            upgrade()
            print("✅ Migrations completed!")
        except Exception as e:
            print(f"⚠️ Migration error: {e}")
            print("Creating tables instead...")
            db.create_all()

if __name__ == '__main__':
    run_migrations()
    app.run(debug=False)