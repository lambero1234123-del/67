# app.py — Parser для Render (бот @dbuxjdjzi_bot, 2 запроса/сессия)

import os, re, asyncio, threading, logging, time, sqlite3
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from telethon.errors import FloodWaitError
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.tl.types import MessageEntityTextUrl

API_ID = 33544148
API_HASH = "31ded48782ea9d640ba379f630cc114f"
DB_FILE = "/tmp/prime_parser.db"
PARSER_API_KEY = "PRIME_SECURE_PARSER_2026"
DAILY_LIMIT = 2
MAX_RETRIES = 3
SEARCH_TIMEOUT = 45
BOT_USERNAME = "@dbuxjdjzi_bot"

PROXY_HOST = os.environ.get("PROXY_HOST", "")
PROXY_PORT = int(os.environ.get("PROXY_PORT", "0") or "0")
PROXY_USER = os.environ.get("PROXY_USER", "")
PROXY_PASS = os.environ.get("PROXY_PASS", "")

def get_proxy():
    if not PROXY_HOST or not PROXY_PORT: return None
    import socks
    return (socks.SOCKS5, PROXY_HOST, PROXY_PORT, True, PROXY_USER, PROXY_PASS)

SESSION_STRINGS = [
    "1BVtsOHEBu1c4bp4cwNBRpES5O-avYu46p1lCILeSl9UpUibw50v-pIqIWuttfQWckT9aMCZtPrVegRSkyaNceBA40oqf1hSzhQQbuWIpsLlKmoMDNuUaYi4UVyGOaX_SIm_hM4IhZk0kO63aKNbAP3xWDZHiCAXipMoBLkfyXokncDlLb2PZbTTL2mRrvKYymlIY4zNIBtZuhdUo3bcRg1lRj-FcgCaJs8LDV9cJcZH1etS4ov17JxpMuY7u1VtVkx-stblKqtetm-6_T6q6WHMQSgDcLU1hMp8wpig-EwTaNpUgNzpZlQDl3PxhlwOV136aAJGVU5vAw2iZ19j-gzgKtnBUw_Q=",
    "1AZWarzMBux4l6kt8pOF698potSnT7iJZpRw12zPkxLPm2_cGiF_z_udGtrOpPm2Q4jzOh7Log2KAK4OecXGCqgouHA8pZGnQtefFFBXsgcSddyQYgbKJTkE0yfCfJ3d5DU-NXLxMXtfwqzz8ns5UsQscpD7X5QnQQA7iAi7elfvpV95AY3yaYi3K9QLhh_q0DbcrPcbdoYhFPgq4KKIwvbaK6BFUKSNz_KWhA4MxFc6LqhwqCWTxcVFQb2qUOoPQmxfGS3h-xgyZNgR8GyApleeSG5xoLTMdXrBGCz2N45SY2NrrnxlF8MIPP90LFkiRnAmF3fV_o4tMPSNXGCjQySmC1FnZcXk=",
    "1AZWarzMBu5u41Q2C6IHBmG2ijVxyhPmTCGkOWcScpGrRG0SPTHjbstKbtXZsusTotnIzKhovNTyqIODy47QVK5YjTJUlsUohKL475_HKOKIPxD6ppkPbau1_WEMtO0OvdBzkC8EeS0G4z4s2NqmMkRVvWc1o1aOYAoos94_o8ZBg3Ah521ksi64C40y6DHSK3eZQ0LRXs3NKH65pMb1jvW0Gmudejh8sqJDrBMEUhcZxGl0yzev6HzPalEdCffBY-n9uZfnTopflJ1uWwZJLL3B-F_alLcwhzopUWphdYYPSK-03SvhO6fIvQAq8LxkLGrqhuF3X6I0cITt2gbjMUuaFXY8H_6c=",
    "1AZWarzMBuwuMqEemTWnxkthAih3DdeizwzK9yhomeZPo9my8Pj4HlCq60O63Lpbyo4g1bH6CUrLSoRD0oq33y4w_oqkcRWXT8YfT3F4OKvN5uAEWb3Bhrl1-yprI0cDKmxqShHOMLOx95T9Ot4VRDVwm7IE-nn-AcrXPG_MSR7SWnQwM_ZDo3WeGkEV3e4joSWo7uBfMS7FLzxh4Z4KGWtVg5CGlCx5MmSP8BYLbYUhVmz6wvLminKzcMcAac-aL9eFIcV1bm5yS8SyyMPw6gVT_BuEpVixFUuPXaBfIsGaOQLjehxxMG-bUDFgVnmJd7u4wJopmMIIR5s7zV-hBkJb15Lp7-PI=",
    "1AZWarzMBu0Uy6a8OB0hXPxpaKVrAwI3cnOjLX6h0zIeD3v4iBMne4M0xlPK88naqg4we37wgFx9q1TcMU9EIf7gmX31wR39hFmpeqPfdufL0ziXp_CZ8ATRTvyl9pO6tALKub2PncZRtzrwCIiVnF7rZGxUfOMisDoOQKrGIk7Zbtb-JdSJcBFXHBpOL_0DweC6ZyoatB-KXeSkP5nfO8_NLaokFac3LkmPPvX369avOarkoIp17dOT6IZtOWHA1jsnJBxL01UK_DpgRHD7jT6BfkxsMloESYgSOxZ9it7TuuWbfxEICkFdAmT80m3L4oDzjaqsdykppkLvIPROeq2SwO62OfMY=",
    "1AZWarzMBuwTRob8VkqCT1TZaw-1_2vUhzn7c5JWWhrSoqyjq5FhoryjtsxxCg0PIzM9Lp1-fJhfW50JLcrWHc9bNG-HyLrFeN7ExvuZ4_K5VC3vgw2L5iHtKNO9B0E9tzumRsR8yN_DieBGOKjml5rfTNkWeORSMG_qd_zVCi4Qxr2Rd6SE-rIUkDRR9j58GWKzmsddDwqtWuiUMm1JlMFVv5pLFgnyWASWDwMSGI9a2MYKfnGsIXZupHt6BByVigM9lAqamlF_OEeBQeMvjFKDJyM3-nNjL4onnXAhu6kBq5LBgWk33tNPmU3OMewbsCUQ00_5Mk22I_s-GnMZYUDKKkG1nJU=",
    "1AZWarzMBuxiKOXDLx5zXGWZQN4fNW3NTW2rc6rqjMIhohqK8boTcCJcf59rxzYpONAOpz5F7z4j9tU6flsN-_5hdVkMVxCI4EgjYsvtMnvDTSkYPW1n2gIfEe2piUGcpud6L8LzSal5fYD2k8tD9cgn1QDiMe2p52ONDbT1uuGhaH38doecmStEmrdICoPrVnVrGVDwrQDVXreevM3owMkBsDzxVKIk56am9B6-CKUeWxPDgZB3JE_q6P5MU3iKVy9CW_4yJSZ_pu0lp5c3Ip_In8JCYZM1IsOXYCOhwDMqhzTmNhq5pE4Sp7BixBXPSgUNsb6HGduDaugFFCJi0bvFyagx5A7E=",
    "1AZWarzMBuzCVyIScT7ym9B3N4JynEbSpuTCL4Frjeegr8s1_cRDhZnhnf6i6QBIDKKFbeE7gkajFMXXb6BTxnMfwdzDMKHEEYoc2OVtU3UicsD0lj6ewrahuXLRqS_xdXxRiGoWpJban95wIQJWO9uSHPkZIMIygFed5njKp5YpRzpWVMURX4bAAELra75oeX9YnNy56UXfhXuZRMrqchAkf-89nY49BB3Rj1XP1MQ3zBeM5oR1kZhXcXdFYtKUzdhh95xFHU5pOxJ_5q0fEbhO43woV4zd722yaMKDUf7-R3tdC6Hv8U1XbUvs8xRgwyx4Kz69N7os3f6vxUeDJ7rOM7sEnTRs=",
    "1AZWarzMBu5ojimvsgTse5a12eZYKhJE2d4lbKwIyYYYT2OJnDs0GC6hElQQQz876RPsgE8h5inUaE6qbl8PHhR8RPe7FaNSTAlB6gHTaTp1-zFmRP3i0CLvDFhIttIjXvX1L45-KIll0MEO5IMJhzH2Uv-jc4BtX5CS90WQkwcTkpwQd7IfDeESXdqhNUDwFN2oHFFbUfIgofY0FKD7kCeaVcHZ0wqQUNPF6WeNvpCcyKLJoGXHJaIwTKyY_U4tlOVfordU6PmxH2qZYDjWhU1JiEOxPe_MUZbK_i4o6mQT1rQ4wA9urAwZXNS4ZuxbKyCIPxP6HmmgRI9oq0dN05uxYd1EH-t8=",
    "1AZWarzMBu4cZlY7jW7czHnkw9LONUt1uxyEWuIhdSo-quY9PM9bAo3l8fJS7saEHFUmWiGneSHERpkSXvsQmmjgHnJszrMfT7NBay0xnQ6Nw2V86vvUm_NzySdu6YJecv8V7j59ubna-_HkcBqQfExKJtA0OpwSIZDIzvY84ZOdZsAJmu5WXRxsGa6dg5yp6MaFyh7UPUqqXQO_An22ogKtU_BpxOSYPDQ330gEWC_Y_9n7_Yf88srkf6kP7IuVe7IKX64hw0A3aubAVF6xzDq-08qEg4B7AcA27KMbcirZawS_g7mJ_4DFHQsmJLU0aaS-FD2FR0YT6I-j_307qXZW6gBUEv_c=",
    "1AZWarzMBu4SeXLSd-_L9P5ZtyFUc21ZQ10J9Dm45YTC3n2wODj96glhu7zq90ebCxfyDkMaPlTju3UmzWc3FeoHUBaM8h5W7NpgOlwxwSk43cBKYfw0FdtWwrOSiHMDlD0tNSmPDkHK7PhCSOXk4BlTTIgVoNHH71IJ4lvqtxk8GhY_Mtd2mfE-o9pRN3VfETLMbtFfKrVKGO3pvnsHdg7dosPffeMOmeX6HzoidAdlXlovRCBWgkwbaFQtohder-92JqNRCqxJd19oEVbd9uvZaSD1LEBZJaw1vLcIahoctbURRz2XRkckwkXlcoySnX-lkYCNIZEnKLR2bj6UxzDmurpzC30g=",
    "1AZWarzMBu0ZDeYT-0wHKZjB4KnK6w1AunIZJqJkK4Uga9TPmr-ud59XZKhWk-2kkwC5H-RujD6zdVisc3LH9amYsPvTsJj8Asbqh_TdkRCM3kEXYoUkKfOLxFY-k6-osKTmBhi8kpIpnySWCnYTwAijiDLg3N3v5Ox1I8nj6Op6gXVAWH3Ygi38m3n34bz0Aed0DH4HH7wbkkOib5VmPpP62pf39szplV5egn0ZQA-nCVmkaTY6j5AXI0MHYQw8pczzMTEq27A7QZW33rcRfHg1nsEhjwPhZrw855oAG-K9TEaEXeCEVVvQVebAAixB0siL3O78mf1BRwZg0xBBltF4yEEP6VzM=",
    "1BVtsOHEBuzBa1BP1CIg4KB2LTChlBMC4eKou1XBfvzE3dnaWe2DQ9yX3XFzrhqXyY3xvDKD4jLziVGCavS2NuWQxei4-u1z45mYux7TgfBgAnv_JPcIi4ExtvBEXYsCREyGzB3Am6xl6z9nrnZf62qOvgEi3t4ThUlnGTxcZ_7S1b6bDMbfLek8Xj7RRPOjJiVJAVWqbXE4o-4JAD4PT3f95dxxxlBHJx44TLun4fGldw2hqRtne_Ls6DQXxVex7LoqSFRRSLq_vKE4ONiYM3F0FQ7UDRoOMQnCxys44e4UR-I3Lh_PQ3MJ2kVBzT9Rj5A9BKJm_mnCbjowTCYKMnVr2zwYcSCw=",
    "1BJWap1sBu1XDY5wH0NECItYC89G3TWKiawo67L_LhbhYPHXVh6jXdEiCn8n4evZVq01itb1bF7964aDodzxDFLTO7t_aBN_Z8VJOtqUOE1JXKuwt_A9go40R6lS0n_U1smmZS7gqCayImLEIVhNepXHQG76UUHx6wHoqA8CT1iDqdNsHI7TZUNvc1q6zD4Bi4rHnq9iJkhGawi643dSbTO5Zc0ILoF3fnrjWVRNpI5q-zAJQ6achyPWObhkMB2VK0c6VyCy7P4uLbTOgfX3s3ChNStcc45oyRRiRNuPNJzPDVcGTxzxPYzbMCSgt9wCke0xoiLfXhUn9FWQkQfed2GB-RUQyPeY=",
    "1AZWarzMBuwXiSfFqIL6uEMofyKsqfAdvOpz2RW3fBrOHZarYDjtGuHCyZLtOYPhE1bKiUd257gvetXFAcZ64maKvpxI3VjS4BeUTkkjXmuE5Eel1OXUPUvqfy9kYi1ovXVl3hxZXzkIHNDRJh8gBSm5dDELPutSi0OD92XZIjAbwGHbY9MjFLNIIy1BNqQhmUfsPB1pFSYBgvVeeIBFi3w-PQLo4y_oAqFsMZIOS3u0pUT-TgC2XG24vdhRvdU-StjzuSfvQgW_IkxUm8VRfWj4ZZCfmDj-8hq7sFMQoMwazHSIg8tTOTFsQ1KoOGEPkSqnS5uFU4wcPfZQCpZAumzPWofLt7fU=",
    "1AZWarzMBu8DutsSGFufFJ2bK38NAzY1M6aVrsxef_DMhjICsGrrY1LIa8yyB-a2IMVCMDUSIf_DuwXMEIyAhqDF-QOLHboZENmQEJTZssPAhhegjMpF5I-cZF5zNas4elrmgHDLNagHDoIydORvCrPqgzrxRamRrDnKYZqZc3H5TB49R-fzl1PFJvYk1KV9qwwPSGlwGbB9o7c1WVNGiOJB7Lj3HXZ0F27N8fElYomoBqFJzpU1ROaqFOi46qPIulojVVWJm8GVrEy_E5YbbelwN3cKsfq0qozQtAc83VgzrowXIR3yR5IaR3vjx7jWOxJoFfg1pJCUG8da1VCkN_p5QQdtW6IE=",
    "1AZWarzMBu2VEXjAKNKTywShkQQzTVgcOvZpSPs75ybD53rSFgVFFgwhUR2L9aRAyqWvTy2DT7QqG_vOPwf_rdwCjijiydh7wf6ti7EskoZVbu3UxDKHelI27Z6Cx2H4xj9Xki68V5w-10Wsg0X_5RlBTUXQMCpX50_j4SodvHXayiqDYxTvERmF-UYTVIACMtKAegQNkzQ5HJgBfqbiy9WQ7qzMzNEQD-g854ukmLK0arBWP_9lCDhgoHeNu7FvxxoU10Nx72cjIWFJ2monmPaY51Yot6DGyreEkKHLV1j4pHdtBlDMgrxfRvJeBhH72an3QKv6bgx4_OdMPMMue3VzqGqcaeNI=",
    "1AZWarzMBu0y6F-9kJB-_TNNoJWevRANT7TwFCTOF8IifG690V1obYBznvbHo2oaP_Qbw5zGGATtR2viZysMRBNfYI3-qQ2W4lqdzFefRU_EA8TFR7U_omm-68VpfTzzXMTqlQ2sYaIPhJKPKG1xMPEP54DWuPnVtIHOey8v4uFdJ8h-j0kvHKsSNlOoVCbwkGXiCn0NbpS6kf1kHexylOmgrqMGTfVRtECo5_0BRBY2--VQ7nMS43v2P5uZ63gmDMuAVOH_qobjsGZoLIPMePbmSl1njawkTagqVrPlnMQscW1uJmeUVpllKdxHD71Q5r1f9nBQX6adDVq-mFpOUsyq4ES2NQrE=",
]

SESSION_NAMES = ["Darveg2","Darvet","Darvet1","Darvet10","Darvet11","Darvet12","Darvet13","Darvet14","Darvet15","Darvet16","Darvet17","Darvet19","Darvet3","Darvet4","Darvet5","Darvet8","Darvet9","darvet18"]

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS cache (query TEXT PRIMARY KEY, result TEXT, timestamp TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS session_stats (session_index INTEGER, date TEXT, count INTEGER, PRIMARY KEY(session_index, date))')
    c.execute('CREATE TABLE IF NOT EXISTS total_stats (date TEXT PRIMARY KEY, total_requests INTEGER, successful INTEGER, failed INTEGER)')
    conn.commit()
    conn.close()

init_db()
logging.info(f"Бот: {BOT_USERNAME} | Сессий: {len(SESSION_STRINGS)} | {len(SESSION_STRINGS)*DAILY_LIMIT} запросов/день")

loop = asyncio.new_event_loop()
threading.Thread(target=lambda: loop.run_forever(), daemon=True).start()

class SM:
    def __init__(self):
        self.idx = 0
        self.lock = threading.Lock()
        self.busy = set()

    def get(self):
        with self.lock:
            for _ in range(len(SESSION_STRINGS)):
                if self.idx >= len(SESSION_STRINGS): self.idx = 0
                i = self.idx; self.idx += 1
                today = datetime.now().strftime('%Y-%m-%d')
                conn = sqlite3.connect(DB_FILE); c = conn.cursor()
                c.execute("SELECT count FROM session_stats WHERE session_index=? AND date=?", (i, today))
                row = c.fetchone(); conn.close()
                if row and row[0] >= DAILY_LIMIT: continue
                if i not in self.busy:
                    self.busy.add(i)
                    return i
            return None

    def release(self, i):
        with self.lock: self.busy.discard(i)

    def used(self, i):
        today = datetime.now().strftime('%Y-%m-%d')
        conn = sqlite3.connect(DB_FILE); c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO session_stats VALUES (?,?,0)", (i, today))
        c.execute("UPDATE session_stats SET count=count+1 WHERE session_index=? AND date=?", (i, today))
        conn.commit(); conn.close()

    def kill(self, i):
        today = datetime.now().strftime('%Y-%m-%d')
        conn = sqlite3.connect(DB_FILE); c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO session_stats VALUES (?,?,0)", (i, today))
        c.execute("UPDATE session_stats SET count=? WHERE session_index=? AND date=?", (DAILY_LIMIT, i, today))
        conn.commit(); conn.close()

sm = SM()

class ParserError(Exception): pass

def cache_get(q):
    conn = sqlite3.connect(DB_FILE); c = conn.cursor()
    c.execute("SELECT result FROM cache WHERE query=?", (q,)); r = c.fetchone(); conn.close()
    return r[0] if r else None

def cache_set(q, r):
    conn = sqlite3.connect(DB_FILE); c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO cache VALUES (?,?,?)", (q, r, datetime.now().isoformat()))
    conn.commit(); conn.close()

def inc_total(ok=True):
    today = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect(DB_FILE); c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO total_stats VALUES (?,0,0,0)", (today,))
    c.execute("UPDATE total_stats SET total_requests=total_requests+1, successful=successful+?, failed=failed+? WHERE date=?",
              (1 if ok else 0, 0 if ok else 1, today))
    conn.commit(); conn.close()

def clean_result(text):
    if not text: return text
    lines = text.strip().split('\n')
    while lines:
        last = lines[-1].lower().strip()
        if any(x in last for x in ['поиск завершен', 'поиск закончен', 'поиск завершён', 'search complete', 'search finished']):
            lines.pop()
        else:
            break
    return '\n'.join(lines).strip()

async def wait_search(client, entity, timeout=SEARCH_TIMEOUT):
    start = time.time()
    seen = set()
    async for msg in client.iter_messages(entity, limit=5):
        seen.add(msg.id)

    collected = []
    while time.time() - start < timeout:
        await asyncio.sleep(2)
        async for msg in client.iter_messages(entity, limit=10):
            if msg.id not in seen:
                seen.add(msg.id)
                if msg.text:
                    t = msg.text.lower()
                    if any(x in t for x in ['лимит', 'limit', 'flood', 'исчерпан', 'попробуйте позже', 'подпишитесь']):
                        return ('LIMIT', msg.text)
                    if 'поиск завершен' in t or 'поиск закончен' in t or 'поиск завершён' in t:
                        collected.append(msg.text)
                        return ('DONE', '\n'.join(reversed(collected)))
                    if any(x in t for x in ['searching', 'поиск', 'загруз', 'load', 'wait', 'подожд', 'обрабат', 'process']):
                        continue
                    if 'not found' in t or 'не найдено' in t or 'no data' in t:
                        return ('DONE', msg.text)
                    collected.append(msg.text)
                elif msg.media and msg.message:
                    collected.append(msg.message)
    return (None, None)

async def check_subscribe(client, entity):
    async for msg in client.iter_messages(entity, limit=3):
        if msg.text and 'subscribe' in msg.text.lower():
            urls = []
            if msg.buttons:
                for row in msg.buttons:
                    for btn in row:
                        if hasattr(btn, 'url') and btn.url: urls.append(btn.url)
            if msg.entities:
                for ent in msg.entities:
                    if isinstance(ent, MessageEntityTextUrl): urls.append(ent.url)
            m = re.search(r'(https://t\.me/\S+|@\w+)', msg.text or '')
            if m: urls.append(m.group(1))
            for url in urls:
                try:
                    if 'joinchat' in url or '+' in url:
                        await client(ImportChatInviteRequest(url.split('/')[-1].replace('+','')))
                    else:
                        await client(JoinChannelRequest(url.split('/')[-1].replace('@','')))
                    await asyncio.sleep(3)
                    return True
                except: pass
    return False

async def parser_flow(username):
    cached = cache_get(username)
    if cached: return cached

    for attempt in range(MAX_RETRIES):
        i = sm.get()
        if i is None:
            raise ParserError("Все сессии исчерпаны.")

        name = SESSION_NAMES[i] if i < len(SESSION_NAMES) else f"s{i}"
        proxy = get_proxy()
        client = TelegramClient(StringSession(SESSION_STRINGS[i]), API_ID, API_HASH, loop=loop,
                                **({"proxy": proxy} if proxy else {}))
        try:
            await client.connect()
            if not await client.is_user_authorized():
                logging.warning(f"{name}: не авторизована")
                sm.kill(i); continue

            entity = await client.get_entity(BOT_USERNAME)

            msgs = [m.id async for m in client.iter_messages(entity, limit=5)]
            if msgs:
                await client.delete_messages(entity, msgs)

            # Отправляем юзернейм сразу
            await client.send_message(entity, username)
            await asyncio.sleep(1)

            # Если бот просит подписку
            if await check_subscribe(client, entity):
                await client.send_message(entity, username)

            status, result = await wait_search(client, entity, SEARCH_TIMEOUT)

            if status == 'LIMIT':
                sm.kill(i); inc_total(False)
                logging.warning(f"{name}: лимит — {result[:50] if result else '?'}")
                continue

            if not result:
                sm.used(i); inc_total(False)
                logging.warning(f"{name}: нет ответа за {SEARCH_TIMEOUT}с")
                continue

            cleaned = clean_result(result)

            if not cleaned or len(cleaned.strip()) < 5:
                sm.used(i); inc_total(False)
                continue

            cache_set(username, cleaned)
            sm.used(i); inc_total(True)
            logging.info(f"{name}: OK — {username}")
            return cleaned

        except FloodWaitError as e:
            logging.error(f"{name}: FloodWait {e.seconds}с")
            sm.kill(i); inc_total(False); continue
        except Exception as e:
            logging.error(f"{name}: {e}")
            sm.used(i); inc_total(False); continue
        finally:
            sm.release(i)
            if client.is_connected():
                await client.disconnect()
            await asyncio.sleep(2)

    raise ParserError("Сессии не ответили. Попробуй ещё раз.")

@app.route('/api/search', methods=['POST'])
def search():
    if request.headers.get("X-Parser-Key", "") != PARSER_API_KEY:
        return jsonify({"error": "Unauthorized"}), 403
    data = request.json
    if not data or not data.get('query'):
        return jsonify({"error": "Query required"}), 400
    q = data['query'].strip().replace('@', '').replace('https://t.me/', '')
    if not q:
        return jsonify({"error": "Invalid query"}), 400
    try:
        future = asyncio.run_coroutine_threadsafe(parser_flow(q), loop)
        result = future.result(timeout=90)
        return jsonify({"success": True, "data": result})
    except Exception as e:
        inc_total(False)
        return jsonify({"error": str(e)}), 500

@app.route('/stats', methods=['GET'])
def stats():
    if request.headers.get("X-Parser-Key", "") != PARSER_API_KEY:
        return jsonify({"error": "Unauthorized"}), 403
    conn = sqlite3.connect(DB_FILE); c = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d')
    c.execute("SELECT session_index, count FROM session_stats WHERE date=?", (today,))
    rows = c.fetchall()
    c.execute("SELECT total_requests, successful, failed FROM total_stats WHERE date=?", (today,))
    total = c.fetchone(); conn.close()
    usage = {r[0]: r[1] for r in rows}
    midnight = (datetime.now() + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    sessions = []
    for i in range(len(SESSION_STRINGS)):
        u = usage.get(i, 0)
        sessions.append({"i": i, "name": SESSION_NAMES[i], "used": u, "left": DAILY_LIMIT - u})
    return jsonify({
        "date": today,
        "reset": str(midnight - datetime.now()).split('.')[0],
        "capacity": len(SESSION_STRINGS) * DAILY_LIMIT,
        "used": sum(usage.values()),
        "left": len(SESSION_STRINGS) * DAILY_LIMIT - sum(usage.values()),
        "total_req": total[0] if total else 0,
        "ok": total[1] if total else 0,
        "fail": total[2] if total else 0,
        "sessions": sessions
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "bot": BOT_USERNAME, "sessions": len(SESSION_STRINGS), "capacity": len(SESSION_STRINGS) * DAILY_LIMIT})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), threaded=True)
