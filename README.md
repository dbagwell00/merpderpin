# Telegram Bot thing for Radio Messages

This is pretty rough and ymmv, but it's fun to play around with.

This Takes MP3s (trunking recorder) of Radio Messages (Unitrunker) and converts them to Text using Whisper (https://github.com/openai/whisper).
It sends them to a Telegram bot, which listens for questions.
Questions are processed using Langchain/ChatAI to produce answers.

You can Google how telebot and Botfather work to get the API and Channel ID stuff.
You'll need to register to get a api key for OPENAI_API_KEY.

I have 4 usb sdr plugged into a ANTRONIX 9-PORT VRA900. This listens to a shared statewide (edacs) system.
I use Unitrunker (which is windows only) to 'follow' the control channel and then tune the other 3 radios to 'listen'.

Unitrunker can be found here: https://groups.google.com/g/unitrunker

A second windows app called Trunking Recorder writes the messages to Mp3 on a shared network folder hosted by my NAS.

Trunking Recorder can be found here: https://groups.google.com/g/trunking-recorder

This program was written to convert those MP3s to Text, and then send them via Telebot to Telegram.  I wanted to be able to read the messages.

Whisper does a decent job of taking the audio and making it text.  It works better on longer messages, so I filter (both in Trunking Recorder, and in the script) based on the length of the call.

My big GPU (an RTX 3090) is on my gaming PC, so I run this in Docker.  You might not need a GPU to run Whisper (it supports CPU) but since I have one I'm using it.
Since my radios record the MP3s to a file share, you have to tell Docker where the volume is, and allow the container to mount it.  You could also write samba things into the Dockerfile I guess, but this was easier.

Some of the derpy things in there are because the script will attempt to load a file that's still 'open' by the other computer writing the MP3 to the filesystem.

I launch it like this:
docker run -it --entrypoint=bash --gpus all --mount source=radio,target=/data wwhisper

For the ollama stuff to work, I just run the docker container like this:
docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama

Then on the whisper container you tell it to use that with something like:
export OLLAMA_HOST=<urcomputerip:11434>

You'll be able to talk to your bot and ask it questions about what's happened.  It's pretty neat!


