import os
from flask import Flask, request, abort

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

from survey_calc import calculate_survey_result


app = Flask(__name__)


# RenderのEnvironment Variablesから取得
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET")


# 環境変数チェック
if not LINE_CHANNEL_ACCESS_TOKEN:
    raise ValueError("LINE_CHANNEL_ACCESS_TOKEN が設定されていません")

if not LINE_CHANNEL_SECRET:
    raise ValueError("LINE_CHANNEL_SECRET が設定されていません")


line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)


# Renderで起動確認するためのページ
@app.route("/", methods=["GET"])
def index():
    return "survey-bot is running", 200


# LINE DevelopersのWebhook URL用
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK", 200


# LINEで文字メッセージを受け取ったときの処理
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text

    try:
        reply_text = calculate_survey_result(user_text)
    except Exception as e:
        reply_text = (
            "計算中にエラーが出ました。\n"
            "入力内容を確認してください。\n\n"
            f"エラー内容: {str(e)}"
        )

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )


# ローカル確認用
# Renderでは gunicorn main:app で起動するので、ここは基本使われません
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
