import os
import time
import telebot
import whisper
import re
from pydub import AudioSegment
import chromadb

import threading
# from telebot.async_telebot import AsyncTeleBot
# import asyncio

from datetime import datetime


from langchain.document_loaders import TextLoader
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain.llms import OpenAI
from langchain.text_splitter import CharacterTextSplitter
from langchain.text_splitter import RecursiveCharacterTextSplitter

from langchain.chains.question_answering import load_qa_chain



os.environ['OPENAI_API_KEY']="ur-key"




model = whisper.load_model("large")
# set up the telegram bot
bot = telebot.TeleBot("ur-key")
chat_id = "ur-chat-id"
start_time = time.time()
folder_path = "/data/"
processed_files = set()


def langthing(question):

    # Load documents from the './messages' directory using TextLoader
    loader = TextLoader("./messages")
    documents = loader.load()

    # Split documents into smaller chunks using CharacterTextSplitter
    # text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=0)
    texts = text_splitter.split_documents(documents)

    # Create embeddings using OpenAIEmbeddings
    embeddings = OpenAIEmbeddings()

    # Initialize a Chroma vector store using embeddings created from the documents
    vectordb = Chroma.from_documents(texts, embeddings)

    # Load a question-answering chain which uses an OpenAI LLM (language model) and 'map_reduce' chain type
    # qa_chain = load_qa_chain(llm=OpenAI(), chain_type="map_reduce")
    # qa_chain = load_qa_chain(llm=OpenAI(), chain_type="stuff")

    # Initialize a RetrievalQA instance using the combine_documents_chain (qa_chain) and chroma vector store 'vectordb'
    # qa = RetrievalQA(combine_documents_chain=qa_chain, retriever=vectordb.as_retriever())
    qa = RetrievalQA.from_chain_type(llm=OpenAI(), chain_type="stuff", retriever=vectordb.as_retriever())

    # Run the RetrievalQA instance with the given question and store the results
    results = qa.run(question)

    return results


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
        herps = open("./messages", "a")
        herps.write(reply_message)
        # herps.close()
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
    results = langthing(message.text)
    result_thing = (f"Asked: {message.text}.  Result: {results}")
    # bot.send_message(chat_id, result_thing)
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
