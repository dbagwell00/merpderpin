import os
import time
import telebot
import whisper
import re
from pydub import AudioSegment

__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

import chromadb
import threading
from datetime import datetime


# do the chroma things
chromadb_client = chromadb.PersistentClient(path="./db")
chromadb_collection = chromadb_client.get_or_create_collection(name="RADIO")

import ollama
model = whisper.load_model("large")
bot = telebot.TeleBot("<ur telebot key")
chat_id = "<ur chat id>"
start_time = time.time()
folder_path = "/data/"
processed_files = set()


def process_file(file_path):
    attempt_count = 0
    max_attempts = 10
    # Check if the file has already been processed
    if file_path in processed_files:
        return

    # Wait for the file to finish writing
    while True:
        try:
            with open(file_path, 'rb') as f:
                f.seek(-128, os.SEEK_END)
                if f.read(128).startswith(b'TAG'):
                    break
        except Exception as error:
            # print(error)
            time.sleep(1)
            attempt_count += 1
            if attempt_count >= max_attempts:
                break

    try:
        # example file path
        # /data/2023-06-11/273-Green 1/2023-06-11_084949_273-Green 1_12598-_22_1.mp3
        # 754-Reno 2 (RN 2 - Carson Area) is the target (754) and label (RN 2 - Carson Area)
        # 11316 is the source and there doesnt appear to be a label associated with it
        split_strings = file_path.split('/')
        last_part = split_strings[-1]
        split_last_part  = last_part.split('_')
        groupid = split_last_part[2].split('-')[0]
        group = split_last_part[2]
        sourceid = split_last_part[3].split('-')[0]
        source = split_last_part[3].split('-')[1]

        # group_markdown = telebot.formatting.escape_markdown(group)


        audio = AudioSegment.from_file(file_path)
        duration = int(len(audio) / 1000)
    except Exception as error:
        print(f'Audio Length Error: {error}')
        time.sleep(1)

    # Check if the mp3 file is longer than  seconds
    if duration < 5:
        # print(f'Skipping {file_path} - file too short')
        processed_files.add(file_path)
        return

    print(f'Processing: {file_path}...')

    try:
        text = model.transcribe(file_path)
        message = text["text"]
        reply_message = (f"On {datetime.now()} we think {sourceid} said to {groupid} (which is also known as {group}): {message}\n")

        response = ollama.embeddings(model="mistral:latest", prompt=reply_message)
        embedding = response["embedding"]
        # print(f'embeddings: {embedding}')
        chromadb_collection.add(
                ids=[datetime.now().strftime('%Y%m%d%H%M%S')],
                embeddings=[embedding],
                documents=[reply_message])


        print(f'Message: {reply_message}')
    except Exception as error:
        print(f'Model error: {error}')
        pass


    try:

        reply_message = (f"On {datetime.now()} We think **{sourceid}** said to **{groupid}** (which is named {group}): \"{message}\"\n")
        # \n\nAlso: {results}")
        bot.send_audio(chat_id, audio=open(file_path, 'rb'))
        bot.send_message(chat_id, reply_message, parse_mode='MARKDOWN')

    except Exception as error:
        print(f'Match Error: {error}')
    print('------------------------------------')
    processed_files.add(file_path)

@bot.message_handler(func=lambda message: True)
def echo_message(message):
   prompt = f'You are a radio dispatcher and listen to radio messages coming in. Please list the relevant quotes from the source material in the list.  {message.text}'

   response = ollama.embeddings(
           prompt=prompt,
           model="mistral:latest")

   embedding_results = chromadb_collection.query(
           query_embeddings=[response["embedding"]],
           n_results=10)

   test_data = embedding_results['documents']

   test_output = ollama.generate(
           model="mistral:latest",
           prompt=f"Using this data: {test_data}.  Respond to this prompt: {prompt}"
           )

   result_thing = (f"Result: {test_output['response']}")
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
                      print(error)
                      pass

    # Wait for new files to be added to the folder
    time.sleep(1)
