from flask import Flask, render_template, request, redirect, url_for, session
from pymongo import MongoClient
from bson.objectid import ObjectId

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database Connection
client = MongoClient("mongodb://localhost:27017/")
db = client.chatbot_db
users_collection = db.users

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
    return render_template('login.html')

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
    
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
