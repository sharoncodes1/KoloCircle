import os, secrets, datetime, json, requests
from flask import render_template, url_for, request, redirect, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from pkg import app, csrf, db
from pkg.models import User, Wallet, Savings, SavingPlan, Saving, Transaction, Group, GroupMember, Contribution, WalletTransaction, Notification, create_notification, create_transaction
from pkg.forms import RegisterForm, LoginForm
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@app.after_request
def after_request(resp):
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return resp

# ===== CONTEXT PROCESSOR - Makes paystack key available globally =====
@app.context_processor
def inject_paystack_key():
    return {
        'paystack_public_key': os.getenv('PAYSTACK_PUBLIC_KEY', '')
    }

# ===== HOMEPAGE =====
@app.route("/") 
def home():
    return render_template("index.html")

# ===== AUTH ROUTES =====
@app.route('/login/', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if request.method == 'GET':
        return render_template('user/login.html', form=form)
    else:
        print("=" * 50)
        print("LOGIN ATTEMPT")
        print(f"Email: {form.email.data}")
        print(f"Password: {form.password.data}")
        
        if form.validate_on_submit():
            print("Form validated")
            email = form.email.data
            password = form.password.data
            
            deets = User.query.filter((User.email == email) | (User.username == email)).first()
            print(f"User found: {deets is not None}")
            
            if deets:
                stored_password = deets.password
                rsp = check_password_hash(stored_password, password)
                print(f"Password correct: {rsp}")
                
                if rsp:
                    session['useronline'] = deets.id
                    session['is_admin'] = deets.is_admin
                    print(f"Login successful! User ID: {deets.id}, Admin: {deets.is_admin}")
                    print(f"Redirecting to: {url_for('dashboard')}")
                    return redirect(url_for('dashboard'))
                else:
                    print("Wrong password")
                    flash('Invalid Password', category='')
                    return redirect(url_for('login'))
            else:
                print("User not found")
                flash('Invalid email or username', category='')
                return redirect(url_for('login'))
        else:
            print("Form validation failed")
            print(f"Form errors: {form.errors}")
            return render_template('user/login.html', form=form)
        

@app.route('/signup/', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('user/signup.html')
    
    # Get form data
    fname = request.form.get('fname', '').strip()
    lname = request.form.get('lname', '').strip()
    email = request.form.get('email', '').strip()
    phone = request.form.get('phone', '').strip()
    password = request.form.get('password', '')
    confirm_password = request.form.get('confirm-password', '')
    
    # Validation
    if not fname or not lname or not email or not password:
        flash('All fields are compulsory!', 'errormsg')  # ✅ Added category
        return redirect(url_for('signup'))
    
    if password != confirm_password:
        flash('The two passwords must match!', 'errormsg')  # ✅ Added category
        return redirect(url_for('signup'))
    
    if len(password) < 8:
        flash('Password must be at least 8 characters!', 'errormsg')  # ✅ Added category
        return redirect(url_for('signup'))
    
    # Check if user already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        flash('Email already registered. Please login.', 'errormsg')  # ✅ Added category
        return redirect(url_for('signup'))
    
    # ===== CREATE USER =====
    try:
        hashed_password = generate_password_hash(password)
        full_name = f"{fname} {lname}"
        username = email.split('@')[0]
        
        # Ensure username uniqueness
        existing_username = User.query.filter_by(username=username).first()
        if existing_username:
            username = f"{username}_{secrets.token_hex(3)}"
        
        user = User(
            fullname=full_name,
            username=username,
            email=email,
            phone=phone if phone else None,
            password=hashed_password,
            wallet_balance=0.0,
            total_saved=0.0,
            is_admin=False,
            is_active=True
        )
        
        db.session.add(user)
        db.session.commit()
        
        # Create user wallet
        wallet = Wallet(user_id=user.id, balance=0.0, total_funded=0.0, total_withdrawn=0.0)
        db.session.add(wallet)
        db.session.commit()
        
        print(f"User and Wallet created: {email}")
        flash('✅ Account created successfully! Please login.', 'success')  # ✅ Added category
        return redirect(url_for('login'))
    
    except Exception as e:
        db.session.rollback()
        print(f"Error creating user: {e}")
        flash('An error occurred. Please try again.', 'errormsg')  # ✅ Added category
        return redirect(url_for('signup'))
@app.get('/logout/')
def logout():
    if session.get('useronline'):
        session.pop('useronline', None)
        session.clear()
    return redirect('/')

# ===== USER ROUTES =====
@app.route('/dashboard/')
def dashboard():
    if 'useronline' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('login'))
    
    user = User.query.get(session['useronline'])
    wallet = Wallet.query.filter_by(user_id=user.id).first()
    if not wallet:
        wallet = Wallet(user_id=user.id, balance=0.0, total_funded=0.0, total_withdrawn=0.0)
        db.session.add(wallet)
        db.session.commit()
        
    group_contribs_sum = sum(c.amount for c in Contribution.query.filter_by(member_id=user.id, paid=True).all())
    
    recent_transactions = WalletTransaction.query.filter_by(wallet_id=wallet.id)\
        .order_by(WalletTransaction.created_at.desc()).limit(5).all()
        
    next_saving = Savings.query.filter_by(user_id=user.id, status='active')\
        .order_by(Savings.next_payment_date.asc()).first()
    next_contrib = Contribution.query.filter_by(member_id=user.id, paid=False)\
        .order_by(Contribution.due_date.asc()).first()
        
    upcoming_payment = None
    if next_saving and next_contrib:
        if next_saving.next_payment_date < next_contrib.due_date:
            upcoming_payment = f"₦{next_saving.amount:,.2f} due on {next_saving.next_payment_date.strftime('%b %d')}"
        else:
            upcoming_payment = f"₦{next_contrib.amount:,.2f} due on {next_contrib.due_date.strftime('%b %d')}"
    elif next_saving:
        upcoming_payment = f"₦{next_saving.amount:,.2f} due on {next_saving.next_payment_date.strftime('%b %d')}"
    elif next_contrib:
        upcoming_payment = f"₦{next_contrib.amount:,.2f} due on {next_contrib.due_date.strftime('%b %d')}"
    else:
        upcoming_payment = "No upcoming payments"
        
    return render_template('user/dashboard.html', 
                           user=user, 
                           wallet=wallet, 
                           group_contribs_sum=group_contribs_sum, 
                           recent_transactions=recent_transactions,
                           upcoming_payment=upcoming_payment)

@app.route('/profile/')
def profile():
    if 'useronline' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('login'))
    user = User.query.get(session['useronline'])
    return render_template('user/profile.html', user=user)

@app.route("/savings/")
def savings():
    if 'useronline' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('login'))
    
    user = User.query.get(session['useronline'])
    savings_plans = SavingPlan.query.filter_by(user_id=user.id).all()

    total_savings_balance = sum((plan.saved_amount or 0.0) for plan in savings_plans)
    total_saved = max(float(user.total_saved or 0.0), total_savings_balance)
    active_plans = sum(1 for plan in savings_plans if plan.status == 'active')

    wallet = Wallet.query.filter_by(user_id=user.id).first()
    monthly_savings = 0.0
    interest_earned = 0.0
    transactions = [] 


    if wallet:
        month_start = datetime.datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_savings = sum(
            (tx.amount or 0.0) for tx in WalletTransaction.query.filter(
                WalletTransaction.wallet_id == wallet.id,
                WalletTransaction.transaction_type == 'savings_deposit',
                WalletTransaction.status == 'completed',
                WalletTransaction.created_at >= month_start
            ).all()
        )
        interest_earned = sum(
            (tx.amount or 0.0) for tx in WalletTransaction.query.filter(
                WalletTransaction.wallet_id == wallet.id,
                WalletTransaction.status == 'completed',
                WalletTransaction.description.ilike('%interest%')
            ).all()
        )

        transactions = WalletTransaction.query.filter_by(wallet_id=wallet.id)\
            .order_by(WalletTransaction.created_at.desc())\
            .limit(5)\
            .all()


    balance_change_text = f"+₦{monthly_savings:,.2f} this month" if monthly_savings else "₦0.00 this month"

    next_plan = Savings.query.filter_by(user_id=user.id, status='active')\
        .filter(Savings.next_payment_date.isnot(None))\
        .order_by(Savings.next_payment_date.asc()).first()

    if next_plan and next_plan.next_payment_date:
        delta_days = (next_plan.next_payment_date.date() - datetime.datetime.now().date()).days
        if delta_days > 0:
            next_contribution_hint = f"Due in {delta_days} days"
        elif delta_days == 0:
            next_contribution_hint = "Due today"
        else:
            next_contribution_hint = f"Overdue by {-delta_days} days"
        next_contribution_amount = f"₦{next_plan.amount:,.2f}"
        next_contribution_class = 'warning'
        next_contribution_icon = 'bi-clock'
    else:
        next_contribution_amount = "No upcoming contributions"
        next_contribution_hint = "Create a new plan"
        next_contribution_class = 'neutral'
        next_contribution_icon = 'bi-info-circle'

    interest_earned = float(interest_earned or 0.0)
    if interest_earned and total_saved:
        interest_change_text = f"+{(interest_earned / total_saved * 100):.1f}%"
        interest_change_class = 'positive'
        interest_change_icon = 'bi-arrow-up-short'
    else:
        interest_change_text = 'No interest yet'
        interest_change_class = 'neutral'
        interest_change_icon = 'bi-dash-circle'

    PAYSTACK_PUBLIC_KEY = os.getenv('PAYSTACK_PUBLIC_KEY')

    return render_template("user/savings.html", 
                         user=user, 
                         savings_plans=savings_plans,
                         transactions=transactions,  # ✅ Now included
                         paystack_public_key=PAYSTACK_PUBLIC_KEY,
                         total_savings_balance=total_savings_balance,
                         total_saved=total_saved,
                         active_plans=active_plans,
                         balance_change_text=balance_change_text,
                         next_contribution_amount=next_contribution_amount,
                         next_contribution_hint=next_contribution_hint,
                         next_contribution_class=next_contribution_class,
                         next_contribution_icon=next_contribution_icon,
                         interest_earned=interest_earned,
                         interest_change_text=interest_change_text,
                         interest_change_class=interest_change_class,
                         interest_change_icon=interest_change_icon)




# ===== SAVINGS - ADD MONEY WITH PAYSTACK =====
@app.route('/savings/add/<int:plan_id>/', methods=['GET', 'POST'])
def add_money(plan_id):
    """Add money to a savings plan using Paystack"""
    if 'useronline' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('login'))
    
    user = User.query.get(session['useronline'])
    saving_plan = SavingPlan.query.get_or_404(plan_id)
    
    # Check if plan belongs to user
    if saving_plan.user_id != user.id:
        flash('This savings plan does not belong to you.', 'error')
        return redirect(url_for('savings'))
    
    if request.method == 'GET':
        return render_template('user/add_money.html', user=user, plan=saving_plan)
    
    # POST - Initialize payment
    if request.method == 'POST':
        amount = request.form.get('amount', type=float)
        
        if not amount or amount < 100:
            flash('Please enter a valid amount (minimum ₦100).', 'error')
            return redirect(url_for('add_money', plan_id=plan_id))
        
        # Generate unique reference
        payref = f"SAV-{plan_id}-{secrets.token_hex(8)}-{int(datetime.datetime.now().timestamp())}"
        
        # Save to session
        session['payref'] = payref
        session['pay_plan_id'] = plan_id
        session['pay_amount'] = amount
        
        # Get or create wallet
        wallet = Wallet.query.filter_by(user_id=user.id).first()
        if not wallet:
            wallet = Wallet(user_id=user.id, balance=0.0, total_funded=0.0, total_withdrawn=0.0)
            db.session.add(wallet)
            db.session.commit()

        # Save transaction record
        transaction = Transaction(
            wallet_id=wallet.id,
            amount=amount,
            type='savings_deposit',
            description=f'Deposit to {saving_plan.name}',
            status='pending',
            payment_reference=payref,
            created_at=datetime.datetime.now()
        )
        db.session.add(transaction)
        db.session.commit()
        
        return redirect(url_for('paystack_init_savings'))

@app.route('/paystack-init-savings/', methods=['GET'])
def paystack_init_savings():
    """Initialize Paystack payment for savings"""
    if 'useronline' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('login'))
    
    # Get Paystack secret key from environment
    PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY')
    if not PAYSTACK_SECRET_KEY:
        flash('Payment system is not configured. Please contact support.', 'error')
        return redirect(url_for('savings'))
    
    try:
        user = User.query.get(session['useronline'])
        ref = session.get('payref')
        plan_id = session.get('pay_plan_id')
        amount = session.get('pay_amount')
        
        if not all([ref, plan_id, amount]):
            flash('Payment details not found. Please try again.', 'error')
            return redirect(url_for('savings'))
        
        # Get transaction record
        transaction = Transaction.query.filter_by(payment_reference=ref).first()
        if not transaction:
            flash('Transaction record not found.', 'error')
            return redirect(url_for('savings'))
        
        amount_in_kobo = int(amount * 100)
        callback_url = url_for('paystack_landing_savings', _external=True)
        
        # Prepare Paystack request
        url = "https://api.paystack.co/transaction/initialize"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"
        }
        data = {
            'amount': amount_in_kobo,
            'email': user.email,
            'reference': ref,
            'callback_url': callback_url,
            'metadata': {
                'user_id': user.id,
                'plan_id': plan_id,
                'transaction_id': transaction.id,
                'type': 'savings_deposit'
            }
        }
        
        print(f"[Paystack] Sending with key: {PAYSTACK_SECRET_KEY[:10]}...")  # Debug
        
        response = requests.post(url, headers=headers, data=json.dumps(data))
        rsp = response.json()
        
        print(f"[Paystack] Response: {rsp}")  # Debug
        
        if rsp.get('status') and rsp.get('data'):
            auth_url = rsp['data']['authorization_url']
            return redirect(auth_url)
        else:
            error_msg = rsp.get('message', 'Payment initialization failed')
            flash(f'Payment error: {error_msg}', 'error')
            return redirect(url_for('savings'))
            
    except Exception as e:
        print(f"[Paystack] Error: {e}")  # Debug
        flash(f'An error occurred: {str(e)}', 'error')
        return redirect(url_for('savings'))

@app.route('/paystack-landing-savings/')
def paystack_landing_savings():
    """Handle Paystack callback after payment"""
    if 'useronline' not in session:
        flash('Please log in again.', 'error')
        return redirect(url_for('login'))
    
    user = User.query.get(session['useronline'])
    ref = session.get('payref')
    
    if not ref:
        flash('Payment reference not found.', 'error')
        return redirect(url_for('savings'))
    
    PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY')
    
    try:
        # Verify payment
        url = f'https://api.paystack.co/transaction/verify/{ref}'
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"
        }
        
        response = requests.get(url, headers=headers)
        rsp = response.json()
        
        if rsp.get('status') and rsp.get('data'):
            payment_data = rsp['data']
            
            if payment_data['status'] == 'success':
                # Get transaction
                transaction = Transaction.query.filter_by(payment_reference=ref).first()
                if transaction:
                    # Update transaction status
                    transaction.status = 'completed'
                    transaction.payment_date = datetime.datetime.now()
                    db.session.commit()
                    
                    # Get savings plan
                    plan_id = session.get('pay_plan_id')
                    amount = session.get('pay_amount')
                    
                    if plan_id and amount:
                        saving_plan = SavingPlan.query.get(plan_id)
                        if saving_plan:
                            # Update savings plan balance
                            saving_plan.current_amount = (saving_plan.current_amount or 0) + amount
                            db.session.commit()
                            
                            # Create savings record
                            saving = Saving(
                                user_id=user.id,
                                plan_id=plan_id,
                                amount=amount,
                                savings_type='deposit',
                                status='completed',
                                created_at=datetime.datetime.now()
                            )
                            db.session.add(saving)
                            db.session.commit()
                    
                    # Clear session
                    session.pop('payref', None)
                    session.pop('pay_plan_id', None)
                    session.pop('pay_amount', None)
                    
                    flash(f'✅ Payment of ₦{transaction.amount:,.2f} successful! Your savings have been updated.', 'success')
                    return redirect(url_for('savings'))
                else:
                    flash('Transaction record not found.', 'error')
            else:
                flash(f'Payment status: {payment_data.get("status", "Unknown")}. Please contact support.', 'error')
        else:
            flash('Payment verification failed.', 'error')
            
        return redirect(url_for('savings'))
        
    except Exception as e:
        flash(f'Error verifying payment: {str(e)}', 'error')
        return redirect(url_for('savings'))

# ===== VERIFY PAYMENT (AJAX) =====
@app.route('/verify-payment/', methods=['POST'])
@csrf.exempt
def verify_payment():
    data = request.get_json()
    reference = data.get('reference')
    plan_id_or_title = data.get('plan')
    amount = float(data.get('amount') or 0.0)
    
    PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY')
    if not PAYSTACK_SECRET_KEY:
        return jsonify({'success': False, 'message': 'Payment system not configured'})
        
    try:
        # Verify with Paystack API
        url = f'https://api.paystack.co/transaction/verify/{reference}'
        headers = {
            'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}',
            'Content-Type': 'application/json'
        }
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return jsonify({'success': False, 'message': 'Failed to reach verification server'})
            
        result = response.json()
        if result.get('data', {}).get('status') == 'success':
            existing_tx = WalletTransaction.query.filter_by(payment_reference=reference).first()
            if existing_tx and existing_tx.status == 'completed':
                return jsonify({'success': True, 'message': 'Payment already verified'})
                
            user_id = session.get('useronline')
            if not user_id:
                meta = result['data'].get('metadata', {})
                user_id = meta.get('user_id')
                
            if not user_id:
                return jsonify({'success': False, 'message': 'User session not found'})
                
            user = User.query.get(user_id)
            wallet = Wallet.query.filter_by(user_id=user.id).first()
            if not wallet:
                wallet = Wallet(user_id=user.id, balance=0.0, total_funded=0.0, total_withdrawn=0.0)
                db.session.add(wallet)
                db.session.commit()
                
            # Find the savings plan
            saving_plan = None
            if plan_id_or_title:
                try:
                    saving_plan = Savings.query.get(int(plan_id_or_title))
                except:
                    pass
                if not saving_plan:
                    saving_plan = Savings.query.filter_by(user_id=user.id, title=plan_id_or_title).first()
                    
            if not saving_plan:
                return jsonify({'success': False, 'message': 'Savings plan not found'})
                
            # Update savings plan progress
            saving_plan.saved_amount = (saving_plan.saved_amount or 0.0) + amount
            user.total_saved = (user.total_saved or 0.0) + amount
            
            if saving_plan.saved_amount >= saving_plan.target_amount:
                saving_plan.status = 'completed'
                create_notification(
                    user_id=user.id,
                    title="🎉 Savings Goal Reached!",
                    message=f"Congratulations! You have reached your savings target of ₦{saving_plan.target_amount:,.2f} for '{saving_plan.title}'."
                )
                
            if not existing_tx:
                existing_tx = WalletTransaction(
                    wallet_id=wallet.id,
                    amount=amount,
                    transaction_type='savings_deposit',
                    payment_reference=reference,
                    description=f"Deposit to savings plan: {saving_plan.title}",
                    status='completed'
                )
                db.session.add(existing_tx)
            else:
                existing_tx.status = 'completed'
                existing_tx.amount = amount
                existing_tx.description = f"Deposit to savings plan: {saving_plan.title}"
                
            db.session.commit()
            
            create_notification(
                user_id=user.id,
                title="💰 Savings Plan Funded",
                message=f"₦{amount:,.2f} has been added to '{saving_plan.title}' savings plan."
            )
            
            return jsonify({'success': True, 'message': 'Payment verified and savings plan credited.'})
        else:
            return jsonify({'success': False, 'message': 'Payment verification failed'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


# ===== SAVINGS PLAN CRUD =====
@app.route('/savings/create/', methods=['POST'])
def create_savings_plan():
    if 'useronline' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('login'))
    
    user = User.query.get(session['useronline'])
    name = request.form.get('name')
    target_amount = request.form.get('target_amount', type=float)
    amount = request.form.get('amount', type=float) # contribution amount per cycle
    frequency = request.form.get('frequency', 'Weekly')
    
    if not all([name, target_amount, amount]):
        flash('Please fill in all required fields.', 'error')
        return redirect(url_for('savings'))
        
    try:
        next_date = datetime.datetime.now()
        if frequency.lower() == 'daily':
            next_date += datetime.timedelta(days=1)
        elif frequency.lower() == 'weekly':
            next_date += datetime.timedelta(weeks=1)
        elif frequency.lower() == 'monthly':
            next_date += datetime.timedelta(days=30)
            
        plan = Savings(
            user_id=user.id,
            title=name,
            amount=amount,
            target_amount=target_amount,
            frequency=frequency,
            next_payment_date=next_date,
            status='active',
            saved_amount=0.0,
            created_at=datetime.datetime.now()
        )
        db.session.add(plan)
        db.session.commit()
        
        flash(f'✅ Savings plan "{name}" created successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating plan: {str(e)}', 'error')
        
    return redirect(url_for('savings'))


# ===== USER WALLET ROUTES =====
@app.route('/wallet/')
def wallet():
    if 'useronline' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('login'))
    user = User.query.get(session['useronline'])
    user_wallet = Wallet.query.filter_by(user_id=user.id).first()
    if not user_wallet:
        user_wallet = Wallet(user_id=user.id, balance=0.0, total_funded=0.0, total_withdrawn=0.0)
        db.session.add(user_wallet)
        db.session.commit()
        
    transactions = WalletTransaction.query.filter_by(wallet_id=user_wallet.id)\
        .order_by(WalletTransaction.created_at.desc()).all()
        
    return render_template('user/wallet.html', user=user, wallet=user_wallet, transactions=transactions)


@app.route('/wallet/fund/initiate/', methods=['POST'])
def initiate_wallet_funding():
    if 'useronline' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
    data = request.get_json() or {}
    amount = data.get('amount')
    if not amount or float(amount) < 100:
        return jsonify({'success': False, 'message': 'Minimum funding amount is ₦100'}), 400
        
    user = User.query.get(session['useronline'])
    user_wallet = Wallet.query.filter_by(user_id=user.id).first()
    
    payref = f"WAL-{user.id}-{secrets.token_hex(6)}-{int(datetime.datetime.now().timestamp())}"
    
    transaction = WalletTransaction(
        wallet_id=user_wallet.id,
        amount=float(amount),
        transaction_type='fund',
        payment_reference=payref,
        description="Wallet funding via Paystack",
        status='pending'
    )
    db.session.add(transaction)
    db.session.commit()
    
    PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY')
    if not PAYSTACK_SECRET_KEY:
        return jsonify({'success': False, 'message': 'Paystack is not configured on the server'}), 500
        
    url = "https://api.paystack.co/transaction/initialize"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"
    }
    data_payload = {
        "amount": int(float(amount) * 100),
        "email": user.email,
        "reference": payref,
        "callback_url": url_for('paystack_landing_wallet', _external=True)
    }
    
    try:
        response = requests.post(url, headers=headers, json=data_payload)
        res_data = response.json()
        if res_data.get('status'):
            return jsonify({
                'success': True,
                'authorization_url': res_data['data']['authorization_url'],
                'reference': payref
            })
        else:
            return jsonify({'success': False, 'message': res_data.get('message', 'Failed to initialize transaction')})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


def verify_and_credit_wallet(reference):
    PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY')
    if not PAYSTACK_SECRET_KEY:
        return False, 'Paystack not configured'
        
    transaction = WalletTransaction.query.filter_by(payment_reference=reference).first()
    if not transaction:
        return False, 'Transaction record not found'
        
    if transaction.status == 'completed':
        return True, 'Transaction already verified.'
        
    url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"
    }
    
    try:
        res = requests.get(url, headers=headers)
        res_data = res.json()
        if res_data.get('status') and res_data['data']['status'] == 'success':
            wallet = Wallet.query.get(transaction.wallet_id)
            user = User.query.get(wallet.user_id)
            
            if transaction.status != 'completed':
                transaction.status = 'completed'
                transaction.created_at = datetime.datetime.now()
                
                amount = float(res_data['data']['amount']) / 100.0
                wallet.balance = (wallet.balance or 0.0) + amount
                wallet.total_funded = (wallet.total_funded or 0.0) + amount
                user.wallet_balance = wallet.balance
                
                db.session.commit()
                
                create_notification(
                    user_id=user.id,
                    title="💳 Wallet Funded Successfully",
                    message=f"Your wallet has been funded with ₦{amount:,.2f}. New Balance: ₦{wallet.balance:,.2f}"
                )
                return True, f"₦{amount:,.2f} added to your wallet."
            return True, 'Already processed.'
        else:
            transaction.status = 'failed'
            db.session.commit()
            return False, 'Payment verification failed'
    except Exception as e:
        return False, str(e)


@app.route('/wallet/fund/verify/', methods=['POST'])
def verify_wallet_funding():
    data = request.get_json() or {}
    reference = data.get('reference')
    if not reference:
        return jsonify({'success': False, 'message': 'Reference is required'}), 400
        
    success, message = verify_and_credit_wallet(reference)
    return jsonify({'success': success, 'message': message})


@app.route('/wallet/fund/callback/')
def paystack_landing_wallet():
    if 'useronline' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('login'))
        
    reference = request.args.get('reference') or request.args.get('trxref')
    if not reference:
        flash('No transaction reference found.', 'error')
        return redirect(url_for('wallet'))
        
    success, message = verify_and_credit_wallet(reference)
    if success:
        flash(f'✅ Wallet funded successfully! {message}', 'success')
    else:
        flash(f'⚠️ Payment verification status: {message}', 'warning')
        
    return redirect(url_for('wallet'))


@app.route('/paystack/webhook/', methods=['POST'])
@csrf.exempt
def paystack_webhook():
    payload = request.get_json() or {}
    event = payload.get('event')
    if event == 'charge.success':
        data = payload.get('data', {})
        reference = data.get('reference')
        if reference:
            success, message = verify_and_credit_wallet(reference)
            return jsonify({'status': 'processed', 'success': success, 'message': message}), 200
            
    return jsonify({'status': 'ignored'}), 200


# ===== GROUP MANAGEMENT BY USER =====
@app.route('/groups/<int:group_id>/join/', methods=['POST'])
def join_group(group_id):
    if 'useronline' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
    user = User.query.get(session['useronline'])
    group = Group.query.get_or_404(group_id)
    
    existing_member = GroupMember.query.filter_by(group_id=group.id, user_id=user.id).first()
    if existing_member:
        if existing_member.status == 'Accepted':
            return jsonify({'success': False, 'message': 'You are already a member of this group.'})
        elif existing_member.status == 'Pending':
            return jsonify({'success': False, 'message': 'Your join request is pending approval.'})
        else:
            existing_member.status = 'Pending'
            existing_member.joined_at = datetime.datetime.now()
            db.session.commit()
            return jsonify({'success': True, 'message': 'Join request sent successfully!'})
            
    if group.maximum_members and group.current_members >= group.maximum_members:
        return jsonify({'success': False, 'message': 'This group is already full.'})
        
    new_member = GroupMember(
        group_id=group.id,
        user_id=user.id,
        status='Pending'
    )
    db.session.add(new_member)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Join request sent successfully!'})


@app.route('/groups/<int:group_id>/')
def group_details(group_id):
    if 'useronline' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('login'))
        
    user = User.query.get(session['useronline'])
    group = Group.query.get_or_404(group_id)
    
    member_record = GroupMember.query.filter_by(group_id=group.id, user_id=user.id).first()
    group_members = GroupMember.query.filter_by(group_id=group.id, status='Accepted').all()
    group_contributions = Contribution.query.filter_by(group_id=group.id).order_by(Contribution.due_date.desc()).all()
    
    user_paid_contributions = Contribution.query.filter_by(group_id=group.id, member_id=user.id, paid=True).all()
    user_total_contributed = sum(c.amount for c in user_paid_contributions)
    
    payout_queue = []
    for gm in group_members:
        member_user = User.query.get(gm.user_id)
        if member_user:
            payout_queue.append({
                'name': member_user.fullname,
                'status': gm.status
            })
            
    return render_template('user/group_details.html', 
                           user=user, 
                           group=group, 
                           member_record=member_record,
                           members=group_members,
                           contributions=group_contributions,
                           user_total_contributed=user_total_contributed,
                           payout_queue=payout_queue)


@app.route('/groups/<int:group_id>/contribute/', methods=['POST'])
def group_contribute(group_id):
    if 'useronline' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
    user = User.query.get(session['useronline'])
    group = Group.query.get_or_404(group_id)
    
    gm = GroupMember.query.filter_by(group_id=group.id, user_id=user.id).first()
    if not gm or gm.status != 'Accepted':
        return jsonify({'success': False, 'message': 'Only accepted group members can make contributions.'})
        
    wallet = Wallet.query.filter_by(user_id=user.id).first()
    if not wallet or wallet.balance < group.contribution_amount:
        return jsonify({'success': False, 'message': f'Insufficient wallet balance. You need ₦{group.contribution_amount:,.2f}'})
        
    wallet.balance -= group.contribution_amount
    user.wallet_balance = wallet.balance
    
    contrib = Contribution.query.filter_by(group_id=group.id, member_id=user.id, paid=False).first()
    if not contrib:
        contrib = Contribution(
            group_id=group.id,
            member_id=user.id,
            amount=group.contribution_amount,
            due_date=datetime.datetime.now(),
            paid=True,
            payment_reference=f"GRP-{group.id}-{user.id}-{secrets.token_hex(4)}"
        )
        db.session.add(contrib)
    else:
        contrib.paid = True
        contrib.payment_reference = f"GRP-{group.id}-{user.id}-{secrets.token_hex(4)}"
        contrib.created_at = datetime.datetime.now()
        
    db.session.commit()
    
    create_transaction(
        user_id=user.id,
        amount=group.contribution_amount,
        type='group_contribution',
        description=f"Group contribution to: {group.group_name}",
        status='completed'
    )
    
    create_notification(
        user_id=user.id,
        title="👥 Group Contribution Successful",
        message=f"₦{group.contribution_amount:,.2f} successfully contributed to '{group.group_name}'."
    )
    
    return jsonify({'success': True, 'message': 'Contribution completed successfully!'})

# ===== GROUP ROUTES =====
@app.route("/groups/")
def groups():
    if 'useronline' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('login'))
    user = User.query.get(session['useronline'])
    all_groups = Group.query.all()
    
    # User's groups
    memberships = GroupMember.query.filter_by(user_id=user.id).all()
    my_group_ids = [m.group_id for m in memberships]
    my_groups = Group.query.filter(Group.id.in_(my_group_ids)).all() if my_group_ids else []
    membership_map = {m.group_id: m.status for m in memberships}

    active_groups_count = GroupMember.query.filter_by(user_id=user.id, status='Accepted').count()
    available_groups_count = len([group for group in all_groups if group.id not in my_group_ids])
    total_saved = user.total_saved or 0.0
    
    return render_template("user/groups.html", 
                           user=user, 
                           groups=all_groups, 
                           my_groups=my_groups, 
                           membership_map=membership_map,
                           active_groups_count=active_groups_count,
                           available_groups_count=available_groups_count,
                           total_saved=total_saved)

# ===== INVESTMENT ROUTES =====
@app.route('/investments/')
def investments():
    if 'useronline' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('login'))
    
    user = User.query.get(session['useronline'])
    
    return render_template('user/investments.html', 
                         user=user,
                         cowrywise_client_id=os.getenv('COWRYWISE_CLIENT_ID'),
                         cowrywise_client_secret=os.getenv('COWRYWISE_CLIENT_SECRET'),
                         cowrywise_account_id=os.getenv('COWRYWISE_ACCOUNT_ID'))

# ===== TRANSFER ROUTES =====
@app.route('/transfers/')
def transfers():
    if 'useronline' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('login'))
    user = User.query.get(session['useronline'])
    return render_template('user/transfers.html', user=user)

# ===== HISTORY ROUTE =====
@app.route('/history/')
def history():
    if 'useronline' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('login'))
    
    user = User.query.get(session['useronline'])
    
    # Get everything in one list
    all_activities = []
    
    # 1. Get transactions (payments, deposits, withdrawals, investments)
    wallet = Wallet.query.filter_by(user_id=user.id).first()
    if wallet:
        transactions = Transaction.query.filter_by(wallet_id=wallet.id)\
            .order_by(Transaction.created_at.desc()).all()
    else:
        transactions = []
    
    for t in transactions:
        all_activities.append({
            'title': t.description,
            'details': f"₦{t.amount:,.2f} - {t.type}",
            'status': t.status,
            'date': t.created_at,
            'type': 'transaction',
            'icon': 'bi-credit-card'
        })
    
    # 2. Get notifications (system messages)
    notifications = Notification.query.filter_by(user_id=user.id)\
        .order_by(Notification.created_at.desc()).all()
    
    for n in notifications:
        all_activities.append({
            'title': n.title,
            'details': n.message,
            'status': 'read' if n.is_read else 'unread',
            'date': n.created_at,
            'type': 'notification',
            'icon': 'bi-bell'
        })
    
    # Sort by date (newest first)
    all_activities.sort(key=lambda x: x['date'], reverse=True)
    
    return render_template('user/history.html', 
                         user=user,
                         activities=all_activities)

# ===== MESSAGES/INBOX =====
@app.route('/inbox/')
def inbox():
    if 'useronline' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('login'))
    user = User.query.get(session['useronline'])
    return render_template('user/messages.html', user=user)

# ===== SETTINGS =====
@app.route('/settings/')
def settings():
    if 'useronline' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('login'))
    user = User.query.get(session['useronline'])
    return render_template('user/settings.html', user=user)

# ===== HELP CENTER =====
@app.route('/help/')
def help():
    return render_template('user/help.html')


# ===== GROUP REQUESTS FOR USERS (GROUP ADMINS) =====
@app.route('/groups/requests/')
def view_group_requests():
    if 'useronline' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('login'))
        
    user = User.query.get(session['useronline'])
    managed_groups = Group.query.filter_by(admin_id=user.id).all()
    managed_group_ids = [g.id for g in managed_groups]
    
    pending_requests = GroupMember.query.filter(
        GroupMember.group_id.in_(managed_group_ids),
        GroupMember.status == 'Pending'
    ).all() if managed_group_ids else []
    
    return render_template('user/group_requests.html', user=user, pending_requests=pending_requests)


@app.route('/groups/request/<int:request_id>/<string:action>/', methods=['POST'])
@csrf.exempt
def handle_group_request(request_id, action):
    if 'useronline' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
    gm = GroupMember.query.get_or_404(request_id)
    group = Group.query.get(gm.group_id)
    
    user_id = session['useronline']
    if group.admin_id != user_id and not session.get('is_admin'):
        return jsonify({'success': False, 'message': 'Permission denied.'})
        
    if action == 'approve':
        if group.maximum_members and group.current_members >= group.maximum_members:
            return jsonify({'success': False, 'message': 'Group is already full.'})
            
        gm.status = 'Accepted'
        group.current_members = (group.current_members or 0) + 1
        
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
        
        create_notification(
            user_id=gm.user_id,
            title="🎉 Group Join Request Approved",
            message=f"Your request to join group '{group.group_name}' has been approved by the admin."
        )
        return jsonify({'success': True, 'message': 'Request approved successfully!'})
        
    elif action == 'reject':
        gm.status = 'Rejected'
        db.session.commit()
        
        create_notification(
            user_id=gm.user_id,
            title="❌ Group Join Request Rejected",
            message=f"Your request to join group '{group.group_name}' has been rejected by the admin."
        )
        return jsonify({'success': True, 'message': 'Request rejected successfully!'})
        
    return jsonify({'success': False, 'message': 'Invalid action'}), 400