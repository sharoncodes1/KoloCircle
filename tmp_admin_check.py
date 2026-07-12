from pkg import app
from pkg.models import User
from werkzeug.security import check_password_hash, generate_password_hash

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
        print('stored matches admin:', check_password_hash(u.password, 'admin'))
        print('fresh hash check:', check_password_hash(generate_password_hash('admin'), 'admin'))
