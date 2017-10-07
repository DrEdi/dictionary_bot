import config
import os
import telebot
import sqlalchemy as sa
import json
import random
import requests

from flask import Flask, request
from models import Base

from models import User, Word, WordToUser
from utils import (
    set_user_game,
    get_answer_for_user,
    finish_user_game,
    create_code_snippet

)


engine = sa.create_engine(config.DATABASE_URL, echo=True)
bot = telebot.TeleBot(config.TOKEN)
app = Flask(__name__)
Session = sa.orm.sessionmaker(bind=engine)


@app.route(f"/{config.TOKEN}", methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "!", 200


@app.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url=f"https://young-wildwood-79639.herokuapp.com/{config.TOKEN}")
    return "!", 200


@bot.message_handler(commands=['help_me'])
def help_message(message):
    """Send message to user with explaining game rules."""

    text = """
    Hello, I'm a super dictionary bot!
    I'll glad to help you with learning new words!
    For register please call /start command!
    Game: first of all you need to add some words to you dictionary
    call /add <your word> command to add new one
    When you'll be ready, just call /game command.
    If you feel that it's enough for today, call /end command just from game
    To see list of all words in dictionary - call /show_all command!
    Hope you'll like me!
    Let's start!
    """
    bot.send_message(message.chat.id, text)


@bot.message_handler(commands=['start'])
def repeat_hello(message):
    """Register new user to db."""

    session = Session()
    u = session.query(User).filter_by(chat_id=message.chat.id).first()
    if u:
        return bot.send_message(message.chat.id, "You already in game!")
    user = User(chat_id=message.chat.id)
    session.add(user)
    session.commit()
    session.close()
    bot.send_message(message.chat.id, "You're in game!")


@bot.message_handler(commands=['show_all'])
def show_all_words(message):
    """Return list of all words registered for current user."""

    session = Session()
    text = "|{}|{}|\n".format('Word'.ljust(23), 'Translation'.ljust(23))
    for w in session.query(Word).join(WordToUser).join(User).filter(User.chat_id==message.chat.id).all():
        text += "|{}|{}|\n".format(w.name.ljust(23), w.translation.ljust(23))
    bot.send_message(message.chat.id, create_code_snippet(text), parse_mode='Markdown')
    session.close()


def end_training(message):
    """End game, if user send /end command."""

    keyboad = telebot.types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, 'Thanks for game! See you later', reply_markup=keyboad)
    finish_user_game(message.chat.id)


@bot.message_handler(commands=['game'])
def training_mode(message):
    """Start new game with current user."""

    session = Session()
    data = []
    for word in session.query(Word).join(WordToUser).join(User).filter(User.chat_id == message.chat.id).all():
        data.append({"name": f'{word.name}', "translation": f'{word.translation}'})
    if not data:
        return bot.send_message(message.chat.id, "Add some words before!")
    if len(data) == 1:
        return bot.send_message(message.chat.id, "You must have more than 2 words!")
    random.shuffle(data)
    session.close()
    word = data.pop(-1)
    wrong_word = data[0]
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add(word['translation'])
    markup.add(wrong_word['translation'])
    set_user_game(message.chat.id, word['translation'])
    msg = bot.send_message(message.chat.id, f"{word['name']}", reply_markup=markup)
    bot.register_next_step_handler(msg, check_answer)


def check_answer(message):
    """Check if response from user if valid."""

    answer = get_answer_for_user(message.chat.id)
    if message.text == answer:
        bot.send_message(message.chat.id, f'🎉🎉 SO GOOD! 🎉🎉')
    elif message.text == '/end':
        return end_training(message)
    else:
        bot.send_message(message.chat.id, f'🌚🌚 Nope, right answer is: {answer} 🌚🌚')
    return training_mode(message)


@bot.message_handler(commands=['add'])
def create_word(message):
    """Add new word to DB and register for current user."""

    session = Session()
    u = session.query(User).filter_by(chat_id=message.chat.id).first()
    if not u:
        bot.send_message(message.chat.id, "Send /start to register")
    else:
        word = ' '.join(message.text.split(' ')[1:]).lower()
        w = session.query(Word).filter_by(name=word).first()
        if not w:
            web_session = requests.session()
            web_session.get('http://service.m-translate.com/translate')
            resp = web_session.post('http://service.m-translate.com/translate',
                                    data={"translate_to": "ru",
                                          "translate_from": "en",
                                          "text": word}
                                    )
            info = json.loads(resp.text)
            w_instance = Word(name=word, translation=info['translate'])
            session.add(w_instance)
            session.commit()
            session.add(WordToUser(user=u.id, word=w_instance.id))
            session.commit()
            bot.send_message(message.chat.id, info['translate'])
        else:
            session.add(WordToUser(user=u.id, word=w.id))
            session.commit()
            bot.send_message(message.chat.id, f"I added this word to your dict. Translation: {w.translation}")
    session.close()


@bot.message_handler(commands=['delete'])
def delete_user_word(message):
    session = Session()
    word = ' '.join(message.text.split(' ')[1:]).lower()
    w = session.query(WordToUser).join(Word).join(User).filter(User.chat_id == message.chat.id,
                                                               Word.name == word).first()
    if not w:
        bot.send_message(message.chat.id, f"Oops, you do now have word {word} in your dict")
    else:
        session.delete(w)
        session.commit()
        bot.send_message(message.chat.id, "I deleted it. Don't forget to add some new 😚")
    session.close()


if __name__ == "__main__":
    Base.metadata.create_all(engine)
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
