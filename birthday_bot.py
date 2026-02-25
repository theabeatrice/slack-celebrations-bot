import os
import json
import random
from datetime import datetime, date, timedelta
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import schedule
import time
import threading
import pytz

# Initialize the Slack app
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# File to store birthdays, wishes, and configuration
BIRTHDAYS_FILE = "birthdays.json"
WISHES_FILE = "birthday_wishes.json"
CONFIG_FILE = "config.json"

# Mountain Time timezone
MOUNTAIN_TZ = pytz.timezone('America/Denver')

# Default configuration
DEFAULT_CONFIG = {
    "announcement_channel": None,  # Set with /setbirthdaychannel
    "announcement_time": "09:00",  # 9 AM Mountain Time
    "reminder_days": 3,  # Remind 3 days before
    "giphy_enabled": True,
    "giphy_api_key": os.environ.get("GIPHY_API_KEY", "")
}

# Zodiac sign mapping
ZODIAC_SIGNS = {
    (1, 20): ("♑", "Capricorn"),
    (2, 19): ("♒", "Aquarius"),
    (3, 21): ("♓", "Pisces"),
    (4, 20): ("♈", "Aries"),
    (5, 21): ("♉", "Taurus"),
    (6, 21): ("♊", "Gemini"),
    (7, 23): ("♋", "Cancer"),
    (8, 23): ("♌", "Leo"),
    (9, 23): ("♍", "Virgo"),
    (10, 23): ("♎", "Libra"),
    (11, 22): ("♏", "Scorpio"),
    (12, 22): ("♐", "Sagittarius"),
    (12, 31): ("♑", "Capricorn"),
}

def get_zodiac_sign(month, day):
    """Get zodiac sign emoji and name from birth date"""
    date_tuple = (month, day)
    
    # Find the zodiac sign
    for end_date, (emoji, name) in ZODIAC_SIGNS.items():
        if month < end_date[0] or (month == end_date[0] and day <= end_date[1]):
            return emoji, name
    
    return "♑", "Capricorn"  # Default fallback

# Fun birthday messages (with zodiac placeholder)
BIRTHDAY_MESSAGES = [
    "🎉 Happy Birthday {name}! {zodiac} Hope your day is as amazing as you are! 🎂",
    "🎈 It's {name}'s special day! {zodiac} Wishing you all the best! 🎊",
    "🎂 Another trip around the sun for {name}! {zodiac} Have a fantastic birthday! ☀️",
    "🎁 Hip hip hooray! It's {name}'s birthday today! {zodiac} 🎉",
    "🌟 Sending birthday wishes to the wonderful {name}! {zodiac} Have an incredible day! 🎈",
    "🎊 {name} is leveling up today! {zodiac} Happy Birthday! 🎮",
    "🎵 Happy Birthday to you, happy birthday to you, happy birthday dear {name}! {zodiac} 🎵",
    "🍰 Time to celebrate {name}! {zodiac} May your birthday be filled with joy and cake! 🎂"
]

# Giphy birthday GIF search terms
GIPHY_SEARCH_TERMS = [
    "happy birthday celebration",
    "birthday cake",
    "birthday party",
    "birthday balloons",
    "happy birthday confetti"
]

def get_mountain_time():
    """Get current time in Mountain Time"""
    utc_now = datetime.now(pytz.utc)
    mountain_now = utc_now.astimezone(MOUNTAIN_TZ)
    return mountain_now

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

def load_wishes():
    """Load birthday wishes from JSON file"""
    try:
        with open(WISHES_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_wishes(wishes):
    """Save birthday wishes to JSON file"""
    with open(WISHES_FILE, 'w') as f:
        json.dump(wishes, f, indent=2)

def load_config():
    """Load configuration from JSON file"""
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            # Update with any missing defaults
            for key, value in DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = value
            return config
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
        config = load_config()
        api_key = config.get("giphy_api_key") or os.environ.get("GIPHY_API_KEY")
        
        if not api_key:
            print("No Giphy API key configured")
            return None
        
        search_term = random.choice(GIPHY_SEARCH_TERMS)
        url = f"https://api.giphy.com/v1/gifs/search?api_key={api_key}&q={search_term}&limit=20&rating=g"
        response = requests.get(url, timeout=5)
        data = response.json()
        
        if data.get('data'):
            gif = random.choice(data['data'])
            return gif['images']['original']['url']
    except Exception as e:
        print(f"Error fetching GIF: {e}")
    return None

def check_birthdays_today():
    """Check if anyone has a birthday today (in Mountain Time)"""
    birthdays = load_birthdays()
    mountain_now = get_mountain_time()
    today_str = mountain_now.strftime("%m-%d")
    
    birthday_people = []
    for user_id, birthday_data in birthdays.items():
        if birthday_data.get("date", "") == today_str:
            month, day = map(int, birthday_data.get("date").split('-'))
            zodiac_emoji, zodiac_name = get_zodiac_sign(month, day)
            birthday_people.append({
                "user_id": user_id,
                "name": birthday_data.get("name", "someone"),
                "zodiac_emoji": zodiac_emoji,
                "zodiac_name": zodiac_name
            })
    
    return birthday_people

def check_upcoming_birthdays(days=3):
    """Check if anyone has a birthday in N days (in Mountain Time)"""
    birthdays = load_birthdays()
    mountain_now = get_mountain_time()
    target_date = mountain_now.date() + timedelta(days=days)
    target_str = target_date.strftime("%m-%d")
    
    upcoming_people = []
    for user_id, birthday_data in birthdays.items():
        if birthday_data.get("date", "") == target_str:
            month, day = map(int, birthday_data.get("date").split('-'))
            zodiac_emoji, zodiac_name = get_zodiac_sign(month, day)
            upcoming_people.append({
                "user_id": user_id,
                "name": birthday_data.get("name", "someone"),
                "date": target_date,
                "zodiac_emoji": zodiac_emoji,
                "zodiac_name": zodiac_name
            })
    
    return upcoming_people

def post_wish_reminder():
    """Post reminders for upcoming birthdays and ask for wishes"""
    config = load_config()
    channel = config.get("announcement_channel")
    reminder_days = config.get("reminder_days", 3)
    
    if not channel:
        return
    
    upcoming = check_upcoming_birthdays(days=reminder_days)
    
    if upcoming:
        for person in upcoming:
            day_name = person['date'].strftime("%A, %B %d")
            message = (
                f"📢 *Upcoming Birthday Alert!* 📢\n\n"
                f"<@{person['user_id']}>'s birthday is coming up on {day_name}! {person['zodiac_emoji']} *{person['zodiac_name']}*\n\n"
                f"💌 Want to wish them a happy birthday? Use:\n"
                f"`/addwish @{person['user_id']} Your personal message here`\n\n"
                f"All wishes will be shared on their special day! 🎂"
            )
            
            try:
                app.client.chat_postMessage(
                    channel=channel,
                    text=message
                )
                print(f"Posted birthday reminder and wish request for {person['name']}")
            except Exception as e:
                print(f"Error posting reminder: {e}")

def post_birthday_announcement():
    """Automatically post birthday announcements with collected wishes"""
    config = load_config()
    channel = config.get("announcement_channel")
    
    if not channel:
        print("No announcement channel set. Use /setbirthdaychannel to configure.")
        return
    
    # Check today's birthdays
    birthday_people = check_birthdays_today()
    
    if birthday_people:
        for person in birthday_people:
            # Get the base birthday message
            zodiac_text = f"{person['zodiac_emoji']} *{person['zodiac_name']}*"
            message = random.choice(BIRTHDAY_MESSAGES).format(
                name=f"<@{person['user_id']}>",
                zodiac=zodiac_text
            )
            
            # Check if there are any wishes for this person
            wishes = load_wishes()
            user_wishes = wishes.get(person['user_id'], [])
            
            # Build the message blocks
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": message
                    }
                }
            ]
            
            # Add wishes if any exist
            if user_wishes:
                wishes_text = "\n\n💌 *Birthday Wishes from the Team:*\n\n"
                for wish in user_wishes:
                    wishes_text += f"• <@{wish['from_user']}>: _{wish['message']}_\n"
                
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": wishes_text
                    }
                })
            
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
                
                # Clear wishes for this person after posting
                if person['user_id'] in wishes:
                    del wishes[person['user_id']]
                    save_wishes(wishes)
                    
            except Exception as e:
                print(f"Error posting birthday announcement: {e}")

def schedule_checker():
    """Background thread to check scheduled tasks in Mountain Time"""
    config = load_config()
    announcement_time = config.get("announcement_time", "09:00")
    
    schedule.every().day.at(announcement_time).do(post_birthday_announcement)
    schedule.every().day.at(announcement_time).do(post_wish_reminder)
    
    print(f"Scheduler configured for {announcement_time} Mountain Time")
    
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
    
    mountain_now = get_mountain_time()
    current_time = mountain_now.strftime("%I:%M %p %Z")
    
    say(f"✅ Birthday announcements will be posted in this channel!\n\n"
        f"🕐 Daily checks at 9:00 AM Mountain Time\n"
        f"⏰ Current time: {current_time}")

# NEW COMMAND: Add a birthday wish
@app.command("/addwish")
def handle_add_wish(ack, command, say):
    """Add a birthday wish for someone"""
    ack()
    
    text = command['text'].strip()
    
    if not text:
        say("Please provide a user and message! Format: `/addwish @user Your birthday message here`")
        return
    
    parts = text.split(None, 1)
    
    if len(parts) < 2 or not parts[0].startswith('<@'):
        say("Please mention a user and include a message! Format: `/addwish @user Your birthday message here`")
        return
    
    user_id = parts[0].strip('<@>|')
    message = parts[1]
    
    # Check if this user has a birthday in the system
    birthdays = load_birthdays()
    if user_id not in birthdays:
        say(f"<@{user_id}> doesn't have a birthday saved yet! They need to add it first with `/addbirthday`.")
        return
    
    # Load wishes and add this one
    wishes = load_wishes()
    if user_id not in wishes:
        wishes[user_id] = []
    
    wishes[user_id].append({
        "from_user": command['user_id'],
        "message": message,
        "timestamp": datetime.now().isoformat()
    })
    
    save_wishes(wishes)
    
    say(f"💌 Your birthday wish for <@{user_id}> has been saved! It will be shared on their birthday. 🎉")

# Command to add a birthday
@app.command("/addbirthday")
def handle_add_birthday(ack, command, say):
    """Handle the /addbirthday command"""
    ack()
    
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
        test_date = datetime.strptime(f"2024-{birthday_date}", "%Y-%m-%d")
        month = test_date.month
        day = test_date.day
        zodiac_emoji, zodiac_name = get_zodiac_sign(month, day)
    except ValueError:
        say("Invalid date format! Please use MM-DD (e.g., 03-15 for March 15)")
        return
    
    # Save the birthday
    birthdays[user_id] = {
        "name": command['user_name'],
        "date": birthday_date
    }
    save_birthdays(birthdays)
    
    say(f"🎂 Birthday saved for <@{user_id}> on {birthday_date}! {zodiac_emoji} *{zodiac_name}*")

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
        month = date_obj.month
        day = date_obj.day
        zodiac_emoji, zodiac_name = get_zodiac_sign(month, day)
        message += f"• <@{user_id}>: {formatted_date} {zodiac_emoji} *{zodiac_name}*\n"
    
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
            message += f"🎂 <@{person['user_id']}> is celebrating today! {person['zodiac_emoji']} *{person['zodiac_name']}*\n"
        say(message)

# Command: Birthday Statistics
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
    zodiac_counts = {}
    
    for user_id, data in birthdays.items():
        month, day = map(int, data['date'].split('-'))
        month_name = datetime(2024, month, 1).strftime("%B")
        month_counts[month_name] = month_counts.get(month_name, 0) + 1
        
        # Count zodiac signs
        _, zodiac_name = get_zodiac_sign(month, day)
        zodiac_counts[zodiac_name] = zodiac_counts.get(zodiac_name, 0) + 1
    
    # Get current month birthdays
    mountain_now = get_mountain_time()
    current_month_name = mountain_now.strftime("%B")
    current_month_count = month_counts.get(current_month_name, 0)
    
    # Find month with most birthdays
    if month_counts:
        max_month = max(month_counts.items(), key=lambda x: x[1])
        max_month_name = max_month[0]
        max_month_count = max_month[1]
    else:
        max_month_name = "None"
        max_month_count = 0
    
    # Most common zodiac sign
    if zodiac_counts:
        max_zodiac = max(zodiac_counts.items(), key=lambda x: x[1])
        max_zodiac_name = max_zodiac[0]
        max_zodiac_count = max_zodiac[1]
    else:
        max_zodiac_name = "None"
        max_zodiac_count = 0
    
    # Get upcoming birthdays this month
    upcoming_this_month = []
    today = mountain_now.date()
    for user_id, data in birthdays.items():
        bday_date = datetime.strptime(f"2024-{data['date']}", "%Y-%m-%d").date()
        if bday_date.month == today.month and bday_date.day >= today.day:
            month, day = map(int, data['date'].split('-'))
            zodiac_emoji, _ = get_zodiac_sign(month, day)
            upcoming_this_month.append(f"<@{user_id}> ({data['date']}) {zodiac_emoji}")
    
    message = f"""📊 *Birthday Statistics* 📊

📅 *Total Birthdays Tracked:* {len(birthdays)}

🎂 *This Month ({current_month_name}):* {current_month_count} birthday{"s" if current_month_count != 1 else ""}

🏆 *Most Popular Month:* {max_month_name} ({max_month_count} birthday{"s" if max_month_count != 1 else ""})

⭐ *Most Common Sign:* {max_zodiac_name} ({max_zodiac_count} {"people" if max_zodiac_count != 1 else "person"})

🎉 *Upcoming This Month:*
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
    say(f"Hi <@{body['event']['user']}>! 👋 I'm the Birthday Bot!\n\n*Commands:*\n• `/addbirthday MM-DD` - Add a birthday\n• `/listbirthdays` - See all birthdays with zodiac signs\n• `/addwish @user message` - Add a birthday wish\n• `/birthdaystats` - View statistics\n• `/setbirthdaychannel` - Set announcement channel")

# Simple message listener for "birthday" keyword
@app.message("birthday")
def respond_to_birthday_message(say):
    """Respond when someone mentions 'birthday' in a message"""
    say("Did someone say birthday? 🎂 Use `/listbirthdays` to see upcoming birthdays with their zodiac signs!")

if __name__ == "__main__":
    # Start the scheduler in a background thread
    scheduler_thread = threading.Thread(target=schedule_checker, daemon=True)
    scheduler_thread.start()
    
    mountain_now = get_mountain_time()
    current_time = mountain_now.strftime("%I:%M %p %Z")
    print(f"📅 Scheduler started - will check for birthdays daily at 9 AM Mountain Time")
    print(f"⏰ Current Mountain Time: {current_time}")
    
    # Start the app using Socket Mode
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    print("⚡️ Birthday Bot is running!")
    handler.start()
