from pkg import app, db

with app.app_context():
    print("🔄 Creating tables if they don't exist...")
    db.create_all()
    print("✅ Tables ready!")

if __name__ == '__main__':
    app.run(debug=False)