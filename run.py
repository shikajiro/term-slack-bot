import datetime
import logging
import os
from typing import List

import gspread
from gspread.models import Worksheet
import jaconv
from oauth2client.service_account import ServiceAccountCredentials
from slackbot.bot import Bot
from slackbot.bot import respond_to
from slackbot.dispatcher import Message

handler = logging.StreamHandler()
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel("DEBUG")

LOGGER_CHANNEL_ID = os.getenv("LOGGER_CHANNEL_ID")
SPREADSHEET_KEY = os.getenv("SPREADSHEET_KEY")
SPREADSHEET = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_KEY}"
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
]

credentials = ServiceAccountCredentials.from_json_keyfile_name("ServiceAccountCredentials.json", SCOPES)
spread = gspread.authorize(credentials)


def main():
    bot = Bot()
    bot.run()


@respond_to("(.*)")
def search(message: Message, something: str):
    try:
        logger.debug(message.body)
        logger.debug(message.user)
        logger.debug(message.channel._body)
        logger.debug(something)

        if something == "help" or not something:
            message.reply(
                f"知りたい用語を教えてほしいワン！ `@tellme 用語` で答えるワン。 用語集の管理は <{SPREADSHEET}|用語集> ここで管理しているワン。どんどん追加して欲しいワン。")
            return

        worksheet = spread.open_by_key(SPREADSHEET_KEY).sheet1
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

        # 分からなかった用語を集計する
        if not res_text:
            unknown: Worksheet = spread.open_by_key(SPREADSHEET_KEY).worksheet("unknown")
            now = datetime.datetime.now().isoformat()
            for i, row in enumerate(unknown.get_all_values()):
                target: str = row[0].lower()
                target = jaconv.hira2kata(target)
                target = jaconv.h2z(target)
                if query == target:
                    logger.debug(f"用語が見つからなかったのでインクリメントします")
                    # 用語の集計値をインクリメントする
                    count = row[1]
                    if count == "":
                        count = 0
                    else:
                        count = int(count)
                    unknown.update_cell(i + 1, 2, count + 1)
                    unknown.update_cell(i + 1, 4, now)
                    break
            else:
                logger.debug(f"用語が見つからなかったので新規追加します")
                # 新たに用語を追加する
                unknown.insert_rows(values=[[query, 1, now, now]],
                                    row=len(unknown.get_all_values()) + 1,
                                    value_input_option="USER_ENTERED")

        # ログとして #bot_test_tellme に出力する
        if LOGGER_CHANNEL_ID:
            msg = ""
            if not res_text:
                msg = f"\nでもこの用語は分からなかったワン・・・だれか <{SPREADSHEET}|用語集> に追加して欲しいワン"
            text = f"<#{message.channel._body['id']}> で <@{message.user['id']}> が *{something}* を検索したワン。{msg}"
            message._client.rtm_send_message(LOGGER_CHANNEL_ID, text)

        if not res_text:
            res_text.append(f"わからなかったワン・・・。意味が分かったら <{SPREADSHEET}|用語集> に追加して欲しいワン")

        message.reply("\n\n".join(res_text))
    except Exception as e:
        logger.exception(e)
        message.reply("エラーが発生したワン・・・")


if __name__ == "__main__":
    main()
