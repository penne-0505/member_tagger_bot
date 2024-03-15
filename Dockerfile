FROM python:3.11
WORKDIR /bot
COPY requirements.txt /bot/
RUN pip install -r requirements.txt
COPY . /bot
# cd to src, then run the bot
CMD ["python", "src/main.py"]