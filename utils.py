import shelve


def set_user_game(chat_id, estimated_answer):
    with shelve.open('shelve') as storage:
        storage[str(chat_id)] = estimated_answer


def finish_user_game(chat_id):
    with shelve.open('shelve') as storage:
        try:
            del storage[str(chat_id)]
        except KeyError:
            pass


def get_answer_for_user(chat_id):
    with shelve.open('shelve') as storage:
        try:
            answer = storage[str(chat_id)]
            return answer
        except KeyError:
            return None


def create_code_snippet(text):
    return f'```\n{text}\n```'

