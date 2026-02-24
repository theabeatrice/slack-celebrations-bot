import os
import json
from datetime import datetime, date
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# Initialize the Slack app
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# File to store birthdays
BIRTHDAYS_FILE = "birthdays.json"

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
        datetime.strptime(birthday_date, "%m-%d")
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
        key=lambda x: datetime.strptime(x[1]['date'], "%m-%d")
    )
    
    message = "🎉 *Upcoming Birthdays* 🎉\n\n"
    for user_id, data in sorted_birthdays:
        date_obj = datetime.strptime(data['date'], "%m-%d")
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

# Event listener for app mentions
@app.event("app_mention")
def handle_mentions(body, say):
    """Respond when the bot is mentioned"""
    say(f"Hi <@{body['event']['user']}>! 👋 I'm the Birthday Bot! Use `/listbirthdays` to see all birthdays or `/addbirthday MM-DD` to add yours!")

# Simple message listener for "birthday" keyword
@app.message("birthday")
def respond_to_birthday_message(say):
    """Respond when someone mentions 'birthday' in a message"""
    say("Did someone say birthday? 🎂 Use `/listbirthdays` to see upcoming birthdays!")

if __name__ == "__main__":
    # Start the app using Socket Mode
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    print("⚡️ Birthday Bot is running!")
    handler.start()
