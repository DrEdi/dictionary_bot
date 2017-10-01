import config
import json
import telebot
import random
import requests
import sqlalchemy as sa

from sqlalchemy.orm import sessionmaker

from models import Base, User, Word, WordToUser
from utils import set_user_game, get_answer_for_user, finish_user_game



bot = telebot.TeleBot(config.TOKEN)
engine = sa.create_engine('sqlite:///main_db', echo=True)
Session = sessionmaker(bind=engine)

@bot.message_handler(commands=['help_me'])
def help_message(message):
	text = """
	Hello, I'm a super dictionary bot!
	I'll glad to help you with learning new words!
	Look, first of all you need to add some words to you dictionary
	call /add <your word> command to add new word
	When you'll be ready, just call /train comand.
	If you feel that it's enough for today, call /end command just from game
	to see list of all words in dictionary - call /show_all command!
	Hope you'll like me!
	Let's start!
	"""
	bot.send_message(message.chat.id, text)


@bot.message_handler(commands=['start'])
def repeat_hello(message):
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
	session = Session()
	text = 'Word: translation\n'
	for w in session.query(Word).join(WordToUser).join(User).filter(User.chat_id==message.chat.id).all():
		text += f'{w.name}: {w.translation}\n'
	bot.send_message(message.chat.id, text)
	session.close()


def end_training(message):
	keyboad = telebot.types.ReplyKeyboardRemove()
	bot.send_message(message.chat.id, 'Thanks for game! See you later', reply_markup=keyboad)
	finish_user_game(message.chat.id)


@bot.message_handler(commands=['train'])
def training_mode(message):
	session = Session()
	data = []
	for word in session.query(Word).join(WordToUser).join(User).filter(User.chat_id==message.chat.id).all():
		data.append({"name": f'{word.name}', "translation": f'{word.translation}'})
	if not data:
		return bot.send_message(message.chat.id, "Add some words before!")
	if len(data) == 1:
		return bot.send_message(message.chat.id, "You must have more than 2 words!")
	random.shuffle(data)
	session.close()
	main_iterator = len(data)-1
	word = data.pop(-1)
	wrong_word = data[0]
	markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
	markup.add(word['translation'])
	markup.add(wrong_word['translation'])
	set_user_game(message.chat.id, word['translation'])
	msg = bot.send_message(message.chat.id, f"{word['name']}", reply_markup=markup)
	bot.register_next_step_handler(msg, check_answer)


def check_answer(message):
	answer = get_answer_for_user(message.chat.id)
	if message.text == answer:
		bot.send_message(message.chat.id, 'Goog!')
	elif message.text == '/end':
		return end_training(message)
	else:
		bot.send_message(message.chat.id, 'Wrong answer')
	return training_mode(message)


@bot.message_handler(commands=['add'])
def create_word(message):
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
									 data={"translate_to":"ru",
									 	   "translate_from":"en",
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
			bot.send_message(message.chat.id, f"I aded this word to your dict. Translation: {w.translation}")
	session.close()


if __name__ == "__main__":
	Base.metadata.create_all(engine)
	bot.polling(none_stop=True)
