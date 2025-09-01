from flask import Flask, render_template, request, jsonify, redirect, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import json
from flask_migrate import Migrate

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///attendance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Add after db initialization
migrate = Migrate(app, db)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    attendances = db.relationship('Attendance', backref='user', lazy=True)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    location = db.Column(db.String(200), nullable=False)
    notes = db.Column(db.String(500), default='')

# Routes
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect('/login')
    
    user = db.session.get(User, session['user_id'])
    
    # Handle case where user doesn't exist in database
    if user is None:
        session.clear()  # Clear invalid session
        return redirect('/login')
    
    return render_template('index.html', username=user.username, is_admin=user.is_admin)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            return render_template('login.html', error='Username and password are required')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            return redirect('/')
        
        return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/admin/create_user', methods=['POST'])
def create_user():
    if not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 403
    
    username = request.form.get('username')
    password = request.form.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400
    
    hashed_password = generate_password_hash(password)
    
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'User already exists'}), 400
    
    new_user = User(username=username, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({'message': 'User created successfully'})

@app.route('/mark_attendance', methods=['POST'])
def mark_attendance():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    data = request.get_json()
    location = data.get('location', 'Unknown')
    notes = data.get('notes', '')
    
    new_attendance = Attendance(
        user_id=session['user_id'],
        location=location,
        notes=notes
    )
    db.session.add(new_attendance)
    db.session.commit()
    
    return jsonify({'message': 'Attendance marked successfully'})

@app.route('/get_attendance')
def get_attendance():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    user_id = session['user_id']
    if session.get('is_admin') and request.args.get('user_id'):
        user_id = request.args.get('user_id')
    
    attendances = Attendance.query.filter_by(user_id=user_id).order_by(Attendance.timestamp.desc()).all()
    
    result = []
    for att in attendances:
        result.append({
            'timestamp': att.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'location': att.location,
            'notes': att.notes
        })
    
    return jsonify(result)

@app.route('/get_all_attendance')
def get_all_attendance():
    if not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Get date range filters if provided
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Base query
    query = Attendance.query.join(User).order_by(Attendance.timestamp.desc())
    
    # Apply date filters if provided
    if start_date:
        start_datetime = datetime.datetime.strptime(start_date, '%Y-%m-%d')
        query = query.filter(Attendance.timestamp >= start_datetime)
    
    if end_date:
        end_datetime = datetime.datetime.strptime(end_date, '%Y-%m-%d') + datetime.timedelta(days=1)
        query = query.filter(Attendance.timestamp <= end_datetime)
    
    attendances = query.all()
    
    result = []
    for att in attendances:
        result.append({
            'id': att.id,
            'user_id': att.user_id,
            'username': att.user.username,
            'timestamp': att.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'location': att.location,
            'notes': att.notes
        })
    
    return jsonify(result)

@app.route('/get_users')
def get_users():
    if not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 403
    
    users = User.query.filter_by(is_admin=False).all()
    result = [{'id': u.id, 'username': u.username} for u in users]
    return jsonify(result)

@app.route('/get_current_user')
def get_current_user():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    user = db.session.get(User, session['user_id'])
    if user is None:
        session.clear()
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'id': user.id,
        'username': user.username,
        'is_admin': user.is_admin
    })

@app.route('/admin/delete_attendance/<int:attendance_id>', methods=['DELETE'])
def delete_attendance(attendance_id):
    if not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 403
    
    attendance = Attendance.query.get(attendance_id)
    if not attendance:
        return jsonify({'error': 'Attendance record not found'}), 404
    
    db.session.delete(attendance)
    db.session.commit()
    
    return jsonify({'message': 'Attendance record deleted successfully'})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Create admin user if not exists
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                password=generate_password_hash('admin11123'),
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
    
    app.run(debug=True)
