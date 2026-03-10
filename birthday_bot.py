import os
import json
import random
import csv
import io
from datetime import datetime, date, timedelta
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import schedule
import time
import threading
import pytz

# Initialize the Slack app
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# File to store birthdays, anniversaries, wishes, and configuration
BIRTHDAYS_FILE = "birthdays.json"
ANNIVERSARIES_FILE = "anniversaries.json"
WISHES_FILE = "wishes.json"
CONFIG_FILE = "config.json"

# Mountain Time timezone
MOUNTAIN_TZ = pytz.timezone('America/Denver')

# Default configuration
DEFAULT_CONFIG = {
    "announcement_channel": None,
    "announcement_time": "09:00",
    "reminder_days": 3,
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

# Zodiac element mapping
ZODIAC_ELEMENTS = {
    "Aries": "Fire", "Leo": "Fire", "Sagittarius": "Fire",
    "Taurus": "Earth", "Virgo": "Earth", "Capricorn": "Earth",
    "Gemini": "Air", "Libra": "Air", "Aquarius": "Air",
    "Cancer": "Water", "Scorpio": "Water", "Pisces": "Water"
}

def get_zodiac_sign(month, day):
    """Get zodiac sign emoji and name from birth date"""
    date_tuple = (month, day)
    
    for end_date, (emoji, name) in ZODIAC_SIGNS.items():
        if month < end_date[0] or (month == end_date[0] and day <= end_date[1]):
            return emoji, name
    
    return "♑", "Capricorn"

# Birthday messages
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

# Anniversary messages
ANNIVERSARY_MESSAGES = [
    "🎊 Happy Work Anniversary {name}! {years} with the team! We're so grateful for you! 🌟",
    "🎉 Celebrating {name}'s {years} anniversary today! Thank you for all you do! 💼",
    "🌟 {years} of excellence! Happy Anniversary {name}! Here's to many more! 🎈",
    "💼 {name} is celebrating {years} with us today! What a milestone! 🎊",
    "🎈 Cheers to {name} for {years} of dedication and hard work! Happy Anniversary! 🥳",
    "🏆 {years} and counting! Happy Work Anniversary {name}! You're amazing! 🎉",
    "✨ Today we celebrate {name}'s {years} with the company! Thank you for everything! 💫",
    "🎯 {years} of making a difference! Happy Anniversary {name}! 🌟"
]

GIPHY_BIRTHDAY_TERMS = [
    "happy birthday celebration",
    "birthday cake",
    "birthday party",
    "birthday balloons",
    "happy birthday confetti"
]

GIPHY_ANNIVERSARY_TERMS = [
    "work anniversary celebration",
    "congratulations confetti",
    "celebration party",
    "anniversary celebration"
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

def load_anniversaries():
    """Load anniversaries from JSON file"""
    try:
        with open(ANNIVERSARIES_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_anniversaries(anniversaries):
    """Save anniversaries to JSON file"""
    with open(ANNIVERSARIES_FILE, 'w') as f:
        json.dump(anniversaries, f, indent=2)

def load_wishes():
    """Load wishes from JSON file"""
    try:
        with open(WISHES_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_wishes(wishes):
    """Save wishes to JSON file"""
    with open(WISHES_FILE, 'w') as f:
        json.dump(wishes, f, indent=2)

def load_config():
    """Load configuration from JSON file"""
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
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

def get_random_gif(is_anniversary=False):
    """Get a random GIF from Giphy"""
    try:
        import requests
        config = load_config()
        api_key = config.get("giphy_api_key") or os.environ.get("GIPHY_API_KEY")
        
        if not api_key:
            print("No Giphy API key configured")
            return None
        
        search_terms = GIPHY_ANNIVERSARY_TERMS if is_anniversary else GIPHY_BIRTHDAY_TERMS
        search_term = random.choice(search_terms)
        url = f"https://api.giphy.com/v1/gifs/search?api_key={api_key}&q={search_term}&limit=20&rating=g"
        response = requests.get(url, timeout=5)
        data = response.json()
        
        if data.get('data'):
            gif = random.choice(data['data'])
            return gif['images']['original']['url']
    except Exception as e:
        print(f"Error fetching GIF: {e}")
    return None

def calculate_years(start_date_str):
    """Calculate years from start date"""
    try:
        start_month, start_day = map(int, start_date_str.split('-'))
        mountain_now = get_mountain_time()
        today = mountain_now.date()
        
        # Calculate years
        years = today.year - 2000  # Placeholder year
        
        # Adjust if haven't reached anniversary this year
        if (today.month < start_month) or (today.month == start_month and today.day < start_day):
            years -= 1
        
        return years if years > 0 else 1
    except:
        return 1

def format_years(years):
    """Format years for display"""
    if years == 1:
        return "1 year"
    else:
        return f"{years} years"

def check_birthdays_today():
    """Check if anyone has a birthday today"""
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
                "zodiac_name": zodiac_name,
                "type": "birthday"
            })
    
    return birthday_people

def check_anniversaries_today():
    """Check if anyone has an anniversary today"""
    anniversaries = load_anniversaries()
    mountain_now = get_mountain_time()
    today_str = mountain_now.strftime("%m-%d")
    
    anniversary_people = []
    for user_id, anniv_data in anniversaries.items():
        if anniv_data.get("date", "") == today_str:
            years = calculate_years(anniv_data.get("date"))
            anniversary_people.append({
                "user_id": user_id,
                "name": anniv_data.get("name", "someone"),
                "years": years,
                "type": "anniversary"
            })
    
    return anniversary_people

def check_upcoming_birthdays(days=3):
    """Check if anyone has a birthday in N days"""
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
                "zodiac_name": zodiac_name,
                "type": "birthday"
            })
    
    return upcoming_people

def check_upcoming_anniversaries(days=3):
    """Check if anyone has an anniversary in N days"""
    anniversaries = load_anniversaries()
    mountain_now = get_mountain_time()
    target_date = mountain_now.date() + timedelta(days=days)
    target_str = target_date.strftime("%m-%d")
    
    upcoming_people = []
    for user_id, anniv_data in anniversaries.items():
        if anniv_data.get("date", "") == target_str:
            years = calculate_years(anniv_data.get("date"))
            upcoming_people.append({
                "user_id": user_id,
                "name": anniv_data.get("name", "someone"),
                "date": target_date,
                "years": years,
                "type": "anniversary"
            })
    
    return upcoming_people

def post_reminders():
    """Post reminders for upcoming birthdays and anniversaries"""
    config = load_config()
    channel = config.get("announcement_channel")
    reminder_days = config.get("reminder_days", 3)
    
    if not channel:
        return
    
    # Birthday reminders
    upcoming_birthdays = check_upcoming_birthdays(days=reminder_days)
    for person in upcoming_birthdays:
        day_name = person['date'].strftime("%A, %B %d")
        message = (
            f"📢 *Upcoming Birthday Alert!* 📢\n\n"
            f"<@{person['user_id']}>'s birthday is coming up on {day_name}! {person['zodiac_emoji']} *{person['zodiac_name']}*\n\n"
            f"💌 Want to wish them a happy birthday? Use:\n"
            f"`/addwish <@{person['user_id']}> Your personal message here`\n\n"
            f"All wishes will be shared on their special day! 🎂"
        )
        
        try:
            app.client.chat_postMessage(channel=channel, text=message)
            print(f"Posted birthday reminder for {person['name']}")
        except Exception as e:
            print(f"Error posting birthday reminder: {e}")
    
    # Anniversary reminders
    upcoming_anniversaries = check_upcoming_anniversaries(days=reminder_days)
    for person in upcoming_anniversaries:
        day_name = person['date'].strftime("%A, %B %d")
        years_text = format_years(person['years'])
        message = (
            f"📢 *Upcoming Anniversary Alert!* 📢\n\n"
            f"<@{person['user_id']}>'s {years_text} work anniversary is coming up on {day_name}! 🎊\n\n"
            f"💌 Want to congratulate them? Use:\n"
            f"`/addwish <@{person['user_id']}> Your congratulations message here`\n\n"
            f"All messages will be shared on their special day! 🌟"
        )
        
        try:
            app.client.chat_postMessage(channel=channel, text=message)
            print(f"Posted anniversary reminder for {person['name']}")
        except Exception as e:
            print(f"Error posting anniversary reminder: {e}")

def post_celebrations():
    """Post birthday and anniversary celebrations"""
    config = load_config()
    channel = config.get("announcement_channel")
    
    if not channel:
        print("No announcement channel set.")
        return
    
    wishes = load_wishes()
    
    # Post birthdays
    birthday_people = check_birthdays_today()
    for person in birthday_people:
        zodiac_text = f"{person['zodiac_emoji']} *{person['zodiac_name']}*"
        message = random.choice(BIRTHDAY_MESSAGES).format(
            name=f"<@{person['user_id']}>",
            zodiac=zodiac_text
        )
        
        user_wishes = wishes.get(f"{person['user_id']}_birthday", [])
        
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message
                }
            }
        ]
        
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
        
        if config.get("giphy_enabled", True):
            gif_url = get_random_gif(is_anniversary=False)
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
            print(f"Posted birthday celebration for {person['name']}")
            
            if f"{person['user_id']}_birthday" in wishes:
                del wishes[f"{person['user_id']}_birthday"]
                save_wishes(wishes)
                
        except Exception as e:
            print(f"Error posting birthday: {e}")
    
    # Post anniversaries
    anniversary_people = check_anniversaries_today()
    for person in anniversary_people:
        years_text = format_years(person['years'])
        message = random.choice(ANNIVERSARY_MESSAGES).format(
            name=f"<@{person['user_id']}>",
            years=years_text
        )
        
        user_wishes = wishes.get(f"{person['user_id']}_anniversary", [])
        
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message
                }
            }
        ]
        
        if user_wishes:
            wishes_text = "\n\n💌 *Congratulations from the Team:*\n\n"
            for wish in user_wishes:
                wishes_text += f"• <@{wish['from_user']}>: _{wish['message']}_\n"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": wishes_text
                }
            })
        
        if config.get("giphy_enabled", True):
            gif_url = get_random_gif(is_anniversary=True)
            if gif_url:
                blocks.append({
                    "type": "image",
                    "image_url": gif_url,
                    "alt_text": "Anniversary celebration"
                })
        
        try:
            app.client.chat_postMessage(
                channel=channel,
                text=message,
                blocks=blocks
            )
            print(f"Posted anniversary celebration for {person['name']}")
            
            if f"{person['user_id']}_anniversary" in wishes:
                del wishes[f"{person['user_id']}_anniversary"]
                save_wishes(wishes)
                
        except Exception as e:
            print(f"Error posting anniversary: {e}")

def schedule_checker():
    """Background thread for scheduled tasks"""
    config = load_config()
    announcement_time = config.get("announcement_time", "09:00")
    
    schedule.every().day.at(announcement_time).do(post_celebrations)
    schedule.every().day.at(announcement_time).do(post_reminders)
    
    print(f"Scheduler configured for {announcement_time} Mountain Time")
    
    while True:
        schedule.run_pending()
        time.sleep(60)

# COMMAND: Import from CSV with anniversaries
@app.command("/importcelebrations")
def handle_import_celebrations(ack, command, say):
    """Handle CSV import of birthdays and anniversaries"""
    ack()
    
    say("📁 Please upload your CSV file with birthdays and anniversaries!\n\n"
        "**CSV Format:**\n"
        "```\n"
        "Name,Birthday,Anniversary,Slack ID\n"
        "John Smith,03-15,06-20,U12345678\n"
        "Sarah Jones,07-22,,U87654321\n"
        "Mike Johnson,,12-05,U11223344\n"
        "```\n\n"
        "**Requirements:**\n"
        "• Date format: MM-DD\n"
        "• Slack User ID starts with 'U'\n"
        "• Leave Birthday or Anniversary blank if not applicable\n\n"
        "Upload your CSV file in this channel! 📤")

# Event listener for file uploads
@app.event("file_shared")
def handle_file_upload(event, say, client):
    """Handle CSV file upload"""
    try:
        file_id = event['file_id']
        file_info = client.files_info(file=file_id)
        file_data = file_info['file']
        
        if not (file_data['name'].endswith('.csv') or file_data['mimetype'] == 'text/csv'):
            return
        
        file_url = file_data['url_private']
        headers = {"Authorization": f"Bearer {os.environ.get('SLACK_BOT_TOKEN')}"}
        
        import requests
        response = requests.get(file_url, headers=headers)
        csv_content = response.text
        
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        
        birthdays = load_birthdays()
        anniversaries = load_anniversaries()
        birthday_count = 0
        anniversary_count = 0
        error_count = 0
        errors = []
        
        for row in csv_reader:
            try:
                name = row.get('Name', '').strip()
                birthday = row.get('Birthday', '').strip()
                anniversary = row.get('Anniversary', '').strip()
                user_id = row.get('Slack ID', '').strip()
                
                if not user_id or not user_id.startswith('U'):
                    error_count += 1
                    errors.append(f"Invalid/missing Slack ID for {name}")
                    continue
                
                # Import birthday if present
                if birthday:
                    try:
                        datetime.strptime(f"2024-{birthday}", "%Y-%m-%d")
                        birthdays[user_id] = {
                            "name": name,
                            "date": birthday
                        }
                        birthday_count += 1
                    except ValueError:
                        error_count += 1
                        errors.append(f"Invalid birthday date for {name}: {birthday}")
                
                # Import anniversary if present
                if anniversary:
                    try:
                        datetime.strptime(f"2024-{anniversary}", "%Y-%m-%d")
                        anniversaries[user_id] = {
                            "name": name,
                            "date": anniversary
                        }
                        anniversary_count += 1
                    except ValueError:
                        error_count += 1
                        errors.append(f"Invalid anniversary date for {name}: {anniversary}")
                
            except Exception as e:
                error_count += 1
                errors.append(f"Error processing {name}: {str(e)}")
        
        save_birthdays(birthdays)
        save_anniversaries(anniversaries)
        
        result_message = f"✅ *Import Complete!*\n\n"
        result_message += f"🎂 Birthdays imported: *{birthday_count}*\n"
        result_message += f"🎊 Anniversaries imported: *{anniversary_count}*\n"
        
        if error_count > 0:
            result_message += f"\n⚠️ Errors: {error_count} rows\n\n"
            if len(errors) <= 5:
                result_message += "*Error details:*\n"
                for error in errors:
                    result_message += f"• {error}\n"
            else:
                result_message += f"*First 5 errors:*\n"
                for error in errors[:5]:
                    result_message += f"• {error}\n"
                result_message += f"\n_...and {len(errors) - 5} more_"
        
        result_message += f"\n\n🎉 Use `/listbirthdays` or `/listanniversaries` to see them!"
        
        say(result_message)
        
    except Exception as e:
        say(f"❌ Error importing CSV: {str(e)}\n\nPlease check your file format and try again!")

@app.command("/listanniversaries")
def handle_list_anniversaries(ack, say):
    """List all anniversaries"""
    ack()
    
    anniversaries = load_anniversaries()
    
    if not anniversaries:
        say("No anniversaries saved yet! Use `/importcelebrations` to add some.")
        return
    
    sorted_anniversaries = sorted(
        anniversaries.items(),
        key=lambda x: datetime.strptime(f"2024-{x[1]['date']}", "%Y-%m-%d")
    )
    
    message = "🎊 *Work Anniversaries* 🎊\n\n"
    for user_id, data in sorted_anniversaries:
        date_obj = datetime.strptime(f"2024-{data['date']}", "%Y-%m-%d")
        formatted_date = date_obj.strftime("%B %d")
        message += f"• <@{user_id}>: {formatted_date}\n"
    
    say(message)

@app.command("/todayscelebrations")
def handle_todays_celebrations(ack, say):
    """Check today's birthdays and anniversaries"""
    ack()
    
    birthdays = check_birthdays_today()
    anniversaries = check_anniversaries_today()
    
    if not birthdays and not anniversaries:
        say("No celebrations today! 🎉")
        return
    
    message = "🎉 *Today's Celebrations!* 🎉\n\n"
    
    if birthdays:
        message += "🎂 *Birthdays:*\n"
        for person in birthdays:
            message += f"• <@{person['user_id']}> {person['zodiac_emoji']}\n"
        message += "\n"
    
    if anniversaries:
        message += "🎊 *Work Anniversaries:*\n"
        for person in anniversaries:
            years_text = format_years(person['years'])
            message += f"• <@{person['user_id']}> ({years_text})\n"
    
    say(message)

# Keep all existing commands from v3...
@app.command("/setbirthdaychannel")
def handle_set_channel(ack, command, say):
    """Set the channel for announcements"""
    ack()
    
    channel_id = command['channel_id']
    config = load_config()
    config['announcement_channel'] = channel_id
    save_config(config)
    
    mountain_now = get_mountain_time()
    current_time = mountain_now.strftime("%I:%M %p %Z")
    
    say(f"✅ Birthday and anniversary announcements will be posted in this channel!\n\n"
        f"🕐 Daily checks at 9:00 AM Mountain Time\n"
        f"⏰ Current time: {current_time}")

@app.command("/addwish")
def handle_add_wish(ack, command, say):
    """Add a wish for birthday or anniversary"""
    ack()
    
    text = command['text'].strip()
    
    if not text or not text.startswith('<@'):
        say("Please mention a user and include a message! Format: `/addwish @user Your message here`")
        return
    
    parts = text.split(None, 1)
    if len(parts) < 2:
        say("Please include a message! Format: `/addwish @user Your message here`")
        return
    
    user_id = parts[0].strip('<@>|')
    message = parts[1]
    
    birthdays = load_birthdays()
    anniversaries = load_anniversaries()
    wishes = load_wishes()
    
    # Determine if it's for birthday or anniversary
    has_birthday = user_id in birthdays
    has_anniversary = user_id in anniversaries
    
    if not has_birthday and not has_anniversary:
        say(f"<@{user_id}> doesn't have a birthday or anniversary saved yet!")
        return
    
    # Store wish (we'll determine type when posting)
    wish_entry = {
        "from_user": command['user_id'],
        "message": message,
        "timestamp": datetime.now().isoformat()
    }
    
    if has_birthday:
        key = f"{user_id}_birthday"
        if key not in wishes:
            wishes[key] = []
        wishes[key].append(wish_entry)
    
    if has_anniversary:
        key = f"{user_id}_anniversary"
        if key not in wishes:
            wishes[key] = []
        wishes[key].append(wish_entry)
    
    save_wishes(wishes)
    
    say(f"💌 Your message for <@{user_id}> has been saved! 🎉")

@app.command("/addbirthday")
def handle_add_birthday(ack, command, say):
    """Add a birthday"""
    ack()
    
    text = command['text'].strip()
    
    if not text:
        say("Please provide a birthday date! Format: `/addbirthday MM-DD` or `/addbirthday @user MM-DD`")
        return
    
    parts = text.split()
    birthdays = load_birthdays()
    
    if parts[0].startswith('<@'):
        if len(parts) < 2:
            say("Please provide a date!")
            return
        user_id = parts[0].strip('<@>|')
        birthday_date = parts[1]
    else:
        user_id = command['user_id']
        birthday_date = parts[0]
    
    try:
        test_date = datetime.strptime(f"2024-{birthday_date}", "%Y-%m-%d")
        month = test_date.month
        day = test_date.day
        zodiac_emoji, zodiac_name = get_zodiac_sign(month, day)
    except ValueError:
        say("Invalid date format! Please use MM-DD")
        return
    
    birthdays[user_id] = {
        "name": command['user_name'],
        "date": birthday_date
    }
    save_birthdays(birthdays)
    
    say(f"🎂 Birthday saved for <@{user_id}> on {birthday_date}! {zodiac_emoji} *{zodiac_name}*")

@app.command("/listbirthdays")
def handle_list_birthdays(ack, say):
    """List all birthdays"""
    ack()
    
    birthdays = load_birthdays()
    
    if not birthdays:
        say("No birthdays saved yet!")
        return
    
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

@app.command("/birthdaystats")
def handle_birthday_stats(ack, say):
    """Show birthday statistics"""
    ack()
    
    birthdays = load_birthdays()
    anniversaries = load_anniversaries()
    
    if not birthdays and not anniversaries:
        say("No data yet!")
        return
    
    message = f"📊 *Celebration Statistics* 📊\n\n"
    message += f"🎂 Total Birthdays: {len(birthdays)}\n"
    message += f"🎊 Total Anniversaries: {len(anniversaries)}\n"
    
    say(message)

@app.event("app_mention")
def handle_mentions(body, say):
    """Respond to mentions"""
    say(f"Hi <@{body['event']['user']}>! 👋 I'm the Celebration Bot!\n\n"
        f"*Commands:*\n"
        f"• `/importcelebrations` - Import birthdays & anniversaries\n"
        f"• `/listbirthdays` - See all birthdays\n"
        f"• `/listanniversaries` - See all anniversaries\n"
        f"• `/todayscelebrations` - Check today's celebrations\n"
        f"• `/addwish @user message` - Add wishes\n"
        f"• `/setbirthdaychannel` - Set announcement channel")

@app.message("birthday")
def respond_to_birthday_message(say):
    """Respond to birthday mentions"""
    say("Did someone say birthday? 🎂 Use `/todayscelebrations` to see today's celebrations!")

if __name__ == "__main__":
    scheduler_thread = threading.Thread(target=schedule_checker, daemon=True)
    scheduler_thread.start()
    
    mountain_now = get_mountain_time()
    current_time = mountain_now.strftime("%I:%M %p %Z")
    print(f"📅 Scheduler started - checks at 9 AM Mountain Time")
    print(f"⏰ Current Mountain Time: {current_time}")
    
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    print("⚡️ Celebration Bot v4 is running!")
    handler.start()
