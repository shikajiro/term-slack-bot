import logging
import os
from typing import List

import gspread
import jaconv
from oauth2client.service_account import ServiceAccountCredentials
from slackbot.bot import Bot
from slackbot.bot import respond_to
from slackbot.dispatcher import Message

handler = logging.streamhandler()
logger = logging.getlogger(__name__)
logger.addhandler(handler)
logger.setlevel("debug")

logger_channel_id = os.getenv("logger_channel_id")
spreadsheet_key = os.getenv("spreadsheet_key")
spreadsheet = f"https://docs.google.com/spreadsheets/d/{spreadsheet_key}"
scopes = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
]

credentials = ServiceAccountCredentials.from_json_keyfile_name("serviceaccountcredentials.json", scopes)
spread = gspread.authorize(credentials)


def main():
    bot = Bot()
    bot.run()


@respond_to("(.*)")
def search(message: Message, something: str):
    try:
        logger.debug(message.body)
        logger.debug(something)

        if something == "help" or not something:
            message.reply(
                f"知りたい用語を教えてほしいワン！ `@tellme 用語` で答えるワン。 用語集の管理は <{spreadsheet}|用語集> ここで管理しているワン。どんどん追加して欲しいワン。")
            return

        # ログとして #bot_test_tellme に出力する
        if logger_channel_id:
            text = f"user:{message.user['name']}, channel:{message.channel._body['name']}, query:{something}"
            message._client.rtm_send_message(logger_channel_id, text)

        worksheet = spread.open_by_key(spreadsheet_key).sheet1
        query: str = something.strip().lower()
        query = jaconv.hira2kata(query)
        query = jaconv.h2z(query)

        res_text: List[str] = []
        for row in worksheet.get_all_values():
            # 英数字は小文字に統一
            # ひらがなは全角カタカナに統一
            target: str = row[0].lower()
            target = jaconv.hira2kata(target)
            target = jaconv.h2z(target)
            if target == "":
                break
            elif (len(query) >= 2 and query in target) or query == target:
                title = ",".join(row[0].split("\n"))
                res_text.append(f"*{title}*\n{row[1]}")

        if not res_text:
            res_text.append(f"わからなかったワン・・・。意味が分かったら <{spreadsheet}|用語集> に追加して欲しいワン")

        message.reply("\n\n".join(res_text))
    except Exception as e:
        logger.exception(e)
        message.reply("エラーが発生したワン・・・")


if __name__ == "__main__":
    main()
