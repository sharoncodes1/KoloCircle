# pkg/models.py
from datetime import datetime
from . import db

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    password = db.Column(db.String(200), nullable=False)
    wallet_balance = db.Column(db.Float, default=0.0)
    total_saved = db.Column(db.Float, default=0.0)
    profile_picture = db.Column(db.String(200), default='default.jpg')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    wallet_rel = db.relationship('Wallet', backref='owner', uselist=False, cascade='all, delete-orphan')
    savings = db.relationship('Savings', backref='saver', lazy='dynamic')
    group_memberships = db.relationship('GroupMember', backref='member', lazy='dynamic')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic')

    # Compatibility properties for existing templates and routes
    @property
    def name(self):
        return self.fullname

    @name.setter
    def name(self, value):
        self.fullname = value

    @property
    def first_name(self):
        parts = self.fullname.split()
        return parts[0] if parts else ''

    @property
    def last_name(self):
        parts = self.fullname.split()
        return parts[1] if len(parts) > 1 else ''

    @property
    def avatar(self):
        return self.profile_picture

    @avatar.setter
    def avatar(self, value):
        self.profile_picture = value

    @property
    def password_hash(self):
        return self.password

    @password_hash.setter
    def password_hash(self, value):
        self.password = value

    def get_avatar_initial(self):
        return self.fullname[0].upper() if self.fullname else 'U'


class Wallet(db.Model):
    __tablename__ = 'wallets'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    balance = db.Column(db.Float, default=0.0)
    total_funded = db.Column(db.Float, default=0.0)
    total_withdrawn = db.Column(db.Float, default=0.0)

    # Relationships
    transactions = db.relationship('WalletTransaction', backref='wallet', lazy='dynamic', cascade='all, delete-orphan')


class Savings(db.Model):
    __tablename__ = 'savings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False) # recurring contribution amount
    target_amount = db.Column(db.Float, nullable=False)
    frequency = db.Column(db.String(50), nullable=False)  # Daily, Weekly, Monthly, Custom
    next_payment_date = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='active')  # active, completed, failed, paused
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    saved_amount = db.Column(db.Float, default=0.0) # total amount saved so far

    # Compatibility properties/methods
    @property
    def name(self):
        return self.title

    @name.setter
    def name(self, value):
        self.title = value

    @property
    def current_amount(self):
        return self.saved_amount

    @current_amount.setter
    def current_amount(self, value):
        self.saved_amount = value

    def progress_percentage(self):
        if self.target_amount > 0:
            return min(100.0, ((self.saved_amount or 0.0) / self.target_amount) * 100.0)
        return 0.0

    def is_completed(self):
        return self.amount >= self.target_amount


class Group(db.Model):
    __tablename__ = 'groups'
    
    id = db.Column(db.Integer, primary_key=True)
    group_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    contribution_amount = db.Column(db.Float, nullable=False)
    frequency = db.Column(db.String(50), nullable=False)  # Weekly, Monthly, Custom
    maximum_members = db.Column(db.Integer, default=10)
    current_members = db.Column(db.Integer, default=0)
    cycle_day = db.Column(db.Integer, default=1)  # 1 for Monday, etc. or day of month
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    members = db.relationship('GroupMember', backref='group', lazy='dynamic', cascade='all, delete-orphan')
    contributions = db.relationship('Contribution', backref='group', lazy='dynamic', cascade='all, delete-orphan')

    # Compatibility properties
    @property
    def name(self):
        return self.group_name

    @name.setter
    def name(self, value):
        self.group_name = value


class GroupMember(db.Model):
    __tablename__ = 'groupmembers'
    
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='Pending')  # Pending, Accepted, Rejected
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)




class Contribution(db.Model):
    __tablename__ = 'contributions'
    
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Map member_id to user_id for ease of query
    amount = db.Column(db.Float, nullable=False)
    due_date = db.Column(db.DateTime, nullable=False)
    paid = db.Column(db.Boolean, default=False)
    payment_reference = db.Column(db.String(100), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Add relationship for convenience
    member = db.relationship('User', backref='group_contributions')


class WalletTransaction(db.Model):
    __tablename__ = 'wallettransactions'
    
    id = db.Column(db.Integer, primary_key=True)
    wallet_id = db.Column(db.Integer, db.ForeignKey('wallets.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    transaction_type = db.Column(db.String(50), nullable=False)  # fund, savings_deduction, group_contribution, withdrawal
    payment_reference = db.Column(db.String(100), unique=True)
    description = db.Column(db.String(200))
    status = db.Column(db.String(20), default='pending')  # pending, completed, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Compatibility properties for existing code that uses Transaction
    @property
    def type(self):
        return self.transaction_type

    @type.setter
    def type(self, value):
        self.transaction_type = value


class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Compatibility properties
    @property
    def details(self):
        return self.message

    @property
    def status(self):
        return 'read' if self.is_read else 'unread'


# ===== ALIAS CLASSES FOR COMPATIBILITY WITH IMPORTS =====
SavingPlan = Savings
Saving = Savings
Transaction = WalletTransaction
Activity = Notification

class GroupAdmin(db.Model):
    __tablename__ = 'groupadmin_dummy'
    id = db.Column(db.Integer, primary_key=True)

class Cycle(db.Model):
    __tablename__ = 'cycles_dummy'
    id = db.Column(db.Integer, primary_key=True)

class Member(db.Model):
    __tablename__ = 'members_dummy'
    id = db.Column(db.Integer, primary_key=True)


# ===== HELPER FUNCTIONS =====
def create_notification(user_id, title, message, type='info', icon='bi-info-circle'):
    """Helper to create a notification"""
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        is_read=False
    )
    db.session.add(notification)
    db.session.commit()
    return notification

def create_transaction(user_id, amount, type, description, payment_reference=None, status='pending'):
    """Helper to create a transaction"""
    # Ensure user has a wallet
    wallet = Wallet.query.filter_by(user_id=user_id).first()
    if not wallet:
        wallet = Wallet(user_id=user_id, balance=0.0, total_funded=0.0, total_withdrawn=0.0)
        db.session.add(wallet)
        db.session.commit()

    transaction = WalletTransaction(
        wallet_id=wallet.id,
        amount=amount,
        transaction_type=type,
        description=description,
        payment_reference=payment_reference,
        status=status,
        created_at=datetime.utcnow()
    )
    db.session.add(transaction)
    db.session.commit()
    return transaction