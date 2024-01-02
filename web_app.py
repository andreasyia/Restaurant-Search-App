from flask import Flask, render_template, request, g
from collections import Counter
import requests
import sqlite3

app = Flask(__name__)
DATABASE = 'search_queries.db'

# Function to get the SQLite connection
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

# Create table if it doesn't exist or modify table structure
def setup_database():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS search_queries 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      ip_address TEXT, 
                      city TEXT,
                      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    # Add the 'city' column if it doesn't exist
    cursor.execute('''PRAGMA table_info(search_queries)''')
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]
    if 'city' not in column_names:
        cursor.execute('''ALTER TABLE search_queries ADD COLUMN city TEXT''')

    db.commit()

# Function to fetch city coordinates using Google Geocoding API
def get_coordinates(city):
 
    api_key = 'AIzaSyBnBdyUht_amxr-OLBOzQ8MY0lvslGdHy8'
    endpoint = 'https://maps.googleapis.com/maps/api/geocode/json'

    params = {
        'address': city,
        'key': api_key
    }

    response = requests.get(endpoint, params=params)
    if response.status_code == 200:
        data = response.json()
        if data['status'] == 'OK' and len(data['results']) > 0:
            location = data['results'][0]['geometry']['location']
            return location.get('lat'), location.get('lng')
    return None, None

# Function to fetch restaurant data using Google Places API
def fetch_google_places(city):
    lat, lng = get_coordinates(city)
    if lat is None or lng is None:
        return []

    api_key = 'AIzaSyDXZZz_kqN5rM_x1nSE7SyyVzmRX4n7NVg'
    endpoint = 'https://maps.googleapis.com/maps/api/place/nearbysearch/json'
    
    params = {
        'key': api_key,
        'location': f"{lat},{lng}",
        'radius': 5000,  
        'type': 'restaurant'  
    }

    response = requests.get(endpoint, params=params)
    if response.status_code == 200:
        return response.json().get('results', [])
    else:
        return []

# Run setup_database function before the first request
@app.before_request
def before_request():
    setup_database()

# Close the database connection at the end of each request
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        city = request.form.get('city')
        if not city:
            return render_template('index.html', error="Please enter a city.")

        ip_address = request.remote_addr

        # Save search query in database
        db = get_db()
        cursor = db.cursor()
        cursor.execute("INSERT INTO search_queries (ip_address, city) VALUES (?, ?)", (ip_address, city))
        db.commit()

        # Google Places API to fetch restaurant data based on the city
        restaurant_data = fetch_google_places(city)

        return render_template('index.html', restaurants=restaurant_data, city=city)

    return render_template('index.html')

# Admin page route to view search query data and counts
@app.route('/admin', methods = ['GET'])
def admin():
    db = get_db()
    cursor = db.cursor()

    # Fetch all search queries
    cursor.execute("SELECT city FROM search_queries")
    rows = cursor.fetchall()

    # Count the frequency of each query
    query_counts = Counter([row[0] for row in rows])

    # Convert query counts to a list of tuples for easy iteration in the template
    query_data = [(query, count)for query, count in query_counts.items()]

    return render_template('admin.html', query_data = query_data)

if __name__ == '__main__':
    app.run(debug=True)
