from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
import google.generativeai as genai

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database Connection
client = MongoClient("mongodb://localhost:27017/")
db = client.chatbot_db
users_collection = db.users
chats_collection = db.chats

# Configure Gemini API
genai.configure(api_key='your_gemini_api_key')
model = genai.GenerativeModel('gemini-pro')

@app.route('/')
def index():
    if 'user' in session:
        return render_template('index.html', username=session['user'])
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = users_collection.find_one({"username": username, "password": password})
        
        if user:
            session['user'] = username
            return redirect(url_for('index'))
        else:
            return "Invalid Credentials! Try again."
    return render_template('login.html'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        existing_user = users_collection.find_one({"username": username})
        if existing_user:
            return "Username already exists! Try a different one."
        
        users_collection.insert_one({"username": username, "email": email, "password": password})
        return redirect(url_for('login'))
    
    return render_template('signup.html'))

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
    
    # Get response from Gemini
    response = model.generate_content(user_message)
    
    # Save chat to database
    chat_data = {
        "username": session['user'],
        "user_message": user_message,
        "bot_message": response.text
    }
    result = chats_collection.insert_one(chat_data)
    
    return jsonify({"response": response.text, "chat_id": str(result.inserted_id)})

@app.route('/chat/history', methods=['GET'])
def chat_history():
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    chats = list(chats_collection.find({"username": session['user']}, {"_id": 1, "user_message": 1, "bot_message": 1}))
    for chat in chats:
        chat['_id'] = str(chat['_id'])
    
    return jsonify(chats)

@app.route('/chat/delete/<chat_id>', methods=['DELETE'])
def delete_chat(chat_id):
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    result = chats_collection.delete_one({"_id": ObjectId(chat_id), "username": session['user']})
    
    if result.deleted_count:
        return jsonify({"success": True})
    else:
        return jsonify({"error": "Chat not found"}), 404

if __name__ == '__main__':
    app.run(debug=True)