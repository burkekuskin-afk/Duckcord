from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required, login_manager
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime



app = Flask(__name__)
app.config["SECRET_KEY"] = "super_secret"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///chat.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

#Render debugging
app.config["DEBUG"] = True

#DB models/framework
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password_hash = db.Column(db.String(128))

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(100))
    text = db.Column(db.Text)
    time_stamp = db.Column(db.String(20))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect("/chat")
        else:
            new_user = User(username=username, password_hash=generate_password_hash(password))
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect("/chat")
    return render_template("login.html")

@app.route("/chat")
@login_required
def chat():
    messages = Message.query.order_by(Message.id).all()
    return render_template("chat.html", username=current_user, messages=messages)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/")

online = {}

@SocketIO.on("connect")
def connect():
    if current_user.is_authenticated:
        online[request.sid] = current_user.username
        emit("staus", f"{current_user.username} joined the chat", broadcast=True)

@SocketIO.on("connect")
def disconnect():
    username = online.pop(request.sid, None)
    if username:
        emit("status", f"{username} has left the chat", broadcast=True)

@SocketIO.on("message")
def data_handle_message(msg):
    data = {
        "user":current_user.username,
        "content":msg,
        "time_stamp":datetime.now().strftime("%H:%M")
    }
    db.session.add(Message(user=data["user"], text=data["content"], time_stamp=data["time_stamp"]))
    db.session.commit()
    emit("message", data, broadcast=True)

@SocketIO.on("typing")
def typing():
    emit("typing", current_user.username, broadcast=True)



if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    SocketIO.run(app, host="0.0.0.0", port=10000, debug=True)