from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO, join_room, leave_room, send

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mysecret'
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*")  # Ensure CORS is allowed if accessing from other domains

# Updated room names and descriptions
rooms = ["Rape Punishments", "Country Politics", "LGBTQ is Shit"]
descriptions = {
    "Rape Punishments": "An open uncensored stage to discuss what should be done as punishment for rapes.",
    "Country Politics": "An open platform to discuss hot politics of any country without censorship.",
    "LGBTQ is Shit": "An uncensored platform to discuss the crazy shit people who represent themselves as batshit crazy things and such related stuff."
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/select_room', methods=['GET', 'POST'])
def select_room():
    if request.method == 'POST':
        alias = request.form.get('alias')
    else:
        alias = request.args.get('alias')
    
    if alias:
        return render_template('select_room.html', alias=alias, rooms=rooms, descriptions=descriptions)
    return redirect(url_for('index'))


@app.route('/chat', methods=['POST'])
def chat():
    alias = request.form.get('alias')
    room = request.form.get('room')
    if alias and room:
        return render_template('chat.html', alias=alias, room=room)
    return redirect(url_for('index'))

@socketio.on('join')
def handle_join(data):
    alias = data['alias']
    room = data['room']
    join_room(room)
    send(f'{alias} has joined the {room} room.', to=room)

@socketio.on('leave')
def handle_leave(data):
    alias = data['alias']
    room = data['room']
    leave_room(room)
    send(f'{alias} has left the {room} room.', to=room)

@socketio.on('message')
def handle_message(data):
    alias = data['alias']
    room = data['room']
    message = data['message']
    send(f'{alias}: {message}', to=room)

if __name__ == '__main__':
    socketio.run(app, debug=True)
