from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, join_room, leave_room, send
from collections import defaultdict
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mysecret'
socketio = SocketIO(app, async_mode="eventlet", cors_allowed_origins="*")

# Admin credentials (should be securely stored in production)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "password"  # Change this to something secure!

# Room names and descriptions
rooms = ["Rape Punishments", "Country Politics", "LGBTQ is Shit"]
descriptions = {
    "Rape Punishments": "An open uncensored stage to discuss what should be done as punishment for rapes.",
    "Country Politics": "An open platform to discuss hot politics of any country without censorship.",
    "LGBTQ is Shit": "An uncensored platform to discuss the crazy shit people who represent themselves as batshit crazy things and such related stuff."
}

# List of banned IP addresses
banned_ips = []

# Dictionary to track connected users {ip: [aliases]}
connected_users = {}

# Dictionary to track recent messages {ip: [(alias, message, timestamp)]}
recent_activity = defaultdict(list)

def get_user_ip():
    """Helper function to get the user's IP address."""
    if request.environ.get('HTTP_X_FORWARDED_FOR') is not None:
        return request.environ['HTTP_X_FORWARDED_FOR'].split(',')[0]
    else:
        return request.environ['REMOTE_ADDR']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/select_room', methods=['GET', 'POST'])
def select_room():
    alias = request.form.get('alias') if request.method == 'POST' else request.args.get('alias')
    
    # Get the user's IP address
    user_ip = get_user_ip()
    
    # Check if the user's IP is banned
    if user_ip in banned_ips:
        return render_template('banned.html', alias=alias, ip=user_ip)

    if alias:
        # Add alias to the connected users list for the IP
        if user_ip in connected_users:
            if alias not in connected_users[user_ip]:
                connected_users[user_ip].append(alias)
        else:
            connected_users[user_ip] = [alias]
        return render_template('select_room.html', alias=alias, rooms=rooms, descriptions=descriptions)
    return redirect(url_for('index'))

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    alias = request.form.get('alias') if request.method == 'POST' else request.args.get('alias')
    room = request.form.get('room') if request.method == 'POST' else request.args.get('room')
    
    # Get the user's IP address
    user_ip = get_user_ip()
    
    # Check if the user's IP is banned
    if user_ip in banned_ips:
        return render_template('banned.html', alias=alias, ip=user_ip)
    
    if alias and room:
        return render_template('chat.html', alias=alias, room=room)
    return redirect(url_for('index'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('admin_login.html', error="Invalid credentials")
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        ip_to_manage = request.form.get('ip')
        action = request.form.get('action')
        
        if action == "ban" and ip_to_manage not in banned_ips:
            banned_ips.append(ip_to_manage)
        elif action == "unban" and ip_to_manage in banned_ips:
            banned_ips.remove(ip_to_manage)
    
    return render_template('admin_dashboard.html', connected_users=connected_users, banned_ips=banned_ips, recent_activity=recent_activity)

@socketio.on('join')
def handle_join(data):
    alias = data['alias']
    room = data['room']
    
    # Get the user's IP address
    user_ip = request.remote_addr
    
    # Prevent joining if the user's IP is banned
    if user_ip in banned_ips:
        return

    join_room(room)
    send(f'{alias} has joined the {room} room.', to=room)

@socketio.on('leave')
def handle_leave(data):
    alias = data['alias']
    room = data['room']
    user_ip = get_user_ip()
    if user_ip in connected_users and alias in connected_users[user_ip]:
        connected_users[user_ip].remove(alias)
        if not connected_users[user_ip]:  # Remove the IP if no aliases are left
            del connected_users[user_ip]
    leave_room(room)
    send(f'{alias} has left the {room} room.', to=room)

@socketio.on('chat_message')
def handle_chat_message(data):
    alias = data["alias"]
    room = data["room"]
    message = data["message"]
    send(f"{alias}: {message}", to=room)
    
    # Get the user's IP address
    user_ip = request.remote_addr
    
    # Prevent sending messages if the user's IP is banned
    if user_ip in banned_ips:
        return
    
    # Log the message with timestamp
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    recent_activity[user_ip].append((alias, message, timestamp))
    
    # Keep only the last 10 messages per IP to avoid clutter
    if len(recent_activity[user_ip]) > 10:
        recent_activity[user_ip] = recent_activity[user_ip][-10:]
    
    send(f'{alias}: {message}', to=room)

if __name__ == '__main__':
    socketio.run(app, debug=True)




