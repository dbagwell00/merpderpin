FROM nvidia/cuda:12.1.0-runtime-ubuntu20.04
ENV DEBIAN_FRONTEND noninteractive
RUN apt-get update && apt-get install -y python3 python3-pip python3-dev libsndfile1 ffmpeg vim
RUN apt-get install -y git
RUN pip install --upgrade pip
RUN pip3 install telebot spacy
RUN pip install git+https://github.com/openai/whisper.git
RUN pip install numba
RUN pip install pydub
RUN pip install openai
RUN pip install chromadb
RUN pip install langchain
RUN pip install asyncio

COPY wwatch.py /app/

WORKDIR /app/

CMD ["python3", "wwatch.py"]
