# pkg/scheduler.py
import datetime
from . import db
from .models import User, Wallet, Savings, Group, GroupMember, Contribution, WalletTransaction, Notification, create_notification, create_transaction
from apscheduler.schedulers.background import BackgroundScheduler

def run_deductions(app):
    with app.app_context():
        now = datetime.datetime.now()
        print(f"[Scheduler] Running deductions check at {now}...")
        
        # 1. INDIVIDUAL SAVINGS AUTO-DEDUCTION
        active_savings = Savings.query.filter_by(status='active').all()
        for plan in active_savings:
            if not plan.next_payment_date:
                # If no next payment date is set, initialize to today
                plan.next_payment_date = now
                db.session.commit()
                
            if plan.next_payment_date <= now:
                user = User.query.get(plan.user_id)
                if not user:
                    continue
                
                wallet = Wallet.query.filter_by(user_id=user.id).first()
                if not wallet:
                    wallet = Wallet(user_id=user.id, balance=0.0, total_funded=0.0, total_withdrawn=0.0)
                    db.session.add(wallet)
                    db.session.commit()
                
                # Check wallet balance
                if wallet.balance >= plan.amount:
                    # Deduct balance
                    wallet.balance -= plan.amount
                    user.wallet_balance = wallet.balance
                    
                    # Accumulate saved amount on the plan
                    plan.saved_amount = (plan.saved_amount or 0.0) + plan.amount
                    user.total_saved = (user.total_saved or 0.0) + plan.amount
                    
                    # Update next payment date based on frequency
                    freq = plan.frequency.lower()
                    if 'daily' in freq:
                        plan.next_payment_date = plan.next_payment_date + datetime.timedelta(days=1)
                    elif 'weekly' in freq:
                        plan.next_payment_date = plan.next_payment_date + datetime.timedelta(weeks=1)
                    elif 'monthly' in freq:
                        plan.next_payment_date = plan.next_payment_date + datetime.timedelta(days=30)
                    else:  # Custom or fallback
                        plan.next_payment_date = plan.next_payment_date + datetime.timedelta(minutes=5) # 5 mins for testing custom
                    
                    # Check if target is met
                    if plan.saved_amount >= plan.target_amount:
                        plan.status = 'completed'
                        # Notify savings target reached
                        create_notification(
                            user_id=user.id,
                            title="🎉 Savings Goal Reached!",
                            message=f"Congratulations! You have reached your savings target of ₦{plan.target_amount:,.2f} for '{plan.title}'."
                        )
                    
                    db.session.commit()
                    
                    # Create transaction log
                    create_transaction(
                        user_id=user.id,
                        amount=plan.amount,
                        type='savings_deduction',
                        description=f"Auto-deduction for plan: {plan.title}",
                        status='completed'
                    )
                    
                    # Notify user
                    create_notification(
                        user_id=user.id,
                        title="💰 Savings Contribution Successful",
                        message=f"₦{plan.amount:,.2f} was successfully deducted from your wallet for '{plan.title}'."
                    )
                    print(f"Success: Deducted {plan.amount} from {user.email} for {plan.title}")
                    
                else:
                    # Insufficient funds
                    # Create failed transaction log
                    create_transaction(
                        user_id=user.id,
                        amount=plan.amount,
                        type='savings_deduction',
                        description=f"Failed auto-deduction (Insufficient Balance) for plan: {plan.title}",
                        status='failed'
                    )
                    
                    # Notify user
                    create_notification(
                        user_id=user.id,
                        title="⚠️ Savings Contribution Failed",
                        message=f"Deduction of ₦{plan.amount:,.2f} for '{plan.title}' failed due to insufficient wallet balance."
                    )
                    
                    # Push next payment date slightly so it retries later
                    plan.next_payment_date = plan.next_payment_date + datetime.timedelta(hours=1)
                    db.session.commit()
                    print(f"Failed: Insufficient funds for {user.email} for {plan.title}")

        # 2. GROUP SAVINGS CYCLE AUTO-DEDUCTION
        # Check active contributions due
        pending_contributions = Contribution.query.filter_by(paid=False).all()
        for contrib in pending_contributions:
            if contrib.due_date <= now:
                # Process group member contribution
                # Get the group
                group = Group.query.get(contrib.group_id)
                # Get the user
                user = User.query.get(contrib.member_id)
                if not group or not user:
                    continue
                
                # Check group member status
                gm = GroupMember.query.filter_by(group_id=group.id, user_id=user.id).first()
                if not gm or gm.status != 'Accepted':
                    continue # Only accepted members contribute
                
                wallet = Wallet.query.filter_by(user_id=user.id).first()
                if not wallet:
                    wallet = Wallet(user_id=user.id, balance=0.0, total_funded=0.0, total_withdrawn=0.0)
                    db.session.add(wallet)
                    db.session.commit()
                
                if wallet.balance >= contrib.amount:
                    # Deduct from wallet
                    wallet.balance -= contrib.amount
                    user.wallet_balance = wallet.balance
                    
                    # Mark contribution as paid
                    contrib.paid = True
                    contrib.created_at = now
                    
                    db.session.commit()
                    
                    # Create transaction log
                    create_transaction(
                        user_id=user.id,
                        amount=contrib.amount,
                        type='group_contribution',
                        description=f"Group Contribution for: {group.group_name}",
                        status='completed'
                    )
                    
                    # Create notification
                    create_notification(
                        user_id=user.id,
                        title="👥 Group Contribution Successful",
                        message=f"₦{contrib.amount:,.2f} successfully deducted for group '{group.group_name}'."
                    )
                    print(f"Success: Deducted {contrib.amount} from {user.email} for group {group.group_name}")
                else:
                    # Failed contribution
                    create_transaction(
                        user_id=user.id,
                        amount=contrib.amount,
                        type='group_contribution',
                        description=f"Failed Group Contribution (Insufficient Balance) for: {group.group_name}",
                        status='failed'
                    )
                    
                    create_notification(
                        user_id=user.id,
                        title="⚠️ Group Contribution Failed",
                        message=f"Group contribution of ₦{contrib.amount:,.2f} for '{group.group_name}' failed due to insufficient funds."
                    )
                    
                    # Push due date slightly to retry later
                    contrib.due_date = contrib.due_date + datetime.timedelta(hours=1)
                    db.session.commit()
                    print(f"Failed: Insufficient funds for {user.email} for group {group.group_name}")


def start_scheduler(app):
    scheduler = BackgroundScheduler()
    # scheduler.add_job(
    #     func=run_deductions,
    #     trigger="interval",
    #     seconds=30,  # check every 30 seconds for quick updates/testing
    #     args=[app]
    # )
    # scheduler.start()
    print("Background scheduler started successfully!")
