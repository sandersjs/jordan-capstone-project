# app.py (no TinyMCE)
from flask import (
    Flask, render_template, request, redirect, url_for, flash,
    session
)
import json
import os
from datetime import datetime
from werkzeug.security import check_password_hash
from functools import wraps
from dotenv import load_dotenv
import uuid
import nh3
import re
from html import unescape
from flask import g

# Load .env
load_dotenv()
PASSWORD_HASH = os.getenv('PASSWORD_HASH')

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'change-this-in-production-2025!!')

DATA_FILE = 'data.json'
UPLOAD_FOLDER = 'static/project_images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ------------------------------------------------------------------
# Data helpers
# ------------------------------------------------------------------
DEFAULT_DATA = {
    "config": {
        "name": "Student Name",
        "course_number": "CIS Python Programming",
        "course_description": "Describe the Course",
        "profile_info": "Tell us something about yourself.",
        "linkedin": "https://www.linkedin.com/in/britt-rios-ellis-58597119/",
        "theme": "quartz",
        "profile_image": ""
    },
    "projects": []
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_data():
    if not os.path.exists(DATA_FILE):
        save_data(DEFAULT_DATA)
        return DEFAULT_DATA
    try:
        with open(DATA_FILE, 'r') as f:
            content = f.read().strip()
            return json.loads(content) if content else DEFAULT_DATA
    except json.JSONDecodeError:
        print("data.json corrupted. Resetting...")
        save_data(DEFAULT_DATA)
        return DEFAULT_DATA

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# ------------------------------------------------------------------
# Context Processor (now uses data.json for global config injection)
# ------------------------------------------------------------------
@app.context_processor
def inject_config():
    data = load_data()
    config = data['config'].copy()  # Avoid mutating the loaded data
    # Ensure defaults (fallback if DEFAULT_DATA changes)
    config.setdefault('theme', 'quartz')
    config.setdefault('name', 'Student Name')
    config.setdefault('course_number', 'CIS Python Programming')
    config.setdefault('course_description', 'Tell us something about yourself.')
    config.setdefault('profile_info', '')
    config.setdefault('linkedin', 'https://www.linkedin.com/in/britt-rios-ellis-58597119/')
    config.setdefault('profile_image', '')
    return dict(config=config)

# ------------------------------------------------------------------
# Sanitization + text length
# ------------------------------------------------------------------
allowed_tags = {
    'p', 'b', 'i', 'u', 'em', 'strong', 'a', 'ul', 'ol', 'li', 'br',
    'h1', 'h2', 'h3', 'blockquote', 'code', 'pre', 'div', 'span'
}
allowed_attributes = {
    '*': {'class', 'style'},
    'a': {'href', 'title', 'target'},
    'img': {'src', 'alt', 'width', 'height'}
}

def clean_description(html):
    if html is None:
        html = ""
    return nh3.clean(str(html), tags=allowed_tags, attributes=allowed_attributes, strip_comments=False)

def get_text_length(html_content):
    if not html_content:
        return 0
    text = re.sub('<[^<]+?>', '', html_content)
    text = unescape(text)
    return len(text.strip())

# ------------------------------------------------------------------
# Authentication decorator
# ------------------------------------------------------------------
def password_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------
@app.route('/')
def index():
    data = load_data()
    return render_template('index.html', projects=data['projects'])  # config now from context processor

@app.route('/project/<int:project_id>')
def project_detail(project_id):
    data = load_data()
    project = next((p for p in data['projects'] if p['id'] == project_id), None)
    if not project:
        flash('Project not found!', 'danger')
        return redirect(url_for('index'))
    return render_template('project_detail.html', project=project)  # config from processor

# --------------------- LOGIN ---------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('authenticated'):
        return redirect(url_for('index'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        if PASSWORD_HASH and check_password_hash(PASSWORD_HASH, password):
            session['authenticated'] = True
            flash('Login successful!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Incorrect password.', 'danger')
    return render_template('login.html')  # config from processor (if needed)

@app.route('/logout')
def logout():
    session.pop('authenticated', None)
    flash('Logged out successfully!', 'info')
    return redirect(url_for('index'))

# --------------------- CONFIG ---------------------
@app.route('/config', methods=['GET', 'POST'])
@password_required
def config():
    data = load_data()
    if request.method == 'POST':
        # Handle profile image (keep existing if no new provided)
        current_image = data['config'].get('profile_image', '')
        new_image_path = None
        if 'image_file' in request.files and request.files['image_file'].filename:
            file = request.files['image_file']
            if file and allowed_file(file.filename):
                ext = os.path.splitext(file.filename)[1]
                filename = f"{uuid.uuid4()}{ext}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                new_image_path = url_for('static', filename=f'project_images/{filename}')
        elif request.form.get('profile_image_url'):
            new_image_path = request.form.get('profile_image_url').strip()

        image_path = new_image_path if new_image_path is not None else current_image

        # Other fields
        data['config'].update({
            'name': request.form['name'].strip(),
            'course_number': request.form['course_number'].strip(),
            'course_description': request.form['course_description'].strip(),
            'profile_info': request.form['profile_info'].strip(),
            'linkedin': request.form['linkedin'].strip(),
            'theme': request.form['theme'].strip(),
            'profile_image': image_path
        })

        # Validation for profile image
        if not image_path:
            flash('Profile image is required!', 'danger')
            return redirect(request.url)

        save_data(data)
        flash('Configuration updated!', 'success')
        return redirect(url_for('index'))
    return render_template('config.html')  # config from processor (pre-fills form)

# --------------------- ADD PROJECT (single route) ---------------------
@app.route('/project/add', methods=['GET', 'POST'])
@password_required
def add_project():
    data = load_data()
    if request.method == 'POST':
        # Image (file or URL)
        image_path = None
        if 'image_file' in request.files and request.files['image_file'].filename:
            file = request.files['image_file']
            if file and allowed_file(file.filename):
                ext = os.path.splitext(file.filename)[1]
                filename = f"{uuid.uuid4()}{ext}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_path = url_for('static', filename=f'project_images/{filename}')
        elif request.form.get('image_url'):
            image_path = request.form.get('image_url').strip()

        if not image_path:
            flash('Project image is required!', 'danger')
            return redirect(request.url)

        # Fields
        title = request.form.get('title', '').strip()
        website_url = request.form.get('website_url', '').strip()
        github_url = request.form.get('github_url', '').strip()
        raw_description = request.form.get('description') or ''
        # Convert newlines to <br> for line breaks (no trailing \n to avoid accumulation)
        raw_description = raw_description.replace('\n', '<br>')
        safe_description = clean_description(raw_description)

        # Validation
        if not title:
            flash('Title is required!', 'danger')
        elif not website_url:
            flash('Website URL is required!', 'danger')
        elif not github_url:
            flash('GitHub URL is required!', 'danger')
        elif get_text_length(safe_description) < 100:
            flash('Description must be at least 100 characters long!', 'danger')
        else:
            project = {
                "id": int(datetime.now().timestamp() * 1000),
                "image": image_path,
                "title": title,
                "website_url": website_url,
                "github_url": github_url,
                "description": safe_description
            }
            data['projects'].append(project)
            save_data(data)
            flash('Project added successfully!', 'success')
            return redirect(url_for('index'))

        return redirect(request.url)

    return render_template('add_project.html')  # config from processor

# --------------------- EDIT PROJECT ---------------------
@app.route('/project/edit/<int:project_id>', methods=['GET', 'POST'])
@password_required
def edit_project(project_id):
    data = load_data()
    project = next((p for p in data['projects'] if p['id'] == project_id), None)
    if not project:
        flash('Project not found!', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        image_path = project['image']
        if 'image_file' in request.files and request.files['image_file'].filename:
            file = request.files['image_file']
            if file and allowed_file(file.filename):
                ext = os.path.splitext(file.filename)[1]
                filename = f"{uuid.uuid4()}{ext}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_path = url_for('static', filename=f'project_images/{filename}')
        elif request.form.get('image_url'):
            image_path = request.form.get('image_url').strip()

        title = request.form.get('title', '').strip()
        website_url = request.form.get('website_url', '').strip()
        github_url = request.form.get('github_url', '').strip()
        raw_description = (request.form.get('description') or '').strip()
        # 1. Normalize Windows line endings (\r\n) to standard (\n)
        raw_description = raw_description.replace('\r\n', '\n')
        # 2. Convert standard newlines to <br>
        raw_description = raw_description.replace('\n', '<br>')
        safe_description = clean_description(raw_description)

        if not title:
            flash('Title is required!', 'danger')
        elif not website_url:
            flash('Website URL is required!', 'danger')
        elif not github_url:
            flash('GitHub URL is required!', 'danger')
        elif get_text_length(safe_description) < 100:
            flash('Description must be at least 100 characters long!', 'danger')
        else:
            project.update({
                'image': image_path,
                'title': title,
                'website_url': website_url,
                'github_url': github_url,
                'description': safe_description
            })
            save_data(data)
            flash('Project updated successfully!', 'success')
            return redirect(url_for('index'))

        return redirect(request.url)

    # For GET: Prepare editable description (convert <br> back to \n, handling legacy <br>\n)
    plain_description = project['description']
    # Cleanup: Normalize existing <br> tags combined with newlines
    plain_description = plain_description.replace('<br>\r\n', '<br>')
    plain_description = plain_description.replace('<br>\n', '<br>')

    # Convert all <br> variants to \n for the editor
    plain_description = re.sub(r'<br\s*/?\s*>', '\n', plain_description, flags=re.IGNORECASE)
    return render_template('edit_project.html', project=project, plain_description=plain_description)  # config from processor

# --------------------- DELETE PROJECT ---------------------
@app.route('/project/delete/<int:project_id>', methods=['POST'])
@password_required
def delete_project(project_id):
    data = load_data()
    data['projects'] = [p for p in data['projects'] if p['id'] != project_id]
    save_data(data)
    flash('Project deleted!', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)