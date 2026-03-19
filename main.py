import requests
import os
import time

VK_TOKEN = os.environ["VK_TOKEN"]
NTFY_TOPIC = os.environ["NTFY_TOPIC"]
YANDEX_API_KEY = os.environ["YANDEX_API_KEY"]
YANDEX_FOLDER_ID = os.environ["YANDEX_FOLDER_ID"]
VK_VERSION = "5.131"
MY_VK_ID = int(os.environ["MY_VK_ID"])

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

def ask_yandex(question):
    response = requests.post(
        "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
        headers={
            "Authorization": f"Api-Key {YANDEX_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt/latest",
            "completionOptions": {"temperature": 0.7, "maxTokens": 500},
            "messages": [
                {"role": "user", "text": question}
            ]
        }
    )
    result = response.json()
    return result["result"]["alternatives"][0]["message"]["text"]

def send_vk_message(peer_id, text):
    requests.get("https://api.vk.com/method/messages.send", params={
        "access_token": VK_TOKEN,
        "v": VK_VERSION,
        "peer_id": peer_id,
        "message": text,
        "random_id": int(time.time() * 1000)
    })

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
                if event[0] == 4:
                    print(f"DEBUG: flags={event[2]}, from_id={event[3]}, is_outgoing={bool(event[2] & 2)}")
                    flags = event[2]
                    from_id = event[3]
                    peer_id = event[3]
                    msg_id = event[1]
                    is_outgoing = bool(flags & 2) or (from_id == MY_VK_ID)

                    # Получаем полный текст сообщения
                    try:
                        msg_r = requests.get("https://api.vk.com/method/messages.getById", params={
                            "access_token": VK_TOKEN,
                            "v": VK_VERSION,
                            "message_ids": msg_id
                        })
                        msg_data = msg_r.json()["response"]["items"][0]
                        text = msg_data.get("text", "") or ""
                        peer_id = msg_data.get("peer_id", peer_id)
                        attachments = msg_data.get("attachments", [])
                        if attachments and not text:
                            types = ", ".join(set(a["type"] for a in attachments))
                            text = f"[{types}]"
                    except:
                        text = ""

                    # Обработка команды $search — только в исходящих сообщениях
                    if is_outgoing and text.strip().lower().startswith("$search"):
                        question = text.strip()[7:].strip()
                        if question:
                            try:
                                answer = ask_yandex(question)
                                send_vk_message(peer_id, f"🤖 {answer}")
                            except Exception as e:
                                send_vk_message(peer_id, f"Ошибка: {e}")

                    # Уведомление о входящем сообщении
                    elif not is_outgoing and from_id < 2000000000:
                        try:
                            name = get_user_name(from_id)
                        except:
                            name = f"ID {from_id}"
                        send_push(f"VK: {name}", text or "(без текста)")

        except Exception as e:
            print(f"Ошибка: {e}")
            time.sleep(5)

if __name__ == "__main__":
    listen()