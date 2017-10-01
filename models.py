from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):
	__tablename__ = 'user'

	id = Column(Integer, primary_key=True)
	chat_id = Column(Integer)
	
	def __repr__(self):
		return f"Chat with user: {self.chat_id}"


class Word(Base):
	__tablename__ = 'word'
	
	id = Column(Integer, primary_key=True)
	name = Column(String)
	translation = Column(String)

	def __repr__(self):
		return f"{self.name}: {self.translation}"


class WordToUser(Base):
	__tablename__ = 'word_to_user'

	id = Column(Integer, primary_key=True)
	user = Column(Integer, ForeignKey('user.id'))
	word = Column(Integer, ForeignKey('word.id'))
	
