# pkg/admin_routes.py
from flask import Blueprint, render_template, request, redirect, session, url_for, flash, jsonify
from werkzeug.security import check_password_hash
from functools import wraps
import datetime
from .models import User, Group, GroupMember, Contribution, Wallet, WalletTransaction, Notification, create_notification
from . import db

# Create blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Decorator to ensure admin is logged in
def admin_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('adminlogin') is None:
            flash('You must be logged in to access the admin dashboard.', category='errormsg')
            return redirect(url_for('admin.admin_login'))
        
        # Verify user is actually admin in DB
        admin_user = User.query.get(session.get('adminlogin'))
        if not admin_user or not admin_user.is_admin:
            session.pop('adminlogin', None)
            flash('Permission denied.', category='errormsg')
            return redirect(url_for('admin.admin_login'))
            
        return f(*args, **kwargs)
    return decorated_function

# @admin_bp.route('/login/', methods=['GET', 'POST'])
# def admin_login():
#     """Admin login page"""
#     if request.method == 'POST':
#         email = request.form.get('email')
#         password = request.form.get('password')
        
#         if not email or not password:
#             flash('All fields are required.', category='errormsg')
#             return redirect(url_for('admin.admin_login'))
            
#         # Query admin from User table where is_admin=True
#         admin = User.query.filter((User.email == email) | (User.username == email)).first()
        
#         if not admin or not admin.is_admin or not check_password_hash(admin.password, password):
#             flash('Invalid admin login details.', category='errormsg')
#             return redirect(url_for('admin.admin_login'))
#         else:
#             session['adminlogin'] = admin.id
#             session['admin_name'] = admin.fullname
#             session['useronline'] = admin.id
#             session['is_admin'] = True
#             flash('You are now logged in as an admin.', category='feedback')
#             return redirect(url_for('admin.admin_dashboard'))
    
#     return render_template('admin/login.html')

@admin_bp.route('/login/', methods=['GET', 'POST'])
def admin_login():
    """Admin login page"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # ===== DEBUG =====
        print("=" * 60)
        print("🔍 ADMIN LOGIN ATTEMPT")
        print(f"   Email input: '{email}'")
        print(f"   Password input: '{password}'")
        # ===== END DEBUG =====
        
        if not email or not password:
            flash('All fields are required.', category='errormsg')
            return redirect(url_for('admin.admin_login'))
        
        # Query admin
        admin = User.query.filter((User.email == email) | (User.username == email)).first()
        
        # ===== DEBUG =====
        print(f"   Admin found in DB: {admin is not None}")
        if admin:
            print(f"   Admin ID: {admin.id}")
            print(f"   Admin fullname: {admin.fullname}")
            print(f"   Admin email: {admin.email}")
            print(f"   is_admin flag: {admin.is_admin}")
            print(f"   Password hash: {admin.password[:20]}...")
            print(f"   Password match: {check_password_hash(admin.password, password)}")
        print("=" * 60)
        # ===== END DEBUG =====
        
        if not admin or not admin.is_admin or not check_password_hash(admin.password, password):
            flash('Invalid admin login details.', category='errormsg')
            return redirect(url_for('admin.admin_login'))
        else:
            session['adminlogin'] = admin.id
            session['admin_name'] = admin.fullname
            session['useronline'] = admin.id
            session['is_admin'] = True
            flash('You are now logged in as an admin.', category='feedback')
            return redirect(url_for('admin.admin_dashboard'))
    
    return render_template('admin/login.html')

@admin_bp.route('/dashboard/')
@admin_login_required
def admin_dashboard():
    """Admin dashboard with statistics"""
    users = User.query.all()
    user_count = len(users)
    
    # Calculate statistics
    total_savings = sum(u.total_saved or 0.0 for u in users)
    total_wallets = sum(u.wallet_balance or 0.0 for u in users)
    groups = Group.query.all()
    group_count = len(groups)
    
    admin = User.query.get(session.get('adminlogin'))
    
    return render_template('admin/dashboard.html', 
                           users=users, 
                           user_count=user_count,
                           total_savings=total_savings,
                           total_wallets=total_wallets,
                           group_count=group_count,
                           admin=admin)

@admin_bp.route('/users/')
@admin_login_required
def admin_users():
    """View all users"""
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/<int:user_id>/')
@admin_login_required
def admin_user_detail(user_id):
    """View specific user details"""
    user = User.query.get_or_404(user_id)
    wallet = Wallet.query.filter_by(user_id=user.id).first()
    transactions = WalletTransaction.query.filter_by(wallet_id=wallet.id).all() if wallet else []
    
    return render_template('admin/user_detail.html', user=user, wallet=wallet, transactions=transactions)

@admin_bp.route('/users/<int:user_id>/delete/', methods=['POST'])
@admin_login_required
def admin_delete_user(user_id):
    """Delete a user"""
    user = User.query.get_or_404(user_id)
    
    # Prevent admin from deleting themselves
    if user.id == session.get('adminlogin'):
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin.admin_users'))
    
    db.session.delete(user)
    db.session.commit()
    flash(f'User {user.name} has been deleted.', 'success')
    return redirect(url_for('admin.admin_users'))

# ===== ADMIN GROUPS LOGIC =====
@admin_bp.route('/groups/')
@admin_login_required
def admin_groups():
    """View all groups"""
    groups = Group.query.all()
    return render_template('admin/groups.html', groups=groups)

@admin_bp.route('/groups/create/', methods=['GET', 'POST'])
@admin_login_required
def admin_create_group():
    """Create a new savings group"""
    if request.method == 'POST':
        name = request.form.get('group_name')
        description = request.form.get('description')
        amount = request.form.get('contribution_amount', type=float)
        frequency = request.form.get('frequency', 'Weekly')
        max_members = request.form.get('maximum_members', type=int, default=10)
        cycle_day = request.form.get('cycle_day', type=int, default=1)
        
        if not name or not amount:
            flash('Group name and contribution amount are required.', 'danger')
            return redirect(url_for('admin.admin_create_group'))
            
        group = Group(
            group_name=name,
            description=description,
            admin_id=session.get('adminlogin'),
            contribution_amount=amount,
            frequency=frequency,
            maximum_members=max_members,
            current_members=0,
            cycle_day=cycle_day
        )
        db.session.add(group)
        db.session.commit()
        
        flash(f"Group '{name}' created successfully!", 'success')
        return redirect(url_for('admin.admin_groups'))
        
    return render_template('admin/groups.html', action='create')

@admin_bp.route('/groups/<int:group_id>/edit/', methods=['GET', 'POST'])
@admin_login_required
def admin_edit_group(group_id):
    """Edit a savings group"""
    group = Group.query.get_or_404(group_id)
    if request.method == 'POST':
        group.group_name = request.form.get('group_name')
        group.description = request.form.get('description')
        group.contribution_amount = request.form.get('contribution_amount', type=float)
        group.frequency = request.form.get('frequency')
        group.maximum_members = request.form.get('maximum_members', type=int)
        group.cycle_day = request.form.get('cycle_day', type=int)
        
        db.session.commit()
        flash('Group details updated successfully.', 'success')
        return redirect(url_for('admin.admin_groups'))
        
    return render_template('admin/groups.html', action='edit', group=group)

@admin_bp.route('/groups/<int:group_id>/delete/', methods=['POST'])
@admin_login_required
def admin_delete_group(group_id):
    """Delete a group"""
    group = Group.query.get_or_404(group_id)
    db.session.delete(group)
    db.session.commit()
    flash(f'Group {group.name} has been deleted.', 'success')
    return redirect(url_for('admin.admin_groups'))

@admin_bp.route('/requests/')
@admin_login_required
def admin_requests():
    """View and manage all pending join requests across all groups"""
    pending_requests = GroupMember.query.filter_by(status='Pending').all()
    return render_template('admin/requests.html', pending_requests=pending_requests)

@admin_bp.route('/requests/<int:member_id>/accept/', methods=['POST'])
@admin_login_required
def accept_request(member_id):
    """Accept user join request"""
    gm = GroupMember.query.get_or_404(member_id)
    group = Group.query.get(gm.group_id)
    
    if group.maximum_members and group.current_members >= group.maximum_members:
        return jsonify({'success': False, 'message': 'Group is already full.'})
        
    gm.status = 'Accepted'
    group.current_members = (group.current_members or 0) + 1
    
    # Schedule their first contribution
    due_date = datetime.datetime.now()
    if group.frequency.lower() == 'weekly':
        due_date += datetime.timedelta(weeks=1)
    elif group.frequency.lower() == 'monthly':
        due_date += datetime.timedelta(days=30)
    else:
        due_date += datetime.timedelta(days=7)
        
    contrib = Contribution(
        group_id=group.id,
        member_id=gm.user_id,
        amount=group.contribution_amount,
        due_date=due_date,
        paid=False
    )
    db.session.add(contrib)
    db.session.commit()
    
    # Send user notification
    create_notification(
        user_id=gm.user_id,
        title="🎉 Group Join Request Approved",
        message=f"Your request to join group '{group.group_name}' has been approved by the administrator."
    )
    
    return jsonify({'success': True, 'message': 'Join request approved.'})

@admin_bp.route('/requests/<int:member_id>/reject/', methods=['POST'])
@admin_login_required
def reject_request(member_id):
    """Reject user join request"""
    gm = GroupMember.query.get_or_404(member_id)
    group = Group.query.get(gm.group_id)
    
    gm.status = 'Rejected'
    db.session.commit()
    
    # Send user notification
    create_notification(
        user_id=gm.user_id,
        title="❌ Group Join Request Rejected",
        message=f"Your request to join group '{group.group_name}' has been rejected by the administrator."
    )
    
    return jsonify({'success': True, 'message': 'Join request rejected.'})

@admin_bp.route('/logout/')
def admin_logout():
    """Admin logout"""
    if session.get('adminlogin'):
        session.pop('adminlogin', None)
        session.pop('admin_name', None)
        session.pop('is_admin', None)
        session.clear()
        flash('You have been logged out.', 'info')
    return redirect(url_for('admin.admin_login'))
