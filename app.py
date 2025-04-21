import os
import requests
from dotenv import load_dotenv
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.exceptions import InvalidSignatureError

# Load .env
load_dotenv()
line_token = os.getenv("LINE_TOKEN")
line_secret = os.getenv("LINE_SECRET")
google_api_key = os.getenv("GOOGLE_MAPS_API_KEY")
default_lat = os.getenv("DEFAULT_LAT", "24.5644")
default_lng = os.getenv("DEFAULT_LNG", "121.2220")

# Init
app = Flask(__name__)
line_bot_api = LineBotApi(line_token)
handler = WebhookHandler(line_secret)

# 關鍵字對應搜尋項目
query_map = {
    "/想吃甜": "甜點",
    "/想吃鹹": "小吃",
    "/想喝飲料": "飲料"
}

def search_nearby_places(keyword, lat, lng, radius=800):
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "key": google_api_key,
        "location": f"{lat},{lng}",
        "radius": radius,
        "keyword": keyword,
        "language": "zh-TW"
    }
    response = requests.get(url, params=params)
    results = response.json().get("results", [])
    return results[:3]  # 只取前三筆

def format_places_message(places):
    if not places:
        return "😢 附近找不到合適的地點，換個方向再試試看吧！"

    messages = []
    for place in places:
        name = place.get("name", "未知店名")
        address = place.get("vicinity", "無地址資料")
        lat = place["geometry"]["location"]["lat"]
        lng = place["geometry"]["location"]["lng"]
        map_link = f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"
        messages.append(f"📍 {name}\n🏠 {address}\n🔗 {map_link}")

    return "\n\n".join(messages)

@app.route("/", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_input = event.message.text.strip()
    user_id = event.source.user_id

    if user_input in query_map:
        keyword = query_map[user_input]
        places = search_nearby_places(keyword, default_lat, default_lng)
        message = format_places_message(places)
    else:
        message = "請輸入 /想吃甜、/想吃鹹 或 /想喝飲料 來尋找附近推薦！"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=message))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
