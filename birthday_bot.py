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
    "balloons celebration",
    "colorful balloons",
    "party balloons",
    "balloon animation",
    "floating balloons"
]

GIPHY_ANNIVERSARY_TERMS = [
    "balloons celebration",
    "colorful balloons",
    "party balloons",
    "balloon animation",
    "floating balloons"
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
    """Calculate years from start date (MM-DD-YYYY or MM-DD)"""
    try:
        mountain_now = get_mountain_time()
        today = mountain_now.date()
        
        # Check if full date (MM-DD-YYYY) or just MM-DD
        if len(start_date_str.split('-')) == 3:
            # Full date format: MM-DD-YYYY
            start_month, start_day, start_year = map(int, start_date_str.split('-'))
        else:
            # Old format: MM-DD (use current year - 1 as estimate)
            start_month, start_day = map(int, start_date_str.split('-'))
            start_year = today.year - 1  # Assume 1 year ago as default
        
        # Calculate years
        years = today.year - start_year
        
        # Adjust if haven't reached anniversary this year
        if (today.month < start_month) or (today.month == start_month and today.day < start_day):
            years -= 1
        
        return years if years > 0 else 1
    except Exception as e:
        print(f"Error calculating years for {start_date_str}: {e}")
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
        stored_date = anniv_data.get("date", "")
        # Extract MM-DD from either MM-DD or MM-DD-YYYY format
        date_parts = stored_date.split('-')
        if len(date_parts) >= 2:
            check_date = f"{date_parts[0]}-{date_parts[1]}"  # MM-DD
        else:
            continue
            
        if check_date == today_str:
            years = calculate_years(stored_date)
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
        stored_date = anniv_data.get("date", "")
        # Extract MM-DD from either MM-DD or MM-DD-YYYY format
        date_parts = stored_date.split('-')
        if len(date_parts) >= 2:
            check_date = f"{date_parts[0]}-{date_parts[1]}"  # MM-DD
        else:
            continue
            
        if check_date == target_str:
            years = calculate_years(stored_date)
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
            f"<@{person['user_id']}>'s birthday is coming up on {day_name}! {person['zodiac_emoji']} *{person['zodiac_name']}*"
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
            f"<@{person['user_id']}>'s {years_text} work anniversary is coming up on {day_name}! 🎊"
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
    
    # Post birthdays
    birthday_people = check_birthdays_today()
    for person in birthday_people:
        zodiac_text = f"{person['zodiac_emoji']} *{person['zodiac_name']}*"
        message = random.choice(BIRTHDAY_MESSAGES).format(
            name=f"<@{person['user_id']}>",
            zodiac=zodiac_text
        )
        
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message
                }
            }
        ]
        
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
        
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message
                }
            }
        ]
        
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
                
        except Exception as e:
            print(f"Error posting anniversary: {e}")

def schedule_checker():
    """Background thread for scheduled tasks - checks every minute for Mountain Time"""
    print(f"📅 Scheduler started - checks at 9 AM Mountain Time")
    mountain_now = get_mountain_time()
    print(f"⏰ Current Mountain Time: {mountain_now.strftime('%I:%M %p %Z')}")
    
    while True:
        # Get current Mountain Time
        mountain_now = get_mountain_time()
        current_hour = mountain_now.hour
        current_minute = mountain_now.minute
        
        # Check if it's 9:00 AM MT
        if current_hour == 9 and current_minute == 0:
            print(f"🎉 It's 9:00 AM MT! Running celebrations...")
            post_celebrations()
            # removed: post_reminders()
            # Sleep for 60 seconds to avoid running multiple times in the same minute
            time.sleep(60)
        
        # Sleep for 30 seconds before next check
        time.sleep(30)

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
                        # Check if it's full format (MM-DD-YYYY) or short (MM-DD)
                        parts = anniversary.split('-')
                        if len(parts) == 3:
                            # Full format: MM-DD-YYYY
                            datetime.strptime(anniversary, "%m-%d-%Y")
                            anniversaries[user_id] = {
                                "name": name,
                                "date": anniversary  # Store as MM-DD-YYYY
                            }
                        else:
                            # Short format: MM-DD (backwards compatible)
                            datetime.strptime(f"2024-{anniversary}", "%Y-%m-%d")
                            anniversaries[user_id] = {
                                "name": name,
                                "date": anniversary  # Store as MM-DD
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
    
    # Sort by MM-DD (ignore year for sorting)
    def get_sort_key(item):
        date_str = item[1]['date']
        # Extract MM-DD from either MM-DD or MM-DD-YYYY
        parts = date_str.split('-')
        if len(parts) >= 2:
            return datetime.strptime(f"2024-{parts[0]}-{parts[1]}", "%Y-%m-%d")
        return datetime.strptime(f"2024-{date_str}", "%Y-%m-%d")
    
    sorted_anniversaries = sorted(anniversaries.items(), key=get_sort_key)
    
    message = "🎊 *Work Anniversaries* 🎊\n\n"
    for user_id, data in sorted_anniversaries:
        date_str = data['date']
        # Extract MM-DD for display
        parts = date_str.split('-')
        if len(parts) >= 2:
            display_date = f"{parts[0]}-{parts[1]}"
        else:
            display_date = date_str
            
        date_obj = datetime.strptime(f"2024-{display_date}", "%Y-%m-%d")
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

@app.command("/upcomingbirthdays")
def handle_upcoming_birthdays(ack, say):
    """Show upcoming birthdays for the next 2 months"""
    ack()
    
    birthdays = load_birthdays()
    
    if not birthdays:
        say("No birthdays saved yet!")
        return
    
    mountain_now = get_mountain_time()
    today = mountain_now.date()
    
    # Get birthdays for next 60 days
    upcoming = []
    for user_id, data in birthdays.items():
        birthday_str = data.get('date', '')
        if not birthday_str:
            continue
            
        try:
            month, day = map(int, birthday_str.split('-'))
            
            # Calculate next occurrence of this birthday
            current_year = today.year
            birthday_this_year = date(current_year, month, day)
            
            if birthday_this_year < today:
                # Birthday already passed this year, use next year
                birthday_next = date(current_year + 1, month, day)
            else:
                birthday_next = birthday_this_year
            
            days_until = (birthday_next - today).days
            
            if days_until <= 60:  # Next 2 months
                zodiac_emoji, zodiac_name = get_zodiac_sign(month, day)
                upcoming.append({
                    'user_id': user_id,
                    'name': data.get('name', 'someone'),
                    'date': birthday_next,
                    'days_until': days_until,
                    'zodiac_emoji': zodiac_emoji,
                    'zodiac_name': zodiac_name
                })
        except:
            continue
    
    if not upcoming:
        say("No birthdays in the next 2 months!")
        return
    
    # Sort by days until birthday
    upcoming.sort(key=lambda x: x['days_until'])
    
    message = "🎂 *Upcoming Birthdays (Next 2 Months)* 🎂\n\n"
    
    for person in upcoming:
        formatted_date = person['date'].strftime("%B %d")
        days = person['days_until']
        
        if days == 0:
            when = "🎉 TODAY!"
        elif days == 1:
            when = "Tomorrow"
        else:
            when = f"in {days} days"
        
        message += f"• <@{person['user_id']}>: {formatted_date} ({when}) {person['zodiac_emoji']}\n"
    
    say(message)

@app.command("/upcominganniversaries")
def handle_upcoming_anniversaries(ack, say):
    """Show upcoming anniversaries for the next 2 months"""
    ack()
    
    anniversaries = load_anniversaries()
    
    if not anniversaries:
        say("No anniversaries saved yet!")
        return
    
    mountain_now = get_mountain_time()
    today = mountain_now.date()
    
    # Get anniversaries for next 60 days
    upcoming = []
    for user_id, anniv_data in anniversaries.items():
        stored_date = anniv_data.get("date", "")
        if not stored_date:
            continue
        
        try:
            # Extract MM-DD from either MM-DD or MM-DD-YYYY format
            date_parts = stored_date.split('-')
            if len(date_parts) >= 2:
                month = int(date_parts[0])
                day = int(date_parts[1])
            else:
                continue
            
            # Calculate next occurrence
            current_year = today.year
            anniv_this_year = date(current_year, month, day)
            
            if anniv_this_year < today:
                anniv_next = date(current_year + 1, month, day)
            else:
                anniv_next = anniv_this_year
            
            days_until = (anniv_next - today).days
            
            if days_until <= 60:  # Next 2 months
                years = calculate_years(stored_date)
                upcoming.append({
                    'user_id': user_id,
                    'name': anniv_data.get('name', 'someone'),
                    'date': anniv_next,
                    'days_until': days_until,
                    'years': years
                })
        except:
            continue
    
    if not upcoming:
        say("No work anniversaries in the next 2 months!")
        return
    
    # Sort by days until anniversary
    upcoming.sort(key=lambda x: x['days_until'])
    
    message = "🎊 *Upcoming Work Anniversaries (Next 2 Months)* 🎊\n\n"
    
    for person in upcoming:
        formatted_date = person['date'].strftime("%B %d")
        days = person['days_until']
        years_text = format_years(person['years'])
        
        if days == 0:
            when = "🎉 TODAY!"
        elif days == 1:
            when = "Tomorrow"
        else:
            when = f"in {days} days"
        
        message += f"• <@{person['user_id']}>: {formatted_date} - {years_text} ({when})\n"
    
    say(message)

@app.command("/addbirthday")
def handle_add_birthday(ack, command, say, client):
    """Add a birthday using Slack user ID"""
    ack()
    
    text = command['text'].strip()
    
    if not text:
        say("Please provide a Slack user ID and birthday date!\n\n"
            "**Format:** `/addbirthday U123456789 MM-DD`\n"
            "**Example:** `/addbirthday U098G5UV54P 07-22`\n\n"
            "💡 **How to find Slack ID:** Right-click someone's name → Copy member ID")
        return
    
    parts = text.split()
    
    if len(parts) < 2:
        say("Please provide both Slack ID and date!\n\n"
            "**Format:** `/addbirthday U123456789 MM-DD`\n"
            "**Example:** `/addbirthday U098G5UV54P 07-22`")
        return
    
    user_id = parts[0]
    birthday_date = parts[1]
    
    # Validate Slack ID format
    if not user_id.startswith('U'):
        say("❌ Invalid Slack ID! It should start with 'U'\n\n"
            "**Format:** `/addbirthday U123456789 MM-DD`\n\n"
            "💡 **How to find Slack ID:** Right-click someone's name → Copy member ID")
        return
    
    # Validate date format
    try:
        test_date = datetime.strptime(f"2024-{birthday_date}", "%Y-%m-%d")
        month = test_date.month
        day = test_date.day
        zodiac_emoji, zodiac_name = get_zodiac_sign(month, day)
    except ValueError:
        say("❌ Invalid date format! Please use MM-DD\n\n"
            "**Format:** `/addbirthday U123456789 MM-DD`\n"
            "**Example:** `/addbirthday U098G5UV54P 07-22`")
        return
    
    # Get user's real name
    try:
        user_info = client.users_info(user=user_id)
        user_name = user_info['user']['real_name']
    except:
        user_name = "Unknown User"
    
    birthdays = load_birthdays()
    birthdays[user_id] = {
        "name": user_name,
        "date": birthday_date
    }
    save_birthdays(birthdays)
    
    say(f"✅ Birthday saved for <@{user_id}> ({user_name})!\n"
        f"📅 Date: {birthday_date}\n"
        f"{zodiac_emoji} Zodiac: *{zodiac_name}*")

@app.command("/addanniversary")
def handle_add_anniversary(ack, command, say, client):
    """Add a work anniversary using Slack user ID"""
    ack()
    
    text = command['text'].strip()
    
    if not text:
        say("Please provide a Slack user ID and anniversary date!\n\n"
            "**Format:** `/addanniversary U123456789 MM-DD-YYYY`\n"
            "**Example:** `/addanniversary U098G5UV54P 03-12-2026`\n\n"
            "💡 **How to find Slack ID:** Right-click someone's name → Copy member ID")
        return
    
    parts = text.split()
    
    if len(parts) < 2:
        say("Please provide both Slack ID and date!\n\n"
            "**Format:** `/addanniversary U123456789 MM-DD-YYYY`\n"
            "**Example:** `/addanniversary U098G5UV54P 03-12-2026`")
        return
    
    user_id = parts[0]
    anniversary_date = parts[1]
    
    # Validate Slack ID format
    if not user_id.startswith('U'):
        say("❌ Invalid Slack ID! It should start with 'U'\n\n"
            "**Format:** `/addanniversary U123456789 MM-DD-YYYY`\n\n"
            "💡 **How to find Slack ID:** Right-click someone's name → Copy member ID")
        return
    
    # Validate date format (MM-DD-YYYY)
    try:
        datetime.strptime(anniversary_date, "%m-%d-%Y")
    except ValueError:
        say("❌ Invalid date format! Please use MM-DD-YYYY (include the year)\n\n"
            "**Format:** `/addanniversary U123456789 MM-DD-YYYY`\n"
            "**Example:** `/addanniversary U098G5UV54P 03-12-2026`")
        return
    
    # Get user's real name
    try:
        user_info = client.users_info(user=user_id)
        user_name = user_info['user']['real_name']
    except:
        user_name = "Unknown User"
    
    # Calculate years
    years = calculate_years(anniversary_date)
    years_text = format_years(years)
    
    anniversaries = load_anniversaries()
    anniversaries[user_id] = {
        "name": user_name,
        "date": anniversary_date
    }
    save_anniversaries(anniversaries)
    
    say(f"✅ Work anniversary saved for <@{user_id}> ({user_name})!\n"
        f"📅 Start date: {anniversary_date}\n"
        f"🎊 Current tenure: {years_text}")

@app.command("/removebirthday")
def handle_remove_birthday(ack, command, say):
    """Remove a birthday using Slack user ID"""
    ack()
    
    text = command['text'].strip()
    
    if not text:
        say("Please provide a Slack user ID!\n\n"
            "**Format:** `/removebirthday U123456789`\n"
            "**Example:** `/removebirthday U098G5UV54P`\n\n"
            "💡 **How to find Slack ID:** Right-click someone's name → Copy member ID")
        return
    
    user_id = text.strip()
    
    # Validate Slack ID format
    if not user_id.startswith('U'):
        say("❌ Invalid Slack ID! It should start with 'U'\n\n"
            "**Format:** `/removebirthday U123456789`")
        return
    
    birthdays = load_birthdays()
    
    if user_id not in birthdays:
        say(f"❌ No birthday found for <@{user_id}>")
        return
    
    user_name = birthdays[user_id].get('name', 'Unknown')
    del birthdays[user_id]
    save_birthdays(birthdays)
    
    say(f"✅ Birthday removed for <@{user_id}> ({user_name})")

@app.command("/removeanniversary")
def handle_remove_anniversary(ack, command, say):
    """Remove a work anniversary using Slack user ID"""
    ack()
    
    text = command['text'].strip()
    
    if not text:
        say("Please provide a Slack user ID!\n\n"
            "**Format:** `/removeanniversary U123456789`\n"
            "**Example:** `/removeanniversary U098G5UV54P`\n\n"
            "💡 **How to find Slack ID:** Right-click someone's name → Copy member ID")
        return
    
    user_id = text.strip()
    
    # Validate Slack ID format
    if not user_id.startswith('U'):
        say("❌ Invalid Slack ID! It should start with 'U'\n\n"
            "**Format:** `/removeanniversary U123456789`")
        return
    
    anniversaries = load_anniversaries()
    
    if user_id not in anniversaries:
        say(f"❌ No anniversary found for <@{user_id}>")
        return
    
    user_name = anniversaries[user_id].get('name', 'Unknown')
    del anniversaries[user_id]
    save_anniversaries(anniversaries)
    
    say(f"✅ Work anniversary removed for <@{user_id}> ({user_name})")

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

@app.event("app_mention")
def handle_mentions(body, say):
    """Respond to mentions"""
    say(f"Hi <@{body['event']['user']}>! 👋 I'm the Celebration Bot!\n\n"
        f"*View Celebrations:*\n"
        f"• `/listbirthdays` - See all birthdays\n"
        f"• `/listanniversaries` - See all anniversaries\n"
        f"• `/upcomingbirthdays` - Next 2 months of birthdays\n"
        f"• `/upcominganniversaries` - Next 2 months of anniversaries\n"
        f"• `/todayscelebrations` - Check today's celebrations\n\n"
        f"*Admin Commands:*\n"
        f"• `/addbirthday U123456 MM-DD` - Add a birthday\n"
        f"• `/addanniversary U123456 MM-DD-YYYY` - Add anniversary\n"
        f"• `/removebirthday U123456` - Remove birthday\n"
        f"• `/removeanniversary U123456` - Remove anniversary\n"
        f"• `/importcelebrations` - Bulk import from CSV\n"
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
    print("⚡️ Celebration Bot v5.2 is running!")
    handler.start()
