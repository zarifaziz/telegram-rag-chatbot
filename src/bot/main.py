import logging
import os

from telegram import Update
from telegram.ext import (ApplicationBuilder, CommandHandler, ContextTypes,
                          MessageHandler, filters)

from .settings import settings
from .speech_to_text import SpeechToTextWhisper
from .vector_shift import VectorShiftAPI

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

vector_shift_api = VectorShiftAPI(settings.VECTORSHIFT_API_KEY)
speech_to_text = SpeechToTextWhisper(settings.OPENAI_API_KEY)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the /start command from the user.

    Parameters
    ----------
    update : telegram.Update
        The update object that contains information about the message.
    context : telegram.ext.ContextTypes.DEFAULT_TYPE
        The context object that contains information about the Telegram bot and its state.

    Returns
    -------
    None
    """
    chat_id = update.effective_chat.id
    greeting_message = "Hello, I'm Team Influence Bot. How can I assist you?"
    await context.bot.send_message(chat_id=chat_id, text=greeting_message)


async def handle_caps_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Converts the text sent by the user to uppercase and sends it back to the user.

    Parameters
    ----------
    update : telegram.Update
        The update object that contains information about the message.
    context : telegram.ext.ContextTypes.DEFAULT_TYPE
        The context object that contains information about the Telegram bot and its state.

    Returns
    -------
    None
    """
    message_text = " ".join(context.args).upper()
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message_text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles incoming messages from the user and sends them to the VectorShift API for processing.

    Parameters
    ----------
    update : telegram.Update
        Contains information about the incoming message.
    context : telegram.ext.ContextTypes.DEFAULT_TYPE
        Contains information about the bot's state.

    Returns
    -------
    None
    """
    message = update.message
    user_message = None

    if message and message.text:
        user_message = message.text
    elif message and message.voice:
        file = await context.bot.get_file(message.voice.file_id)
        file_path = os.path.join("downloads", f"{file.file_id}.oga")
        await file.download_to_drive(file_path)
        try:
            user_message = speech_to_text.transcribe(file_path)
        finally:
            os.remove(file_path)
    else:
        logging.info("Received a message without text or voice, ignoring.")
        return

    if user_message:
        response = vector_shift_api.get_response(user_message)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Sorry, I couldn't process your message.",
        )


if __name__ == "__main__":
    application = ApplicationBuilder().token(settings.TELEGRAM_BOT_TOKEN).build()

    start_handler = CommandHandler("start", start)
    message_handler = MessageHandler(filters.TEXT | filters.VOICE, handle_message)

    application.add_handler(start_handler)
    application.add_handler(message_handler)

    application.run_polling()
