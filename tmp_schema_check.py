from pkg import app, db
from pkg.models import User
from sqlalchemy import text

with app.app_context():
    print('=== Schema info ===')
    q = text("SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' AND COLUMN_NAME = 'password'")
    for row in db.session.execute(q):
        print(row)
    print('=== Admin password ===')
    u = User.query.filter_by(email='admin@kolocircle.com').first()
    if not u:
        print('Admin not found')
    else:
        print('repr:', repr(u.password))
        print('len:', len(u.password))
        print('raw:', u.password)
        print('chars:', [ord(c) for c in u.password])
        from werkzeug.security import check_password_hash
        print('check admin:', check_password_hash(u.password, 'admin'))
