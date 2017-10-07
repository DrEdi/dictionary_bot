import config
import os
import telebot
import sqlalchemy as sa

from flask import Flask, request
from models import Base


engine = sa.create_engine(config.DATABASE_URL, echo=True)
bot = telebot.TeleBot(config.TOKEN)
app = Flask(__name__)


@app.route(f"/{config.TOKEN}", methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "!", 200


@app.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url=f"https://young-wildwood-79639.herokuapp.com/{config.TOKEN}")
    return "!", 200


if __name__ == "__main__":
    Base.metadata.create_all(engine)
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
