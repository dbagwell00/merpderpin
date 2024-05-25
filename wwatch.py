import os
import time
import telebot
import whisper
import re
from pydub import AudioSegment
import sys
import chromadb
import threading
from datetime import datetime

# Adjust SQLite module import
__import__('pysqlite3')
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

# Initialize ChromaDB client and collection
chromadb_client = chromadb.PersistentClient(path="./db")
chromadb_collection = chromadb_client.get_or_create_collection(name="RADIO")

# Load Whisper model and initialize Telegram bot
model = whisper.load_model("large")
bot = telebot.TeleBot("<your_telebot_key>")
chat_id = "<your_chat_id>"
start_time = time.time()
folder_path = "/data/"
processed_files = set()

def process_file(file_path):
    if file_path in processed_files:
        return

    attempt_count = 0
    max_attempts = 10

    # Wait for the file to finish writing
    while attempt_count < max_attempts:
        try:
            with open(file_path, 'rb') as f:
                f.seek(-128, os.SEEK_END)
                if f.read(128).startswith(b'TAG'):
                    break
        except Exception:
            time.sleep(1)
            attempt_count += 1
    else:
        return

    try:
        # Extract group and source information from file name
        split_last_part = os.path.basename(file_path).split('_')
        groupid = split_last_part[2].split('-')[0]
        group = split_last_part[2]
        sourceid = split_last_part[3].split('-')[0]

        # Load audio file and get its duration
        audio = AudioSegment.from_file(file_path)
        duration = int(len(audio) / 1000)
    except Exception as error:
        print(f'Error processing audio file: {error}')
        return

    if duration < 5:
        processed_files.add(file_path)
        return

    print(f'Processing: {file_path}...')

    try:
        # Transcribe audio using Whisper
        text = model.transcribe(file_path)
        message = text["text"]
        reply_message = f"On {datetime.now()} we think {sourceid} said to {groupid} (which is also known as {group}): {message}\n"

        # Get embeddings from Ollama and store in ChromaDB
        response = ollama.embeddings(model="mistral:latest", prompt=reply_message)
        embedding = response["embedding"]
        chromadb_collection.add(
            ids=[datetime.now().strftime('%Y%m%d%H%M%S')],
            embeddings=[embedding],
            documents=[reply_message]
        )

        print(f'Message: {reply_message}')
    except Exception as error:
        print(f'Model error: {error}')
        return

    try:
        # Send transcription result and audio file via Telegram bot
        bot.send_audio(chat_id, audio=open(file_path, 'rb'))
        bot.send_message(chat_id, reply_message, parse_mode='MARKDOWN')
    except Exception as error:
        print(f'Telegram error: {error}')
    
    print('------------------------------------')
    processed_files.add(file_path)

@bot.message_handler(func=lambda message: True)
def echo_message(message):
    prompt = f'You are a radio dispatcher and listen to radio messages coming in. Please list the relevant quotes from the source material in the list. {message.text}'

    response = ollama.embeddings(
        prompt=prompt,
        model="mistral:latest"
    )

    embedding_results = chromadb_collection.query(
        query_embeddings=[response["embedding"]],
        n_results=10
    )

    test_data = embedding_results['documents']

    test_output = ollama.generate(
        model="mistral:latest",
        prompt=f"Using this data: {test_data}. Respond to this prompt: {prompt}"
    )

    result_thing = f"Result: {test_output['response']}"
    bot.send_message(chat_id, result_thing)
    bot.reply_to(message, result_thing)

def start_polling():
    bot.infinity_polling()

polling_thread = threading.Thread(target=start_polling)
polling_thread.start()

while True:
    for root, dirs, files in os.walk(folder_path):
        for filename in files:
            file_path = os.path.join(root, filename)
            if os.path.isfile(file_path) and file_path.endswith('.mp3'):
                mod_time = os.path.getmtime(file_path)
                if mod_time > start_time:
                    try:
                        process_file(file_path)
                    except Exception as error:
                        print(f'Error processing file {file_path}: {error}')
    time.sleep(1)