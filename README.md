# Telegram Bot thing for Radio Messages

This Takes MP3s (trunking recorder) of Radio Messages (Unitrunker) and converts them to Text using Whisper.
It sends them to a Telegram bot, which listens for questions.
Questions are processed using Langchain/ChatAI to produce answers.

It expects an nvidia gpu.
It expects a volume to mount a network share (where the mp3s live), mounted into /data on the container.

docker run -it --entrypoint=bash --gpus all --mount source=radio,target=/data wwhisper


