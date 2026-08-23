# app.py
# Сервер для Render: Flask + Telethon (Bot Client)
# Обрабатывает кнопки бота @manultoolbot

import os
import sys
import asyncio
import threading
import logging
import time
from flask import Flask, request, jsonify

try:
    from telethon import TelegramClient, events
    from telethon.sessions import StringSession
except ImportError:
    print("ERROR: pip install telethon flask")
    sys.exit(1)

# ================= КОНФИГ =================
SESSION_STRING = "1ApWapzMBu6PifDR7W6CuOdAU6nFQDibI9O_73zHTzJ5GTe05960JralJFL8WcM6dX8Ny3CBwPt3IJlp6d0PWUTNVxkbqPGV-j4TjKHXUCQyDilGmM-JFcW9TKDWW2oHL6Rg2S0h_wCoiNziJm43fmMhTdtimBwWvedxouJRkuSuccVHlmZfMjeaOmebd8MqbSFd0_QV2uBHQmD39O49eAPGY6nFCpdmeyvFvUCpr-E1Sgbje_mhjyJ_LXLHIisiBUdnFaV8pVEmfok3Gvjz_2dtxKqQlMpFwZfU6_VeWgKF4VQykYXMDL7AzrT-T9UzL6J_i9eMolo_2bjLXvV_h_aiVAFYLMpc="

API_ID = 33544148
API_HASH = "31ded48782ea9d640ba379f630cc114f"
BOT_USERNAME = "manultoolbot"
# ===========================================

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
loop = asyncio.new_event_loop()

def run_loop():
    asyncio.set_event_loop(loop)
    loop.run_forever()

threading.Thread(target=run_loop, daemon=True).start()

message_queue = None

async def init_client():
    """Инициализация клиента и очереди внутри event loop"""
    global message_queue
    message_queue = asyncio.Queue()
    await client.connect()
    
    @client.on(events.NewMessage(from_users=BOT_USERNAME))
    async def on_new_message(event):
        await message_queue.put(event)

    @client.on(events.MessageEdited(from_users=BOT_USERNAME))
    async def on_edited_message(event):
        await message_queue.put(event)

async def click_button(msg, text_pattern):
    """Ищет и нажимает inline/markdown кнопку"""
    try:
        if not msg or not msg.buttons:
            return False
        for row in msg.buttons:
            for btn in row:
                if hasattr(btn, 'text') and text_pattern.lower() in btn.text.lower():
                    await btn.click()
                    return True
    except Exception as e:
        logging.error(f"Button click error: {e}")
    return False

async def get_next_message(timeout=60):
    """Ждёт следующего сообщения или редактирования от бота"""
    try:
        return await asyncio.wait_for(message_queue.get(), timeout=timeout)
    except asyncio.TimeoutError:
        return None

async def process_query_telethon(query):
    """Основная логика общения с ботом"""
    logging.info(f"Starting query: {query}")
    
    # Очищаем очередь от старых сообщений
    while not message_queue.empty():
        message_queue.get_nowait()

    # 1. Отправляем /start
    await client.send_message(BOT_USERNAME, '/start')
    start_msg = await get_next_message(timeout=30)
    if not start_msg:
        return {"error": "Bot didn't respond to /start"}
    
    await asyncio.sleep(1)
    
    # 2. Нажимаем Search
    clicked = await click_button(start_msg, 'search')
    if not clicked:
        clicked = await click_button(start_msg, 'поиск')
    
    search_msg = await get_next_message(timeout=30)
    if not search_msg:
        return {"error": "Bot didn't respond after Search"}
    
    await asyncio.sleep(1)
    
    # 3. Нажимаем Telegram
    clicked = await click_button(search_msg, 'telegram')
    if not clicked:
        clicked = await click_button(search_msg, 'tg')
        
    tg_msg = await get_next_message(timeout=30)
    if not tg_msg:
        return {"error": "Bot didn't respond after Telegram"}
    
    await asyncio.sleep(1)
    
    # 4. Отправляем сам запрос
    await client.send_message(BOT_USERNAME, query)
    
    # 5. Ждём первого сообщения с прогрессом
    progress_msg = await get_next_message(timeout=60)
    if not progress_msg:
        return {"error": "Bot didn't send progress message"}
    
    response_text = progress_msg.message.text or ""
    
    # Ждём завершения анализа (до 180 секунд)
    start_wait = time.time()
    while time.time() - start_wait < 180:
        if any(keyword in response_text.lower() for keyword in ['analysis complete', 'анализ завершен', 'complete', 'готово', 'finished']):
            break
            
        new_event = await get_next_message(timeout=10)
        if new_event:
            response_text = new_event.message.text or ""
        else:
            break
    
    # 6. Нажимаем Back
    last_msg = await client.get_messages(BOT_USERNAME, limit=1)
    if last_msg:
        await click_button(last_msg[0], 'back')
        if not await click_button(last_msg[0], 'назад'):
            await click_button(last_msg[0], '←')
    
    return {"success": True, "data": response_text}

@app.route('/api/search', methods=['POST'])
def search():
    """API Эндпоинт для Cloudflare Worker"""
    data = request.json
    query = data.get('query')
    
    if not query:
        return jsonify({"error": "Query is required"}), 400
        
    try:
        future = asyncio.run_coroutine_threadsafe(process_query_telethon(query), loop)
        result = future.result(timeout=240)
        return jsonify(result)
    except Exception as e:
        logging.error(f"Error processing query: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    return "PRIME Render Server is Online!"

if __name__ == '__main__':
    # Запускаем Telethon клиент в нашем loop
    asyncio.run_coroutine_threadsafe(init_client(), loop)
    time.sleep(5)
    logging.info("Telethon client started!")
    
    # Запускаем Flask
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
