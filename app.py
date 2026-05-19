import os

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    flash,
    session
)
from models import db, User, Skill, Request, Message, Rating
from flask_socketio import SocketIO, emit
from flask_mail import Mail, Message as MailMessage
import random

from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user
)

app = Flask(__name__)
socketio = SocketIO(app)

app.secret_key = "skillswapsecret"
# EMAIL CONFIGURATION

app.config['MAIL_SERVER'] = 'smtp.gmail.com'

app.config['MAIL_PORT'] = 587

app.config['MAIL_USE_TLS'] = True

app.config['MAIL_USERNAME'] = os.environ.get(
    'MAIL_USERNAME'
)

app.config['MAIL_PASSWORD'] = os.environ.get(
    'MAIL_PASSWORD'
)

mail = Mail(app)
# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

# Flask Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Create tables
with app.app_context():
    db.create_all()

# Load user
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

#Profile
@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():

    if request.method == 'POST':

        current_user.name = request.form['name']

        current_user.qualification = request.form['qualification']

        current_user.bio = request.form['bio']

        current_user.contact = request.form['contact']

        db.session.commit()

        flash("Profile updated successfully")

        return redirect('/profile/' + str(current_user.id))

    return render_template(
        "edit_profile.html"
    )

#Profile Edit
@app.route('/profile/<int:user_id>')
@login_required
def profile(user_id):

    user = User.query.get(user_id)

    skills = Skill.query.filter_by(
        user_id=user_id
    ).all()

    reviews = Rating.query.filter_by(
        receiver_id=user_id
    ).all()

    # Average rating
    avg_rating = None

    if reviews:

        total = 0

        for review in reviews:

            total += review.rating

        avg_rating = round(total / len(reviews), 1)

    return render_template(
        "profile.html",
        user=user,
        skills=skills,
        reviews=reviews,
        avg_rating=avg_rating,
        User=User
    )


# Home Dashboard
@app.route('/', methods=['GET', 'POST'])
def home():

    # If user logged in → dashboard
    if current_user.is_authenticated:

        # Add skill
        if request.method == 'POST':

            skill_name = request.form['skill']

            new_skill = Skill(
                skill_name=skill_name,
                user_id=current_user.id
            )

            db.session.add(new_skill)

            db.session.commit()

        # User skills
        skills = Skill.query.filter_by(
            user_id=current_user.id
        ).all()

        return render_template(
            "dashboard.html",
            user=current_user,
            skills=skills
        )

    # If not logged in → landing page
    return render_template("landing.html")

#search
@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():

    results = []

    search_skill = ""

    # Dashboard GET search
    if request.method == 'GET':

        search_skill = request.args.get('search', '')

    # Search page POST search
    elif request.method == 'POST':

        search_skill = request.form['search']

    # Search query
    if search_skill:

        results = Skill.query.filter(
            Skill.skill_name.ilike(f'%{search_skill}%')
        ).all()

    return render_template(
        "search.html",
        results=results,
        User=User,
        Rating=Rating,
        search_skill=search_skill
    )

#Send
@app.route('/send_request/<int:skill_id>')
@login_required
def send_request(skill_id):

    skill = Skill.query.get(skill_id)

    # Prevent sending request to yourself
    if skill.user_id == current_user.id:

        flash("You cannot connect with yourself")

        return redirect('/search')

    # Create request
    new_request = Request(

        sender_id=current_user.id,

        receiver_id=skill.user_id,

        skill_id=skill.id
    )

    db.session.add(new_request)

    db.session.commit()

    flash("Request sent successfully")

    return redirect('/search')

#RequestPageRoute
@app.route('/requests')
@login_required
def requests_page():

    # Only pending received requests
    received_requests = Request.query.filter_by(
        receiver_id=current_user.id,
        status="Pending"
    ).all()

    # Only pending sent requests
    sent_requests = Request.query.filter_by(
        sender_id=current_user.id,
        status="Pending"
    ).all()

    return render_template(
        "requests.html",
        received_requests=received_requests,
        sent_requests=sent_requests,
        User=User
    )

#Chats(2)
@app.route('/chats')
@login_required
def chats_page():

    chats = Request.query.filter(

        ((Request.sender_id == current_user.id) |
         (Request.receiver_id == current_user.id)) &

        (Request.status == "Accepted")

    ).all()

    return render_template(
        "chats.html",
        chats=chats,
        User=User,
        current_user=current_user
    )

#Accept
@app.route('/accept_request/<int:request_id>')
@login_required
def accept_request(request_id):

    request_item = Request.query.get(request_id)

    request_item.status = "Accepted"

    db.session.commit()
    # GET SENDER USER

    sender_user = User.query.get(
        request_item.sender_id
    )

    receiver_user = User.query.get(
        request_item.receiver_id
    )

# SEND EMAIL

    msg = MailMessage(

    subject="Your SkillSwap Request Was Accepted!",

    sender=app.config['MAIL_USERNAME'],

    recipients=[sender_user.email]

)

    msg.body = f"""

Hello {sender_user.name},

Good news!

        {receiver_user.name} has accepted your collaboration request on SkillSwap.

You can now start chatting and exchanging skills.

Login now to continue learning together.

- SkillSwap Team
"""

    mail.send(msg)

    flash("Request accepted")

    return redirect('/requests')

#Reject
@app.route('/reject_request/<int:request_id>')
@login_required
def reject_request(request_id):

    request_item = Request.query.get(request_id)

    request_item.status = "Rejected"

    db.session.commit()

    flash("Request rejected")

    return redirect('/requests')

#Chat
@app.route('/chat/<int:request_id>', methods=['GET', 'POST'])
@login_required
def chat(request_id):

    request_item = Request.query.get(request_id)

    # Send message
    if request.method == 'POST':

        text = request.form['message']

        new_message = Message(
            request_id=request_id,
            sender_id=current_user.id,
            text=text
        )

        db.session.add(new_message)

        db.session.commit()

        # IMPORTANT FIX
        return redirect(f'/chat/{request_id}')

    # Fetch messages
    messages = Message.query.filter_by(
        request_id=request_id
    ).all()

    return render_template(
    "chat.html",
    messages=messages,
    request_item=request_item,
    User=User,
    current_user=current_user
)

#Rating
@app.route('/rate/<int:user_id>', methods=['GET', 'POST'])
@login_required
def rate_user(user_id):

    if request.method == 'POST':

        rating = request.form['rating']

        feedback = request.form['feedback']

        new_rating = Rating(

            receiver_id=user_id,

            sender_id=current_user.id,

            rating=rating,

            feedback=feedback
        )

        db.session.add(new_rating)

        db.session.commit()

        flash("Feedback submitted successfully")

        return redirect('/')

    return render_template(
        "rating.html",
        user_id=user_id
    )

#Reviews
@app.route('/reviews/<int:user_id>')
@login_required
def reviews(user_id):

    user = User.query.get(user_id)

    reviews = Rating.query.filter_by(
        receiver_id=user_id
    ).all()

    return render_template(
        "reviews.html",
        user=user,
        reviews=reviews,
        User=User
    )


# Register
# REGISTER WITH OTP

@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        name = request.form['name']

        email = request.form['email']

        password = request.form['password']

        # CHECK EXISTING USER

        existing_user = User.query.filter_by(
            email=email
        ).first()

        if existing_user:

            flash("Email already exists")

            return redirect('/register')

        # GENERATE OTP

        otp = str(random.randint(100000, 999999))

        # STORE TEMP DATA

        session['temp_name'] = name

        session['temp_email'] = email

        session['temp_password'] = password

        session['otp'] = otp

        # SEND OTP EMAIL

        msg = MailMessage(

            subject="SkillSwap OTP Verification",

            sender=app.config['MAIL_USERNAME'],

            recipients=[email]

        )

        msg.body = f"""

Hello {name},

Your SkillSwap OTP is:

{otp}

This OTP is used for email verification.

- SkillSwap Team
"""

        mail.send(msg)

        flash("OTP sent to your email")

        return redirect('/verify_otp')

    return render_template("register.html")

#OTP Route
# VERIFY OTP

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():

    if request.method == 'POST':

        entered_otp = request.form['otp']

        # CHECK OTP

        if entered_otp == session.get('otp'):

            # CREATE USER

            new_user = User(

                name=session.get('temp_name'),

                email=session.get('temp_email'),

                password=session.get('temp_password')

            )

            db.session.add(new_user)

            db.session.commit()

            # SEND WELCOME EMAIL

            msg = MailMessage(

                subject="Welcome to SkillSwap!",

                sender=app.config['MAIL_USERNAME'],

                recipients=[session.get('temp_email')]

            )

            msg.body = f"""

Hello {session.get('temp_name')},

Welcome to SkillSwap!

Your account has been verified successfully.

- SkillSwap Team
"""

            mail.send(msg)

            # CLEAR SESSION

            session.pop('otp', None)

            session.pop('temp_name', None)

            session.pop('temp_email', None)

            session.pop('temp_password', None)

            flash("Registration successful")

            return redirect('/login')

        else:

            flash("Invalid OTP")

    return render_template("verify_otp.html")


# FORGOT PASSWORD

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():

    if request.method == 'POST':

        email = request.form['email']

        user = User.query.filter_by(
            email=email
        ).first()

        if not user:

            flash("Email not found")

            return redirect('/forgot_password')

        # GENERATE OTP

        otp = str(random.randint(100000, 999999))

        # STORE IN SESSION

        session['reset_email'] = email

        session['reset_otp'] = otp

        # SEND EMAIL

        msg = MailMessage(

            subject="SkillSwap Password Reset OTP",

            sender=app.config['MAIL_USERNAME'],

            recipients=[email]

        )

        msg.body = f"""

Hello,

Your OTP for password reset is:

{otp}

- SkillSwap Team
"""

        mail.send(msg)

        flash("OTP sent to your email")

        return redirect('/verify_reset_otp')

    return render_template(
        "forgot_password.html"
    )

# VERIFY RESET OTP

@app.route('/verify_reset_otp', methods=['GET', 'POST'])
def verify_reset_otp():

    if request.method == 'POST':

        entered_otp = request.form['otp']

        if entered_otp == session.get('reset_otp'):

            return redirect('/reset_password')

        else:

            flash("Invalid OTP")

    return render_template(
        "verify_reset_otp.html"
    )

# RESET PASSWORD

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():

    if request.method == 'POST':

        new_password = request.form['password']

        user = User.query.filter_by(
            email=session.get('reset_email')
        ).first()

        user.password = new_password

        db.session.commit()

        # CLEAR SESSION

        session.pop('reset_email', None)

        session.pop('reset_otp', None)

        flash("Password updated successfully")

        return redirect('/login')

    return render_template(
        "reset_password.html"
    )

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and user.password == password:

            login_user(user)

            return redirect('/')

        else:
            flash("Invalid email or password")

    return render_template("login.html")


# Logout
@app.route('/logout')
@login_required
def logout():

    logout_user()

    return redirect('/login')


@socketio.on('send_message')
def handle_send_message(data):

    # SAVE MESSAGE IN DATABASE

    new_message = Message(

        request_id=data['request_id'],

        sender_id=data['sender_id'],

        text=data['message']

    )

    db.session.add(new_message)

    db.session.commit()

    # SEND LIVE MESSAGE

    emit(

        'receive_message',

        {

            'username': data['username'],

            'message': data['message'],

            'sender_id': data['sender_id']

        },

        broadcast=True

    )


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)