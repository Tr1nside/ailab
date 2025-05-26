def get_context(text, context):
    return f"{context}\n{text}"


def ask_bot(text, context):
    update_context = f"{context}\n{text}"
    response = "Сообщение прочтанно"
    return update_context, response

