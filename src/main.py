from flask import Flask, request, jsonify
import mysql.connector
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import requests
from enum import Enum

app = Flask(__name__)

load_dotenv()
AVATAR_URL = "http://3.84.46.162:5050"
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

class StreakUpdateStatus(Enum):
    INCREASED = 'increased'
    SAME = 'same'
    RESET = 'reset'

def update_streak(cursor, provided_date, last_streak_date, user_id) -> StreakUpdateStatus:
    if provided_date.date() == (last_streak_date + timedelta(days=1)).date():
        cursor.execute("UPDATE Users SET streak_count = streak_count + 1, last_streak = %s WHERE user_id = %s", (provided_date, user_id))
        return StreakUpdateStatus.INCREASED
    elif provided_date.date() == last_streak_date.date():
        # adding to streak count when date same for demo purposes
        cursor.execute("UPDATE Users SET streak_count = streak_count + 1, last_streak = %s WHERE user_id = %s", (provided_date, user_id))
        # cursor.execute("UPDATE Users SET last_streak = %s WHERE user_id = %s", (provided_date, user_id))
        return StreakUpdateStatus.INCREASED # Not same for demo purposes
    else:
        cursor.execute("UPDATE Users SET streak_count = 0, last_streak = %s WHERE user_id = %s", (provided_date, user_id))
        return StreakUpdateStatus.RESET

def call_upgrade_avatar_tier(user_id):
    url = f'{AVATAR_URL}/avatars/upgrade/{user_id}'
    
    response = requests.put(url)
    
    if response.status_code == 200:
        return response.json() 
    else:
        return None
        # raise Exception(f"Failed to upgrade avatar tier: {response.text}")

def call_downgrade_avatar_tier(user_id):
    url = f'{AVATAR_URL}/avatars/downgrade/{user_id}'
    
    response = requests.put(url)
    
    if response.status_code == 200:
        return response.json() 
    else:
        return None
        # raise Exception(f"Failed to downgrade avatar tier: {response.text}")


def upgrade_avatar(user_id: int):
    call_upgrade_avatar_tier(user_id)

def downgrade_avatar(user_id: int):
    call_downgrade_avatar_tier(user_id)

def adjust_avatar_state(user_id: int, update_status: StreakUpdateStatus):
    if update_status == StreakUpdateStatus.INCREASED:
        upgrade_avatar(user_id)
        message = 'User streak increased and avatar upgraded successfully.'
    elif update_status == StreakUpdateStatus.RESET:
        downgrade_avatar(user_id)
        message = 'User streak reset and avatar downgraded successfully.'
    else:
        upgrade_avatar(user_id)
        message = 'User streak remains the same, no avatar change.'
    return message

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
            streak_update_status = update_streak(cursor, provided_date, last_streak_date, user_id)
        
        message = adjust_avatar_state(user_id, streak_update_status)

        return jsonify({'message': message}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)

