from datetime import datetime
from flask_socketio import join_room, leave_room, emit
from extensions import socketio, db
from models import ChatMessage

@socketio.on('join')
def on_join(data):
    room = data['room']
    join_room(room)

@socketio.on('leave')
def on_leave(data):
    room = data['room']
    leave_room(room)

@socketio.on('message')
def handle_message(data):
    room = data['room']
    message = data['message']
    sender_id = data['sender_id']
    receiver_id = data['receiver_id']
    
    # Save message to database
    chat_message = ChatMessage(
        sender_id=sender_id,
        receiver_id=receiver_id,
        content=message,
        chat_room=room,
        timestamp=datetime.utcnow()
    )
    db.session.add(chat_message)
    db.session.commit()
    
    # Broadcast message to room
    emit('message', {
        'message': message,
        'sender_id': sender_id,
        'timestamp': chat_message.timestamp.strftime('%H:%M')
    }, room=room)