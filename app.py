# app.py
# PRIME Parser: StringSession + SQLite Cache + Failover

import os
import re
import asyncio
import threading
import logging
import time
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, request, jsonify
from telethon.errors import FloodWaitError
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.tl.types import MessageEntityTextUrl

# --- КОНФИГ ---
API_ID = 33544148
API_HASH = "31ded48782ea9d640ba379f630cc114f"
DB_FILE = "prime_parser.db"
PARSER_API_KEY = "PRIME_SECURE_PARSER_2026"
DAILY_LIMIT_PER_SESSION = 3
MAX_RETRIES = 3

BOTS = [
    {"name": "manultoolbot", "username": "@manultoolbot"}
]

# --- СЕССИИ (18 штук, StringSession) ---
SESSION_STRINGS = [
    "1BVtsOHEBu1c4bp4cwNBRpES5O-avYu46p1lCILeSl9UpUibw50v-pIqIWuttfQWckT9aMCZtPrVegRSkyaNceBA40oqf1hSzhQQbuWIpsLlKmoMDNuUaYi4UVyGOaX_SIm_hM4IhZk0kO63aKNbAP3xWDZHiCAXipMoBLkfyXokncDlLb2PZbTTL2mRrvKYymlIY4zNIBtZuhdUo3bcRg1lRj-FcgCaJs8LDV9cJcZH1etS4ov17JxpMuY7u1VtVkx-stblKqtetm-6_T6q6WHMQSgDcLU1hMp8wpig-EwTaNpUgNzpZlQDl3PxhlwOV136aAJGVU5vAw2iZ19j-gzgKtnBUw_Q=",
    "1AZWarzMBux4l6kt8pOF698potSnT7iJZpRw12zPkxLPm2_cGiF_z_udGtrOpPm2Q4jzOh7Log2KAK4OecXGCqgouHA8pZGnQtefFFBXsgcSddyQYgbKJTkE0yfCfJ3d5DU-NXLxMXtfwqzz8ns5UsQscpD7X5QnQQA7iAi7elfvpV95AY3yaYi3K9QLhh_q0DbcrPcbdoYhFPgq4KKIwvbaK6BFUKSNz_KWhA4MxFc6LqhwqCWTxcVFQb2qUOoPQmxfGS3h-xgyZNgR8GyApleeSG5xoLTMdXrBGCz2N45SY2NrrnxlF8MIPP90LFkiRnAmF3fV_o4tMPSNXGCjQySmC1FnZcXk=",
    "1AZWarzMBu5u41Q2C6IHBmG2ijVxyhPmTCGkOWcScpGrRG0SPTHjbstKbtXZsusTotnIzKhovNTyqIODy47QVK5YjTJUlsUohKL475_HKOKIPxD6ppkPbau1_WEMtO0OvdBzkC8EeS0G4z4s2NqmMkRVvWc1o1aOYAoos94_o8ZBg3Ah521ksi64C40y6DHSK3eZQ0LRXs3NKH65pMb1jvW0Gmudejh8sqJDrBMEUhcZxGl0yzev6HzPalEdCffBY-n9uZfnTopflJ1uWwZJLL3B-F_alLcwhzopUWphdYYPSK-03SvhO6fIvQAq8LxkLGrqhuF3X6I0cITt2gbjMUuaFXY8H_6c=",
    "1AZWarzMBuwuMqEemTWnxkthAih3DdeizwzK9yhomeZPo9my8Pj4HlCq60O63Lpbyo4g1bH6CUrLSoRD0oq33y4w_oqkcRWXT8YfT3F4OKvN5uAEWb3Bhrl1-yprI0cDKmxqShHOMLOx95T9Ot4VRDVwm7IE-nn-AcrXPG_MSR7SWnQwM_ZDo3WeGkEV3e4joSWo7uBfMS7FLzxh4Z4KGWtVg5CGlCx5MmSP8BYLbYUhVmz6wvLminKzcMcAac-aL9eFIcV1bm5yS8SyyMPw6gVT_BuEpVixFUuPXaBfIsGaOQLjehxxMG-bUDFgVnmJd7u4wJopmMIIR5s7zV-hBkJb15Lp7-PI=",
    "1AZWarzMBu0Uy6a8OB0hXPxpaKVrAwI3cnOjLX6h0zIeD3v4iBMne4M0xlPK88naqg4we37wgFx9q1TcMU9EIf7gmX31wR39hFmpeqPfdufL0ziXp_CZ8ATRTvyl9pO6tALKub2PncZRtzrwCIiVnF7rZGxUfOMisDoOQKrGIk7Zbtb-JdSJcBFXHBpOL_0DweC6ZyoatB-KXeSkP5nfO8_NLaokFac3LkmPPvX369avOarkoIp17dOT6IZtOWHA1jsnJBxL01UK_DpgRHD7jT6BfkxsMloESYgSOxZ9it7TuuWbfxEICkFdAmT80m3L4oDzjaqsdykppkLvIPROeq2SwO62OfMY=",
    "1AZWarzMBuwTRob8VkqCT1TZaw-1_2vUhzn7c5JWWhrSoqyjq5FhoryjtsxxCg0PIzM9Lp1-fJhfW50JLcrWHc9bNG-HyLrFeN7ExvuZ4_K5VC3vgw2L5iHtKNO9B0E9tzumRsR8FyN_DieBGOKjml5rfTNkWeORSMG_qd_zVCi4Qxr2Rd6SE-rIUkDRR9j58GWKzmsddDwqtWuiUMm1JlMFVv5pLFgnyWASWDwMSGI9a2MYKfnGsIXZupHt6BByVigM9lAqamlF_OEeBQeMvjFKDJyM3-nNjL4onnXAhu6kBq5LBgWk33tNPmU3OMewbsCUQ00_5Mk22I_s-GnMZYUDKKkG1nJU=",
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

SESSION_NAMES = [
    "Darveg2", "Darvet", "Darvet1", "Darvet10", "Darvet11",
    "Darvet12", "Darvet13", "Darvet14", "Darvet15", "Darvet16",
    "Darvet17", "Darvet19", "Darvet3", "Darvet4", "Darvet5",
    "Darvet8", "Darvet9", "darvet18"
]

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS cache (query TEXT PRIMARY KEY, result TEXT, timestamp TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS session_stats (session_index INTEGER, date TEXT, count INTEGER, PRIMARY KEY (session_index, date))''')
    c.execute('''CREATE TABLE IF NOT EXISTS total_stats (date TEXT PRIMARY KEY, total_requests INTEGER, successful INTEGER, failed INTEGER)''')
    conn.commit()
    conn.close()

init_db()

logging.info(f"Загружено StringSession: {len(SESSION_STRINGS)}")
logging.info(f"Лимит на сессию в день: {DAILY_LIMIT_PER_SESSION}")
logging.info(f"Всего запросов в день: {len(SESSION_STRINGS) * DAILY_LIMIT_PER_SESSION}")

loop = asyncio.new_event_loop()
threading.Thread(target=lambda: loop.run_forever(), daemon=True).start()

class SessionManager:
    def __init__(self, session_strings, session_names):
        self.sessions = session_strings
        self.names = session_names
        self.current_index = 0
        self.lock = threading.Lock()
        self.busy_sessions = set()

    def get_available(self):
        with self.lock:
            for _ in range(len(self.sessions)):
                if self.current_index >= len(self.sessions):
                    self.current_index = 0
                idx = self.current_index
                self.current_index += 1

                today = datetime.now().strftime('%Y-%m-%d')
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute("SELECT count FROM session_stats WHERE session_index=? AND date=?", (idx, today))
                row = c.fetchone()
                conn.close()

                if row and row[0] >= DAILY_LIMIT_PER_SESSION:
                    continue

                if idx not in self.busy_sessions:
                    self.busy_sessions.add(idx)
                    name = self.names[idx] if idx < len(self.names) else f"session_{idx}"
                    logging.info(f"Выдана сессия: {name} (idx={idx}, использовано {row[0] if row else 0}/{DAILY_LIMIT_PER_SESSION})")
                    return (idx, self.sessions[idx])
            return None

    def release(self, idx):
        with self.lock:
            if idx in self.busy_sessions:
                self.busy_sessions.remove(idx)

    def increment_usage(self, idx):
        today = datetime.now().strftime('%Y-%m-%d')
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO session_stats (session_index, date, count) VALUES (?, ?, 0)", (idx, today))
        c.execute("UPDATE session_stats SET count = count + 1 WHERE session_index=? AND date=?", (idx, today))
        conn.commit()
        conn.close()

    def mark_exhausted(self, idx):
        today = datetime.now().strftime('%Y-%m-%d')
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO session_stats (session_index, date, count) VALUES (?, ?, 0)", (idx, today))
        c.execute("UPDATE session_stats SET count = ? WHERE session_index=? AND date=?", (DAILY_LIMIT_PER_SESSION, idx, today))
        conn.commit()
        conn.close()
        name = self.names[idx] if idx < len(self.names) else f"session_{idx}"
        logging.info(f"Сессия {name} исчерпана.")

session_manager = SessionManager(SESSION_STRINGS, SESSION_NAMES)

class ParserError(Exception):
    pass

# --- КЭШ ---
def get_cached_result(query):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT result FROM cache WHERE query=?", (query,))
    row = c.fetchone()
    conn.close()
    if row:
        logging.info(f"Кэш HIT: {query}")
        return row[0]
    return None

def save_to_cache(query, result):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO cache (query, result, timestamp) VALUES (?, ?, ?)",
              (query, result, datetime.now().isoformat()))
    conn.commit()
    conn.close()

# --- СТАТИСТИКА ---
def increment_total(success=True):
    today = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO total_stats (date, total_requests, successful, failed) VALUES (?, 0, 0, 0)", (today,))
    c.execute("UPDATE total_stats SET total_requests = total_requests + 1, successful = successful + ?, failed = failed + ? WHERE date=?",
              (1 if success else 0, 0 if success else 1, today))
    conn.commit()
    conn.close()

def get_session_stats():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d')

    c.execute("SELECT session_index, count FROM session_stats WHERE date=?", (today,))
    rows = c.fetchall()

    c.execute("SELECT total_requests, successful, failed FROM total_stats WHERE date=?", (today,))
    total_row = c.fetchone()
    conn.close()

    now = datetime.now()
    midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    time_left = str(midnight - now).split('.')[0]

    usage_map = {row[0]: row[1] for row in rows}

    sessions = []
    total_used = 0
    total_limit = len(SESSION_STRINGS) * DAILY_LIMIT_PER_SESSION

    for i in range(len(SESSION_STRINGS)):
        used = usage_map.get(i, 0)
        total_used += used
        name = SESSION_NAMES[i] if i < len(SESSION_NAMES) else f"session_{i}"
        sessions.append({
            "index": i,
            "name": name,
            "used": used,
            "limit": DAILY_LIMIT_PER_SESSION,
            "remaining": DAILY_LIMIT_PER_SESSION - used,
            "status": "Исчерпана" if used >= DAILY_LIMIT_PER_SESSION else ("Занята" if i in session_manager.busy_sessions else "Активна")
        })

    return {
        "date": today,
        "reset_timer": time_left,
        "total_limit": total_limit,
        "total_used": total_used,
        "total_remaining": total_limit - total_used,
        "total_requests_today": total_row[0] if total_row else 0,
        "successful_today": total_row[1] if total_row else 0,
        "failed_today": total_row[2] if total_row else 0,
        "active_sessions": sum(1 for s in sessions if s["status"] == "Активна"),
        "exhausted_sessions": sum(1 for s in sessions if s["status"] == "Исчерпана"),
        "sessions": sessions
    }

# --- TELETHON ЛОГИКА ---
async def clear_chat_history(client, entity, count=10):
    try:
        msgs = [m.id async for m in client.iter_messages(entity, limit=count)]
        if msgs:
            await client.delete_messages(entity, msgs)
    except Exception as e:
        logging.error(f"Очистка чата: {e}")

async def click_button_by_text(client, entity, text_patterns):
    await asyncio.sleep(1)
    async for msg in client.iter_messages(entity, limit=3):
        if msg.buttons:
            for row in msg.buttons:
                for btn in row:
                    if btn and btn.text:
                        for pattern in text_patterns:
                            if pattern in btn.text.lower():
                                await btn.click()
                                logging.info(f"Кнопка: {btn.text}")
                                return True
    return False

async def wait_for_response(client, entity, timeout=8):
    start_time = time.time()
    seen_ids = set()
    async for msg in client.iter_messages(entity, limit=5):
        seen_ids.add(msg.id)

    while time.time() - start_time < timeout:
        await asyncio.sleep(1)
        async for msg in client.iter_messages(entity, limit=5):
            if msg.id not in seen_ids:
                seen_ids.add(msg.id)
                if msg.text:
                    t = msg.text.lower().strip()
                    if "not found" in t or "не найдено" in t or "no data" in t:
                        return msg.text
                    if any(x in t for x in ["analysis in progress", "analysis complete", "loading", "please wait"]):
                        async for prev_msg in client.iter_messages(entity, limit=1, offset_id=msg.id):
                            if prev_msg and prev_msg.text:
                                pt = prev_msg.text.lower()
                                if not any(x in pt for x in ["analysis in progress", "analysis complete", "loading", "please wait"]):
                                    return prev_msg.text
                        continue
                    return msg.text
                elif msg.media and msg.message:
                    return msg.message
    return None

def check_limit_text(text):
    if not text: return False
    t = text.lower()
    return any(x in t for x in ["лимит", "limit", "flood", "исчерпан", "попробуйте позже", "слишком много", "закончились запросы", "subscribe to use", "подпишитесь", "оформите"])

async def subscribe_to_channel(client, url):
    try:
        if "joinchat" in url or "+" in url:
            hash_code = url.split("/")[-1].replace("+", "")
            await client(ImportChatInviteRequest(hash_code))
        else:
            channel_name = url.split("/")[-1].replace("@", "")
            await client(JoinChannelRequest(channel_name))
        logging.info(f"Подписка: {url}")
        await asyncio.sleep(2)
        return True
    except Exception as e:
        if "already" in str(e).lower() or "invitation" in str(e).lower():
            return True
        logging.error(f"Подписка {url}: {e}")
        return False

async def check_and_subscribe(client, entity):
    async for msg in client.iter_messages(entity, limit=3):
        if msg.text and "subscribe to use" in msg.text.lower():
            if msg.buttons:
                for row in msg.buttons:
                    for btn in row:
                        if hasattr(btn, 'url') and btn.url:
                            if await subscribe_to_channel(client, btn.url): return True
            if msg.entities:
                for ent in msg.entities:
                    if isinstance(ent, MessageEntityTextUrl):
                        if await subscribe_to_channel(client, ent.url): return True
            if msg.text:
                match = re.search(r'(@\w+|https://t.me/\w+)', msg.text)
                if match:
                    if await subscribe_to_channel(client, match.group(1)): return True
    return False

async def parser_flow(username):
    cached = get_cached_result(username)
    if cached: return cached

    bot = BOTS[0]

    for attempt in range(MAX_RETRIES):
        result = session_manager.get_available()
        if not result:
            raise ParserError("Все сессии исчерпаны или заняты.")

        idx, session_string = result
        name = SESSION_NAMES[idx] if idx < len(SESSION_NAMES) else f"session_{idx}"

        client = TelegramClient(StringSession(session_string), API_ID, API_HASH, loop=loop)
        try:
            await client.connect()
            if not await client.is_user_authorized():
                logging.warning(f"{name}: не авторизована, скип")
                session_manager.mark_exhausted(idx)
                continue

            entity = await client.get_entity(bot["username"])
            await clear_chat_history(client, entity, 5)

            await client.send_message(entity, "/start")
            await asyncio.sleep(1.5)

            if await check_and_subscribe(client, entity):
                await client.send_message(entity, "/start")
                await asyncio.sleep(1.5)

            await click_button_by_text(client, entity, ["search", "поиск", "найти", "🔍", "🔎", "искать"])
            await asyncio.sleep(1)
            await click_button_by_text(client, entity, ["telegram", "тг", "tele", "телеграм"])

            await asyncio.sleep(0.5)
            await client.send_message(entity, username)

            response_text = await wait_for_response(client, entity, timeout=8)

            if not response_text:
                logging.warning(f"{name}: нет ответа за 8 сек")
                session_manager.increment_usage(idx)
                increment_total(success=False)
                continue

            if check_limit_text(response_text):
                session_manager.mark_exhausted(idx)
                increment_total(success=False)
                logging.warning(f"{name}: лимит исчерпан ботом")
                continue

            save_to_cache(username, response_text)
            session_manager.increment_usage(idx)
            increment_total(success=True)
            await clear_chat_history(client, entity, 10)
            logging.info(f"{name}: успех — {username}")
            return response_text

        except FloodWaitError as e:
            logging.error(f"{name}: FloodWait {e.seconds}с")
            session_manager.mark_exhausted(idx)
            increment_total(success=False)
            continue
        except Exception as e:
            logging.error(f"{name}: {e}")
            session_manager.increment_usage(idx)
            increment_total(success=False)
            continue
        finally:
            session_manager.release(idx)
            if client.is_connected():
                await client.disconnect()

    raise ParserError("3 сессии подряд не ответили. Попробуй ещё раз.")

# --- FLASK API ---
@app.route('/api/search', methods=['POST'])
def search():
    auth_header = request.headers.get("X-Parser-Key", "")
    if auth_header != PARSER_API_KEY:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json
    if not data or not data.get('query'):
        return jsonify({"error": "Query required"}), 400

    query = data['query'].strip().replace('@', '').replace('https://t.me/', '')
    if not query:
        return jsonify({"error": "Invalid query"}), 400

    try:
        future = asyncio.run_coroutine_threadsafe(parser_flow(query), loop)
        result = future.result(timeout=60)
        return jsonify({"success": True, "data": result})
    except Exception as e:
        logging.error(f"API Error: {e}")
        increment_total(success=False)
        return jsonify({"error": str(e)}), 500

@app.route('/stats', methods=['GET'])
def stats():
    auth_header = request.headers.get("X-Parser-Key", "")
    if auth_header != PARSER_API_KEY:
        return jsonify({"error": "Unauthorized"}), 403
    return jsonify(get_session_stats())

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "sessions": len(SESSION_STRINGS), "daily_capacity": len(SESSION_STRINGS) * DAILY_LIMIT_PER_SESSION})

if __name__ == '__main__':
    logging.info(f"PRIME Parser на порту 5000 | {len(SESSION_STRINGS)} сессий | {len(SESSION_STRINGS) * DAILY_LIMIT_PER_SESSION} запросов/день")
    app.run(host='0.0.0.0', port=5000, threaded=True)
