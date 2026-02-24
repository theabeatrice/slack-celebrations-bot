import os
import json
import random
from datetime import datetime, date, timedelta
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import schedule
import time
import threading

# Initialize the Slack app
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# File to store birthdays and configuration
BIRTHDAYS_FILE = "birthdays.json"
CONFIG_FILE = "config.json"

# Default configuration
DEFAULT_CONFIG = {
    "announcement_channel": None,  # Set with /setbirthdaychannel
    "announcement_time": "09:00",  # 9 AM
    "reminder_days": 3,  # Remind 3 days before
    "giphy_enabled": True
}

# Fun birthday messages
BIRTHDAY_MESSAGES = [
    "🎉 Happy Birthday {name}! Hope your day is as amazing as you are! 🎂",
    "🎈 It's {name}'s special day! Wishing you all the best! 🎊",
    "🎂 Another trip around the sun for {name}! Have a fantastic birthday! ☀️",
    "🎁 Hip hip hooray! It's {name}'s birthday today! 🎉",
    "🌟 Sending birthday wishes to the wonderful {name}! Have an incredible day! 🎈",
    "🎊 {name} is leveling up today! Happy Birthday! 🎮",
    "🎵 Happy Birthday to you, happy birthday to you, happy birthday dear {name}! 🎵",
    "🍰 Time to celebrate {name}! May your birthday be filled with joy and cake! 🎂"
]

# Giphy birthday GIF search terms (family-friendly)
GIPHY_SEARCH_TERMS = [
    "happy birthday celebration",
    "birthday cake",
    "birthday party",
    "birthday balloons",
    "happy birthday confetti"
]

def load_birthdays():
    """Load birthdays from JSON file"""
    try:
        with open(BIRTHDAYS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_birthdays(birthdays):
    """Save birthdays to JSON file"""
    with open(BIRTHDAYS_FILE, 'w') as f:
        json.dump(birthdays, f, indent=2)

def load_config():
    """Load configuration from JSON file"""
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return DEFAULT_CONFIG.copy()

def save_config(config):
    """Save configuration to JSON file"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def get_random_birthday_gif():
    """Get a random birthday GIF from Giphy"""
    try:
        import requests
        # Using Giphy's public beta key (rate limited, but works for demo)
        # For production, get your own key at developers.giphy.com
        api_key = "dc6zaTOxFJmzC"  # Giphy public beta key
        search_term = random.choice(GIPHY_SEARCH_TERMS)
        
        url = f"https://api.giphy.com/v1/gifs/search?api_key={api_key}&q={search_term}&limit=20&rating=g"
        response = requests.get(url)
        data = response.json()
        
        if data.get('data'):
            gif = random.choice(data['data'])
            return gif['images']['original']['url']
    except:
        pass
    return None

def check_birthdays_today():
    """Check if anyone has a birthday today"""
    birthdays = load_birthdays()
    today = date.today()
    today_str = today.strftime("%m-%d")
    
    birthday_people = []
    for user_id, birthday_data in birthdays.items():
        if birthday_data.get("date", "").endswith(today_str):
            birthday_people.append({
                "user_id": user_id,
                "name": birthday_data.get("name", "someone")
            })
    
    return birthday_people

def check_upcoming_birthdays(days=3):
    """Check if anyone has a birthday in N days"""
    birthdays = load_birthdays()
    target_date = date.today() + timedelta(days=days)
    target_str = target_date.strftime("%m-%d")
    
    upcoming_people = []
    for user_id, birthday_data in birthdays.items():
        if birthday_data.get("date", "") == target_str:
            upcoming_people.append({
                "user_id": user_id,
                "name": birthday_data.get("name", "someone"),
                "date": target_date
            })
    
    return upcoming_people

def post_birthday_announcement():
    """Automatically post birthday announcements"""
    config = load_config()
    channel = config.get("announcement_channel")
    
    if not channel:
        print("No announcement channel set. Use /setbirthdaychannel to configure.")
        return
    
    # Check today's birthdays
    birthday_people = check_birthdays_today()
    
    if birthday_people:
        for person in birthday_people:
            message = random.choice(BIRTHDAY_MESSAGES).format(name=f"<@{person['user_id']}>")
            
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": message
                    }
                }
            ]
            
            # Try to add a GIF if enabled
            if config.get("giphy_enabled", True):
                gif_url = get_random_birthday_gif()
                if gif_url:
                    blocks.append({
                        "type": "image",
                        "image_url": gif_url,
                        "alt_text": "Birthday celebration"
                    })
            
            try:
                app.client.chat_postMessage(
                    channel=channel,
                    text=message,
                    blocks=blocks
                )
                print(f"Posted birthday announcement for {person['name']}")
            except Exception as e:
                print(f"Error posting birthday announcement: {e}")

def post_birthday_reminder():
    """Post reminders for upcoming birthdays"""
    config = load_config()
    channel = config.get("announcement_channel")
    reminder_days = config.get("reminder_days", 3)
    
    if not channel:
        return
    
    upcoming = check_upcoming_birthdays(days=reminder_days)
    
    if upcoming:
        for person in upcoming:
            day_name = person['date'].strftime("%A")
            message = f"📢 Reminder: <@{person['user_id']}>'s birthday is coming up on {day_name}! 🎂"
            
            try:
                app.client.chat_postMessage(
                    channel=channel,
                    text=message
                )
                print(f"Posted birthday reminder for {person['name']}")
            except Exception as e:
                print(f"Error posting reminder: {e}")

def schedule_checker():
    """Background thread to check scheduled tasks"""
    schedule.every().day.at("09:00").do(post_birthday_announcement)
    schedule.every().day.at("09:00").do(post_birthday_reminder)
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

# Command to set the announcement channel
@app.command("/setbirthdaychannel")
def handle_set_channel(ack, command, say):
    """Set the channel for birthday announcements"""
    ack()
    
    channel_id = command['channel_id']
    config = load_config()
    config['announcement_channel'] = channel_id
    save_config(config)
    
    say(f"✅ Birthday announcements will be posted in this channel! I'll check for birthdays every day at 9 AM.")

# Command to add a birthday
@app.command("/addbirthday")
def handle_add_birthday(ack, command, say):
    """Handle the /addbirthday command"""
    ack()
    
    # Parse the command text (expected format: @user MM-DD or MM-DD for self)
    text = command['text'].strip()
    
    if not text:
        say("Please provide a birthday date! Format: `/addbirthday MM-DD` or `/addbirthday @user MM-DD`")
        return
    
    parts = text.split()
    birthdays = load_birthdays()
    
    # Check if mentioning another user
    if parts[0].startswith('<@'):
        if len(parts) < 2:
            say("Please provide a date after the user mention! Format: `/addbirthday @user MM-DD`")
            return
        
        user_id = parts[0].strip('<@>|')
        birthday_date = parts[1]
    else:
        # Adding own birthday
        user_id = command['user_id']
        birthday_date = parts[0]
    
    # Validate date format
    try:
        # Use a leap year to allow 02-29
        datetime.strptime(f"2024-{birthday_date}", "%Y-%m-%d")
    except ValueError:
        say("Invalid date format! Please use MM-DD (e.g., 03-15 for March 15)")
        return
    
    # Save the birthday
    birthdays[user_id] = {
        "name": command['user_name'],
        "date": birthday_date
    }
    save_birthdays(birthdays)
    
    say(f"🎂 Birthday saved for <@{user_id}> on {birthday_date}!")

# Command to list all birthdays
@app.command("/listbirthdays")
def handle_list_birthdays(ack, say):
    """Handle the /listbirthdays command"""
    ack()
    
    birthdays = load_birthdays()
    
    if not birthdays:
        say("No birthdays saved yet! Use `/addbirthday MM-DD` to add one.")
        return
    
    # Sort birthdays by month and day
    sorted_birthdays = sorted(
        birthdays.items(),
        key=lambda x: datetime.strptime(f"2024-{x[1]['date']}", "%Y-%m-%d")
    )
    
    message = "🎉 *Upcoming Birthdays* 🎉\n\n"
    for user_id, data in sorted_birthdays:
        date_obj = datetime.strptime(f"2024-{data['date']}", "%Y-%m-%d")
        formatted_date = date_obj.strftime("%B %d")
        message += f"• <@{user_id}>: {formatted_date}\n"
    
    say(message)

# Command to remove a birthday
@app.command("/removebirthday")
def handle_remove_birthday(ack, command, say):
    """Handle the /removebirthday command"""
    ack()
    
    text = command['text'].strip()
    birthdays = load_birthdays()
    
    # If user mentions someone, remove that person's birthday
    if text.startswith('<@'):
        user_id = text.strip('<@>|').split()[0]
    else:
        # Remove own birthday
        user_id = command['user_id']
    
    if user_id in birthdays:
        del birthdays[user_id]
        save_birthdays(birthdays)
        say(f"Birthday for <@{user_id}> has been removed.")
    else:
        say(f"No birthday found for <@{user_id}>.")

# Command to check today's birthdays
@app.command("/birthdaytoday")
def handle_birthday_today(ack, say):
    """Handle the /birthdaytoday command"""
    ack()
    
    birthday_people = check_birthdays_today()
    
    if not birthday_people:
        say("No birthdays today! 🎂")
    else:
        message = "🎉 *Happy Birthday!* 🎉\n\n"
        for person in birthday_people:
            message += f"🎂 <@{person['user_id']}> is celebrating today!\n"
        say(message)

# NEW COMMAND: Birthday Statistics
@app.command("/birthdaystats")
def handle_birthday_stats(ack, say):
    """Show birthday statistics"""
    ack()
    
    birthdays = load_birthdays()
    
    if not birthdays:
        say("No birthdays saved yet! Use `/addbirthday MM-DD` to add one.")
        return
    
    # Count by month
    month_counts = {}
    for user_id, data in birthdays.items():
        month = data['date'].split('-')[0]
        month_counts[month] = month_counts.get(month, 0) + 1
    
    # Get current month birthdays
    current_month = date.today().strftime("%m")
    current_month_count = month_counts.get(current_month, 0)
    
    # Find month with most birthdays
    if month_counts:
        max_month = max(month_counts.items(), key=lambda x: x[1])
        max_month_name = datetime.strptime(f"2024-{max_month[0]}-01", "%Y-%m-%d").strftime("%B")
        max_month_count = max_month[1]
    else:
        max_month_name = "None"
        max_month_count = 0
    
    # Get upcoming birthdays this month
    upcoming_this_month = []
    today = date.today()
    for user_id, data in birthdays.items():
        bday_date = datetime.strptime(f"2024-{data['date']}", "%Y-%m-%d").date()
        if bday_date.month == today.month and bday_date.day >= today.day:
            upcoming_this_month.append(f"<@{user_id}> ({data['date']})")
    
    message = f"""📊 *Birthday Statistics* 📊

📅 **Total Birthdays Tracked:** {len(birthdays)}

🎂 **This Month ({datetime.now().strftime('%B')}):** {current_month_count} birthday{"s" if current_month_count != 1 else ""}

🏆 **Most Popular Month:** {max_month_name} ({max_month_count} birthday{"s" if max_month_count != 1 else ""})

🎉 **Upcoming This Month:**
"""
    
    if upcoming_this_month:
        for person in upcoming_this_month:
            message += f"• {person}\n"
    else:
        message += "• None\n"
    
    say(message)

# Event listener for app mentions
@app.event("app_mention")
def handle_mentions(body, say):
    """Respond when the bot is mentioned"""
    say(f"Hi <@{body['event']['user']}>! 👋 I'm the Birthday Bot!\n\n*Commands:*\n• `/addbirthday MM-DD` - Add your birthday\n• `/listbirthdays` - See all birthdays\n• `/birthdaystats` - View statistics\n• `/setbirthdaychannel` - Set announcement channel")

# Simple message listener for "birthday" keyword
@app.message("birthday")
def respond_to_birthday_message(say):
    """Respond when someone mentions 'birthday' in a message"""
    say("Did someone say birthday? 🎂 Use `/listbirthdays` to see upcoming birthdays!")

if __name__ == "__main__":
    # Start the scheduler in a background thread
    scheduler_thread = threading.Thread(target=schedule_checker, daemon=True)
    scheduler_thread.start()
    print("📅 Scheduler started - will check for birthdays daily at 9 AM")
    
    # Start the app using Socket Mode
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    print("⚡️ Birthday Bot is running!")
    handler.start()
