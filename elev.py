

import requests

url = "https://api.elevenlabs.io/v1/text-to-speech/cMwNSpaX3z1AKQIC6wZC/stream"

payload = {
    "text": """The grandfather clock's pendulum swung to the rhythm of the universe, hypnotizing the dust motes that danced in the sepia-tinted light.

The typewriter's keys clicked in Morse code, sending messages to the ghosts that lingered between the lines of the unwritten novel.

The chandelier's crystals cast rainbows upon the walls, as the velvet curtains parted to reveal the stage of the mind's eye, where dreams and reality intertwined.""",
}
headers = {
    "Content-Type": "application/json",
    "xi-api-key": "69f0a07f829c8fd44ffa55fb896c88ef"
}

response = requests.request(
    "POST",
    url,
    json=payload,
    headers=headers,
    stream=True
)

print("Response Headers:")
for header, value in response.headers.items():
    print(f"{header}: {value}")

for chunk in response.iter_content(chunk_size=1024):
    if chunk:
        print(len(chunk))
    else:
        print(" sorry nothing")

