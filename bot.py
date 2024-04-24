import os
from dotenv import load_dotenv
from pathlib import Path
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from plumber import process_pdf

load_dotenv()

TOKEN = os.getenv("TG_BOT_TOKEN")

async def start(update:Update,context:ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Hi! Send me a PDF file.')

async def process_file(update:Update,context:ContextTypes.DEFAULT_TYPE) -> None:
    pdf_file = update.message.document
    input_file = f'./input/{pdf_file.file_id}.pdf'
    output_file = f'./output/{pdf_file.file_id}.csv'

    if (pdf_file.mime_type == 'application/binary' or pdf_file.mime_type == 'application/pdf') \
        and pdf_file.file_name.split(".")[-1] in ['PDF','pdf'] :
        new_pdf_file = await context.bot.get_file(pdf_file.file_id)
        downloaded_file = await new_pdf_file.download_to_drive(
            custom_path=input_file,
        )
        
        password = pdf_file.file_name.split("-")[-1].split(".")[0].strip()
        if password == "":
            password = None

        process_pdf(input=downloaded_file ,output=output_file, password=password , debugLog=False)
        
        #Open out put file and send it
        output = Path(output_file)
        await update.message.reply_document(output, filename=pdf_file.file_name.replace(".pdf", ".csv").replace(".PDF", ".csv"))

        # delete the file
        output.unlink()
        downloaded_file.unlink()
    else:
        await update.message.reply_text('Please send a PDF file.')

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler(command="start", callback=start))
    app.add_handler(MessageHandler(filters=filters.Document.ALL, callback=process_file))

    app.run_polling()