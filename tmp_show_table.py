from pkg import app, db
from pkg.models import User

with app.app_context():
    try:
        result = db.engine.execute('SHOW CREATE TABLE users')
        row = result.fetchone()
        print('SHOW CREATE TABLE users:')
        print(row[1] if row else 'No result')
    except Exception as e:
        print('SHOW CREATE TABLE failed:', e)
    u = User.query.filter_by(email='admin@kolocircle.com').first()
    if u:
        print('admin password repr:', repr(u.password))
        print('admin password length:', len(u.password))
        print('password eq actual stored?')
        print(db.session.execute("SELECT password, CHAR_LENGTH(password) FROM users WHERE email='admin@kolocircle.com'").fetchone())
