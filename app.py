import os
import requests
from dotenv import load_dotenv
from flask import Flask, request, abort
import openai

# LINE SDK v3
from linebot.v3.webhook import WebhookHandler, MessageEvent
from linebot.v3.messaging import (
    MessagingApi, ApiClient, Configuration,
    TextMessage, ReplyMessageRequest
)
from linebot.v3.exceptions import InvalidSignatureError

# ===== 1. 環境變數與初始化 =====
load_dotenv()
channel_token = os.getenv("LINE_TOKEN")
channel_secret = os.getenv("LINE_SECRET")
google_key = os.getenv("GOOGLE_MAPS_API_KEY")
openai.api_key = os.getenv("OPENAI_API_KEY")
default_lat = os.getenv("DEFAULT_LAT", "24.5644")
default_lng = os.getenv("DEFAULT_LNG", "121.2220")

# Flask
app = Flask(__name__)

# LINE 初始化
handler = WebhookHandler(channel_secret)
configuration = Configuration(access_token=channel_token)
api_client = ApiClient(configuration)
messaging_api = MessagingApi(api_client)

# ===== 2. 指令對應查詢關鍵字 =====
query_map = {
    "/想吃甜": "甜點",
    "/想吃鹹": "小吃",
    "/想喝飲料": "飲料"
}

# ===== 3. Google Maps 查詢函式 =====
def search_google_places(keyword, lat, lng, radius=1000):
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "key": google_key,
        "location": f"{lat},{lng}",
        "radius": radius,
        "keyword": keyword,
        "language": "zh-TW"
    }
    res = requests.get(url, params=params)
    results = res.json().get("results", [])
    return results[:3]

# ===== 4. 用 OpenAI 過濾並推薦店家 =====
def filter_places_with_gpt(places, category):
    if not places:
        return "🥲 附近沒有地點資料。"

    descriptions = []
    for idx, p in enumerate(places):
        name = p.get("name", "未知店家")
        address = p.get("vicinity", "未知地址")
        descriptions.append(f"{idx+1}. {name}（地址：{address}）")

    input_text = "\n".join(descriptions)
    prompt = (
        f"以下是附近的{category}類型店家，請你推薦哪些比較適合目前需求（{category}），"
        "可以加點評論，但請只挑 1~2 間最適合的，並附理由：\n\n"
        f"{input_text}\n\n請用條列式中文回覆："
    )

    try:
        res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500
        )
        return res.choices[0].message.content.strip()
    except Exception as e:
        return f"❌ GPT 處理錯誤：{e}"

# ===== 5. Webhook 路由 =====
@app.route("/", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"

# ===== 6. 處理文字訊息事件 =====
@handler.add(MessageEvent)
def handle_message(event):
    if not hasattr(event, "message") or event.message.type != "text":
        return

    user_text = event.message.text.strip()

    if user_text in query_map:
        keyword = query_map[user_text]
        places = search_google_places(keyword, default_lat, default_lng)
        reply_text = filter_places_with_gpt(places, keyword)
    else:
        reply_text = (
            "請輸入以下指令查詢附近地點：\n"
            "/想吃甜 🍰\n"
            "/想吃鹹 🍱\n"
            "/想喝飲料 🧋"
        )

    messaging_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text=reply_text)]
        )
    )

# ===== 7. 啟動應用 =====
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))