from flask import Flask, request, render_template_string, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from azure.storage.blob import BlobServiceClient, ContentSettings, PublicAccess
from azure.core.exceptions import ResourceExistsError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'f1340841002453968837b6053f9dc3fdc7fd3b7d86b87dca'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mssql+pyodbc://asadmehmood10:Admin123@com769project.database.windows.net/ScalableProject1?driver=ODBC+Driver+17+for+SQL+Server'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

AZURE_CONNECTION_STRING = "DefaultEndpointsProtocol=https;AccountName=asadmehmood;AccountKey=ocujReTA6iRh8EoTKs54g43hn8px/WH0TcGzjnA3fUFkY8bj5PMiYYU8G/DyWPyKoDW8rgf8pFd8+AStWEzJig==;EndpointSuffix=core.windows.net"
AZURE_CONTAINER_NAME = "videos"

db = SQLAlchemy(app)
blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)

try:
    blob_service_client.create_container(AZURE_CONTAINER_NAME)
except Exception:
    pass

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(512), nullable=False)

class Media(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    caption = db.Column(db.String(256), nullable=True)
    location = db.Column(db.String(100), nullable=True)
    people_present = db.Column(db.String(256), nullable=True)
    upload_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    file_path = db.Column(db.String(512), nullable=False)
    media_type = db.Column(db.String(20), nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comments = db.relationship('Comment', backref='media')
    ratings = db.relationship('Rating', backref='media')

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    media_id = db.Column(db.Integer, db.ForeignKey('media.id'), nullable=False)

class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    media_id = db.Column(db.Integer, db.ForeignKey('media.id'), nullable=False)
    __table_args__ = (db.UniqueConstraint('user_id', 'media_id', name='unique_user_media_rating'),)

with app.app_context():
    db.create_all()

BASE_CSS = '''
    /* Warm Creative Theme */
    :root {
        --bg-primary: #F5E8C7; /* Warm beige */
        --bg-secondary: #DCC7AA; /* Soft taupe */
        --bg-card: #FF9999; /* Light coral */
        --accent: #F97316; /* Vibrant orange */
        --accent-hover: #FB923C; /* Orange hover */
        --highlight: #2DD4BF; /* Bright teal */
        --highlight-hover: #5EEAD4; /* Teal hover */
        --text-primary: #2D2D2D; /* Deep charcoal */
        --text-secondary: #6B7280; /* Muted gray */
        --success: #22C55E; /* Green */
        --error: #EF4444; /* Red */
        --warning: #FACC15; /* Yellow */
    }

    * {
        box-sizing: border-box;
        margin: 0;
        padding: 0;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    body {
        background-color: var(--bg-primary);
        color: var(--text-primary);
        line-height: 1.5;
        min-height: 100vh;
    }

    .container {
        max-width: 1280px;
        margin: 0 auto;
        padding: 24px;
    }

    .btn {
        display: inline-block;
        background-color: var(--accent);
        color: var(--text-primary);
        border: none;
        padding: 12px 28px;
        border-radius: 12px;
        cursor: pointer;
        font-weight: 500;
        letter-spacing: 0.5px;
        transition: all 0.3s ease;
        text-decoration: none;
        font-size: 16px;
        text-align: center;
    }

    .btn:hover {
        background-color: var(--accent-hover);
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(249, 115, 22, 0.3);
    }

    input, select, textarea {
        background-color: var(--bg-secondary);
        border: 1px solid #A3A3A3;
        color: var(--text-primary);
        padding: 12px 16px;
        border-radius: 8px;
        margin-bottom: 16px;
        width: 100%;
        font-size: 16px;
        transition: border-color 0.3s ease;
    }

    input:focus, select:focus, textarea:focus {
        border-color: var(--accent);
        outline: none;
        box-shadow: 0 0 0 3px rgba(249, 115, 22, 0.2);
    }

    .card {
        background-color: var(--bg-card);
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 12px 32px rgba(0, 0, 0, 0.15);
        margin-bottom: 32px;
        transition: transform 0.3s ease;
    }

    .card:hover {
        transform: translateY(-4px);
    }

    .card-body {
        padding: 28px;
    }

    .navbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 16px 0;
        margin-bottom: 32px;
        border-bottom: 1px solid #A3A3A3;
    }

    .navbar-brand {
        font-size: 28px;
        font-weight: 700;
        color: var(--accent);
        text-decoration: none;
    }

    .navbar-links {
        display: flex;
        gap: 24px;
    }

    .navbar-links a {
        color: var(--text-secondary);
        text-decoration: none;
        transition: color 0.3s ease;
        font-weight: 500;
    }

    .navbar-links a:hover {
        color: var(--accent);
    }

    .alert {
        padding: 14px 20px;
        border-radius: 10px;
        margin-bottom: 24px;
    }

    .alert-success {
        background-color: var(--success);
        color: var(--text-primary);
    }

    .alert-danger {
        background-color: var(--error);
        color: var(--text-primary);
    }

    .alert-warning {
        background-color: var(--warning);
        color: var(--text-primary);
    }

    .grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
        gap: 32px;
    }

    @media (max-width: 768px) {
        .grid {
            grid-template-columns: 1fr;
        }

        .navbar {
            flex-direction: column;
            gap: 16px;
        }
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(16px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .animate-fade-in {
        animation: fadeIn 0.6s ease forwards;
    }

    .form-container {
        max-width: 480px;
        margin: 0 auto;
        animation: fadeIn 0.6s ease forwards;
    }

    .form-title {
        font-size: 36px;
        margin-bottom: 24px;
        text-align: center;
        font-weight: 700;
        background: linear-gradient(to right, var(--accent), var(--highlight));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .form-group {
        margin-bottom: 24px;
    }

    .form-label {
        display: block;
        margin-bottom: 8px;
        font-weight: 500;
        color: var(--text-secondary);
    }

    .media-title {
        font-size: 22px;
        margin-bottom: 12px;
        color: var(--text-primary);
    }

    .media-caption {
        color: var(--text-secondary);
        margin-bottom: 16px;
        font-size: 15px;
    }

    .media-meta {
        display: flex;
        gap: 16px;
        margin-bottom: 16px;
        font-size: 14px;
        color: var(--text-secondary);
    }

    .media-meta span {
        display: flex;
        align-items: center;
        gap: 6px;
    }

    .media-content {
        width: 100%;
        margin-bottom: 20px;
        border-radius: 12px;
        overflow: hidden;
    }

    .actions-container {
        margin-top: 24px;
        border-top: 1px solid #A3A3A3;
        padding-top: 20px;
    }

    .rating-container {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 20px;
    }

    .rating-stars {
        display: inline-flex;
        gap: 3px;
        font-size: 18px;
        color: var(--highlight);
    }

    .comments-section {
        margin-top: 24px;
    }

    .comment-item {
        padding: 14px 18px;
        background-color: var(--bg-secondary);
        border-radius: 10px;
        margin-bottom: 14px;
    }

    .star-rating {
        display: flex;
        flex-direction: row-reverse;
        gap: 8px;
    }

    .star-rating input {
        display: none;
    }

    .star-rating label {
        cursor: pointer;
        width: 28px;
        height: 28px;
        background-color: var(--bg-secondary);
        border-radius: 50%;
        display: flex;
        justify-content: center;
        align-items: center;
        color: var(--text-secondary);
        font-size: 18px;
        transition: all 0.2s ease;
    }

    .star-rating label:hover,
    .star-rating label:hover ~ label,
    .star-rating input:checked ~ label {
        color: var(--highlight);
    }
'''

@app.route('/')
def index():
    return render_template_string('''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>PixelPatch</title>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
            <style>
                ''' + BASE_CSS + '''
                .hero {
                    height: 100vh;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    text-align: center;
                    padding: 0 24px;
                    background: linear-gradient(rgba(245, 232, 199, 0.8), rgba(245, 232, 199, 0.8)), 
                                url('https://images.unsplash.com/photo-1505373877841-8d25f7d46678');
                    background-size: cover;
                    background-position: center;
                }

                .hero-title {
                    font-size: 4.5rem;
                    margin-bottom: 20px;
                    font-weight: 800;
                    background: linear-gradient(to right, var(--accent), var(--highlight));
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    animation: fadeIn 0.7s ease forwards;
                }

                .hero-subtitle {
                    font-size: 1.6rem;
                    margin-bottom: 36px;
                    color: var(--text-secondary);
                    max-width: 680px;
                    font-weight: 400;
                    animation: fadeIn 0.9s ease forwards;
                }

                .hero-buttons {
                    display: flex;
                    gap: 20px;
                    animation: fadeIn 1.1s ease forwards;
                }

                .btn-secondary {
                    background: transparent;
                    border: 2px solid var(--accent);
                    color: var(--accent);
                }

                .btn-secondary:hover {
                    background: rgba(249, 115, 22, 0.1);
                    color: var(--accent-hover);
                    border-color: var(--accent-hover);
                }

                .wave-shape {
                    position: absolute;
                    bottom: 0;
                    left: 0;
                    width: 100%;
                    height: 120px;
                    background: url("data:image/svg+xml,%3Csvg viewBox='0 0 1440 120' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M0 120V80C144 40 288 0 432 0C576 0 720 40 864 80C1008 120 1152 120 1296 80C1380 56 1440 32 1440 32V120H0Z' fill='%23F97316'/%3E%3C/svg%3E");
                    background-size: cover;
                }
            </style>
        </head>
        <body>
            <div class="hero">
                <h1 class="hero-title">PixelPatch</h1>
                <p class="hero-subtitle">Capture, share, and explore creative videos and photos in a vibrant community!</p>
                <div class="hero-buttons">
                    <a href="{{ url_for('login') }}" class="btn">Log In</a>
                    <a href="{{ url_for('register') }}" class="btn btn-secondary">Sign Up</a>
                </div>
                <div class="wave-shape"></div>
            </div>
        </body>
        </html>
    ''')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        hashed_password = generate_password_hash(password)
        user = User(username=username, email=email, role=role, password=hashed_password)
        try:
            db.session.add(user)
            db.session.commit()
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        except IntegrityError:
            db.session.rollback()
            flash('Username or email already exists.', 'danger')
    return render_template_string('''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Register - PixelPatch</title>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
            <style>
                ''' + BASE_CSS + '''
                .auth-container {
                    display: flex;
                    min-height: 100vh;
                    background: linear-gradient(rgba(245, 232, 199, 0.85), rgba(245, 232, 199, 0.85)), 
                                url('https://images.unsplash.com/photo-1513364776144-60967b0f800f');
                    background-size: cover;
                    background-position: center;
                }

                .auth-form {
                    flex: 1;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    padding: 48px;
                    max-width: 520px;
                    margin: 0 auto;
                }

                .auth-logo {
                    font-size: 28px;
                    font-weight: 700;
                    margin-bottom: 32px;
                    color: var(--accent);
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }

                .auth-title {
                    font-size: 36px;
                    margin-bottom: 12px;
                    font-weight: 700;
                    color: var(--text-primary);
                }

                .auth-subtitle {
                    color: var(--text-secondary);
                    margin-bottom: 28px;
                    font-size: 16px;
                }

                .role-selector {
                    display: flex;
                    gap: 16px;
                    margin-bottom: 24px;
                }

                .role-option {
                    flex: 1;
                    position: relative;
                }

                .role-option input {
                    position: absolute;
                    opacity: 0;
                    cursor: pointer;
                }

                .role-option label {
                    display: block;
                    background-color: var(--bg-secondary);
                    padding: 16px;
                    border-radius: 10px;
                    text-align: center;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    border: 2px solid transparent;
                }

                .role-option input:checked + label {
                    border-color: var(--accent);
                    background-color: rgba(249, 115, 22, 0.15);
                }

                .role-title {
                    font-weight: 600;
                    margin-bottom: 6px;
                    color: var(--text-primary);
                }

                .role-desc {
                    font-size: 13px;
                    color: var(--text-secondary);
                }

                .auth-footer {
                    margin-top: 28px;
                    text-align: center;
                    color: var(--text-secondary);
                }

                .auth-footer a {
                    color: var(--accent);
                    text-decoration: none;
                    font-weight: 500;
                }

                .auth-footer a:hover {
                    color: var(--accent-hover);
                }

                @media (max-width: 768px) {
                    .auth-form {
                        padding: 24px;
                    }
                }
            </style>
        </head>
        <body>
            <div class="auth-container">
                <div class="auth-form">
                    <div class="auth-logo">
                        <i class="fas fa-th"></i>
                        PixelPatch
                    </div>

                    <h1 class="auth-title">Join PixelPatch</h1>
                    <p class="auth-subtitle">Create your account to start sharing or exploring!</p>

                    <form method="POST" action="{{ url_for('register') }}">
                        <div class="form-group">
                            <label class="form-label">Username</label>
                            <input type="text" name="username" placeholder="Choose a username" required>
                        </div>

                        <div class="form-group">
                            <label class="form-label">Email</label>
                            <input type="email" name="email" placeholder="Your email address" required>
                        </div>

                        <div class="form-group">
                            <label class="form-label">Password</label>
                            <input type="password" name="password" placeholder="Create a password" required>
                        </div>

                        <div class="form-group">
                            <label class="form-label">Account Type</label>
                            <div class="role-selector">
                                <div class="role-option">
                                    <input type="radio" id="creator" name="role" value="creator" checked>
                                    <label for="creator">
                                        <div class="role-title">Creator</div>
                                        <div class="role-desc">Share your creative content</div>
                                    </label>
                                </div>
                                <div class="role-option">
                                    <input type="radio" id="consumer" name="role" value="consumer">
                                    <label for="consumer">
                                        <div class="role-title">Consumer</div>
                                        <div class="role-desc">Explore and enjoy content</div>
                                    </label>
                                </div>
                            </div>
                        </div>

                        <button type="submit" class="btn">Create Account</button>
                    </form>

                    <div class="auth-footer">
                        Already have an account? <a href="{{ url_for('login') }}">Log In</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
    ''')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['role'] = user.role
            session['username'] = user.username
            flash('Welcome back!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template_string('''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Login - PixelPatch</title>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
            <style>
                ''' + BASE_CSS + '''
                .auth-container {
                    display: flex;
                    min-height: 100vh;
                    background: linear-gradient(rgba(245, 232, 199, 0.85), rgba(245, 232, 199, 0.85)), 
                                url('https://images.unsplash.com/photo-1517604931442-7e0c8ed2962c');
                    background-size: cover;
                    background-position: center;
                }

                .auth-form {
                    flex: 1;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    padding: 48px;
                    max-width: 520px;
                    margin: 0 auto;
                }

                .auth-logo {
                    font-size: 28px;
                    font-weight: 700;
                    margin-bottom: 32px;
                    color: var(--accent);
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }

                .auth-title {
                    font-size: 36px;
                    margin-bottom: 12px;
                    font-weight: 700;
                    color: var(--text-primary);
                }

                .auth-subtitle {
                    color: var(--text-secondary);
                    margin-bottom: 28px;
                    font-size: 16px;
                }

                .auth-footer {
                    margin-top: 28px;
                    text-align: center;
                    color: var(--text-secondary);
                }

                .auth-footer a {
                    color: var(--accent);
                    text-decoration: none;
                    font-weight: 500;
                }

                .auth-footer a:hover {
                    color: var(--accent-hover);
                }

                .flash-message {
                    padding: 14px 20px;
                    border-radius: 10px;
                    margin-bottom: 24px;
                    color: var(--text-primary);
                }

                .flash-success {
                    background-color: var(--success);
                }

                .flash-danger {
                    background-color: var(--error);
                }

                @media (max-width: 768px) {
                    .auth-form {
                        padding: 24px;
                    }
                }
            </style>
        </head>
        <body>
            <div class="auth-container">
                <div class="auth-form">
                    <div class="auth-logo">
                        <i class="fas fa-th"></i>
                        PixelPatch
                    </div>

                    <h1 class="auth-title">Welcome Back</h1>
                    <p class="auth-subtitle">Log in to continue your creative journey</p>

                    {% with messages = get_flashed_messages(with_categories=true) %}
                        {% if messages %}
                            {% for category, message in messages %}
                                <div class="flash-message flash-{{ category }}">
                                    {{ message }}
                                </div>
                            {% endfor %}
                        {% endif %}
                    {% endwith %}

                    <form method="POST" action="{{ url_for('login') }}">
                        <div class="form-group">
                            <label class="form-label">Username</label>
                            <input type="text" name="username" placeholder="Your username" required>
                        </div>

                        <div class="form-group">
                            <label class="form-label">Password</label>
                            <input type="password" name="password" placeholder="Your password" required>
                        </div>

                        <button type="submit" class="btn">Log In</button>
                    </form>

                    <div class="auth-footer">
                        Need an account? <a href="{{ url_for('register') }}">Sign Up</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
    ''')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    search_query = request.form.get('search_query', '')
    media = Media.query.filter(Media.title.contains(search_query)).options(
        joinedload(Media.comments),
        joinedload(Media.ratings)
    ).all()

    if session['role'] == 'creator':
        return render_template_string('''
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Creator Dashboard - PixelPatch</title>
                <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
                <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
                <style>
                    ''' + BASE_CSS + '''
                    .dashboard {
                        display: flex;
                        min-height: 100vh;
                        background: var(--bg-primary);
                    }

                    .sidebar {
                        width: 280px;
                        background-color: var(--bg-secondary);
                        padding: 24px;
                        transition: all 0.3s ease;
                    }

                    .sidebar-logo {
                        font-size: 26px;
                        font-weight: 700;
                        color: var(--accent);
                        margin-bottom: 32px;
                        display: flex;
                        align-items: center;
                        gap: 10px;
                    }

                    .sidebar-menu {
                        display: flex;
                        flex-direction: column;
                        gap: 6px;
                    }

                    .sidebar-link {
                        display: flex;
                        align-items: center;
                        gap: 12px;
                        padding: 12px 16px;
                        border-radius: 10px;
                        color: var(--text-secondary);
                        text-decoration: none;
                        transition: all 0.3s ease;
                    }

                    .sidebar-link:hover, .sidebar-link.active {
                        background-color: var(--accent);
                        color: var(--text-primary);
                    }

                    .sidebar-link i {
                        font-size: 18px;
                        width: 24px;
                        text-align: center;
                    }

                    .main-content {
                        flex: 1;
                        padding: 32px;
                        background-color: var(--bg-primary);
                    }

                    .dashboard-header {
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        margin-bottom: 32px;
                    }

                    .dashboard-title {
                        font-size: 28px;
                        font-weight: 700;
                        background: linear-gradient(to right, var(--accent), var(--highlight));
                        -webkit-background-clip: text;
                        -webkit-text-fill-color: transparent;
                    }

                    .user-profile {
                        display: flex;
                        align-items: center;
                        gap: 12px;
                    }

                    .user-avatar {
                        width: 44px;
                        height: 44px;
                        border-radius: 50%;
                        background-color: var(--accent);
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-weight: 600;
                        color: var(--text-primary);
                        font-size: 18px;
                    }

                    .user-name {
                        font-weight: 500;
                        color: var(--text-primary);
                    }

                    .panel {
                        background-color: var(--bg-card);
                        border-radius: 16px;
                        padding: 32px;
                        box-shadow: 0 12px 32px rgba(0, 0, 0, 0.15);
                        margin-bottom: 32px;
                    }

                    .panel-title {
                        font-size: 22px;
                        margin-bottom: 24px;
                        font-weight: 600;
                        color: var(--text-primary);
                    }

                    .upload-container {
                        border: 2px dashed #A3A3A3;
                        border-radius: 12px;
                        padding: 48px;
                        text-align: center;
                        transition: all 0.3s ease;
                        cursor: pointer;
                    }

                    .upload-container:hover {
                        border-color: var(--accent);
                        background-color: rgba(249, 115, 22, 0.05);
                    }

                    .upload-icon {
                        font-size: 56px;
                        color: var(--accent);
                        margin-bottom: 16px;
                    }

                    .upload-text {
                        margin-bottom: 16px;
                        color: var(--text-secondary);
                        font-size: 16px;
                    }

                    .file-input {
                        display: none;
                    }

                    #dropzone {
                        min-height: 180px;
                        display: flex;
                        flex-direction: column;
                        justify-content: center;
                        align-items: center;
                    }

                    .flash-message {
                        padding: 14px 20px;
                        border-radius: 10px;
                        margin-bottom: 24px;
                        color: var(--text-primary);
                    }

                    .flash-success {
                        background-color: var(--success);
                    }

                    .flash-danger {
                        background-color: var(--error);
                    }

                    @media (max-width: 768px) {
                        .dashboard {
                            flex-direction: column;
                        }

                        .sidebar {
                            width: 100%;
                        }
                    }
                </style>
            </head>
            <body>
                <div class="dashboard">
                    <div class="sidebar">
                        <div class="sidebar-logo">
                            <i class="fas fa-th"></i>
                            PixelPatch
                        </div>

                        <nav class="sidebar-menu">
                            <a href="{{ url_for('dashboard') }}" class="sidebar-link active">
                                <i class="fas fa-home"></i>
                                Dashboard
                            </a>
                            <a href="{{ url_for('logout') }}" class="sidebar-link">
                                <i class="fas fa-sign-out-alt"></i>
                                Logout
                            </a>
                        </nav>
                    </div>

                    <div class="main-content">
                        <div class="dashboard-header">
                            <h1 class="dashboard-title">Creator Dashboard</h1>
                            <div class="user-profile">
                                <div class="user-avatar">
                                    {{ session.username[0] | upper if session.username else 'U' }}
                                </div>
                                <span class="user-name">{{ session.username | title if session.username else 'Creator' }}</span>
                            </div>
                        </div>

                        {% with messages = get_flashed_messages(with_categories=true) %}
                            {% if messages %}
                                {% for category, message in messages %}
                                    <div class="flash-message flash-{{ category }}">
                                        {{ message }}
                                    </div>
                                {% endfor %}
                            {% endif %}
                        {% endwith %}

                        <div class="panel">
                            <h2 class="panel-title">Upload New Media</h2>

                            <form method="POST" action="{{ url_for('upload') }}" enctype="multipart/form-data">
                                <div class="form-group">
                                    <label class="form-label">Title</label>
                                    <input type="text" name="title" placeholder="Give your media a title" required>
                                </div>

                                <div class="form-group">
                                    <label class="form-label">Caption</label>
                                    <textarea name="caption" placeholder="Add a caption to describe your media" rows="3"></textarea>
                                </div>

                                <div class="form-group">
                                    <label class="form-label">Location</label>
                                    <input type="text" name="location" placeholder="Where was this taken?">
                                </div>

                                <div class="form-group">
                                    <label class="form-label">People Present</label>
                                    <input type="text" name="people_present" placeholder="Who's in this media?">
                                </div>

                                <div class="form-group">
                                    <label class="form-label">Media Type</label>
                                    <select name="media_type" required>
                                        <option value="video">Video</option>
                                        <option value="picture">Picture</option>
                                    </select>
                                </div>

                                <div class="form-group">
                                    <label class="form-label">File</label>
                                    <div class="upload-container" id="dropzone" onclick="document.getElementById('file-input').click()">
                                        <i class="fas fa-cloud-upload-alt upload-icon"></i>
                                        <p class="upload-text">Drag & drop your file here or click to browse</p>
                                        <input type="file" name="file" id="file-input" class="file-input" required>
                                        <p id="selected-file">No file selected</p>
                                    </div>
                                </div>

                                <button type="submit" class="btn">Upload Media</button>
                            </form>
                        </div>
                    </div>
                </div>

                <script>
                    const fileInput = document.getElementById('file-input');
                    const selectedFile = document.getElementById('selected-file');

                    fileInput.addEventListener('change', function() {
                        if(fileInput.files.length > 0) {
                            selectedFile.textContent = fileInput.files[0].name;
                        } else {
                            selectedFile.textContent = 'No file selected';
                        }
                    });

                    const dropzone = document.getElementById('dropzone');

                    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                        dropzone.addEventListener(eventName, preventDefaults, false);
                    });

                    function preventDefaults(e) {
                        e.preventDefault();
                        e.stopPropagation();
                    }

                    ['dragenter', 'dragover'].forEach(eventName => {
                        dropzone.addEventListener(eventName, highlight, false);
                    });

                    ['dragleave', 'drop'].forEach(eventName => {
                        dropzone.addEventListener(eventName, unhighlight, false);
                    });

                    function highlight() {
                        dropzone.style.borderColor = 'var(--accent)';
                        dropzone.style.backgroundColor = 'rgba(249, 115, 22, 0.05)';
                    }

                    function unhighlight() {
                        dropzone.style.borderColor = '#A3A3A3';
                        dropzone.style.backgroundColor = 'transparent';
                    }

                    dropzone.addEventListener('drop', handleDrop, false);

                    function handleDrop(e) {
                        const dt = e.dataTransfer;
                        const files = dt.files;
                        fileInput.files = files;

                        if(files.length > 0) {
                            selectedFile.textContent = files[0].name;
                        }
                    }
                </script>
            </body>
            </html>
        ''')

    else:
        return render_template_string('''
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>PixelPatch</title>
                <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
                <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
                <style>
                    ''' + BASE_CSS + '''
                    .header {
                        padding: 16px 0;
                        background-color: var(--bg-secondary);
                        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
                    }

                    .header-container {
                        max-width: 1280px;
                        margin: 0 auto;
                        padding: 0 24px;
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                    }

                    .logo {
                        font-size: 26px;
                        font-weight: 700;
                        color: var(--accent);
                        text-decoration: none;
                        display: flex;
                        align-items: center;
                        gap: 10px;
                    }

                    .nav-links {
                        display: flex;
                        gap: 24px;
                    }

                    .nav-link {
                        color: var(--text-secondary);
                        text-decoration: none;
                        transition: color 0.3s ease;
                        display: flex;
                        align-items: center;
                        gap: 6px;
                        font-weight: 500;
                    }

                    .nav-link:hover, .nav-link.active {
                        color: var(--accent);
                    }

                    .search-container {
                        max-width: 1280px;
                        margin: 32px auto;
                        padding: 0 24px;
                    }

                    .search-form {
                        display: flex;
                        gap: 12px;
                        max-width: 600px;
                        margin: 0 auto;
                    }

                    .search-input {
                        flex: 1;
                        padding: 12px 20px;
                        border-radius: 12px;
                        border: none;
                        background-color: var(--bg-secondary);
                        color: var(--text-primary);
                        font-size: 16px;
                    }

                    .search-btn {
                        background-color: var(--accent);
                        color: var(--text-primary);
                        border: none;
                        border-radius: 12px;
                        padding: 0 28px;
                        cursor: pointer;
                        transition: all 0.3s ease;
                        font-weight: 500;
                    }

                    .search-btn:hover {
                        background-color: var(--accent-hover);
                    }

                    .media-grid {
                        max-width: 1280px;
                        margin: 0 auto;
                        padding: 0 24px;
                        display: grid;
                        grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
                        gap: 32px;
                    }

                    .media-item {
                        background-color: var(--bg-card);
                        border-radius: 16px;
                        overflow: hidden;
                        box-shadow: 0 12px 32px rgba(0, 0, 0, 0.15);
                        transition: transform 0.3s ease;
                    }

                    .media-item:hover {
                        transform: translateY(-6px);
                    }

                    .media-preview {
                        width: 100%;
                        aspect-ratio: 16/9;
                        object-fit: cover;
                    }

                    .media-info {
                        padding: 20px;
                    }

                    .media-title {
                        font-size: 20px;
                        font-weight: 600;
                        margin-bottom: 8px;
                        color: var(--text-primary);
                    }

                    .media-caption {
                        color: var(--text-secondary);
                        font-size: 14px;
                        margin-bottom: 12px;
                    }

                    .media-meta {
                        display: flex;
                        justify-content: space-between;
                        color: var(--text-secondary);
                        font-size: 13px;
                    }

                    .modal {
                        display: none;
                        position: fixed;
                        top: 0;
                        left: 0;
                        width: 100%;
                        height: 100%;
                        background-color: rgba(245, 232, 199, 0.95);
                        z-index: 1000;
                        overflow-y: auto;
                    }

                    .modal-content {
                        background-color: var(--bg-card);
                        margin: 48px auto;
                        max-width: 960px;
                        border-radius: 16px;
                        overflow: hidden;
                        animation: modalFadeIn 0.3s ease;
                    }

                    @keyframes modalFadeIn {
                        from { opacity: 0; transform: translateY(-48px); }
                        to { opacity: 1; transform: translateY(0); }
                    }

                    .modal-header {
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        padding: 20px;
                        border-bottom: 1px solid #A3A3A3;
                    }

                    .modal-title {
                        font-size: 24px;
                        font-weight: 600;
                        color: var(--text-primary);
                    }

                    .modal-close {
                        background: none;
                        border: none;
                        color: var(--text-secondary);
                        font-size: 24px;
                        cursor: pointer;
                        transition: color 0.3s ease;
                    }

                    .modal-close:hover {
                        color: var(--accent);
                    }

                    .modal-body {
                        padding: 24px;
                    }

                    .modal-media {
                        width: 100%;
                        max-height: 540px;
                        object-fit: contain;
                        border-radius: 12px;
                        margin-bottom: 24px;
                    }

                    .modal-caption {
                        color: var(--text-secondary);
                        margin-bottom: 20px;
                        font-size: 15px;
                    }

                    .modal-metadata {
                        display: flex;
                        gap: 16px;
                        color: var(--text-secondary);
                        margin-bottom: 20px;
                        font-size: 14px;
                    }

                    .interaction-bar {
                        display: flex;
                        gap: 20px;
                        margin-top: 20px;
                        padding-top: 20px;
                        border-top: 1px solid #A3A3A3;
                    }

                    .rating-form {
                        display: flex;
                        align-items: center;
                        gap: 12px;
                    }

                    .comments-section {
                        margin-top: 28px;
                    }

                    .comment-form {
                        display: flex;
                        gap: 12px;
                        margin-bottom: 20px;
                    }

                    .comment-input {
                        flex: 1;
                    }

                    .comment {
                        background-color: var(--bg-secondary);
                        padding: 16px;
                        border-radius: 10px;
                        margin-bottom: 16px;
                    }

                    .comment-meta {
                        display: flex;
                        justify-content: space-between;
                        color: var(--text-secondary);
                        font-size: 13px;
                        margin-bottom: 8px;
                    }

                    .avg-rating {
                        display: flex;
                        align-items: center;
                        gap: 6px;
                    }

                    .stars {
                        color: var(--highlight);
                    }

                    .no-results {
                        text-align: center;
                        padding: 64px 0;
                        color: var(--text-secondary);
                    }

                    .flash-message {
                        max-width: 1280px;
                        margin: 24px auto;
                        padding: 14px 20px;
                        border-radius: 10px;
                        color: var(--text-primary);
                    }

                    .flash-success {
                        background-color: var(--success);
                    }

                    .flash-danger {
                        background-color: var(--error);
                    }
                </style>
            </head>
            <body>
                <header class="header">
                    <div class="header-container">
                        <a href="{{ url_for('dashboard') }}" class="logo">
                            <i class="fas fa-th"></i>
                            PixelPatch
                        </a>
                        <nav class="nav-links">
                            <a href="{{ url_for('logout') }}" class="nav-link">
                                <i class="fas fa-sign-out-alt"></i> Logout
                            </a>
                        </nav>
                    </div>
                </header>

                <div class="search-container">
                    {% with messages = get_flashed_messages(with_categories=true) %}
                        {% if messages %}
                            {% for category, message in messages %}
                                <div class="flash-message flash-{{ category }}">
                                    {{ message }}
                                </div>
                            {% endfor %}
                        {% endif %}
                    {% endwith %}

                    <form class="search-form" method="POST" action="{{ url_for('dashboard') }}">
                        <input type="text" name="search_query" placeholder="Search for media..." class="search-input" value="{{ request.form.get('search_query', '') }}">
                        <button type="submit" class="search-btn">Search</button>
                    </form>
                </div>

                <div class="media-grid">
                    {% if media %}
                        {% for item in media %}
                            <div class="media-item" onclick="openModal({{ item.id }})">
                                {% if item.media_type == 'video' %}
                                    <video class="media-preview" poster="{{ item.file_path }}?format=jpg">
                                        <source src="{{ item.file_path }}" type="video/mp4">
                                    </video>
                                {% else %}
                                    <img src="{{ item.file_path }}" alt="{{ item.title }}" class="media-preview">
                                {% endif %}
                                <div class="media-info">
                                    <h3 class="media-title">{{ item.title | e }}</h3>
                                    <p class="media-caption">{{ item.caption | e }}</p>
                                    <div class="media-meta">
                                        <div class="avg-rating">
                                            <i class="fas fa-star stars"></i>
                                            {% set rating_sum = namespace(value=0) %}
                                            {% for rating in item.ratings %}
                                                {% set rating_sum.value = rating_sum.value + rating.value %}
                                            {% endfor %}
                                            {% if item.ratings|length > 0 %}
                                                {{ (rating_sum.value / item.ratings|length) | round(1) }}
                                            {% else %}
                                                No ratings
                                            {% endif %}
                                        </div>
                                        <span>{{ item.comments|length }} comments</span>
                                    </div>
                                </div>
                            </div>

                            <div id="modal-{{ item.id }}" class="modal">
                                <div class="modal-content">
                                    <div class="modal-header">
                                        <h2 class="modal-title">{{ item.title | e }}</h2>
                                        <button class="modal-close" onclick="closeModal({{ item.id }})">×</button>
                                    </div>
                                    <div class="modal-body">
                                        {% if item.media_type == 'video' %}
                                            <video class="modal-media" controls>
                                                <source src="{{ item.file_path }}" type="video/mp4">
                                                Your browser does not support video playback.
                                            </video>
                                        {% else %}
                                            <img src="{{ item.file_path }}" alt="{{ item.title }}" class="modal-media">
                                        {% endif %}
                                        <p class="modal-caption">{{ item.caption | e }}</p>
                                        <div class="modal-metadata">
                                            {% if item.location %}
                                                <div>
                                                    <i class="fas fa-map-marker-alt"></i> {{ item.location | e }}
                                                </div>
                                            {% endif %}
                                            {% if item.people_present %}
                                                <div>
                                                    <i class="fas fa-users"></i> {{ item.people_present | e }}
                                                </div>
                                            {% endif %}
                                            <div>
                                                <i class="fas fa-calendar"></i> {{ item.upload_date.strftime('%B %d, %Y') }}
                                            </div>
                                        </div>

                                        <div class="interaction-bar">
                                            <form class="rating-form" method="POST" action="{{ url_for('rate') }}">
                                                <input type="hidden" name="media_id" value="{{ item.id }}">
                                                <select name="value" required>
                                                    <option value="">Rate this</option>
                                                    <option value="1">1 - Poor</option>
                                                    <option value="2">2 - Fair</option>
                                                    <option value="3">3 - Good</option>
                                                    <option value="4">4 - Very Good</option>
                                                    <option value="5">5 - Excellent</option>
                                                </select>
                                                <button type="submit" class="btn">Rate</button>
                                            </form>
                                        </div>

                                        <div class="comments-section">
                                            <h3>Comments ({{ item.comments|length }})</h3>
                                            <form class="comment-form" method="POST" action="{{ url_for('comment') }}">
                                                <input type="hidden" name="media_id" value="{{ item.id }}">
                                                <input type="text" name="text" placeholder="Add a comment..." class="comment-input" required>
                                                <button type="submit" class="btn">Post</button>
                                            </form>

                                            {% if item.comments %}
                                                {% for comment in item.comments %}
                                                    <div class="comment">
                                                        <div class="comment-meta">
                                                            <span>User #{{ comment.user_id }}</span>
                                                            <span>{{ comment.date.strftime('%B %d, %Y') }}</span>
                                                        </div>
                                                        <p>{{ comment.text | e }}</p>
                                                    </div>
                                                {% endfor %}
                                            {% else %}
                                                <p>No comments yet. Be the first to comment!</p>
                                            {% endif %}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        {% endfor %}
                    {% else %}
                        <div class="no-results">
                            <i class="fas fa-search" style="font-size: 56px; margin-bottom: 24px;"></i>
                            <h2>No results found</h2>
                            <p>Try searching with different keywords</p>
                        </div>
                    {% endif %}
                </div>

                <script>
                    function openModal(id) {
                        document.getElementById('modal-' + id).style.display = "block";
                        document.body.style.overflow = "hidden";
                    }

                    function closeModal(id) {
                        document.getElementById('modal-' + id).style.display = "none";
                        document.body.style.overflow = "auto";
                    }

                    window.onclick = function(event) {
                        if (event.target.classList.contains('modal')) {
                            event.target.style.display = "none";
                            document.body.style.overflow = "auto";
                        }
                    }
                </script>
            </body>
            </html>
        ''', media=media)

@app.route('/upload', methods=['POST'])
def upload():
    if 'user_id' not in session or session['role'] != 'creator':
        return redirect(url_for('login'))

    title = request.form['title']
    caption = request.form['caption']
    location = request.form['location']
    people_present = request.form['people_present']
    file = request.files['file']
    media_type = request.form['media_type']

    if file:
        filename = f"{uuid.uuid4()}_{file.filename}"
        blob_client = blob_service_client.get_blob_client(container=AZURE_CONTAINER_NAME, blob=filename)
        blob_client.upload_blob(file, overwrite=True, content_settings=ContentSettings(
            content_type='video/mp4' if media_type == 'video' else 'image/jpeg'))
        blob_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{AZURE_CONTAINER_NAME}/{filename}"

        media = Media(
            title=title,
            caption=caption,
            location=location,
            people_present=people_present,
            file_path=blob_url,
            media_type=media_type,
            creator_id=session['user_id']
        )
        db.session.add(media)
        db.session.commit()
        flash('Media uploaded successfully!', 'success')
    else:
        flash('No file selected!', 'danger')

    return redirect(url_for('dashboard'))

@app.route('/comment', methods=['POST'])
def comment():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    text = request.form['text']
    media_id = request.form['media_id']

    comment = Comment(
        text=text,
        user_id=session['user_id'],
        media_id=media_id
    )
    db.session.add(comment)
    db.session.commit()
    flash('Comment added!', 'success')

    return redirect(url_for('dashboard'))

@app.route('/rate', methods=['POST'])
def rate():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    media_id = request.form['media_id']
    value = request.form['value']

    existing_rating = Rating.query.filter_by(user_id=session['user_id'], media_id=media_id).first()
    if existing_rating:
        flash('You have already rated this media!', 'warning')
        return redirect(url_for('dashboard'))

    rating = Rating(
        value=value,
        user_id=session['user_id'],
        media_id=media_id
    )
    db.session.add(rating)
    db.session.commit()
    flash('Media rated!', 'success')

    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('role', None)
    session.pop('username', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run()
