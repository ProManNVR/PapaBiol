import re
import os
import telegram
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

TOKEN = "7827776450:AAHg41ab3nnzpm56RyOSfexdNAtul-j3Cmc"  # Replace with your actual bot token
ADMIN_IDS = {6433690542, 7827776450}  # Replace with your actual admin user IDs as a set
AUTHORIZED_USERS = set()

# Load authorized users from a file
AUTH_FILE = "authorized_users.txt"
if os.path.exists(AUTH_FILE):
    with open(AUTH_FILE, "r") as f:
        AUTHORIZED_USERS = set(map(int, f.read().splitlines()))

def save_auth_users():
    with open(AUTH_FILE, "w") as f:
        f.write("\n".join(map(str, AUTHORIZED_USERS)))

def is_admin(update: Update) -> bool:
    return update.message.from_user.id in ADMIN_IDS

def is_authorized(update: Update) -> bool:
    return update.message.from_user.id in AUTHORIZED_USERS or is_admin(update)

def grant_access(update: Update, context: CallbackContext) -> None:
    if not is_admin(update):
        update.message.reply_text("🚫 You are not authorized to use this command.")
        return
    
    if context.args:
        user_id = int(context.args[0])
        AUTHORIZED_USERS.add(user_id)
        save_auth_users()
        update.message.reply_text(f"✅ User {user_id} has been granted access.")
    else:
        update.message.reply_text("⚠️ Usage: /grant <user_id>")

def revoke_access(update: Update, context: CallbackContext) -> None:
    if not is_admin(update):
        update.message.reply_text("🚫 You are not authorized to use this command.")
        return
    
    if context.args:
        user_id = int(context.args[0])
        AUTHORIZED_USERS.discard(user_id)
        save_auth_users()
        update.message.reply_text(f"❌ User {user_id} has been revoked access.")
    else:
        update.message.reply_text("⚠️ Usage: /revoke <user_id>")

def start(update: Update, context: CallbackContext) -> None:
    if is_authorized(update):
        update.message.reply_text("📥 Send me a combo file, and I'll sort the emails for you!")
    else:
        update.message.reply_text("🚫 You are not authorized to use this bot.")

def handle_document(update: Update, context: CallbackContext) -> None:
    if not is_authorized(update):
        update.message.reply_text("🚫 You are not authorized to use this bot.")
        return
    
    file = update.message.document
    file_path = f"downloads/{file.file_name}"
    os.makedirs("downloads", exist_ok=True)
    
    file_id = file.file_id
    new_file = context.bot.get_file(file_id)
    new_file.download(file_path)
    
    update.message.reply_text("🔄 Processing file... 📂")
    separate_emails(update, file_path)
    
    for provider in ["gmail", "microsoft", "yahoo", "others"]:
        output_file = f"{provider}.txt"
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            with open(output_file, "rb") as f:
                update.message.reply_document(f, caption=f"✅ Sorted {provider} emails!")
    
    update.message.reply_text("🎉 Sorting completed! Here are the sorted files.")

def separate_emails(update: Update, file_path):
    email_providers = {
        "gmail": "gmail.com",
        "microsoft": ["outlook.com", "hotmail.com", "live.com", "msn.com"],
        "yahoo": ["yahoo.com", "ymail.com", "rocketmail.com"],
    }
    
    output_files = {provider: open(f"{provider}.txt", "w") for provider in email_providers}
    output_files["others"] = open("others.txt", "w")
    
    total_count = 0
    count_per_provider = {provider: 0 for provider in email_providers}
    count_per_provider["others"] = 0
    
    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            match = re.match(r'([^:@]+@([^:@]+)):(.+)', line)
            
            if match:
                email, domain, password = match.groups()
                stored = False
                total_count += 1
                
                for provider, domains in email_providers.items():
                    if isinstance(domains, list) and domain in domains:
                        output_files[provider].write(f"{email}:{password}\n")
                        count_per_provider[provider] += 1
                        stored = True
                        break
                    elif isinstance(domains, str) and domain == domains:
                        output_files[provider].write(f"{email}:{password}\n")
                        count_per_provider[provider] += 1
                        stored = True
                        break
                
                if not stored:
                    output_files["others"].write(f"{email}:{password}\n")
                    count_per_provider["others"] += 1
                
                if total_count % 100 == 0:
                    update.message.reply_text(f"📊 Processed {total_count} emails so far...")
    
    for file in output_files.values():
        file.close()
    
    summary = "📊 Sorting Summary:\n"
    for provider, count in count_per_provider.items():
        summary += f"✅ {provider.capitalize()}: {count}\n"
    update.message.reply_text(summary)

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("grant", grant_access, pass_args=True))
    dp.add_handler(CommandHandler("revoke", revoke_access, pass_args=True))
    dp.add_handler(MessageHandler(Filters.document, handle_document))
    
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
