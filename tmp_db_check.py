from pkg import app, db
from pkg.models import User
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import inspect

with app.app_context():
    u = User.query.filter_by(email='admin@kolocircle.com').first()
    print('Found:', u is not None)
    if u:
        print('id:', u.id)
        print('username:', u.username)
        print('is_admin:', u.is_admin)
        print('email:', u.email)
        print('password repr:', repr(u.password))
        print('password len:', len(u.password))
        print('password chars:', [ord(c) for c in u.password])
        print('stored matches admin:', check_password_hash(u.password, 'admin'))
        print('fresh hash matches admin:', check_password_hash(generate_password_hash('admin'), 'admin'))
    insp = inspect(db.engine)
    cols = insp.get_columns('users')
    for c in cols:
        if c['name'] == 'password':
            print('password column type:', c['type'])
            print('password column nullable:', c['nullable'])
            if hasattr(c['type'], 'length'):
                print('password column length:', c['type'].length)
