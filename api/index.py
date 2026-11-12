import os
import json
import logging
import requests
from http.server import BaseHTTPRequestHandler

TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")

API = f"https://api.telegram.org/bot{TOKEN}/"

PACKAGES = {
    "w": ("Weekly Pass", 6900),
    "t": ("Twilight Pass", 34500),
    "86": ("86 Dia", 5800),
    "172": ("172 Dia", 11000),
    "257": ("257 Dia", 16300),
    "343": ("343 Dia", 21800),
    "429": ("429 Dia", 27000),
    "514": ("514 Dia", 32500),
    "600": ("600 Dia", 37600),
    "706": ("706 Dia", 42900),
    "878": ("878 Dia", 53600),
    "964": ("964 Dia", 58900),
    "1049": ("1049 Dia", 64100),
    "2195": ("2195 Dia", 127500),
    "50": ("Double 2x50", 4100),
    "150": ("Double 2x150", 11500),
    "250": ("Double 2x250", 17200),
    "500": ("Double 2x500", 33700),
}


def tg(method, data):
    r = requests.post(
        API + method, json=data, timeout=20
    )
    r.raise_for_status()
    result = r.json()
    if not result.get("ok"):
        raise RuntimeError(str(result))
    return result["result"]


def send(chat_id, message, markup=None):
    data = {
        "chat_id": chat_id,
        "text": message
    }
    if markup:
        data["reply_markup"] = markup
    return tg("sendMessage", data)


def ask(chat_id, message):
    return send(chat_id, message, {
        "force_reply": True,
        "selective": True
    })


def answer_callback(query_id, message=""):
    tg("answerCallbackQuery", {
        "callback_query_id": query_id,
        "text": message
    })


def package_keyboard():
    rows = []
    for key, (name, price) in PACKAGES.items():
        rows.append([{
            "text": f"{name} - {price:,} Ks",
            "callback_data": f"pkg:{key}"
        }])
    return {"inline_keyboard": rows}


def start(chat_id):
    send(
        chat_id,
        "💎 Welcome to League 2 Diamond Shop!\n\n"
        "ဝယ်ယူလိုသော Diamond Package ကို ရွေးချယ်ပါ။",
        package_keyboard()
    )


def handle_message(m):
    chat_id = m["chat"]["id"]
    text = m.get("text", "").strip()
    reply = m.get("reply_to_message") or {}
    prompt = reply.get("text", "")

    if text == "/start":
        start(chat_id)
        return

    if text == "/cancel":
        start(chat_id)
        return

    # Customer sends payment receipt
    if prompt.startswith("RECEIPT|"):
        if chat_id == ADMIN_ID:
            return

        if not m.get("photo"):
            ask(
                chat_id,
                prompt + "\n\nဓာတ်ပုံဖြင့် ပြေစာပို့ပေးပါ။"
            )
            return

        _, pkg, uid, sid, payment = prompt.split("|")
        name, price = PACKAGES[pkg]
        photo_id = m["photo"][-1]["file_id"]

        caption = (
            "💎 NEW DIAMOND ORDER\n\n"
            f"Package: {name}\n"
            f"Price: {price:,} Ks\n"
            f"MLBB User ID: {uid}\n"
            f"Server ID: {sid}\n"
            f"Payment: {payment}\n"
            f"Customer ID: {chat_id}\n"
            "Status: PENDING"
        )

        keyboard = {
            "inline_keyboard": [[
                {
                    "text": "✅ APPROVE",
                    "callback_data": f"approve:{chat_id}"
                },
                {
                    "text": "❌ REJECT",
                    "callback_data": f"reject:{chat_id}"
                }
            ]]
        }

        tg("sendPhoto", {
            "chat_id": ADMIN_ID,
            "photo": photo_id,
            "caption": caption,
            "reply_markup": keyboard
        })

        send(
            chat_id,
            "✅ Order တင်ပြီးပါပြီ။\n"
            "Admin မှ စစ်ဆေးပေးပါမယ်။"
        )
        return

    # Customer enters User ID
    if prompt.startswith("USER|"):
        pkg = prompt.split("|")[1]

        if not text.isdigit():
            ask(chat_id, prompt + "\nUser ID ကို နံပါတ်ဖြင့် ထည့်ပါ။")
            return

        ask(chat_id, f"SERVER|{pkg}|{text}\n\nMLBB Server ID ထည့်ပါ။")
        return

    # Customer enters Server ID
    if prompt.startswith("SERVER|"):
        _, pkg, uid = prompt.split("|")

        if not text.isdigit():
            ask(chat_id, prompt + "\nServer ID ကို နံပါတ်ဖြင့် ထည့်ပါ။")
            return

        keyboard = {
            "inline_keyboard": [[
                {
                    "text": "KPay",
                    "callback_data": f"pay:k:{pkg}:{uid}:{text}"
                },
                {
                    "text": "WavePay",
                    "callback_data": f"pay:w:{pkg}:{uid}:{text}"
                }
            ]]
        }

        send(chat_id, "ငွေပေးချေမည့်နည်းလမ်း ရွေးချယ်ပါ။", keyboard)
        return

    if m.get("photo"):
        send(
            chat_id,
            "ပြေစာကို သက်ဆိုင်ရာ Order ရဲ့ ပြေစာတောင်းထားတဲ့ Message ကို Reply လုပ်ပြီး ပို့ပေးပါ။"
        )
        return

    send(chat_id, "စတင်ရန် /start နှိပ်ပါ။")


def handle_callback(c):
    data = c["data"]
    user_id = c["from"]["id"]
    chat_id = c["message"]["chat"]["id"]

    if data.startswith("pkg:"):
        if chat_id != user_id:
            answer_callback(c["id"], "ကိုယ်ပိုင် Chat မှာသာ ဝယ်ယူပါ။")
            return

        pkg = data.split(":")[1]
        if pkg not in PACKAGES:
            answer_callback(c["id"], "Package မရှိပါ။")
            return

        name, price = PACKAGES[pkg]
        ask(
            chat_id,
            f"USER|{pkg}\n"
            f"ရွေးချယ်ထားသော Package: {name}\n"
            f"ဈေးနှုန်း: {price:,} Ks\n\n"
            "MLBB User ID ထည့်ပေးပါ။"
        )
        answer_callback(c["id"], "Package ရွေးချယ်ပြီးပါပြီ။")
        return

    if data.startswith("pay:"):
        if chat_id != user_id:
            answer_callback(c["id"], "ကိုယ်ပိုင် Chat မှာသာ ဝယ်ယူပါ။")
            return

        _, method, pkg, uid, sid = data.split(":")
        if pkg not in PACKAGES:
            answer_callback(c["id"], "Package မရှိပါ။")
            return

        payment = "KPay" if method == "k" else "WavePay"
        number = (
            "09422190218" if method == "k"
            else "09893463559"
        )
        name, price = PACKAGES[pkg]

        ask(
            chat_id,
            f"RECEIPT|{pkg}|{uid}|{sid}|{payment}\n\n"
            f"💳 {payment}\n"
            f"Account: {number}\n"
            f"Package: {name}\n"
            f"Amount: {price:,} Ks\n\n"
            "ငွေလွှဲပြီးပါက ဒီ Message ကို Reply လုပ်ပြီး "
            "ပြေစာ Screenshot ပို့ပေးပါ။"
        )
        answer_callback(c["id"], "ငွေပေးချေမှုနည်းလမ်း ရွေးပြီးပါပြီ။")
        return

    # Only Admin can approve or reject
    if data.startswith("approve:") or data.startswith("reject:"):
        if user_id != ADMIN_ID:
            answer_callback(c["id"], "Admin သာ အသုံးပြုနိုင်ပါသည်။")
            return

        customer_id = int(data.split(":")[1])
        approved = data.startswith("approve:")

        if approved:
            send(customer_id, "ထည့်လိုက်ပါပြီ✅")
            answer_callback(c["id"], "Order Approved!")
        else:
            send(
                customer_id,
                "❌ Order ကို ပယ်ဖျက်လိုက်ပါပြီ။ "
                "Admin ကို ဆက်သွယ်ပါ။"
            )
            answer_callback(c["id"], "Order Rejected!")

        tg("editMessageReplyMarkup", {
            "chat_id": chat_id,
            "message_id": c["message"]["message_id"],
            "reply_markup": {"inline_keyboard": []}
        })


class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"League 2 Diamond Shop Bot is running")

    def do_POST(self):
        if WEBHOOK_SECRET:
            received = self.headers.get(
                "X-Telegram-Bot-Api-Secret-Token", ""
            )
            if received != WEBHOOK_SECRET:
                self.send_error(403)
                return

        try:
            length = int(self.headers.get("Content-Length", 0))
            update = json.loads(self.rfile.read(length))

            if "message" in update:
                handle_message(update["message"])
            elif "callback_query" in update:
                handle_callback(update["callback_query"])

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")

        except Exception:
            logging.exception("Telegram webhook error")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
            import
