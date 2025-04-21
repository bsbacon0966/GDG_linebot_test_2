import os
import requests
from dotenv import load_dotenv
from flask import Flask, request, abort

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

def format_results(places):
    if not places:
        return "🥲 附近沒有找到合適的地點，再換個指令試試看吧！"

    lines = []
    for p in places:
        name = p.get("name", "未知店家")
        address = p.get("vicinity", "未知地址")
        lat = p["geometry"]["location"]["lat"]
        lng = p["geometry"]["location"]["lng"]
        gmap_url = f"https://www.google.com/maps?q={lat},{lng}"
        lines.append(f"📍 {name}\n🏠 {address}\n🔗 {gmap_url}")
    return "\n\n".join(lines)

# ===== 4. Webhook 路由 =====
@app.route("/", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"

# ===== 5. 處理文字訊息事件 =====
@handler.add(MessageEvent)
def handle_message(event):
    if not hasattr(event, "message") or event.message.type != "text":
        return

    user_text = event.message.text.strip()

    if user_text in query_map:
        keyword = query_map[user_text]
        places = search_google_places(keyword, default_lat, default_lng)
        reply_text = format_results(places)
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

# ===== 6. 啟動應用 =====
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
