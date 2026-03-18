import requests
import os
import time

VK_TOKEN = os.environ["VK_TOKEN"]
NTFY_TOPIC = os.environ["NTFY_TOPIC"]
VK_VERSION = "5.131"

def send_push(title, message):
    requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=message.encode("utf-8"),
        headers={
            "Title": title.encode("utf-8").decode("latin-1", errors="replace"),
            "Priority": "high",
            "Content-Type": "text/plain; charset=utf-8"
        }
    )

def get_long_poll_server():
    r = requests.get("https://api.vk.com/method/messages.getLongPollServer", params={
        "access_token": VK_TOKEN,
        "v": VK_VERSION,
        "lp_version": 3
    })
    return r.json()["response"]

def get_user_name(user_id):
    r = requests.get("https://api.vk.com/method/users.get", params={
        "user_ids": user_id,
        "access_token": VK_TOKEN,
        "v": VK_VERSION
    })
    u = r.json()["response"][0]
    return f"{u['first_name']} {u['last_name']}"

def listen():
    server_info = get_long_poll_server()
    server = server_info["server"]
    key = server_info["key"]
    ts = server_info["ts"]

    print("Слушаю VK сообщения...")
    send_push("✅ Бот запущен", "VK уведомления активны!")

    while True:
        try:
            r = requests.get(f"https://{server}", params={
                "act": "a_check",
                "key": key,
                "ts": ts,
                "wait": 25,
                "mode": 2,
                "version": 3
            })
            data = r.json()

            if "failed" in data:
                server_info = get_long_poll_server()
                key = server_info["key"]
                ts = server_info["ts"]
                continue

            ts = data["ts"]

            for event in data.get("updates", []):
                if event[0] == 4 and not (event[2] & 2):
                    from_id = event[3]
                    text = event[6] or "(без текста)"
                    try:
                        name = get_user_name(from_id)
                    except:
                        name = f"ID {from_id}"
                    send_push(f"📩 {name}", text)

        except Exception as e:
            print(f"Ошибка: {e}")
            time.sleep(5)

if __name__ == "__main__":
    listen()