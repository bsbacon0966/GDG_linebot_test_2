import os
import requests
from dotenv import load_dotenv
from flask import Flask, request, abort

# v3 SDK
from linebot.v3.webhook import WebhookHandler
from linebot.v3.messaging import MessagingApi, Configuration
from linebot.v3.messaging.models import TextMessage, ReplyMessageRequest
from linebot.v3.webhook_models import MessageEvent
from linebot.v3.exceptions import InvalidSignatureError

# ===== 1. Init =====
load_dotenv()
channel_token = os.getenv("LINE_TOKEN")
channel_secret = os.getenv("LINE_SECRET")
google_key = os.getenv("GOOGLE_MAPS_API_KEY")
default_lat = os.getenv("DEFAULT_LAT", "24.5644")
default_lng = os.getenv("DEFAULT_LNG", "121.2220")

# Init Flask & LINE
app = Flask(__name__)
handler = WebhookHandler(channel_secret)
config = Configuration(access_token=channel_token)
messaging_api = MessagingApi(configuration=config)

# ===== 2. 查詢設定 =====
query_map = {
    "/想吃甜": "甜點",
    "/想吃鹹": "小吃",
    "/想喝飲料": "飲料"
}

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
        return "🥲 附近沒有找到適合的地點，再換個指令試試看吧！"
    
    lines = []
    for p in places:
        name = p.get("name", "未知店家")
        address = p.get("vicinity", "未知地址")
        lat = p["geometry"]["location"]["lat"]
        lng = p["geometry"]["location"]["lng"]
        gmap = f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"
        lines.append(f"📍 {name}\n🏠 {address}\n🔗 {gmap}")
    return "\n\n".join(lines)

# ===== 3. Webhook入口 =====
@app.route("/", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

# ===== 4. 處理訊息事件 =====
@handler.add(MessageEvent)
def handle(event):
    if not hasattr(event, "message") or event.message.type != "text":
        return

    user_text = event.message.text.strip()

    if user_text in query_map:
        keyword = query_map[user_text]
        results = search_google_places(keyword, default_lat, default_lng)
        reply_text = format_results(results)
    else:
        reply_text = "請輸入以下指令試試看 👇\n/想吃甜\n/想吃鹹\n/想喝飲料"

    messaging_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text=reply_text)]
        )
    )

# ===== 5. 啟動伺服器 =====
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

