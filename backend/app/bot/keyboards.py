from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("Я на смене", request_location=True)],
            [KeyboardButton("Закончил работу")],
            [KeyboardButton("Статус смены")],
        ],
        resize_keyboard=True,
    )


def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()
