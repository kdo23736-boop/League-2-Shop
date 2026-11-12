
import os
import json
import logging
import requests
from http.server import BaseHTTPRequestHandler

TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])
SECRET = os.environ.get("WEBHOOK_SECRET", "")

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


def telegram(method, data):
    response = requests.post(
        API + method, json=data, timeout=15
    )
    response.raise_for_status()
    result = response.json()

    if not result.get("ok"):
        raise RuntimeError(str(result))

    return result["result"]


def send(chat_id, text, markup=None):
    data = {"chat_id": chat_id, "text": text}

    if markup:
        data["reply_markup"] = markup

    return telegram("sendMessage", data)


def ask(chat_id, text):
    return send(chat_id, text, {
        "force_reply": True,
        "selective": True
    })


def answer(query_id, text=""):
    telegram("answerCallbackQuery", {
        "callback_query_id": query_id,
        "text": text
    })


def show_packages(chat_id):
    rows = []

    for key, (name, price) in PACKAGES.items():
        rows.append([{
            "text": f"{name} - {price:,} Ks",
            "callback_data": f"pkg:{key}"
        }])

    send(chat_id,
         "💎 League 2 Diamond Shop\n\nPackage ရွေးချယ်ပါ။",
         {"inline_keyboard": rows})


def handle_message(message):
    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()
    reply = message.get("reply_to_message") or {}
    prompt = reply.get("text", "")

    if text == "/start":
        show_packages(chat_id)
        return

    if text == "/cancel":
        show_packages(chat_id)
        return

    # User ID
    if prompt.startswith("USER|"):
        pkg = prompt.split("|")[1]

        if not text.isdigit():
            ask(chat_id, prompt + "\nUser ID ကို နံပါတ်ဖြင့်ထည့်ပါ။")
            return

        ask(chat_id, f"SERVER|{pkg}|{text}\n\nServer ID ထည့်ပါ။")
        return

    # Server ID
    if prompt.startswith("SERVER|"):
        _, pkg, uid = prompt.split("|")

        if not text.isdigit():
            ask(chat_id, prompt + "\nServer ID မှန်ကန်စွာထည့်ပါ။")
            return

        keyboard = {
            "inline_keyboard": [[
                {"text": "KPay",
                 "callback_data": f"pay:k:{pkg}:{uid}:{text}"},
                {"text": "WavePay",
                 "callback_data": f"pay:w:{pkg}:{uid}:{text}"}
            ]]
        }

        send(chat_id, "ငွေပေးချေမှုနည်းလမ်း ရွေးပါ။", keyboard)
        return

    # Receipt
    if prompt.startswith("RECEIPT|"):
        if not message.get("photo"):
            ask(chat_id, prompt + "\nပြေစာ Screenshot ပို့ပါ။")
            return

        _, pkg, uid, sid, payment = prompt.split("|")
        name, price = PACKAGES[pkg]
        photo = message["photo"][-1]["file_id"]

        caption = (
            "💎 NEW ORDER\n\n"
            f"Package: {name}\n"
            f"Price: {price:,} Ks\n"
            f"User ID: {uid}\n"
            f"Server ID: {sid}\n"
            f"Payment: {payment}\n"
            f"Customer ID: {chat_id}\n"
            "Status: PENDING"
        )

        keyboard = {
            "inline_keyboard": [[
                {"text": "✅ APPROVE",
                 "callback_data": f"approve:{chat_id}"},
                {"text": "❌ REJECT",
                 "callback_data": f"reject:{chat_id}"}
            ]]
        }

        telegram("sendPhoto", {
            "chat_id": ADMIN_ID,
            "photo": photo,
            "caption": caption,
            "reply_markup": keyboard
        })

        send(chat_id,
             "✅ Order တင်ပြီးပါပြီ။ Admin စစ်ဆေးပေးပါမယ်။")
        return

    send(chat_id, "/start နှိပ်ပြီး စတင်ပါ။")


def handle_callback(callback):
    data = callback["data"]
    sender_id = callback["from"]["id"]
    chat_id = callback["message"]["chat"]["id"]
    query_id = callback["id"]

    if data.startswith("pkg:"):
        if chat_id != sender_id:
            answer(query_id, "ကိုယ်ပိုင် Chat မှာသာ ဝယ်ယူပါ။")
            return

        pkg = data.split(":")[1]

        if pkg not in PACKAGES:
            answer(query_id, "Package မရှိပါ။")
            return

        name, price = PACKAGES[pkg]

        ask(chat_id,
            f"USER|{pkg}\n{name} - {price:,} Ks\n\n"
            "MLBB User ID ထည့်ပေးပါ။")

        answer(query_id, "Package ရွေးပြီးပါပြီ။")
        return

    if data.startswith("pay:"):
        if chat_id != sender_id:
            answer(query_id, "ကိုယ်ပိုင် Chat မှာသာ ဝယ်ယူပါ။")
            return

        _, method, pkg, uid, sid = data.split(":")

        if pkg not in PACKAGES:
            answer(query_id, "Package မရှိပါ။")
            return

        payment = "KPay" if method == "k" else "WavePay"
        number = "09422190218" if method == "k" else "09893463559"
        name, price = PACKAGES[pkg]

        ask(
            chat_id,
            f"RECEIPT|{pkg}|{uid}|{sid}|{payment}\n\n"
            f"💳 {payment}\n"
            f"Account: {number}\n"
            f"Package: {name}\n"
            f"Amount: {price:,} Ks\n\n"
            "ငွေလွှဲပြီးပါက ဒီ Message ကို Reply လုပ်ပြီး "
            "ပြေစာ Screenshot ပို့ပါ။"
        )

        answer(query_id, "Payment ရွေးချယ်ပြီးပါပြီ။")
        return

    if data.startswith(("approve:", "reject:")):
        if sender_id != ADMIN_ID:
            answer(query_id, "Admin သာ အသုံးပြုနိုင်ပါသည်။")
            return

        customer_id = int(data.split(":")[1])
        approved = data.startswith("approve:")

        if approved:
            send(customer_id, "ထည့်လိုက်ပါပြီ✅")
            answer(query_id, "Approved!")
        else:
            send(customer_id,
                 "❌ Order ပယ်ဖျက်လိုက်ပါပြီ။ Admin ကိုဆက်သွယ်ပါ။")
            answer(query_id, "Rejected!")

        telegram("editMessageReplyMarkup", {
            "chat_id": chat_id,
            "message_id": callback["message"]["message_id"],
            "reply_markup": {"inline_keyboard": []}
        })


class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        body = b"League 2 Diamond Shop Bot Running"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if SECRET:
            received = self.headers.get(
                "X-Telegram-Bot-Api-Secret-Token", ""
            )
            if received != SECRET:
                self.send_error(403)
                return

        try:
            length = int(self.headers.get("Content-Length", 0))
            update = json.loads(self.rfile.read(length))

            if "message" in update:
                handle_message(update["message"])

            elif "callback_query" in update:
                handle_callback(update["callback_query"])

        except Exception:
            logging.exception("Telegram Bot Error")

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
        
