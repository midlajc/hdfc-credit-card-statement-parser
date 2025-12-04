import os
from dotenv import load_dotenv
from pathlib import Path
from telegram import Update, Document, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, 
    MessageHandler, filters, CallbackContext,CallbackQueryHandler
)
from old_plumber import process_pdf_old
from new_plumber import process_pdf_new

load_dotenv()
TOKEN = os.getenv("TG_BOT_TOKEN")

# Ensure necessary directories exist
os.makedirs("./input", exist_ok=True)
os.makedirs("./output", exist_ok=True)

# Dictionary to store pending files waiting for a password
pending_files = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message to the user."""
    await update.message.reply_text('Hi! Send me a PDF file to convert it to CSV.')

async def process_file(update: Update, context: CallbackContext) -> None:
    """Processes the received PDF file and converts it to CSV."""
    pdf_file: Document = update.message.document
    
    # Ensure it's a valid PDF
    if pdf_file.mime_type not in ['application/pdf', 'application/octet-stream'] or not pdf_file.file_name.lower().endswith('.pdf'):
        await update.message.reply_text('Please send a valid PDF file.')
        return

    file_id = pdf_file.file_id
    file_name = pdf_file.file_name.replace(" ", "")  # Avoid spaces in file names
    input_file = f'./input/{file_id}_{file_name}'
    output_file = f'./output/{file_id}.csv'

    # Try to extract password from message caption
    password = update.message.caption.strip() if update.message.caption else None

    pending_files[update.message.chat_id] = {
            "file_id": file_id, "file_name": file_name,
            "input_file": input_file, "output_file": output_file,
            "password": None,
            "format": None
        }
        
    # Store password if provided in caption
    if password:
        pending_files[update.message.chat_id]['password'] = password
        
    # Ask for format choice using inline buttons
    keyboard = [
        [InlineKeyboardButton("Old Format", callback_data='old')],
        [InlineKeyboardButton("New Format", callback_data='new')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Please choose the format:', reply_markup=reply_markup)
    return

async def receive_password(update: Update, context: CallbackContext) -> None:
    """Receives the user's password and processes the pending file."""
    chat_id = update.message.chat_id
    if chat_id not in pending_files:
        await update.message.reply_text("No pending PDF file found. Please send a new PDF.")
        return
    password = update.message.text.strip()
    pending_files[chat_id]['password'] = password
    
    file_info = pending_files[chat_id]
    
    await process_pdf_file(
        update.message,
        context,
        file_info['file_id'],
        file_info['file_name'],
        file_info['input_file'],
        file_info['output_file'],
        file_info['password'],
        file_info['format']
    )
    
async def receive_format(update: Update, context: CallbackContext) -> None:
    """Receives the user's format choice and processes the pending file."""
    chat_id = update.callback_query.message.chat.id
    if chat_id not in pending_files:
        await update.callback_query.message.reply_text("No pending PDF file found. Please send a new PDF.")
        return

    user_format = update.callback_query.data.strip().lower()
    if user_format not in ['old', 'new']:
        await update.callback_query.message.reply_text("Invalid format. Please reply with 'old' or 'new'.")
        return

    pending_files[chat_id]['format'] = user_format
    file_info = pending_files.pop(chat_id)
    
    # Ask for password if not already provided
    if not file_info['password']:
        # Remove format selection message 
        await update.callback_query.message.delete()
        await update.callback_query.message.reply_text("Please provide the password for the PDF (or type 'none' if there is no password):")
        return
    
    # send processing message and delete callback message
    await update.callback_query.message.reply_text("Processing your file, please wait...")
    await update.callback_query.message.delete()

    await process_pdf_file(
        update.callback_query.message, 
        context,
        file_info['file_id'],
        file_info['file_name'],
        file_info['input_file'],
        file_info['output_file'],
        file_info['password'],
        file_info['format']
    )

async def process_pdf_file(message, context, file_id, file_name, input_file, output_file, password, user_format):
    """Handles the actual PDF processing and sends the output CSV."""
    try:
        new_pdf_file = await context.bot.get_file(file_id)
        await new_pdf_file.download_to_drive(custom_path=input_file)

        # Process the PDF
        if user_format == 'old':
            process_pdf_old(input=input_file, output=output_file, password=password, debugLog=False)
        else:
            process_pdf_new(input=input_file, output=output_file, password=password, debugLog=False)

        # Send the CSV file
        output_path = Path(output_file)
        await message.reply_document(output_path, filename=file_name.replace(".pdf", ".csv").replace(".PDF", ".csv"))

    except Exception as e:
        print(e)
        await message.reply_text(f"An error occurred while processing your file: {str(e)}")
    finally:
        # Cleanup files
        for file in [input_file, output_file]:
            try:
                os.remove(file)
            except FileNotFoundError:
                pass

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, process_file))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_password))
    app.add_handler(CallbackQueryHandler(receive_format))

    app.run_polling()