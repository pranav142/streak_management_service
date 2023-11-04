from flask import Flask, request, jsonify
import mysql.connector
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

app = Flask(__name__)

load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME')
}

class Database:
    def __enter__(self):
        self.conn = mysql.connector.connect(**DB_CONFIG)
        self.cursor = self.conn.cursor()
        return self.cursor

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.commit()
        self.cursor.close()
        self.conn.close()

def update_streak(cursor, provided_date, last_streak_date, user_id):
    if provided_date.date() == (last_streak_date + timedelta(days=1)).date():
        cursor.execute("UPDATE Users SET streak_count = streak_count + 1, last_streak = %s WHERE user_id = %s", (provided_date, user_id))
    elif provided_date.date() == last_streak_date.date():
        cursor.execute("UPDATE Users SET last_streak = %s WHERE user_id = %s", (provided_date, user_id))
    else:
        cursor.execute("UPDATE Users SET streak_count = 0, last_streak = %s WHERE user_id = %s", (provided_date, user_id))


def get_last_streak_date(cursor, user_id):
    cursor.execute(f"SELECT last_streak FROM Users WHERE user_id = {user_id}")
    result = cursor.fetchone()
    if not result:
        return None
    return result[0]

@app.route('/upgrade/<user_id>', methods=['POST'])
def upgrade(user_id):
    try:
        timestamp = request.json.get('timestamp')
        if not timestamp:
            return jsonify({'error': 'Timestamp not provided'}), 400
        
        provided_date = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")

        with Database() as cursor:
            last_streak_date = get_last_streak_date(cursor, user_id)
            if not last_streak_date:
                return jsonify({'error': 'User not found'}), 404
            update_streak(cursor, provided_date, last_streak_date, user_id)

        return jsonify({'message': 'User streak updated successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)

