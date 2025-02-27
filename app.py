from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
import google.generativeai as genai
from flask_cors import CORS
import bcrypt
import logging

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SESSION_COOKIE_SECURE'] = True  # Ensure cookies are only sent over HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent client-side script access to the cookie
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # Session expires after 1 hour

# Enable CORS for all routes
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database Connection
client = MongoClient("mongodb://localhost:27017/")
db = client.chatbot_db
users_collection = db.users
chats_collection = db.chats

# Configure Gemini API
genai.configure(api_key='AIzaSyBpU9tt9KmP0Oi8fkLufx0mwV8Tts-uQ-g')
model = genai.GenerativeModel('gemini-2.0-flash')

@app.route('/')
def index():
    if 'user' in session:
        return render_template('index.html', username=session['user'])
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            return "Username and password are required.", 400
        
        user = users_collection.find_one({"username": username})
        
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            session['user'] = username
            return redirect(url_for('index'))
        else:
            return "Invalid Credentials! Try again.", 401
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not username or not email or not password:
            return "All fields are required.", 400
        
        existing_user = users_collection.find_one({"username": username})
        if existing_user:
            return "Username already exists! Try a different one.", 400
        
        # Hash the password before storing it
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        # Store the hashed password as a string
        users_collection.insert_one({
            "username": username,
            "email": email,
            "password": hashed_password.decode('utf-8')  # Convert bytes to string
        })
        return redirect(url_for('login'))
    
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/chat', methods=['POST'])
def chat():
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    user_message = request.json.get('message')
    if not user_message:
        return jsonify({"error": "No message provided"}), 400
    
    try:
        # Get response from Gemini
        response = model.generate_content(user_message)
        
        # Save chat to database
        chat_data = {
            "username": session['user'],
            "user_message": user_message,
            "bot_message": response.text
        }
        result = chats_collection.insert_one(chat_data)
        
        return jsonify({
            "response": response.text,
            "chat_id": str(result.inserted_id)
        })
    except Exception as e:
        logger.error(f"Error in Gemini API: {e}")
        return jsonify({"error": "Failed to generate response"}), 500

@app.route('/chat/history', methods=['GET'])
def chat_history():
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    chats = list(chats_collection.find({"username": session['user']}, {"_id": 1, "user_message": 1, "bot_message": 1}))
    for chat in chats:
        chat['_id'] = str(chat['_id'])
    
    return jsonify(chats)

@app.route('/chat/clear', methods=['POST'])
def clear_chat():
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        # Delete all chats for the current user
        result = chats_collection.delete_many({"username": session['user']})
        
        if result.deleted_count:
            return jsonify({"success": True})
        else:
            return jsonify({"error": "No chats found"}), 404
    except Exception as e:
        logger.error(f"Error clearing chat: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/chat/delete/<chat_id>', methods=['DELETE'])
def delete_chat(chat_id):
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        result = chats_collection.delete_one({"_id": ObjectId(chat_id), "username": session['user']})
        
        if result.deleted_count:
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Chat not found"}), 404
    except Exception as e:
        logger.error(f"Error deleting chat: {e}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(debug=True)