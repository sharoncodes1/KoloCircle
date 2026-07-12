# seed.py
from pkg import app, db
from pkg.models import User, Group
from werkzeug.security import generate_password_hash

with app.app_context():
    # 1. Seed Admin user
    admin_email = "admin@kolocircle.com"
    admin = User.query.filter_by(email=admin_email).first()
    if not admin:
        hashed_password = generate_password_hash("admin")
        admin = User(
            fullname="System Administrator",
            username="admin",
            email=admin_email,
            password=hashed_password,
            is_admin=True,
            wallet_balance=1000000.0,
            total_saved=0.0
        )
        db.session.add(admin)
        print("Admin user seeded: admin@kolocircle.com / admin")
    else:
        invalid_hash = (not admin.password or '...' in admin.password or len(admin.password) < 50)
        if invalid_hash:
            admin.password = generate_password_hash("admin")
            admin.is_admin = True
            db.session.add(admin)
            print("Admin password was invalid and has been reset to the default password: admin")
        else:
            print("Admin user already exists.")
        
    db.session.commit()
    
    # 2. Seed default groups
    if Group.query.count() == 0:
        groups = [
            Group(
                group_name="Family Ajo Circle",
                description="Weekly savings circle for family members.",
                admin_id=admin.id,
                contribution_amount=10000.0,
                frequency="Weekly",
                maximum_members=10,
                current_members=0,
                cycle_day=1
            ),
            Group(
                group_name="Friends Savings Club",
                description="Monthly savings with close friends.",
                admin_id=admin.id,
                contribution_amount=5000.0,
                frequency="Monthly",
                maximum_members=6,
                current_members=0,
                cycle_day=1
            ),
            Group(
                group_name="Business Ajo Network",
                description="Professional networking and savings circle.",
                admin_id=admin.id,
                contribution_amount=20000.0,
                frequency="Monthly",
                maximum_members=10,
                current_members=0,
                cycle_day=1
            )
        ]
        for g in groups:
            db.session.add(g)
        print("Default savings groups seeded.")
    else:
        print("Savings groups already exist.")
        
    db.session.commit()
    print("Seeding complete!")
