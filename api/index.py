
import os
import requests
from http.server import BaseHTTPRequestHandler

TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])
API = f"https://api.telegram.org/bot{TOKEN}/"

PACKAGES = {
    "w": ("Weekly Pass", 6900),
    "t": ("Twilight Pass", 34500),
    "86": ("86 Diamonds", 5800),
    "172": ("172 Diamonds", 11000),
    "257": ("257 Diamonds", 16300),
    "343": ("343 Diamonds", 21800),
    "429": ("429 Diamonds", 27000),
    "514": ("514 Diamonds", 32500),
    "600": ("600 Diamonds", 37600),
    "706": ("706 Diamonds", 42900),
    "878": ("878 Diamonds", 53600),
    "964": ("964 Diamonds", 58900),
    "1049": ("1049 Diamonds", 64100),
    "2195": ("2195 Diamonds", 127500),
    "50": ("Double 2x50", 4100),
    "150": ("Double 2x150", 11500),
    "250": ("Double 2x250", 17200),
    "500": ("Double 2x500", 33700),
}

def api(method, data):
    return requests.post(
        API + method, data=data, timeout=20
    ).json()

def send(chat, text, keyboard=None):
    data = {"chat_id": chat, "text": text}
    if keyboard:
        data["reply_markup"] = keyboard
    return api("sendMessage", data)

def answer(query_id, text=""):
    api("answerCallbackQuery", {
        "callback_query_id": query_id,
        "text": text
    })

def main_keyboard():
    buttons = []
    for key, (name, price) in PACKAGES.items():
        buttons.append([{
            "text": f"{name} - {price:,} Ks",
            "callback_data": f"pkg:{key}"
        }])
    return {"inline_keyboard": buttons}

def handle_message(m):
    chat = m["chat"]["id"]
    text = m.get("text", "")
    reply = m.get("reply_to_message", {})
    prompt = reply.get("text", "")

    if text == "/start":
        send(
            chat,
            "💎 Welcome to League 2 Diamond Shop!\n\n"
            "မင်္ဂလာပါ။ Diamond Package ရွေးချယ်ပါ။",
            main_keyboard()
        )
        return

    if prompt.startswith("USER|"):
        uid = text.strip()
        if not uid.isdigit():
            send(chat, "User ID ကို နံပါတ်ဖြင့်သာ ထည့်ပါ။")
            return
        pkg = prompt.split("|")[1]
        send(
            chat,
            f"SERVER|{pkg}|{uid}\n\n"
            "MLBB Server ID ကို ထည့်ပေးပါ။"
        )
        return

    if prompt.startswith("SERVER|"):
        parts = prompt.split("|")
        pkg, uid = parts[1], parts[2]
        sid = text.strip()

        if not sid.isdigit():
            send(chat, "Server ID ကို နံပါတ်ဖြင့်သာ ထည့်ပါ။")
            return

        keyboard = {
            "inline_keyboard": [[
                {"text": "KPay", "callback_data":
                 f"pay:k:{pkg}:{uid}:{sid}"},
                {"text": "WavePay", "callback_data":
                 f"pay:w:{pkg}:{uid}:{sid}"}
            ]]
        }
        send(chat, "ငွေပေးချေမည့်နည်းလမ်း ရွေးချယ်ပါ။",
             keyboard)
        return

    if prompt.startswith("RECEIPT|"):
        if not m.get("photo"):
            send(chat, "ငွေလွှဲပြေစာ Screenshot ပုံ ပို့ပေးပါ။")
            return

        parts = prompt.split("|")
        _, pkg, uid, sid, payment = parts
        name, price = PACKAGES[pkg]
        photo = m["photo"][-1]["file_id"]

        caption = (
            "💎 NEW DIAMOND ORDER\n\n"
            f"Package: {name}\n"
            f"Price: {price:,} Ks\n"
            f"User ID: {uid}\n"
            f"Server ID: {sid}\n"
            f"Payment: {payment}\n"
            f"Customer ID: {chat}\n"
            "Status: PENDING"
        )

        keyboard = {
            "inline_keyboard": [[
                {"text": "✅ APPROVE",
                 "callback_data": f"ok:{chat}"},
                {"text": "❌ REJECT",
                 "callback_data": f"no:{chat}"}
            ]]
        }

        api("sendPhoto", {
            "chat_id": ADMIN_ID,
            "photo": photo,
            "caption": caption,
            "reply_markup": keyboard
        })

        send(chat, "Order တင်ပြီးပါပြီ။ Admin စစ်ဆေးပေးပါမယ်။")
        return

    send(chat, "ကျေးဇူးပြု၍ /start နှိပ်ပြီး စတင်ပါ။")

def handle_callback(c):
    data = c["data"]
    chat = c["message"]["chat"]["id"]
    mid = c["message"]["message_id"]

    if data.startswith("pkg:"):
        key = data.split(":")[1]
        name, price = PACKAGES[key]
        send(chat,
             f"ရွေးချယ်ထားသည်: {name}\nဈေးနှုန်း: {price:,} Ks\n\n"
             f"USER|{key}\nMLBB User ID ထည့်ပေးပါ။")
        answer(c["id"])
        return

    if data.startswith("pay:"):
        _, method, pkg, uid, sid = data.split(":")
        payment = "KPay" if method == "k" else "WavePay"
        number = "09422190218" if method == "k" else "09893463559"
        name, price = PACKAGES[pkg]

        send(
            chat,
            f"💳 {payment}\n"
            f"Account: {number}\n"
            f"Package: {name}\n"
            f"Amount: {price:,} Ks\n\n"
            f"RECEIPT|{pkg}|{uid}|{sid}|{payment}\n"
            "ငွေလွှဲပြီးပါက ပြေစာ Screenshot ကို Reply လုပ်ပြီး ပို့ပါ။"
        )
        answer(c["id"])
        return

    if data.startswith("ok:") or data.startswith("no:"):
        if c["from"]["id"] != ADMIN_ID:
            answer(c["id"], "Admin only!")
            return

        user = int(data.split(":")[1])
        approved = data.startswith("ok:")

        send(
            user,
            "ထည့်လိုက်ပါပြီ✅" if approved
            else "Order ကို ပယ်ဖျက်လိုက်ပါပြီ။ Admin ကို ဆက်သွယ်ပါ။"
        )

        api("editMessageReplyMarkup", {
            "chat_id": chat,
            "message_id": mid,
            "reply_markup": {"inline_keyboard": []}
        })

        answer(c["id"], "Approved!" if approved else "Rejected!")

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"League 2 Diamond Shop Bot Running")

    def do_POST(self):
        import json
        length = int(self.headers.get("Content-Length", 0))
        update = json.loads(self.rfile.read(length))

        try:
            if "message" in update:
                handle_message(update["message"])
            elif "callback_query" in update:
                handle_callback(update["callback_query"])
        except Exception as e:
            print("BOT ERROR:", str(e))

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
