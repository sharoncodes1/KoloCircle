from flask import render_template,url_for,request,redirect,flash
from pkg.models import User
from pkg import app

@app.after_request
def after_request(resp):
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return resp

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/dashboard/")
def dashboard():
    return render_template("pages/dashboard.html")

@app.route("/login/", methods=["GET", "POST"])
def login():
    if request == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()
        if not user:
            flash("No account found with this email!", "danger")
            return render_template("pages/login.html")
        
        # Check password
        if not user.check_password(password):
            flash("Incorrect password!", "danger")
            return render_template("pages/login.html")
         
    return render_template("pages/login.html")

@app.route("/signup/", methods=["GET", "POST"])
def signup():
    
    if request.method == "POST":
        name= request.form.get("name")
        email= request.form.get("email")
        password= request.form.get("password")
        confirm_password= request.form.get("confirm_password")
        if not name or not email or not password or not confirm_password:
                    flash("All fields are required!", "danger")
                    return render_template("pages/signup.html")  
        
        if password != confirm_password:
            flash("Passwords do not match!", "danger")
            return render_template("pages/signup.html")
        
        if len(password) < 8:
            flash("Password must be at least 8 characters!", "danger")
            return render_template("pages/signup.html")
        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already registered! Please login.", "warning")
            return redirect(url_for("login"))
         
        return redirect(url_for("login"))
    return render_template("pages/signup.html")


@app.route("/savings/")
def savings():
    return render_template("pages/savings.html")

@app.route("/groups/")
def groups():
    return render_template("pages/groups.html")

@app.route('/investments/')
def investments():
    return render_template('pages/investments.html')

# ===== TRANSFERS =====
@app.route('/transfers/')
def transfers():
    return render_template('pages/transfers.html')

# ===== HISTORY =====
@app.route('/history/')
def history():
    return render_template('pages/history.html')

# ===== MESSAGES =====
@app.route('/messages/')
def messages():
    return render_template('pages/messages.html')

# ===== SETTINGS =====
@app.route('/settings/')
def settings():
    return render_template('pages/settings.html')

# ===== HELP =====
@app.route('/help/')
def help():
    return render_template('pages/help.html')
