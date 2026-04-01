from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = '123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50))
    password = db.Column(db.String(50))
    role = db.Column(db.String(10))


class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer)
    month = db.Column(db.String(10))
    amount = db.Column(db.Float)


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(50))
    member = db.Column(db.String(100))
    month = db.Column(db.String(10))
    old_value = db.Column(db.Float)
    new_value = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(
            username=request.form['username'],
            password=request.form['password']
        ).first()

        if user:
            login_user(user)
            return redirect('/dashboard')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')


months = ["Jan", "Feb", "Mar", "Apr", "Maj", "Jun", "Jul", "Avg", "Sep", "Okt", "Nov", "Dec"]

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():

    if request.method == 'POST':
        member_id = request.form['member_id']
        month = request.form['month']
        amount = float(request.form['amount'])

        member = Member.query.get(member_id)

        existing = Payment.query.filter_by(member_id=member_id, month=month).first()
        old_value = existing.amount if existing else 0

        if existing:
            existing.amount = amount
        else:
            db.session.add(Payment(member_id=member_id, month=month, amount=amount))

        db.session.add(AuditLog(
            user=current_user.username,
            member=member.name,
            month=month,
            old_value=old_value,
            new_value=amount
        ))

        db.session.commit()

    members = Member.query.all()
    payments = Payment.query.all()

    data = {}
    for m in members:
        data[m.id] = {month: 0 for month in months}

    for p in payments:
        data[p.member_id][p.month] = p.amount

    return render_template('dashboard.html', members=members, data=data, months=months)


@app.route('/audit')
@login_required
def audit():
    if current_user.role != "admin":
        return "Nema pristupa"

    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).all()
    return render_template('audit.html', logs=logs)


@app.before_first_request
def setup():
    db.create_all()

    if not User.query.first():
        db.session.add(User(username="MIODRAG", password="123", role="admin"))
        db.session.add(User(username="user", password="123", role="user"))

        db.session.add(Member(name="Marko"))
        db.session.add(Member(name="Ivan"))

        db.session.commit()


if __name__ == '__main__':
    app.run()
