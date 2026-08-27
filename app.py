# Prepared with love by YakomoDev - https://ko-fi.com/yakomodev
import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"
import datetime
import math
import threading
import sqlite3
import calendar
import socket
import theme_manager as tm
from settings_screen import SettingsScreen
from about_screen import AboutScreen


# Strict Offline Environment Guard
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

_original_connect = socket.socket.connect
def guarded_connect(self, address):
    host = address[0] if isinstance(address, tuple) else address
    # Allow local loopback and local Unix sockets for X11 compatibility
    if host not in ("127.0.0.1", "localhost", "::1") and not str(host).startswith("/"):
        raise socket.error(f"Network access denied to {host}. Application is running in a strictly offline environment.")
    return _original_connect(self, address)
socket.socket.connect = guarded_connect

# Application Path Settings (forces execution-relative lookup for Nuitka compilation and cross-platform safety)
APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "data", "missions.db")

try:
    import llama_cpp
    if llama_cpp is not None and hasattr(llama_cpp, 'llama_log_set'):
        import ctypes
        def silent_llama_log_callback(level, message, user_data):
            pass
        _llama_log_callback = ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_char_p, ctypes.c_void_p)(silent_llama_log_callback)
        llama_cpp.llama_log_set(_llama_log_callback, ctypes.c_void_p())
except ImportError:
    llama_cpp = None
except Exception:
    pass

# Styling Constants - Loaded dynamically from theme_manager
BG_DARK = tm.BG_DARK
BG_CARD = tm.BG_CARD
BG_CARD_HEADER = tm.BG_CARD_HEADER
BORDER_COLOR = tm.BORDER_COLOR
TEXT_WHITE = tm.TEXT_WHITE
TEXT_MUTED = tm.TEXT_MUTED
ACCENT_PURPLE = tm.ACCENT_PURPLE
ACCENT_CYAN = tm.ACCENT_CYAN
SUCCESS_GREEN = tm.SUCCESS_GREEN
GLOW_COLOR = tm.GLOW_COLOR
WARN_ORANGE = tm.WARN_ORANGE
ERR_RED = tm.ERR_RED

_reshaper = None

def get_reshaper():
    global _reshaper
    if _reshaper is None:
        try:
            import arabic_reshaper
            config = {'delete_harakat': False}
            _reshaper = arabic_reshaper.ArabicReshaper(configuration=config)
        except Exception as e:
            print(f"Error initializing arabic_reshaper: {e}")
    return _reshaper

def get_arabic_text(text):
    if not text:
        return ""
    try:
        from bidi.algorithm import get_display
        reshaper = get_reshaper()
        if reshaper is not None:
            return get_display(reshaper.reshape(text))
    except Exception as e:
        print(f"Error shaping Arabic: {e}")
    return text


def normalize_arabic(text):
    if not text:
        return ""
    import re
    # Remove tashkeel/diacritics (harakat/chakkel)
    text = re.sub(r'[\u064B-\u065F\u0670]', '', text)
    # Normalize Alef forms (أإآ -> ا)
    text = re.sub(r'[أإآ]', 'ا', text)
    # Normalize Yaa/Alif Maqsura (ى -> ي)
    text = re.sub(r'ى', 'ي', text)
    # Normalize Taa Marbuta / Haa (ة -> ه)
    text = re.sub(r'ة', 'ه', text)
    return text

def shape_for_display(text):
    return tm.shape_for_display(text)

def get_model_path():
    agent_dir = os.path.join(APP_DIR, "agent")
    if os.path.exists(agent_dir):
        try:
            gguf_files = [f for f in os.listdir(agent_dir) if f.lower().endswith(".gguf")]
            if gguf_files:
                # Prioritize larger models by sorting by file size descending
                gguf_files.sort(key=lambda x: os.path.getsize(os.path.join(agent_dir, x)), reverse=True)
                return os.path.join(agent_dir, gguf_files[0])
        except Exception:
            pass
    return os.path.join(agent_dir, "Gemma 3 1B.gguf")

def get_arabic_text_multiline(text, max_chars=48):
    if not text:
        return ""
    try:
        from bidi.algorithm import get_display
        reshaper = get_reshaper()
        if reshaper is not None:
            import textwrap
            lines = textwrap.wrap(text, width=max_chars)
            shaped_lines = [get_display(reshaper.reshape(line)) for line in lines]
            return "\n".join(shaped_lines)
    except Exception as e:
        print(f"Error shaping Arabic multiline: {e}")
    return text

def is_english_or_french(text):
    if not text:
        return True
    valid_accents = "éèàçùâêîôûëïüÿœæÉÈÀÇÙÂÊÎÔÛËÏÜŸŒÆ"
    for char in text:
        val = ord(char)
        if 32 <= val <= 126 or char in valid_accents or char in "\r\n\t":
            continue
        else:
            return False
    return True

def get_mp3_duration(file_path):
    try:
        from mutagen.mp3 import MP3
        audio = MP3(file_path)
        if audio.info.length > 0:
            return audio.info.length
    except Exception:
        pass

    try:
        import pygame
        import os
        size = os.path.getsize(file_path)
        if size < 5 * 1024 * 1024:
            if pygame.mixer.get_init():
                sound = pygame.mixer.Sound(file_path)
                return sound.get_length()
    except Exception:
        pass

    try:
        import os
        size = os.path.getsize(file_path)
        with open(file_path, "rb") as f:
            # Read first 256KB to skip any large ID3 tags
            data = f.read(256 * 1024)
            
        # Check for ID3v2 header and skip it
        start_idx = 0
        if data.startswith(b"ID3") and len(data) >= 10:
            # ID3v2 size is at bytes 6-9 (4 bytes, synchsafe integer: 7 bits per byte)
            size_bytes = data[6:10]
            id3_size = (size_bytes[0] << 21) | (size_bytes[1] << 14) | (size_bytes[2] << 7) | size_bytes[3]
            # Add 10 bytes for the header itself
            id3_size += 10
            if id3_size < len(data):
                start_idx = id3_size

        bitrate = None
        for i in range(start_idx, len(data) - 4):
            if data[i] == 0xFF and (data[i+1] & 0xE0) == 0xE0:
                header = data[i:i+4]
                version = (header[1] & 0x18) >> 3
                layer = (header[1] & 0x06) >> 1
                bitrate_idx = (header[2] & 0xF0) >> 4
                if version == 3 and layer == 1: # MPEG 1 Layer 3
                    bitrates = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320]
                    if 0 < bitrate_idx < len(bitrates):
                        bitrate = bitrates[bitrate_idx] * 1000
                        break
                elif (version == 2 or version == 0) and layer == 1: # MPEG 2 or 2.5 Layer 3
                    bitrates = [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160]
                    if 0 < bitrate_idx < len(bitrates):
                        bitrate = bitrates[bitrate_idx] * 1000
                        break
        if bitrate:
            return (size * 8.0) / bitrate
    except Exception:
        pass

    return 18000.0

SURAH_MAPPING = [
    {"num": 1, "english": "Al-Fatihah", "arabic": "الفاتحة"},
    {"num": 2, "english": "Al-Baqarah", "arabic": "البقرة"},
    {"num": 3, "english": "Al-Imran", "arabic": "آل عمران"},
    {"num": 4, "english": "An-Nisa'", "arabic": "النساء"},
    {"num": 5, "english": "Al-Ma'idah", "arabic": "المائدة"},
    {"num": 6, "english": "Al-An'am", "arabic": "الأنعام"},
    {"num": 7, "english": "Al-A'raf", "arabic": "الأعراف"},
    {"num": 8, "english": "Al-Anfal", "arabic": "الأنفال"},
    {"num": 9, "english": "At-Taubah", "arabic": "التوبة"},
    {"num": 10, "english": "Yunus", "arabic": "يونس"},
    {"num": 11, "english": "Hud", "arabic": "هود"},
    {"num": 12, "english": "Yusuf", "arabic": "يوسف"},
    {"num": 13, "english": "Ar-Ra'd", "arabic": "الرعد"},
    {"num": 14, "english": "Ibrahim", "arabic": "إبراهيم"},
    {"num": 15, "english": "Al-Hijr", "arabic": "الحجر"},
    {"num": 16, "english": "An-Nahl", "arabic": "النحل"},
    {"num": 17, "english": "Al-Isra", "arabic": "الإسراء"},
    {"num": 18, "english": "Al-Kahf", "arabic": "الكهف"},
    {"num": 19, "english": "Maryam", "arabic": "مريم"},
    {"num": 20, "english": "Ta Ha", "arabic": "طه"},
    {"num": 21, "english": "Al-Anbiya'", "arabic": "الأنبياء"},
    {"num": 22, "english": "Al-Hajj", "arabic": "الحج"},
    {"num": 23, "english": "Al-Mu'minun", "arabic": "المؤمنون"},
    {"num": 24, "english": "An-Nur", "arabic": "النور"},
    {"num": 25, "english": "Al-Furqan", "arabic": "الفرقان"},
    {"num": 26, "english": "Ash-Shu'ara'", "arabic": "الشعراء"},
    {"num": 27, "english": "An-Naml", "arabic": "النمل"},
    {"num": 28, "english": "Al-Qasas", "arabic": "القصص"},
    {"num": 29, "english": "Al-'Ankabut", "arabic": "العنكبوت"},
    {"num": 30, "english": "Ar-Rum", "arabic": "الروم"},
    {"num": 31, "english": "Luqman", "arabic": "لقمان"},
    {"num": 32, "english": "As-Sajdah", "arabic": "السجدة"},
    {"num": 33, "english": "Al-Ahzab", "arabic": "الأحزاب"},
    {"num": 34, "english": "Saba'", "arabic": "سبأ"},
    {"num": 35, "english": "Fatir", "arabic": "فاطر"},
    {"num": 36, "english": "Ya Sin", "arabic": "يس"},
    {"num": 37, "english": "As-Saffat", "arabic": "الصافات"},
    {"num": 38, "english": "Sad", "arabic": "ص"},
    {"num": 39, "english": "Az-Zumar", "arabic": "الزمر"},
    {"num": 40, "english": "Ghafir", "arabic": "غافر"},
    {"num": 41, "english": "Fussilat", "arabic": "فصلت"},
    {"num": 42, "english": "Ash-Shura", "arabic": "الشورى"},
    {"num": 43, "english": "Az-Zukhruf", "arabic": "الزخرف"},
    {"num": 44, "english": "Ad-Dukhan", "arabic": "الدخان"},
    {"num": 45, "english": "Al-Jathiyah", "arabic": "الجاثية"},
    {"num": 46, "english": "Al-Ahqaf", "arabic": "الأحقاف"},
    {"num": 47, "english": "Muhammad", "arabic": "محمد"},
    {"num": 48, "english": "Al-Fath", "arabic": "الفتح"},
    {"num": 49, "english": "Al-Hujurat", "arabic": "الحجرات"},
    {"num": 50, "english": "Qaf", "arabic": "ق"},
    {"num": 51, "english": "Ad-Dhariyat", "arabic": "الذاريات"},
    {"num": 52, "english": "At-Tur", "arabic": "الطور"},
    {"num": 53, "english": "An-Najm", "arabic": "النجم"},
    {"num": 54, "english": "Al-Qamar", "arabic": "القمر"},
    {"num": 55, "english": "Ar-Rahman", "arabic": "الرحمن"},
    {"num": 56, "english": "Al-Waqi'ah", "arabic": "الواقعة"},
    {"num": 57, "english": "Al-Hadid", "arabic": "الحديد"},
    {"num": 58, "english": "Al-Mujadilah", "arabic": "المجادلة"},
    {"num": 59, "english": "Al-Hashr", "arabic": "الحشر"},
    {"num": 60, "english": "Al-Mumtahanah", "arabic": "الممتحنة"},
    {"num": 61, "english": "As-Saff", "arabic": "الصف"},
    {"num": 62, "english": "Al-Jumu'ah", "arabic": "الجمعة"},
    {"num": 63, "english": "Al-Munafiqun", "arabic": "المنافقون"},
    {"num": 64, "english": "At-Taghabun", "arabic": "التغابن"},
    {"num": 65, "english": "At-Talaq", "arabic": "الطلاق"},
    {"num": 66, "english": "At-Tahrim", "arabic": "التحريم"},
    {"num": 67, "english": "Al-Mulk", "arabic": "الملك"},
    {"num": 68, "english": "Al-Qalam", "arabic": "القلم"},
    {"num": 69, "english": "Al-Haqqah", "arabic": "الحاقة"},
    {"num": 70, "english": "Al-Ma'arij", "arabic": "المعارج"},
    {"num": 71, "english": "Nuh", "arabic": "نوح"},
    {"num": 72, "english": "Al-Jinn", "arabic": "الجن"},
    {"num": 73, "english": "Al-Muzzammil", "arabic": "المزمل"},
    {"num": 74, "english": "Al-Muddaththir", "arabic": "المدثر"},
    {"num": 75, "english": "Al-Qiyamah", "arabic": "القيامة"},
    {"num": 76, "english": "Al-Insan", "arabic": "الإنسان"},
    {"num": 77, "english": "Al-Mursalat", "arabic": "المرسلات"},
    {"num": 78, "english": "An-Naba'", "arabic": "النبأ"},
    {"num": 79, "english": "An-Nazi'at", "arabic": "النازعات"},
    {"num": 80, "english": "Abasa", "arabic": "عبس"},
    {"num": 81, "english": "At-Takwir", "arabic": "التكوير"},
    {"num": 82, "english": "Al-Infitar", "arabic": "الانفطار"},
    {"num": 83, "english": "Al-Mutaffifin", "arabic": "المطففين"},
    {"num": 84, "english": "Al-Inshiqaq", "arabic": "الانشقاق"},
    {"num": 85, "english": "Al-Buruj", "arabic": "البروج"},
    {"num": 86, "english": "At-Tariq", "arabic": "الطارق"},
    {"num": 87, "english": "Al-A'la", "arabic": "الأعلى"},
    {"num": 88, "english": "Al-Ghashiyah", "arabic": "الغاشية"},
    {"num": 89, "english": "Al-Fajr", "arabic": "الفجر"},
    {"num": 90, "english": "Al-Balad", "arabic": "البلد"},
    {"num": 91, "english": "Ash-Shams", "arabic": "الشمس"},
    {"num": 92, "english": "Al-Lail", "arabic": "الليل"},
    {"num": 93, "english": "Ad-Duha", "arabic": "الضحى"},
    {"num": 94, "english": "Ash-Sharh", "arabic": "الشرح"},
    {"num": 95, "english": "At-Tin", "arabic": "التين"},
    {"num": 96, "english": "Al-'Alaq", "arabic": "العلق"},
    {"num": 97, "english": "Al-Qadr", "arabic": "القدر"},
    {"num": 98, "english": "Al-Bayyinah", "arabic": "البينة"},
    {"num": 99, "english": "Al-Zilzal", "arabic": "الزلزلة"},
    {"num": 100, "english": "Al-'Adiyat", "arabic": "العاديات"},
    {"num": 101, "english": "Al-Qari'ah", "arabic": "القارعة"},
    {"num": 102, "english": "At-Takathur", "arabic": "التكاثر"},
    {"num": 103, "english": "Al-'Asr", "arabic": "العصر"},
    {"num": 104, "english": "Al-Humazah", "arabic": "الهمزة"},
    {"num": 105, "english": "Al-Fil", "arabic": "الفيل"},
    {"num": 106, "english": "Quraish", "arabic": "قريش"},
    {"num": 107, "english": "Al-Ma'un", "arabic": "الماعون"},
    {"num": 108, "english": "Al-Kauthar", "arabic": "الكوثر"},
    {"num": 109, "english": "Al-Kafirun", "arabic": "الكافرون"},
    {"num": 110, "english": "An-Nasr", "arabic": "النصر"},
    {"num": 111, "english": "Al-Masad", "arabic": "المسد"},
    {"num": 112, "english": "Al-Ikhlas", "arabic": "الإخلاص"},
    {"num": 113, "english": "Al-Falaq", "arabic": "الفلق"},
    {"num": 114, "english": "An-Nas", "arabic": "الناس"}
]

_global_reshaper = None

def get_shared_reshaper():
    global _global_reshaper
    if _global_reshaper is None:
        import arabic_reshaper
        _global_reshaper = arabic_reshaper.ArabicReshaper()
    return _global_reshaper


def fmt_stat(key, val_str):
    raw_lbl = tm.tr(key).replace(':', '').strip()
    if tm._current_language == "Arabic":
        return f"{val_str} :{raw_lbl}"
    else:
        return f"{tm.tr(key)} {val_str}"


def init_db():
    """
    Initializes the single-file SQLite database and automatically migrates
    any legacy JSON files into SQLite to preserve existing data.
    """
    os.makedirs(os.path.join(APP_DIR, "data"), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Create Tables
    c.execute("""
        CREATE TABLE IF NOT EXISTS days (
            date TEXT PRIMARY KEY,
            blueprint_name TEXT,
            main_tasks TEXT,
            side_tasks TEXT,
            ai_comment TEXT,
            small_advice TEXT,
            deep_advice TEXT
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS daily_diary (
            date TEXT PRIMARY KEY,
            content TEXT
        )
    """)
    
    # PRAGMA Column Migration check (for existing databases)
    c.execute("PRAGMA table_info(days)")
    columns = [col[1] for col in c.fetchall()]
    if "small_advice" not in columns:
        c.execute("ALTER TABLE days ADD COLUMN small_advice TEXT")
    if "deep_advice" not in columns:
        c.execute("ALTER TABLE days ADD COLUMN deep_advice TEXT")
        
    c.execute("""
        CREATE TABLE IF NOT EXISTS blueprints (
            name TEXT PRIMARY KEY,
            main_tasks TEXT,
            side_tasks TEXT
        )
    """)
    
    # Create Starred Packs Table
    c.execute("""
        CREATE TABLE IF NOT EXISTS starred_packs (
            title TEXT PRIMARY KEY,
            stars REAL,
            items TEXT
        )
    """)
    
    # Create Quran Progress Table
    c.execute("""
        CREATE TABLE IF NOT EXISTS quran_progress (
            id INTEGER PRIMARY KEY,
            current_page INTEGER DEFAULT 1,
            completion_count INTEGER DEFAULT 0
        )
    """)
    
    # Create Quran Audio Progress Table
    c.execute("""
        CREATE TABLE IF NOT EXISTS quran_audio_progress (
            surah_number INTEGER PRIMARY KEY,
            last_position REAL DEFAULT 0.0
        )
    """)
    
    # Create Calendar Adjustments Table
    # Stores per-month day delta so users can add/remove days from a calendar month
    # year_month format: "YYYY-MM", day_delta: integer offset applied to standard days count
    c.execute("""
        CREATE TABLE IF NOT EXISTS calendar_adjustments (
            year_month TEXT PRIMARY KEY,
            day_delta  INTEGER DEFAULT 0
        )
    """)
    
    # Create Azkar Progress Table
    # Stores per-category azkar counter state + the date it was last active (for midnight reset)
    c.execute("""
        CREATE TABLE IF NOT EXISTS azkar_progress (
            category   TEXT PRIMARY KEY,
            reset_date TEXT NOT NULL DEFAULT '',
            progress   TEXT NOT NULL DEFAULT '{}'
        )
    """)

    # Create Monthly Comments Table for Monthly Graph summarizations
    c.execute("""
        CREATE TABLE IF NOT EXISTS monthly_comments (
            year_month TEXT PRIMARY KEY,
            comment    TEXT NOT NULL DEFAULT ''
        )
    """)
    
    # Ensure there is exactly one row in quran_progress
    c.execute("SELECT COUNT(*) FROM quran_progress")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO quran_progress (id, current_page, completion_count) VALUES (1, 1, 0)")
        
    conn.commit()
    
    # Legacy Migration: blueprints JSON -> SQLite blueprints table
    legacy_bp_dir = os.path.join(APP_DIR, "data", "blueprints")
    if os.path.exists(legacy_bp_dir):
        print("[*] Migrating legacy blueprint JSON files to database...")
        for file in os.listdir(legacy_bp_dir):
            if file.endswith(".json"):
                name = file[:-5]
                try:
                    with open(os.path.join(legacy_bp_dir, file), "r", encoding="utf-8") as f:
                        data = json.load(f)
                    c.execute("INSERT OR REPLACE INTO blueprints VALUES (?, ?, ?)",
                              (name, json.dumps(data.get("main_tasks", [])), json.dumps(data.get("side_tasks", []))))
                except Exception as e:
                    print(f"[-] Blueprint migration error ({file}): {e}")
        try:
            os.rename(legacy_bp_dir, os.path.join(APP_DIR, "data", "blueprints_migrated_backup"))
            print("[*] Blueprints legacy folder renamed to backup.")
        except Exception as e:
            print(f"[-] Failed to rename blueprints legacy folder: {e}")
                    
    # Legacy Migration: days JSON -> SQLite days table
    legacy_days_dir = os.path.join(APP_DIR, "data", "days")
    if os.path.exists(legacy_days_dir):
        print("[*] Migrating legacy day tracker JSON files to database...")
        for file in os.listdir(legacy_days_dir):
            if file.endswith(".json"):
                date_str = file[:-5]
                try:
                    datetime.date.fromisoformat(date_str) # Validate date format
                    with open(os.path.join(legacy_days_dir, file), "r", encoding="utf-8") as f:
                        data = json.load(f)
                    c.execute("INSERT OR REPLACE INTO days (date, blueprint_name, main_tasks, side_tasks, ai_comment) VALUES (?, ?, ?, ?, ?)",
                              (date_str, 
                               data.get("blueprint_name", "Blank"),
                               json.dumps(data.get("main_tasks", [])),
                               json.dumps(data.get("side_tasks", [])),
                               data.get("ai_comment", "")))
                except Exception as e:
                    print(f"[-] Day data migration error ({file}): {e}")
        try:
            os.rename(legacy_days_dir, os.path.join(APP_DIR, "data", "days_migrated_backup"))
            print("[*] Day tracker legacy folder renamed to backup.")
        except Exception as e:
            print(f"[-] Failed to rename days legacy folder: {e}")
    conn.commit()
    
    # Ensure default template exists
    c.execute("SELECT name FROM blueprints WHERE name = 'daily_tracker_template_blank'")
    if not c.fetchone():
        default_main = [
            {"id": 1, "title": "Routine & Health", "stars": 10, "items": []},
            {"id": 2, "title": "Core Focus / Work", "stars": 20, "items": []},
            {"id": 3, "title": "Learning & Skill Development", "stars": 15, "items": []}
        ]
        default_side = []
        c.execute("INSERT INTO blueprints VALUES (?, ?, ?)",
                  ("daily_tracker_template_blank", json.dumps(default_main), json.dumps(default_side)))
        conn.commit()
        
    conn.close()


class ScrollableFrame(tk.Frame):
    """
    A custom scrollable container in Tkinter that uses a canvas and a scrollbar.
    Supports mousewheel scrolling on Linux and Windows.
    """
    def __init__(self, container, *args, **kwargs):
        bg = kwargs.pop('bg', BG_DARK)
        super().__init__(container, *args, **kwargs)
        self.configure(bg=bg)
        
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=bg)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        
        # Bind scroll globally when mouse enters this frame
        self.scrollable_frame.bind("<Enter>", self._bind_mousewheel)
        self.scrollable_frame.bind("<Leave>", self._unbind_mousewheel)
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)
        
    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)
        
    def _bind_mousewheel(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)
        
    def _unbind_mousewheel(self, event):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")
        
    def _on_mousewheel(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(-2, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(2, "units")
        elif event.delta:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120) * 2), "units")


class ModernScale(tk.Canvas):
    """
    A beautiful, modern, customizable slider widget for Tkinter.
    Supports click-to-seek, drag-to-seek, and mousewheel scrolling.
    Works perfectly across platforms (Linux, Windows, macOS).
    """
    def __init__(self, parent, from_=0, to=100, command=None, height=18, **kwargs):
        # Background fallback
        import theme_manager as tm
        bg = kwargs.pop("bg", None) or kwargs.pop("background", None) or tm.BG_CARD
        super().__init__(parent, height=height, bg=bg, highlightthickness=0, cursor="hand2", **kwargs)
        
        self.from_val = float(from_)
        self.to_val = float(to)
        self.value = self.from_val
        self.command = command
        self.release_command = None
        self.hovered = False
        self.dragging = False
        
        self.bind("<Configure>", lambda e: self.draw())
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Button-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_drag)
        super().bind("<ButtonRelease-1>", self.on_release)
        self.bind("<MouseWheel>", self.on_wheel)
        self.bind("<Button-4>", self.on_wheel)  # Scroll up Linux
        self.bind("<Button-5>", self.on_wheel)  # Scroll down Linux

    def draw(self):
        self.delete("all")
        width = self.winfo_width()
        height = self.winfo_height()
        if width <= 1:
            return
            
        import theme_manager as tm
        bg_card = tm.BG_CARD
        border_color = tm.BORDER_COLOR
        accent_cyan = tm.ACCENT_CYAN
        text_white = tm.TEXT_WHITE
        glow_color = tm.GLOW_COLOR
        
        # Dynamically update the canvas background to match the theme
        super().configure(bg=bg_card)
        
        # We can draw a clean horizontal track in the vertical center of the canvas
        track_height = 4
        
        # Margins on the left and right to allow the thumb to draw fully without clipping
        pad = 8
        usable_width = width - 2 * pad
        
        # Value ratio
        val_range = self.to_val - self.from_val
        if val_range == 0:
            ratio = 0.0
        else:
            ratio = (self.value - self.from_val) / val_range
        ratio = max(0.0, min(1.0, ratio))
        
        thumb_x = pad + ratio * usable_width
        
        # Draw background track (unfilled)
        self.create_line(pad, height // 2, pad + usable_width, height // 2,
                         width=track_height, fill=border_color, capstyle="round")
                         
        # Draw filled track (progress)
        if thumb_x > pad:
            self.create_line(pad, height // 2, thumb_x, height // 2,
                             width=track_height, fill=accent_cyan, capstyle="round")
                             
        # Draw thumb/handle
        if self.hovered or self.dragging:
            r = 6
            color = glow_color
        else:
            r = 4
            color = text_white
            
        self.create_oval(thumb_x - r, (height // 2) - r, thumb_x + r, (height // 2) + r,
                         fill=color, outline=color)

    def get_value_at_x(self, x):
        width = self.winfo_width()
        pad = 8
        usable_width = width - 2 * pad
        if usable_width <= 0:
            return self.from_val
        x_clamped = max(pad, min(x, pad + usable_width))
        ratio = (x_clamped - pad) / usable_width
        return self.from_val + ratio * (self.to_val - self.from_val)

    def on_enter(self, event):
        self.hovered = True
        self.draw()
        try:
            self.focus_set()
        except Exception:
            pass

    def on_leave(self, event):
        self.hovered = False
        self.draw()

    def on_click(self, event):
        self.dragging = True
        val = self.get_value_at_x(event.x)
        self.set(val, force=True)
        if self.command:
            try:
                self.command(val)
            except Exception:
                pass

    def on_drag(self, event):
        if not self.dragging:
            return
        val = self.get_value_at_x(event.x)
        self.set(val, force=True)
        if self.command:
            try:
                self.command(val)
            except Exception:
                pass

    def on_release(self, event):
        self.dragging = False
        self.draw()
        if self.release_command:
            try:
                self.release_command(event)
            except Exception:
                pass

    def on_wheel(self, event):
        direction = 0
        if event.num == 4:
            direction = 1
        elif event.num == 5:
            direction = -1
        elif event.delta:
            direction = 1 if event.delta > 0 else -1
            
        if direction == 0:
            return
            
        # Dynamically determine step based on range
        val_range = abs(self.to_val - self.from_val)
        if val_range <= 2.0:
            step = 0.05
        else:
            step = max(5.0, val_range * 0.01)
            
        new_val = self.value + direction * step
        low = min(self.from_val, self.to_val)
        high = max(self.from_val, self.to_val)
        new_val = max(low, min(new_val, high))
        
        self.set(new_val, force=True)
        
        if self.command:
            try:
                self.command(new_val)
            except Exception:
                pass
                
        # Trigger release callback to seek immediately on scroll
        if self.release_command:
            try:
                self.release_command(None)
            except Exception:
                pass

    def get(self):
        return self.value

    def set(self, val, force=False):
        if self.dragging and not force:
            return
        low = min(self.from_val, self.to_val)
        high = max(self.from_val, self.to_val)
        self.value = max(low, min(float(val), high))
        self.draw()

    def bind(self, sequence, func, add=None):
        if sequence == "<ButtonRelease-1>":
            self.release_command = func
            return
        return super().bind(sequence, func, add)

    def configure(self, cnf=None, **kw):
        if "from_" in kw:
            self.from_val = float(kw.pop("from_"))
        if "to" in kw:
            self.to_val = float(kw.pop("to"))
        if "command" in kw:
            self.command = kw.pop("command")
            
        res = super().configure(cnf, **kw)
        self.draw()
        return res

    def config(self, cnf=None, **kw):
        return self.configure(cnf, **kw)


class ExitListeningDialog(tk.Toplevel):
    def __init__(self, parent, on_choice):
        super().__init__(parent)
        self.title(tm.tr("listening_options_title") or "Quran Listening")
        self.configure(bg=BG_DARK)
        self.geometry("380x220")
        self.resizable(False, False)
        self.transient(parent)
        
        # Center relative to parent
        x = parent.winfo_rootx() + (parent.winfo_width() / 2) - 190
        y = parent.winfo_rooty() + (parent.winfo_height() / 2) - 110
        self.geometry(f"+{int(x)}+{int(y)}")
        
        prompt_txt = "What would you like to do with the current recitation?"
        if tm._current_language == "French":
            prompt_txt = "Que souhaitez-vous faire avec la récitation en cours ?"
        elif tm._current_language == "Arabic":
            prompt_txt = "ماذا تريد أن تفعل بالتلاوة الحالية؟"
            
        lbl = tk.Label(self, text=prompt_txt, 
                       bg=BG_DARK, fg=TEXT_WHITE, font=("Helvetica", 11, "bold"), wraplength=340, justify="center")
        lbl.pack(pady=(20, 15))
        
        btn_frame = tk.Frame(self, bg=BG_DARK)
        btn_frame.pack(pady=5, padx=30, fill="x")
        
        # Continue Button
        lbl_continue = "Continue Listening"
        if tm._current_language == "French":
            lbl_continue = "Continuer l'écoute"
        elif tm._current_language == "Arabic":
            lbl_continue = "متابعة الاستماع"
            
        btn_continue = tk.Button(btn_frame, text=lbl_continue, bg=ACCENT_PURPLE, fg=TEXT_WHITE, 
                                 activebackground=GLOW_COLOR, activeforeground=TEXT_WHITE, relief="flat", font=("Helvetica", 9, "bold"), height=2,
                                 command=lambda: self.select("continue"))
        btn_continue.pack(fill="x", pady=4)
        
        # Pause Button
        lbl_pause = tm.tr("pause") or "Pause"
        btn_pause = tk.Button(btn_frame, text=lbl_pause, bg=BG_CARD, fg=TEXT_WHITE, 
                              activebackground=ACCENT_CYAN, activeforeground=BG_DARK, relief="flat", font=("Helvetica", 9, "bold"), height=2,
                              command=lambda: self.select("pause"))
        btn_pause.pack(fill="x", pady=4)
        
        # Quit Button
        lbl_quit = tm.tr("quit") or "Quit"
        if tm._current_language == "French" and lbl_quit == "quit":
            lbl_quit = "Quitter"
        elif tm._current_language == "Arabic" and lbl_quit == "quit":
            lbl_quit = "خروج"
        btn_quit = tk.Button(btn_frame, text=lbl_quit, bg=BG_CARD, fg=ERR_RED or "#ef4444", 
                             activebackground="#ef4444", activeforeground=TEXT_WHITE, relief="flat", font=("Helvetica", 9, "bold"), height=2,
                             command=lambda: self.select("quit"))
        btn_quit.pack(fill="x", pady=4)
        
        self.choice = None
        self.on_choice = on_choice
        
        self.protocol("WM_DELETE_WINDOW", lambda: self.select("continue"))
        self.wait_visibility()
        self.grab_set()
        
    def select(self, choice):
        self.choice = choice
        self.destroy()
        if self.on_choice:
            self.on_choice(choice)


class WriteCommentDialog(tk.Toplevel):
    def __init__(self, parent, initial_val=""):
        super().__init__(parent)
        self.title("Write Comment")
        self.configure(bg=BG_DARK)
        self.geometry("450x300")
        self.resizable(False, False)
        self.transient(parent)
        
        # Center relative to parent
        x = parent.winfo_rootx() + (parent.winfo_width() / 2) - 225
        y = parent.winfo_rooty() + (parent.winfo_height() / 2) - 150
        self.geometry(f"+{int(x)}+{int(y)}")
        
        self.result = None
        
        prompt_lbl = "Type your custom comment below:"
        if tm._current_language == "French":
            prompt_lbl = "Saisissez votre commentaire personnalisé ci-dessous :"
            
        lbl = tk.Label(self, text=prompt_lbl, bg=BG_DARK, fg=TEXT_WHITE, font=("Helvetica", 11, "bold"))
        lbl.pack(pady=(15, 10))
        
        self.text_area = tk.Text(self, bg=BG_CARD, fg=TEXT_WHITE, insertbackground=ACCENT_CYAN,
                                 selectbackground=ACCENT_PURPLE, selectforeground=TEXT_WHITE,
                                 borderwidth=1, highlightbackground=BORDER_COLOR, highlightthickness=1,
                                 relief="flat", font=("Helvetica", 10), wrap="word", height=8)
        self.text_area.pack(padx=20, pady=5, fill="x")
        self.text_area.insert("1.0", initial_val)
        self.text_area.focus_set()
        
        btn_frame = tk.Frame(self, bg=BG_DARK, pady=10)
        btn_frame.pack(fill="x")
        
        lbl_confirm = tm.tr("confirm") or "Confirm"
        btn_ok = tk.Button(btn_frame, text=lbl_confirm, width=12, bg=ACCENT_PURPLE, fg=TEXT_WHITE, relief="flat", font=("Helvetica", 9, "bold"), command=self.on_ok)
        btn_ok.pack(side="left", padx=30)
        
        lbl_cancel = tm.tr("cancel") or "Cancel"
        btn_cancel = tk.Button(btn_frame, text=lbl_cancel, width=12, bg=BG_CARD, fg=TEXT_MUTED, relief="flat", font=("Helvetica", 9, "bold"), command=self.on_cancel)
        btn_cancel.pack(side="right", padx=30)
        
        self.wait_visibility()
        self.grab_set()
        
    def on_ok(self):
        self.result = self.text_area.get("1.0", "end-1c").strip()
        self.destroy()
        
    def on_cancel(self):
        self.destroy()


class CommentOptionsDialog(tk.Toplevel):
    def __init__(self, parent, default_ai_comment=""):
        super().__init__(parent)
        self.title("Comment Options" if tm._current_language != "French" else "Options de commentaire")
        self.configure(bg=BG_DARK)
        self.geometry("450x260")
        self.resizable(False, False)
        self.transient(parent)
        
        # Center relative to parent
        x = parent.winfo_rootx() + (parent.winfo_width() / 2) - 225
        y = parent.winfo_rooty() + (parent.winfo_height() / 2) - 130
        self.geometry(f"+{int(x)}+{int(y)}")
        
        self.result_type = None # "ai", "custom", "blank"
        self.default_ai_comment = default_ai_comment
        
        lbl_title = "Choose Commentary for Export"
        if tm._current_language == "French":
            lbl_title = "Choisir le commentaire pour l'export"
            
        lbl = tk.Label(self, text=lbl_title, bg=BG_DARK, fg=TEXT_WHITE, font=("Helvetica", 12, "bold"))
        lbl.pack(pady=15)
        
        btn_frame = tk.Frame(self, bg=BG_DARK)
        btn_frame.pack(pady=10, padx=30, fill="x")
        
        # AI Comment Button
        lbl_ai = "🤖 Use AI Commentary"
        if tm._current_language == "French":
            lbl_ai = "🤖 Utiliser le commentaire IA"
        btn_ai = tk.Button(btn_frame, text=lbl_ai, bg=ACCENT_PURPLE, fg=TEXT_WHITE,
                           activebackground=GLOW_COLOR, relief="flat", font=("Helvetica", 10, "bold"), height=2,
                           command=self.select_ai)
        btn_ai.pack(fill="x", pady=5)
        
        # Custom Comment Button
        lbl_custom = "✍️ Write a Custom Comment"
        if tm._current_language == "French":
            lbl_custom = "✍️ Écrire un commentaire personnalisé"
        btn_custom = tk.Button(btn_frame, text=lbl_custom, bg=BG_CARD, fg=TEXT_WHITE,
                               activebackground=ACCENT_CYAN, activeforeground=BG_DARK, relief="flat", font=("Helvetica", 10, "bold"), height=2,
                               command=self.select_custom)
        btn_custom.pack(fill="x", pady=5)
        
        # Blank Button
        lbl_blank = "📄 Leave Blank (No Comment)"
        if tm._current_language == "French":
            lbl_blank = "📄 Laisser vide (sans commentaire)"
        btn_blank = tk.Button(btn_frame, text=lbl_blank, bg=BG_CARD, fg=TEXT_MUTED,
                              activebackground=BORDER_COLOR, activeforeground=TEXT_WHITE, relief="flat", font=("Helvetica", 10, "bold"), height=2,
                              command=self.select_blank)
        btn_blank.pack(fill="x", pady=5)
        
        self.wait_visibility()
        self.grab_set()
        
    def select_ai(self):
        self.result_type = "ai"
        self.destroy()
        
    def select_custom(self):
        self.result_type = "custom"
        self.destroy()
        
    def select_blank(self):
        self.result_type = "blank"
        self.destroy()


class CustomDialog(tk.Toplevel):
    """
    A beautiful dark-themed popup window for entering single text values.
    """
    def __init__(self, parent, title, prompt, value="", is_numeric=False):
        super().__init__(parent)
        self.title(title)
        self.configure(bg=BG_DARK)
        self.geometry("380x190")
        self.resizable(False, False)
        self.transient(parent)
        
        # Center relative to parent
        x = parent.winfo_rootx() + (parent.winfo_width() / 2) - 190
        y = parent.winfo_rooty() + (parent.winfo_height() / 2) - 95
        self.geometry(f"+{int(x)}+{int(y)}")
        
        self.result = None
        self.is_numeric = is_numeric
        self.is_arabic = (tm._current_language == "Arabic" and not is_numeric)
        font_family = "Amiri" if self.is_arabic else "Helvetica"
        
        lbl = tk.Label(self, text=prompt, bg=BG_DARK, fg=TEXT_WHITE, font=(font_family, 11, "bold"), wraplength=340)
        lbl.pack(pady=(18, 10))
        
        justify_side = "right" if self.is_arabic else "left"
        self.entry = tk.Entry(self, bg=BG_CARD, fg=TEXT_WHITE, insertbackground=TEXT_WHITE, 
                             relief="flat", highlightbackground=BORDER_COLOR, highlightcolor=ACCENT_PURPLE, 
                             highlightthickness=1, font=(font_family, 12), justify=justify_side)
        self.entry.insert(0, value)
        self.entry.pack(pady=10, padx=20, fill="x")
        self.entry.focus_set()
        self.entry.selection_range(0, tk.END)
        
        btn_frame = tk.Frame(self, bg=BG_DARK)
        btn_frame.pack(pady=10)
        
        ok_btn = tk.Button(btn_frame, text=tm.tr("confirm"), width=10, bg=ACCENT_PURPLE, fg=TEXT_WHITE, 
                           activebackground=GLOW_COLOR, activeforeground=TEXT_WHITE, relief="flat", font=("Helvetica", 9, "bold"), command=self.on_ok)
        ok_btn.pack(side="left", padx=5)
        
        cancel_btn = tk.Button(btn_frame, text=tm.tr("cancel"), width=10, bg=BG_CARD, fg=TEXT_MUTED, 
                               activebackground=BORDER_COLOR, activeforeground=TEXT_WHITE, relief="flat", font=("Helvetica", 9, "bold"), command=self.on_cancel)
        cancel_btn.pack(side="right", padx=5)
        
        self.bind("<Return>", lambda e: self.on_ok())
        self.bind("<Escape>", lambda e: self.on_cancel())
        
        self.wait_visibility()
        self.grab_set()
        
    def on_ok(self):
        val = self.entry.get().strip()
        if not val:
            messagebox.showerror(tm.tr("error"), tm.tr("input_cannot_be_empty"))
            return
            
        if self.is_numeric:
            try:
                num = int(val)
                if num < 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror(tm.tr("error"), tm.tr("enter_valid_integer"))
                return
        else:
            if not is_english_or_french(val):
                err_msg = "The app only supports English and French for now. You cannot save other languages."
                if tm._current_language == "French":
                    err_msg = "L'application ne prend en charge que l'anglais et le français pour le moment. Vous ne pouvez pas enregistrer dans d'autres langues."
                messagebox.showerror(tm.tr("error") or "Error", err_msg)
                return
                
        self.result = val
        self.destroy()
        
    def on_cancel(self):
        self.destroy()


class PercentageDialog(tk.Toplevel):
    """
    A dark-themed dialog for adjusting proportional splits for tasks in a group.
    """
    def __init__(self, parent, title, items):
        super().__init__(parent)
        self.title(title)
        self.configure(bg=BG_DARK)
        self.geometry("420x450")
        self.transient(parent)
        
        x = parent.winfo_rootx() + (parent.winfo_width() / 2) - 210
        y = parent.winfo_rooty() + (parent.winfo_height() / 2) - 225
        self.geometry(f"+{int(x)}+{int(y)}")
        
        self.result = None
        self.entries = []
        
        title_lbl = tk.Label(self, text=tm.tr("set_pct_weights"), bg=BG_DARK, fg=TEXT_WHITE, font=("Helvetica", 12, "bold"))
        title_lbl.pack(pady=15)
        
        # Scrollable container for items
        self.scroll = ScrollableFrame(self, bg=BG_DARK)
        self.scroll.pack(fill="both", expand=True, padx=20, pady=10)
        
        for item in items:
            row = tk.Frame(self.scroll.scrollable_frame, bg=BG_DARK, pady=6)
            row.pack(fill="x")
            
            item_lbl = tk.Label(row, text=item["name"], bg=BG_DARK, fg=TEXT_WHITE, font=("Helvetica", 10), anchor="w", wraplength=220, justify="left")
            item_lbl.pack(side="left", fill="x", expand=True, padx=(5, 10))
            
            entry = tk.Entry(row, width=8, bg=BG_CARD, fg=TEXT_WHITE, insertbackground=TEXT_WHITE, 
                             relief="flat", highlightbackground=BORDER_COLOR, highlightcolor=ACCENT_CYAN, highlightthickness=1, font=("Helvetica", 10, "bold"), justify="center")
            entry.insert(0, f"{item['percent']:.1f}")
            entry.pack(side="right", padx=5)
            
            pct_lbl = tk.Label(row, text="%", bg=BG_DARK, fg=TEXT_MUTED, font=("Helvetica", 10, "bold"))
            pct_lbl.pack(side="right")
            
            self.entries.append((item, entry))
            
        # Summary footer inside dialog
        self.sum_lbl = tk.Label(self, text=f"{tm.tr('sum_label')}0.0%", bg=BG_DARK, fg=ACCENT_CYAN, font=("Helvetica", 10, "bold"))
        self.sum_lbl.pack(pady=5)
        self.check_sum()
        
        # Bind entry modifications to update sum label
        for _, entry in self.entries:
            entry.bind("<KeyRelease>", lambda e: self.check_sum())
            
        btn_frame = tk.Frame(self, bg=BG_DARK, pady=15)
        btn_frame.pack(fill="x", side="bottom")
        
        equal_btn = tk.Button(btn_frame, text=tm.tr("equal_split"), bg=ACCENT_CYAN, fg=BG_DARK, 
                              activebackground=GLOW_COLOR, relief="flat", font=("Helvetica", 9, "bold"), padx=10, command=self.equal_split)
        equal_btn.pack(side="left", padx=20)
        
        ok_btn = tk.Button(btn_frame, text=tm.tr("save"), width=10, bg=ACCENT_PURPLE, fg=TEXT_WHITE, 
                           activebackground=GLOW_COLOR, relief="flat", font=("Helvetica", 9, "bold"), command=self.on_save)
        ok_btn.pack(side="right", padx=5)
        
        cancel_btn = tk.Button(btn_frame, text=tm.tr("cancel"), width=10, bg=BG_CARD, fg=TEXT_MUTED, 
                               relief="flat", font=("Helvetica", 9, "bold"), command=self.destroy)
        cancel_btn.pack(side="right", padx=20)
        
        self.wait_visibility()
        self.grab_set()
        
    def check_sum(self):
        total = 0.0
        for _, entry in self.entries:
            try:
                total += float(entry.get() or 0)
            except ValueError:
                pass
        self.sum_lbl.config(text=f"{tm.tr('sum_label')}{total:.1f}%")
        if abs(total - 100.0) < 0.05:
            self.sum_lbl.config(fg=SUCCESS_GREEN)
        else:
            self.sum_lbl.config(fg=ACCENT_CYAN)
            
    def equal_split(self):
        if not self.entries:
            return
        n = len(self.entries)
        base = round(100.0 / n, 1)
        diff = round(100.0 - (base * n), 1)
        for i, (_, entry) in enumerate(self.entries):
            val = base
            if i == n - 1:
                val = round(base + diff, 1)
            entry.delete(0, tk.END)
            entry.insert(0, f"{val:.1f}")
        self.check_sum()
        
    def on_save(self):
        total = 0.0
        new_items = []
        for item, entry in self.entries:
            try:
                val = float(entry.get())
                if val < 0:
                    raise ValueError
                total += val
                new_item = item.copy()
                new_item["percent"] = val
                new_items.append(new_item)
            except ValueError:
                messagebox.showerror(tm.tr("error"), tm.tr("invalid_pct_val").format(name=item.get("name", "")))
                return
                
        if not new_items:
            self.destroy()
            return
            
        if abs(total - 100.0) > 0.05:
            if messagebox.askyesno(tm.tr("normalize_title"), tm.tr("normalize_body").format(total=total)):
                if total > 0:
                    for item in new_items:
                        item["percent"] = round((item["percent"] / total) * 100.0, 1)
                else:
                    for item in new_items:
                        item["percent"] = round(100.0 / len(new_items), 1)
                total_sum = sum(i["percent"] for i in new_items[:-1])
                new_items[-1]["percent"] = round(100.0 - total_sum, 1)
            else:
                return
                
        self.result = new_items
        self.destroy()


class InitializeDayDialog(tk.Toplevel):
    """
    Choice modal for creating trackers for arbitrary calendar dates.
    Shows built-in blueprints or a blank start.
    """

    # ── Pre-built blueprint definitions ──────────────────────────────────────
    BLUEPRINTS = [
        {
            "name": "Study Day",
            "emoji": "📚",
            "main_tasks": [
                {"title": "Morning Review", "stars": 3, "done": False,
                 "items": [{"label": "Read course notes", "done": False, "percent": 40},
                           {"label": "Watch lecture", "done": False, "percent": 60}]},
                {"title": "Deep Work Session", "stars": 5, "done": False,
                 "items": [{"label": "Practice exercises", "done": False, "percent": 50},
                           {"label": "Solve problems", "done": False, "percent": 50}]},
                {"title": "Evening Review", "stars": 2, "done": False,
                 "items": [{"label": "Summarize what I learned", "done": False, "percent": 100}]},
            ],
            "side_tasks": [
                {"title": "Reading", "stars": 2, "done": False,
                 "items": [{"label": "Read 20 pages", "done": False, "percent": 100}]},
                {"title": "Vocabulary", "stars": 1, "done": False,
                 "items": [{"label": "Learn 10 new words", "done": False, "percent": 100}]},
            ]
        },
        {
            "name": "Work Day",
            "emoji": "💼",
            "main_tasks": [
                {"title": "Morning Planning", "stars": 2, "done": False,
                 "items": [{"label": "Review today's agenda", "done": False, "percent": 50},
                           {"label": "Set top 3 priorities", "done": False, "percent": 50}]},
                {"title": "Deep Work Block", "stars": 5, "done": False,
                 "items": [{"label": "Complete main task", "done": False, "percent": 60},
                           {"label": "Review and polish", "done": False, "percent": 40}]},
                {"title": "Meetings & Communication", "stars": 3, "done": False,
                 "items": [{"label": "Reply to emails", "done": False, "percent": 40},
                           {"label": "Attend standup", "done": False, "percent": 60}]},
            ],
            "side_tasks": [
                {"title": "Professional Growth", "stars": 2, "done": False,
                 "items": [{"label": "Read industry article", "done": False, "percent": 100}]},
            ]
        },
        {
            "name": "Ramadan Day",
            "emoji": "🌙",
            "main_tasks": [
                {"title": "Fajr Prayer", "stars": 5, "done": False,
                 "items": [{"label": "Pray Fajr on time", "done": False, "percent": 60},
                           {"label": "Morning Adhkar", "done": False, "percent": 40}]},
                {"title": "Quran Recitation", "stars": 5, "done": False,
                 "items": [{"label": "Read 1 Juz", "done": False, "percent": 70},
                           {"label": "Reflect on meaning", "done": False, "percent": 30}]},
                {"title": "Tarawih", "stars": 4, "done": False,
                 "items": [{"label": "Pray Tarawih", "done": False, "percent": 100}]},
                {"title": "Iftar & Maghrib", "stars": 3, "done": False,
                 "items": [{"label": "Prepare iftar", "done": False, "percent": 30},
                           {"label": "Pray Maghrib", "done": False, "percent": 70}]},
            ],
            "side_tasks": [
                {"title": "Charity", "stars": 3, "done": False,
                 "items": [{"label": "Give sadaqah", "done": False, "percent": 100}]},
                {"title": "Du'a", "stars": 2, "done": False,
                 "items": [{"label": "Evening Adhkar", "done": False, "percent": 100}]},
            ]
        },
        {
            "name": "Workout Day",
            "emoji": "💪",
            "main_tasks": [
                {"title": "Warm-up", "stars": 2, "done": False,
                 "items": [{"label": "Stretch 10 min", "done": False, "percent": 50},
                           {"label": "Light cardio", "done": False, "percent": 50}]},
                {"title": "Main Training", "stars": 5, "done": False,
                 "items": [{"label": "Complete workout sets", "done": False, "percent": 70},
                           {"label": "Core exercises", "done": False, "percent": 30}]},
                {"title": "Recovery", "stars": 3, "done": False,
                 "items": [{"label": "Cool-down stretching", "done": False, "percent": 50},
                           {"label": "Protein & hydration", "done": False, "percent": 50}]},
            ],
            "side_tasks": [
                {"title": "Wellness", "stars": 2, "done": False,
                 "items": [{"label": "8 glasses of water", "done": False, "percent": 50},
                           {"label": "Sleep 8h tonight", "done": False, "percent": 50}]},
            ]
        },
    ]

    def __init__(self, parent, date_str):
        super().__init__(parent)
        self.title(f"{tm.tr('initialize')} {date_str}")
        self.configure(bg=BG_DARK)
        self.geometry("400x460")
        self.resizable(False, False)
        self.transient(parent)

        x = parent.winfo_rootx() + (parent.winfo_width() / 2) - 200
        y = parent.winfo_rooty() + (parent.winfo_height() / 2) - 230
        self.geometry(f"+{int(x)}+{int(y)}")

        self.result = None
        self.result_blueprint = None

        # Title label
        lbl = tk.Label(self,
                       text=f"{tm.tr('start_tracking_for')}\n{date_str}",
                       bg=BG_DARK, fg=TEXT_WHITE,
                       font=("Helvetica", 11, "bold"), justify="center")
        lbl.pack(pady=(15, 8))

        sub = tk.Label(self, text=tm.tr("choose_blueprint"),
                       bg=BG_DARK, fg=TEXT_MUTED,
                       font=("Helvetica", 9, "italic"))
        sub.pack()

        # Blueprint buttons
        btn_frame = tk.Frame(self, bg=BG_DARK)
        btn_frame.pack(fill="x", padx=30, pady=10)

        for bp in self.BLUEPRINTS:
            btn = tk.Button(
                btn_frame,
                text=f"{bp['emoji']}  {bp['name']}",
                bg=BG_CARD, fg=TEXT_WHITE,
                activebackground=ACCENT_PURPLE, activeforeground=BG_DARK,
                highlightbackground=BORDER_COLOR, highlightthickness=1,
                relief="flat", font=("Helvetica", 10, "bold"),
                height=2,
                command=lambda b=bp: self._on_blueprint(b)
            )
            btn.pack(fill="x", pady=4)
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=ACCENT_PURPLE, fg=BG_DARK))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg=BG_CARD, fg=TEXT_WHITE))

        # Divider
        tk.Frame(self, bg=BORDER_COLOR, height=1).pack(fill="x", padx=30, pady=6)

        # Blank page button
        blank_btn = tk.Button(
            self, text=f"⬜  {tm.tr('start_blank')}",
            bg=BG_CARD, fg=TEXT_MUTED,
            activebackground=ACCENT_CYAN, activeforeground=BG_DARK,
            highlightbackground=BORDER_COLOR, highlightthickness=1,
            relief="flat", font=("Helvetica", 10, "bold"),
            height=2, command=self.on_blank
        )
        blank_btn.pack(fill="x", padx=30, pady=4)
        blank_btn.bind("<Enter>", lambda e: blank_btn.config(bg=ACCENT_CYAN, fg=BG_DARK))
        blank_btn.bind("<Leave>", lambda e: blank_btn.config(bg=BG_CARD, fg=TEXT_MUTED))

        # Cancel
        cancel_btn = tk.Button(self, text=tm.tr("cancel"),
                               bg=BG_DARK, fg=TEXT_MUTED,
                               relief="flat", font=("Helvetica", 9),
                               command=self.destroy)
        cancel_btn.pack(pady=(6, 12))

        self.wait_visibility()
        self.grab_set()

    def _on_blueprint(self, bp):
        self.result = "blueprint"
        self.result_blueprint = bp
        self.destroy()

    def on_blank(self):
        self.result = "blank"
        self.destroy()


class QuranViewerDialog(tk.Toplevel):
    """
    RTL book reader interface for the Quran with reading progress tracking.
    """
    def __init__(self, parent, pages_dir):
        super().__init__(parent)
        self.title(tm.tr("quran_reader_title"))
        self.configure(bg=BG_DARK)
        self.geometry("640x940")
        self.resizable(False, False)
        self.transient(parent)
        
        # Center
        x = parent.winfo_rootx() + (parent.winfo_width() / 2) - 320
        y = parent.winfo_rooty() + (parent.winfo_height() / 2) - 470
        self.geometry(f"+{int(x)}+{int(y)}")
        
        self.pages_dir = pages_dir
        
        self.image_files = sorted([f for f in os.listdir(pages_dir) if f.endswith(".jpg")])
        self.total_pages = len(self.image_files)
        if self.total_pages == 0:
            messagebox.showerror(tm.tr("error"), tm.tr("no_quran_pages_error"))
            self.destroy()
            return
            
        self.current_page = 1
        self.completions = 0
        self.load_progress()
        
        self.setup_ui()
        
        self.bind("<Right>", lambda e: self.prev_page())
        self.bind("<Left>", lambda e: self.next_page())
        
        self.animating = False
        self.render_current_page()
        
        self.wait_visibility()
        
    def load_progress(self):
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT current_page, completion_count FROM quran_progress WHERE id = 1")
            row = c.fetchone()
            conn.close()
            if row:
                self.current_page = max(1, min(row[0], self.total_pages))
                self.completions = row[1]
        except Exception as e:
            print(f"Error loading Quran progress: {e}")
            
    def save_progress(self):
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("UPDATE quran_progress SET current_page = ?, completion_count = ? WHERE id = 1", (self.current_page, self.completions))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error saving Quran progress: {e}")
            
    def setup_ui(self):
        self.header_frame = tk.Frame(self, bg=BG_DARK)
        self.header_frame.pack(fill="x", padx=20, pady=5)
        
        self.info_lbl = tk.Label(self.header_frame, text="", bg=BG_DARK, fg=TEXT_WHITE, font=("Helvetica", 11, "bold"))
        self.info_lbl.pack(pady=1)
        
        self.left_lbl = tk.Label(self.header_frame, text="", bg=BG_DARK, fg=TEXT_MUTED, font=("Helvetica", 9, "bold"))
        self.left_lbl.pack(pady=1)
        
        self.comp_lbl = tk.Label(self.header_frame, text="", bg=BG_DARK, fg=ACCENT_CYAN, font=("Helvetica", 9, "bold"))
        self.comp_lbl.pack(pady=1)
        
        self.canvas_frame = tk.Frame(self, bg=BG_DARK, highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.canvas_frame.pack(padx=20, pady=5)
        
        self.canvas = tk.Canvas(self.canvas_frame, width=600, height=760, bg=BG_DARK, bd=0, highlightthickness=0)
        self.canvas.pack()
        
        self.footer_frame = tk.Frame(self, bg=BG_DARK)
        self.footer_frame.pack(fill="x", padx=20, pady=10)
        
        _ar = tm._current_language == "Arabic"
        if _ar:
            next_text = get_arabic_text("التالي ←")
            prev_text = get_arabic_text("← السابق")  # In RTL, ← is left pointing arrow which means back/previous
        elif tm._current_language == "French":
            next_text = get_arabic_text("Suivant (التالي) ←")
            prev_text = get_arabic_text("→ Précédent (السابق)")
        else:
            next_text = get_arabic_text("Next (التالي) ←")
            prev_text = get_arabic_text("→ Previous (السابق)")
            
        btn_font = ("Amiri", 11, "bold") if _ar else ("Helvetica", 10, "bold")
            
        self.next_btn = tk.Button(self.footer_frame, text=next_text, bg=BG_CARD, fg=TEXT_WHITE,
                                  activebackground=ACCENT_PURPLE, activeforeground=BG_DARK,
                                  highlightbackground=BORDER_COLOR, highlightthickness=1, relief="flat",
                                  font=btn_font, width=16, height=2, command=self.next_page)
        self.next_btn.pack(side="left")
        self.bind_button_hover(self.next_btn, ACCENT_PURPLE, BG_CARD, TEXT_WHITE, BG_DARK)
        
        self.prev_btn = tk.Button(self.footer_frame, text=prev_text, bg=BG_CARD, fg=TEXT_WHITE,
                                  activebackground=ACCENT_CYAN, activeforeground=BG_DARK,
                                  highlightbackground=BORDER_COLOR, highlightthickness=1, relief="flat",
                                  font=btn_font, width=16, height=2, command=self.prev_page)
        self.prev_btn.pack(side="right")
        self.bind_button_hover(self.prev_btn, ACCENT_CYAN, BG_CARD, TEXT_WHITE, BG_DARK)
        
        self.scale = tk.Scale(self, from_=1, to=self.total_pages, orient="horizontal", bg=BG_DARK, fg=TEXT_MUTED,
                              troughcolor=BG_CARD, activebackground=ACCENT_PURPLE, highlightthickness=0,
                              font=("Helvetica", 8), command=self.on_scale_moved)
        self.scale.pack(fill="x", padx=30, pady=(5, 10))
        self.scale.set(self.current_page)
        
    def bind_button_hover(self, btn, active_bg, normal_bg, normal_fg, active_fg):
        btn.bind("<Enter>", lambda e=None: btn.config(bg=active_bg, fg=active_fg, highlightbackground=active_bg))
        btn.bind("<Leave>", lambda e=None: btn.config(bg=normal_bg, fg=normal_fg, highlightbackground=BORDER_COLOR))
        
    def on_scale_moved(self, val):
        target = int(val)
        if target != self.current_page and not self.animating:
            self.current_page = target
            self.render_current_page()
            self.save_progress()
            
    def get_page_image(self, page_num):
        from PIL import Image, ImageTk
        img_path = os.path.join(self.pages_dir, f"page_{page_num:03d}.jpg")
        img = Image.open(img_path)
        
        try:
            resample_filter = Image.Resampling.LANCZOS
        except AttributeError:
            try:
                resample_filter = Image.LANCZOS
            except AttributeError:
                resample_filter = Image.ANTIALIAS
                
        img = img.resize((600, 760), resample_filter)
        return ImageTk.PhotoImage(img)
        
    def render_current_page(self):
        self.current_photo = self.get_page_image(self.current_page)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.current_photo, anchor="nw")
        self.update_labels()
        
    def update_labels(self):
        info_ar = get_arabic_text(f"الصفحة {self.current_page}")
        self.info_lbl.config(text=f"{tm.tr('quran_page_of').format(current=self.current_page, total=self.total_pages)} ({info_ar})")
        left = self.total_pages - self.current_page
        left_ar = get_arabic_text(f"المتبقي {left}")
        self.left_lbl.config(text=f"{tm.tr('quran_pages_left').format(left=left)} ({left_ar})")
        comp_ar = get_arabic_text("ختمات القرآن")
        self.comp_lbl.config(text=f"{tm.tr('quran_completions').format(count=self.completions)} ({comp_ar})")
        self.scale.set(self.current_page)
        
    def next_page(self):
        if self.animating:
            return
        if self.current_page >= self.total_pages:
            self.completions += 1
            self.current_page = 1
            self.save_progress()
            self.render_current_page()
            messagebox.showinfo(tm.tr("mashaallah"), tm.tr("quran_completion_success"))
            return
            
        old_photo = self.current_photo
        new_page = self.current_page + 1
        new_photo = self.get_page_image(new_page)
        
        self.animating = True
        self.animate_slide("next", old_photo, new_photo, new_page)
        
    def prev_page(self):
        if self.animating:
            return
        if self.current_page <= 1:
            return
            
        old_photo = self.current_photo
        new_page = self.current_page - 1
        new_photo = self.get_page_image(new_page)
        
        self.animating = True
        self.animate_slide("prev", old_photo, new_photo, new_page)
        
    def animate_slide(self, direction, old_photo, new_photo, target_page):
        width = 600
        steps = 10
        delay = 12
        
        if direction == "next":
            start_x_old = 0
            end_x_old = width
            start_x_new = -width
            end_x_new = 0
        else:
            start_x_old = 0
            end_x_old = -width
            start_x_new = width
            end_x_new = 0
            
        self.canvas.delete("all")
        self.old_photo_ref = old_photo
        self.new_photo_ref = new_photo
        
        item_old = self.canvas.create_image(start_x_old, 0, image=old_photo, anchor="nw")
        item_new = self.canvas.create_image(start_x_new, 0, image=new_photo, anchor="nw")
        
        current_step = 0
        
        def step():
            if not self.winfo_exists():
                return
            nonlocal current_step
            current_step += 1
            pct = current_step / steps
            ease_pct = 1.0 - (1.0 - pct) ** 2
            
            curr_x_old = start_x_old + (end_x_old - start_x_old) * ease_pct
            curr_x_new = start_x_new + (end_x_new - start_x_new) * ease_pct
            
            try:
                self.canvas.coords(item_old, curr_x_old, 0)
                self.canvas.coords(item_new, curr_x_new, 0)
            except Exception:
                return
            
            if current_step < steps:
                self.canvas.after(delay, step)
            else:
                try:
                    self.canvas.delete(item_old)
                    self.canvas.coords(item_new, 0, 0)
                except Exception:
                    pass
                
                self.current_page = target_page
                self.current_photo = new_photo
                self.update_labels()
                self.save_progress()
                self.animating = False
                
        step()


class QuranAudioScreen(tk.Frame):
    """
    Full-page screen for listening to Quran.
    Divided into a split layout:
      - Left column: Search input and scrollable list of Surahs.
      - Right column: Audio player panel (vinyl image, large playback control, volume).
    """
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.configure(bg=BG_DARK)
        
        # Hide mini player when entering the QuranAudioScreen page
        self.parent.hide_mini_player()
        
        self.current_surah = self.parent.bg_current_surah
        self.active_timers = []
        self.raw_search_query = ""
        self.surah_rows = []
        
        self.progress_map = self.load_all_progress()
        
        self.setup_ui()
        self.build_surah_rows()
        self.filter_surahs("")
        
        if self.current_surah:
            self.sync_play_state_ui()
            
        self.update_playback_loop()
        
    def load_all_progress(self):
        progress = {}
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT surah_number, last_position FROM quran_audio_progress")
            for r in c.fetchall():
                progress[r[0]] = r[1]
            conn.close()
        except Exception as e:
            print(f"Error loading audio progress: {e}")
        return progress
        
    def get_saved_position(self, surah_num):
        return self.progress_map.get(surah_num, 0.0)
        
    def save_position(self, surah_num, pos):
        self.progress_map[surah_num] = pos
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO quran_audio_progress (surah_number, last_position) VALUES (?, ?)", (surah_num, pos))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error saving audio progress: {e}")
            
    def setup_ui(self):
        # 1. Header Frame
        header = tk.Frame(self, bg=BG_CARD, highlightbackground=BORDER_COLOR, highlightthickness=1)
        header.pack(fill="x", side="top")
        
        back_btn = tk.Button(header, text=f"← {tm.tr('back_to_home')}", bg=BG_DARK, fg=TEXT_MUTED, relief="flat", font=("Helvetica", 10, "bold"), padx=15, pady=8, command=self.go_back)
        back_btn.pack(side="left", padx=15, pady=10)
        self.bind_button_hover(back_btn, ACCENT_PURPLE, BG_DARK, TEXT_MUTED, BG_DARK)
        
        title_lbl = tk.Label(header, text=tm.tr("quran_recitations"), bg=BG_CARD, fg=TEXT_WHITE, font=("Helvetica", 13, "bold"))
        title_lbl.pack(side="right", padx=15, pady=10)
        
        # 2. Main Content Split Pane
        content_pane = tk.Frame(self, bg=BG_DARK)
        content_pane.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Left Panel (Surah list and search)
        left_panel = tk.Frame(content_pane, bg=BG_DARK)
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        # Search area inside left panel
        search_frame = tk.Frame(left_panel, bg=BG_DARK)
        search_frame.pack(fill="x", pady=(0, 10))
        
        tk.Label(search_frame, text=tm.tr("search_surah"), bg=BG_DARK, fg=TEXT_MUTED, font=("Helvetica", 10, "bold")).pack(side="left", padx=(0, 10))
        
        self.search_entry = tk.Entry(search_frame, bg=BG_CARD, fg=TEXT_WHITE, relief="flat", font=("Helvetica", 11), insertbackground=TEXT_WHITE)
        self.search_entry.pack(fill="x", expand=True, ipady=5)
        self.search_entry.bind("<Key>", self.on_entry_key)
        
        # Helper label
        tk.Label(left_panel, text=tm.tr("search_helper_text"), bg=BG_DARK, fg=TEXT_MUTED, font=("Helvetica", 8, "italic")).pack(anchor="w", pady=(0, 5))
        
        # Scrollable Surah Container
        scroll_container = tk.Frame(left_panel, bg=BG_DARK, highlightbackground=BORDER_COLOR, highlightthickness=1)
        scroll_container.pack(fill="both", expand=True)
        
        self.scroll_frame = ScrollableFrame(scroll_container)
        self.scroll_frame.pack(fill="both", expand=True)
        
        # Right Panel (Player Panel)
        right_panel = tk.Frame(content_pane, bg=BG_CARD, highlightbackground=BORDER_COLOR, highlightthickness=1, width=460)
        right_panel.pack(side="right", fill="both", padx=(10, 0))
        right_panel.pack_propagate(False)
        
        # Big Vinyl/Player icon
        disc_lbl = tk.Label(right_panel, text="🎧", bg=BG_CARD, fg=ACCENT_CYAN, font=("Helvetica", 64), height=2)
        disc_lbl.pack(pady=40)
        
        self.now_playing_lbl = tk.Label(right_panel, text=tm.tr("select_surah_to_listen"), bg=BG_CARD, fg=TEXT_WHITE, font=("Helvetica", 12, "bold"), wraplength=400, justify="center")
        self.now_playing_lbl.pack(fill="x", padx=30, pady=10)
        
        # Progress Bar & Duration Labels Frame
        slider_frame = tk.Frame(right_panel, bg=BG_CARD)
        slider_frame.pack(fill="x", padx=30, pady=15)
        
        self.time_curr_lbl = tk.Label(slider_frame, text="00:00", bg=BG_CARD, fg=TEXT_MUTED, font=("Helvetica", 9))
        self.time_curr_lbl.pack(side="left")
        
        self.time_total_lbl = tk.Label(slider_frame, text="00:00", bg=BG_CARD, fg=TEXT_MUTED, font=("Helvetica", 9))
        self.time_total_lbl.pack(side="right")
        
        self.progress_scale = ModernScale(slider_frame, from_=0, to=100, command=self.on_slider_change)
        self.progress_scale.pack(side="left", fill="x", expand=True, padx=10)
        self.progress_scale.bind("<ButtonRelease-1>", self.on_slider_released)
        
        # Playback Controls
        ctrl_frame = tk.Frame(right_panel, bg=BG_CARD)
        ctrl_frame.pack(pady=20)
        
        self.play_btn = tk.Button(ctrl_frame, text=tm.tr("play"), bg=BG_DARK, fg=TEXT_WHITE, relief="flat", font=("Helvetica", 11, "bold"), width=12, height=2, state="disabled", command=self.toggle_play_pause)
        self.play_btn.pack(side="left", padx=10)
        self.bind_button_hover(self.play_btn, ACCENT_PURPLE, BG_DARK, TEXT_WHITE, BG_DARK)
        
        self.stop_btn = tk.Button(ctrl_frame, text=tm.tr("stop"), bg=BG_DARK, fg=TEXT_WHITE, relief="flat", font=("Helvetica", 11, "bold"), width=12, height=2, state="disabled", command=self.stop_audio)
        self.stop_btn.pack(side="left", padx=10)
        self.bind_button_hover(self.stop_btn, ACCENT_CYAN, BG_DARK, TEXT_WHITE, BG_DARK)
        
        # Play Mode Control
        mode_frame = tk.Frame(right_panel, bg=BG_CARD)
        mode_frame.pack(fill="x", padx=60, pady=10)
        
        mode_lbl = tk.Label(mode_frame, text=tm.tr("play_mode"), bg=BG_CARD, fg=TEXT_MUTED, font=("Helvetica", 10))
        mode_lbl.pack(side="left", padx=5)
        
        modes_map = {
            "single": tm.tr("mode_single"),
            "loop": tm.tr("mode_loop"),
            "next": tm.tr("mode_next"),
            "shuffle": tm.tr("mode_shuffle")
        }
        
        self.play_mode_display = tk.StringVar(value=modes_map[self.parent.bg_play_mode])
        
        def on_mode_change(*args):
            disp = self.play_mode_display.get()
            for k, v in modes_map.items():
                if v == disp:
                    self.parent.bg_play_mode = k
                    break
                    
        self.play_mode_display.trace_add("write", on_mode_change)
        
        opt = tk.OptionMenu(mode_frame, self.play_mode_display, *modes_map.values())
        opt.config(bg=BG_DARK, fg=TEXT_WHITE, activebackground=ACCENT_PURPLE, activeforeground=BG_DARK, relief="flat", font=("Helvetica", 9, "bold"), highlightthickness=0)
        opt["menu"].config(bg=BG_DARK, fg=TEXT_WHITE, font=("Helvetica", 9, "bold"))
        opt.pack(side="left", fill="x", expand=True, padx=5)

        # Volume Control
        vol_frame = tk.Frame(right_panel, bg=BG_CARD)
        vol_frame.pack(fill="x", padx=60, pady=20)
        
        tk.Label(vol_frame, text=tm.tr("volume"), bg=BG_CARD, fg=TEXT_MUTED, font=("Helvetica", 10)).pack(side="left", padx=5)
        self.vol_scale = ModernScale(vol_frame, from_=0, to=1.0, command=self.on_volume_changed)
        self.vol_scale.pack(side="left", fill="x", expand=True, padx=5)
        self.vol_scale.set(0.7)
        
    def bind_button_hover(self, btn, active_bg, normal_bg, normal_fg, active_fg):
        btn.bind("<Enter>", lambda e=None: btn.config(bg=active_bg, fg=active_fg) if btn["state"] != "disabled" else None)
        btn.bind("<Leave>", lambda e=None: btn.config(bg=normal_bg, fg=normal_fg) if btn["state"] != "disabled" else None)
        
    def on_entry_key(self, event):
        key = event.keysym
        char = event.char
        
        if event.state & 4:  # Ignore Ctrl shortcuts
            return
            
        if key in ("Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R", "Caps_Lock", "Escape", "Left", "Right", "Up", "Down", "Tab"):
            return
            
        if key == "BackSpace":
            self.raw_search_query = self.raw_search_query[:-1]
        elif char:
            self.raw_search_query += char
        else:
            return
            
        # Display correctly reshaped Arabic inside search box
        shaped_text = get_arabic_text(self.raw_search_query)
        self.search_entry.delete(0, tk.END)
        self.search_entry.insert(0, shaped_text)
        
        # Filter rows immediately
        self.filter_surahs(self.raw_search_query.strip().lower())
        return "break"
        
    def build_surah_rows(self):
        # List files in dos_6 folder
        audio_dir = os.path.join(APP_DIR, "data", "dos_6")
        available_files = {}
        if os.path.exists(audio_dir):
            try:
                for filename in os.listdir(audio_dir):
                    if filename.endswith(".mp3"):
                        try:
                            num = int(filename.split(".")[0])
                            available_files[num] = filename
                        except ValueError:
                            pass
            except Exception:
                pass
                
        for surah in SURAH_MAPPING:
            num = surah['num']
            
            row = tk.Frame(self.scroll_frame.scrollable_frame, bg=BG_CARD, highlightbackground=BORDER_COLOR, highlightthickness=1)
            
            ar_name = get_arabic_text(surah['arabic'])
            label_text = f"{num:03d}. {surah['english']} ({ar_name})"
            
            lbl_info = tk.Label(row, text=label_text, bg=BG_CARD, fg=TEXT_WHITE, font=("Helvetica", 10, "bold"), anchor="w", justify="left")
            lbl_info.pack(side="left", fill="x", expand=True, padx=10, pady=10)
            
            # Progress sub-info
            saved_pos = self.get_saved_position(num)
            pos_lbl = None
            if saved_pos > 0.5:
                m, s = divmod(int(saved_pos), 60)
                h, m = divmod(m, 60)
                time_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
                pos_lbl = tk.Label(row, text=f"{tm.tr('last_pos')}: {time_str}", bg=BG_CARD, fg=TEXT_MUTED, font=("Helvetica", 8, "italic"))
                pos_lbl.pack(side="left", padx=10)
                
            # Play Button
            is_available = num in available_files
            play_btn = None
            if is_available:
                play_btn = tk.Button(row, text=tm.tr("play"), bg=BG_DARK, fg=TEXT_WHITE, relief="flat", font=("Helvetica", 9, "bold"), padx=10, command=lambda s=surah: self.play_surah(s))
                play_btn.pack(side="right", padx=10, pady=10)
                self.bind_button_hover(play_btn, ACCENT_PURPLE, BG_DARK, TEXT_WHITE, BG_DARK)
            else:
                missing_lbl = tk.Label(row, text=tm.tr("file_missing"), bg=BG_CARD, fg=TEXT_MUTED, font=("Helvetica", 9, "italic"))
                missing_lbl.pack(side="right", padx=10, pady=10)
                
            self.surah_rows.append({
                "num": num,
                "english": surah['english'],
                "arabic": surah['arabic'],
                "widget": row,
                "pos_lbl": pos_lbl,
                "play_btn": play_btn
            })
            
    def filter_surahs(self, query=""):
        is_num = False
        try:
            num_query = int(query)
            is_num = True
        except ValueError:
            pass
            
        norm_query = normalize_arabic(query.strip().lower())
            
        for row in self.surah_rows:
            match = False
            if not query:
                match = True
            elif is_num and row['num'] == num_query:
                match = True
            elif query in row['english'].lower():
                match = True
            elif norm_query and norm_query in normalize_arabic(row['arabic']):
                match = True
                
            if match:
                row['widget'].pack(fill="x", padx=10, pady=5)
            else:
                row['widget'].pack_forget()
        
    def update_row_last_position(self, num, pos):
        for row in self.surah_rows:
            if row['num'] == num:
                if pos <= 0.5:
                    if row['pos_lbl']:
                        row['pos_lbl'].destroy()
                        row['pos_lbl'] = None
                else:
                    m, s = divmod(int(pos), 60)
                    h, m = divmod(m, 60)
                    time_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
                    if row['pos_lbl'] and row['pos_lbl'].winfo_exists():
                        row['pos_lbl'].config(text=f"{tm.tr('last_pos')}: {time_str}")
                    else:
                        row['pos_lbl'] = tk.Label(row['widget'], text=f"{tm.tr('last_pos')}: {time_str}", bg=BG_CARD, fg=TEXT_MUTED, font=("Helvetica", 8, "italic"))
                        row['pos_lbl'].pack(side="left", padx=10)
                        
    def play_surah(self, surah):
        self.parent.play_surah_bg(surah)
        self.current_surah = surah

    def toggle_play_pause(self):
        self.parent.toggle_play_pause_bg()

    def stop_audio(self):
        self.parent.stop_surah_bg()
        self.current_surah = None

    def on_slider_change(self, val):
        sec = float(val)
        m, s = divmod(int(sec), 60)
        h, m = divmod(m, 60)
        curr_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
        self.time_curr_lbl.config(text=curr_str)

    def on_slider_released(self, event):
        if not self.current_surah:
            return
        target_sec = self.progress_scale.get()
        self.seek_to(target_sec)

    def seek_to(self, seconds):
        self.parent.seek_bg(seconds)

    def on_volume_changed(self, val):
        vol = float(val)
        import pygame
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.set_volume(vol)
        except Exception:
            pass

    def sync_playback_state(self, curr_sec):
        if not self.winfo_exists():
            return
        self.progress_scale.set(curr_sec)
        m, s = divmod(int(curr_sec), 60)
        h, m = divmod(m, 60)
        curr_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
        self.time_curr_lbl.config(text=curr_str)

    def sync_play_state_ui(self):
        if not self.winfo_exists():
            return
        surah = self.parent.bg_current_surah
        self.current_surah = surah
        if surah:
            ar_name = get_arabic_text(surah['arabic'])
            self.now_playing_lbl.config(text=f"{tm.tr('now_playing_prefix')}{surah['num']:03d}. {surah['english']} ({ar_name})")
            self.play_btn.config(state="normal")
            self.stop_btn.config(state="normal")
            
            # Set play/pause text
            play_text = tm.tr("pause") if (self.parent.bg_music_active and not self.parent.bg_music_paused) else tm.tr("play")
            self.play_btn.config(text=play_text)
            
            # Duration labels
            self.progress_scale.config(to=self.parent.bg_total_duration)
            tot_m, tot_s = divmod(int(self.parent.bg_total_duration), 60)
            tot_h, tot_m = divmod(tot_m, 60)
            tot_str = f"{tot_h:02d}:{tot_m:02d}:{tot_s:02d}" if tot_h > 0 else f"{tot_m:02d}:{tot_s:02d}"
            self.time_total_lbl.config(text=tot_str)
        else:
            self.now_playing_lbl.config(text=tm.tr("select_surah_to_listen"))
            self.play_btn.config(text=tm.tr("play"), state="disabled")
            self.stop_btn.config(state="disabled")
            self.progress_scale.set(0)
            self.progress_scale.config(to=100)
            self.time_curr_lbl.config(text="00:00")
            self.time_total_lbl.config(text="00:00")

    def update_playback_loop(self):
        if self.parent.bg_music_active and not self.parent.bg_music_paused:
            import pygame
            try:
                pos_ms = pygame.mixer.music.get_pos()
                if pos_ms >= 0:
                    curr_sec = self.parent.bg_start_time_offset + (pos_ms / 1000.0)
                    self.sync_playback_state(curr_sec)
            except Exception:
                pass
        timer_id = self.after(500, self.update_playback_loop)
        self.active_timers.append(timer_id)

    def go_back(self):
        if self.parent.bg_music_active:
            def handle_choice(choice):
                if choice == "pause":
                    import pygame
                    try:
                        pygame.mixer.music.pause()
                    except Exception:
                        pass
                    self.parent.bg_music_paused = True
                    self.parent.show_mini_player()
                elif choice == "quit":
                    self.parent.stop_surah_bg()
                else: # continue
                    self.parent.show_mini_player()
                
                for tid in self.active_timers:
                    try:
                        self.after_cancel(tid)
                    except Exception:
                        pass
                self.parent.show_start_screen(show_tools=True)
                
            ExitListeningDialog(self.parent, handle_choice)
        else:
            for tid in self.active_timers:
                try:
                    self.after_cancel(tid)
                except Exception:
                    pass
            self.parent.show_start_screen(show_tools=True)


class AzkarScreen(tk.Frame):
    """
    Daily Azkar interactive interface as a full-page screen.
    Allows user to select a category, read Azkars, click to count,
    and shows progress and completion.
    """
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.configure(bg=BG_DARK)
        
        self.azkar_data = self.load_azkar_data()
        
        self.main_container = tk.Frame(self, bg=BG_DARK)
        self.main_container.pack(fill="both", expand=True)
        
        self.current_category = None
        self.current_azkar = []
        
        self.show_category_selection()
        
    def load_azkar_data(self):
        json_path = os.path.join(APP_DIR, "data", "azkar.json")
        
        # If it doesn't exist, try to download and decrypt once
        if not os.path.exists(json_path):
            try:
                import urllib.request
                import hashlib
                import base64
                import subprocess
                
                url = "https://alazkar.today/api/azkar.php"
                req = urllib.request.Request(url)
                req.add_header("X-Azkar-Token", "h0ozWAsuLaMXIyHQjBCMTA5Mqy4MWxBc")
                req.add_header("User-Agent", "Mozilla/5.0")
                
                with urllib.request.urlopen(req, timeout=10) as response:
                    res_json = json.loads(response.read().decode('utf-8'))
                    
                enc_data_b64 = res_json["data"]
                iv_b64 = res_json["iv"]
                
                enc_data = base64.b64decode(enc_data_b64)
                iv = base64.b64decode(iv_b64)
                
                key_str = "AzkarToday@2024!SecureKey#Islam"
                key_bytes = hashlib.sha256(key_str.encode('utf-8')).digest()
                
                key_hex = key_bytes.hex()
                iv_hex = iv.hex()
                
                proc = subprocess.Popen(
                    ["openssl", "enc", "-d", "-aes-256-cbc", "-K", key_hex, "-iv", iv_hex, "-nosalt"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                stdout, stderr = proc.communicate(input=enc_data)
                
                if proc.returncode == 0:
                    decrypted_data = json.loads(stdout.decode('utf-8'))
                    os.makedirs(os.path.dirname(json_path), exist_ok=True)
                    with open(json_path, "w", encoding="utf-8") as f_out:
                        json.dump(decrypted_data, f_out, ensure_ascii=False, indent=2)
            except Exception:
                pass
                
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                import re
                for item in data:
                    if 'zekr' in item:
                        val = item['zekr']
                        # Normalize spaces before commas and convert English commas
                        val = re.sub(r'\s+[،,]', '،', val)
                        val = re.sub(r',', '،', val)
                        # Ensure exactly one space after each comma
                        val = re.sub(r'،\s*', '، ', val)
                        # Double check trailing space correction
                        val = re.sub(r'\s+،', '،', val)
                        # Fix joint words and make them separate
                        val = val.replace("أَعوذُبِكَ", "أَعُوذُ بِكَ").replace("أَعُوذُبِكَ", "أَعُوذُ بِكَ").replace("أَعوذُ بِكَ", "أَعُوذُ بِكَ")
                        item['zekr'] = val.strip()
                return data
            except Exception as e:
                print(f"Error loading azkar.json: {e}")
        return []
        
    def show_category_selection(self):
        # Clear main container
        for widget in self.main_container.winfo_children():
            widget.destroy()
            
        # Top Header Frame
        header = tk.Frame(self.main_container, bg=BG_CARD, highlightbackground=BORDER_COLOR, highlightthickness=1)
        header.pack(fill="x", side="top")
        
        back_btn = tk.Button(header, text=f"← {tm.tr('back_to_home')}", bg=BG_DARK, fg=TEXT_MUTED, relief="flat", font=("Helvetica", 10, "bold"), padx=15, pady=8, command=lambda: self.parent.show_start_screen(show_tools=True))
        back_btn.pack(side="left", padx=15, pady=10)
        self.bind_button_hover(back_btn, ACCENT_PURPLE, BG_DARK, TEXT_MUTED, BG_DARK)
        
        # Center Pane for Categories
        center_pane = tk.Frame(self.main_container, bg=BG_DARK)
        center_pane.pack(expand=True)
        
        # Title
        lbl_title = tk.Label(center_pane, text=tm.tr("daily_azkar_title"), bg=BG_DARK, fg=TEXT_WHITE, font=("Helvetica", 20, "bold"), justify="center")
        lbl_title.pack(pady=(0, 20))
        
        lbl_subtitle = tk.Label(center_pane, text=tm.tr("select_azkar_category"), bg=BG_DARK, fg=TEXT_MUTED, font=("Helvetica", 11, "italic"))
        lbl_subtitle.pack(pady=(0, 40))
        
        # Category Buttons Frame
        btn_frame = tk.Frame(center_pane, bg=BG_DARK)
        btn_frame.pack(fill="x", padx=60)
        
        # 1. Morning Azkar
        morning_text = get_arabic_text("أذكار الصباح")
        morning_btn = tk.Button(btn_frame, text=f"🌅 {morning_text} ({tm.tr('morning_tag')})", bg=BG_CARD, fg=TEXT_WHITE,
                                activebackground=ACCENT_PURPLE, activeforeground=BG_DARK,
                                highlightbackground=BORDER_COLOR, highlightthickness=1, relief="flat",
                                font=("Helvetica", 13, "bold"), width=32, height=3, command=lambda: self.start_azkar("أذكار الصباح"))
        morning_btn.pack(pady=12)
        self.bind_button_hover(morning_btn, ACCENT_PURPLE, BG_CARD, TEXT_WHITE, BG_DARK)
        
        # 2. Evening Azkar
        evening_text = get_arabic_text("أذكار المساء")
        evening_btn = tk.Button(btn_frame, text=f"🌃 {evening_text} ({tm.tr('evening_tag')})", bg=BG_CARD, fg=TEXT_WHITE,
                                activebackground=ACCENT_CYAN, activeforeground=BG_DARK,
                                highlightbackground=BORDER_COLOR, highlightthickness=1, relief="flat",
                                font=("Helvetica", 13, "bold"), width=32, height=3, command=lambda: self.start_azkar("أذكار المساء"))
        evening_btn.pack(pady=12)
        self.bind_button_hover(evening_btn, ACCENT_CYAN, BG_CARD, TEXT_WHITE, BG_DARK)
        
        # 3. Sleep Azkar
        sleep_text = get_arabic_text("أذكار النوم")
        sleep_btn = tk.Button(btn_frame, text=f"🛌 {sleep_text} ({tm.tr('sleep_tag')})", bg=BG_CARD, fg=TEXT_WHITE,
                              activebackground=ACCENT_PURPLE, activeforeground=BG_DARK,
                              highlightbackground=BORDER_COLOR, highlightthickness=1, relief="flat",
                              font=("Helvetica", 13, "bold"), width=32, height=3, command=lambda: self.start_azkar("أذكار النوم"))
        sleep_btn.pack(pady=12)
        self.bind_button_hover(sleep_btn, ACCENT_PURPLE, BG_CARD, TEXT_WHITE, BG_DARK)
        
    def start_azkar(self, category):
        raw_items = [item for item in self.azkar_data if item.get('category') == category]
        
        if not raw_items:
            messagebox.showerror(tm.tr("error"), tm.tr("no_azkar_found").format(category=category))
            return
            
        self.current_category = category
        self.current_azkar = []
        for item in raw_items:
            self.current_azkar.append({
                "zekr": item.get("zekr", ""),
                "description": item.get("description", ""),
                "reference": item.get("reference", ""),
                "audio": item.get("audio", ""),
                "target_count": item.get("count", 1),
                "current_count": 0,
                "card_frame": None,
                "counter_btn": None
            })
        
        # Load saved progress for today (resets after midnight automatically)
        self._load_azkar_progress()
            
        self.show_azkar_viewer()
        
    def show_azkar_viewer(self):
        for widget in self.main_container.winfo_children():
            widget.destroy()
            
        # Header
        header = tk.Frame(self.main_container, bg=BG_CARD, highlightbackground=BORDER_COLOR, highlightthickness=1)
        header.pack(fill="x", side="top")
        
        back_btn = tk.Button(header, text=tm.tr("back"), bg=BG_DARK, fg=TEXT_MUTED, relief="flat", font=("Helvetica", 10), command=self.show_category_selection)
        back_btn.pack(side="left", padx=15, pady=10)
        self.bind_button_hover(back_btn, ACCENT_PURPLE, BG_DARK, TEXT_MUTED, BG_DARK)
        
        cat_text = get_arabic_text(self.current_category)
        title_lbl = tk.Label(header, text=cat_text, bg=BG_CARD, fg=TEXT_WHITE, font=("Helvetica", 12, "bold"))
        title_lbl.pack(side="right", padx=15, pady=10)
        
        # Progress Frame
        self.progress_frame = tk.Frame(self.main_container, bg=BG_DARK)
        self.progress_frame.pack(fill="x", padx=40, pady=15)
        
        self.progress_lbl = tk.Label(self.progress_frame, text=f"0 / 0 {tm.tr('completed')} (0%)", bg=BG_DARK, fg=TEXT_MUTED, font=("Helvetica", 10, "bold"))
        self.progress_lbl.pack(anchor="w")
        
        self.progress_canvas = tk.Canvas(self.progress_frame, bg=BG_CARD, height=8, highlightthickness=0)
        self.progress_canvas.pack(fill="x", pady=(5, 0))
        self.progress_fill_id = self.progress_canvas.create_rectangle(0, 0, 0, 8, fill=ACCENT_CYAN, width=0)
        
        # Scrollable Frame
        self.scroll_container = tk.Frame(self.main_container, bg=BG_DARK, highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.scroll_container.pack(fill="both", expand=True, padx=40, pady=(0, 20))
        
        self.scroll_frame = ScrollableFrame(self.scroll_container)
        self.scroll_frame.pack(fill="both", expand=True)
        
        self.render_azkar_list()
        self._apply_restored_counts()
        self.update_overall_progress()
        
        # Start the midnight reset scheduler (track which day we opened the viewer)
        self._last_known_date = datetime.date.today().isoformat()
        self._schedule_midnight_reset()
        
    def render_azkar_list(self):
        for index, item in enumerate(self.current_azkar):
            card = tk.Frame(self.scroll_frame.scrollable_frame, bg=BG_CARD, highlightbackground=BORDER_COLOR, highlightthickness=1)
            card.pack(fill="x", padx=15, pady=10)
            item["card_frame"] = card
            
            # Zikr text - wider max_chars for full page!
            zekr_reshaped = get_arabic_text_multiline(item["zekr"], max_chars=80)
            zekr_lbl = tk.Label(card, text=zekr_reshaped, bg=BG_CARD, fg=TEXT_WHITE, font=("Amiri", 14, "bold"), justify="right", anchor="e")
            zekr_lbl.pack(fill="x", padx=25, pady=(20, 10))
            
            # Info Frame (only reference)
            info_frame = tk.Frame(card, bg=BG_CARD)
            info_frame.pack(fill="x", padx=25, pady=(5, 12))
            
            ref_txt = item["reference"]
            if ref_txt:
                ref_reshaped = get_arabic_text(ref_txt)
                ref_lbl = tk.Label(info_frame, text=ref_reshaped, bg=BG_CARD, fg=ACCENT_CYAN, font=("Helvetica", 9), justify="right", anchor="e")
                ref_lbl.pack(fill="x", pady=2)
                
            # Bottom control
            bottom_frame = tk.Frame(card, bg=BG_CARD)
            bottom_frame.pack(fill="x", padx=25, pady=(0, 20))
            
            target = item["target_count"]
            btn_txt = f"0 / {target}"
            
            btn_counter = tk.Button(bottom_frame, text=btn_txt, bg=BG_DARK, fg=TEXT_WHITE, relief="flat", font=("Helvetica", 11, "bold"), padx=25, pady=10, command=lambda idx=index: self.increment_zikr(idx))
            btn_counter.pack(side="left")
            self.bind_button_hover(btn_counter, ACCENT_PURPLE, BG_DARK, TEXT_WHITE, BG_DARK)
            item["counter_btn"] = btn_counter
            
            # Click bindings to allow clicking anywhere on the card to count
            card.bind("<Button-1>", lambda e, idx=index: self.increment_zikr(idx))
            zekr_lbl.bind("<Button-1>", lambda e, idx=index: self.increment_zikr(idx))
                
    def increment_zikr(self, index):
        item = self.current_azkar[index]
        target = item["target_count"]
        curr = item["current_count"]
        
        if curr >= target:
            # Already completed: ask to reset
            confirm = messagebox.askyesno(tm.tr("reset_zikr_title"), tm.tr("reset_zikr_confirm"))
            if confirm:
                item["current_count"] = 0
                item["counter_btn"].config(text=f"0 / {target}", bg=BG_DARK, fg=TEXT_WHITE)
                self.bind_button_hover(item["counter_btn"], ACCENT_PURPLE, BG_DARK, TEXT_WHITE, BG_DARK)
                item["card_frame"].config(highlightbackground=BORDER_COLOR, highlightthickness=1)
                self.update_overall_progress()
            return
            
        item["current_count"] += 1
        new_curr = item["current_count"]
        
        if new_curr >= target:
            # Complete Zikr
            item["counter_btn"].config(text=f"✓ {new_curr} / {target}", bg=SUCCESS_GREEN, fg=BG_DARK)
            item["counter_btn"].bind("<Enter>", lambda e: None)
            item["counter_btn"].bind("<Leave>", lambda e: None)
            item["card_frame"].config(highlightbackground=SUCCESS_GREEN, highlightthickness=2)
        else:
            # Increment Zikr, highlight card in progress
            item["counter_btn"].config(text=f"{new_curr} / {target}")
            item["card_frame"].config(highlightbackground=ACCENT_CYAN, highlightthickness=1)
            
        self._save_azkar_progress()
        self.update_overall_progress()
        
    def update_overall_progress(self):
        total = len(self.current_azkar)
        completed = sum(1 for item in self.current_azkar if item["current_count"] >= item["target_count"])
        
        percent = int((completed / total) * 100) if total > 0 else 0
        self.progress_lbl.config(text=f"{completed} / {total} {tm.tr('completed')} ({percent}%)")
        
        canvas_width = self.progress_canvas.winfo_width()
        if canvas_width <= 1:
            canvas_width = 1120
            
        fill_width = int((percent / 100.0) * canvas_width)
        self.progress_canvas.coords(self.progress_fill_id, 0, 0, fill_width, 8)
        
        if completed == total and total > 0:
            self.show_completion_message()
            
    def show_completion_message(self):
        overlay = tk.Toplevel(self)
        overlay.title(tm.tr("mashaallah"))
        overlay.configure(bg=BG_DARK)
        overlay.geometry("400x300")
        overlay.resizable(False, False)
        overlay.transient(self)
        
        # Center relative to self
        x = self.winfo_rootx() + (self.winfo_width() / 2) - 200
        y = self.winfo_rooty() + (self.winfo_height() / 2) - 150
        overlay.geometry(f"+{int(x)}+{int(y)}")
        
        lbl_congrats = tk.Label(overlay, text=tm.tr("mashaallah"), bg=BG_DARK, fg=SUCCESS_GREEN, font=("Helvetica", 18, "bold"))
        lbl_congrats.pack(pady=(40, 10))
        
        lbl_title = tk.Label(overlay, text=tm.tr("azkar_completed_title"), bg=BG_DARK, fg=TEXT_WHITE, font=("Helvetica", 15, "bold"))
        lbl_title.pack(pady=5)
        
        lbl_subtitle = tk.Label(overlay, text=tm.tr("azkar_completed_subtitle"), bg=BG_DARK, fg=TEXT_MUTED, font=("Helvetica", 12, "italic"))
        lbl_subtitle.pack(pady=10)
        
        close_btn = tk.Button(overlay, text=tm.tr("ameen"), bg=BG_CARD, fg=TEXT_WHITE, relief="flat", font=("Helvetica", 11, "bold"), padx=35, pady=10, command=overlay.destroy)
        close_btn.pack(pady=(20, 0))
        self.bind_button_hover(close_btn, ACCENT_PURPLE, BG_CARD, TEXT_WHITE, BG_DARK)
        
        overlay.grab_set()
        
    # ── Azkar Progress Persistence ────────────────────────────────────────
    def _apply_restored_counts(self):
        """After render_azkar_list, update button labels and card highlights to match restored counts."""
        for item in self.current_azkar:
            curr = item["current_count"]
            target = item["target_count"]
            btn = item.get("counter_btn")
            card = item.get("card_frame")
            if btn is None:
                continue
            if curr >= target and curr > 0:
                btn.config(text=f"✓ {curr} / {target}", bg=SUCCESS_GREEN, fg=BG_DARK)
                btn.bind("<Enter>", lambda e: None)
                btn.bind("<Leave>", lambda e: None)
                if card:
                    card.config(highlightbackground=SUCCESS_GREEN, highlightthickness=2)
            elif curr > 0:
                btn.config(text=f"{curr} / {target}")
                if card:
                    card.config(highlightbackground=ACCENT_CYAN, highlightthickness=1)

    def _load_azkar_progress(self):
        """Load saved counter state for the current category.
        If the saved date != today, treat progress as fresh (midnight reset)."""
        today_str = datetime.date.today().isoformat()
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT reset_date, progress FROM azkar_progress WHERE category = ?",
                      (self.current_category,))
            row = c.fetchone()
            conn.close()
            if row and row[0] == today_str:
                saved = json.loads(row[1])
                # Apply saved counts back to current_azkar list
                for idx, item in enumerate(self.current_azkar):
                    item["current_count"] = saved.get(str(idx), 0)
            # If date differs or no row → keep default 0 (daily reset)
        except Exception:
            pass

    def _save_azkar_progress(self):
        """Persist current counter state for the current category."""
        today_str = datetime.date.today().isoformat()
        progress = {str(idx): item["current_count"] for idx, item in enumerate(self.current_azkar)}
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute(
                "INSERT INTO azkar_progress (category, reset_date, progress) VALUES (?, ?, ?) "
                "ON CONFLICT(category) DO UPDATE SET reset_date = excluded.reset_date, progress = excluded.progress",
                (self.current_category, today_str, json.dumps(progress))
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

    def _schedule_midnight_reset(self):
        """Schedule a check every minute; if we crossed midnight, reload viewer so counts reset."""
        now = datetime.datetime.now()
        # Milliseconds until the next full minute
        ms_until_next_minute = (60 - now.second) * 1000 - now.microsecond // 1000
        self.after(ms_until_next_minute, self._check_midnight)

    def _check_midnight(self):
        """Called every minute. If the calendar day has changed, reset counts to 0 and refresh UI."""
        now = datetime.datetime.now()
        today_str = datetime.date.today().isoformat()
        if hasattr(self, '_last_known_date') and self._last_known_date != today_str:
            # New day crossed midnight — clear progress and rebuild the viewer
            for item in self.current_azkar:
                item["current_count"] = 0
            self._save_azkar_progress()
            self.show_azkar_viewer()
        self._last_known_date = today_str
        # Schedule next check in ~60 seconds
        self.after(60000, self._check_midnight)

    def bind_button_hover(self, btn, active_bg, normal_bg, normal_fg, active_fg):
        btn.bind("<Enter>", lambda e=None: btn.config(bg=active_bg, fg=active_fg) if btn["state"] != "disabled" else None)
        btn.bind("<Leave>", lambda e=None: btn.config(bg=normal_bg, fg=normal_fg) if btn["state"] != "disabled" else None)


class AdviceDisplayDialog(tk.Toplevel):
    """
    A beautiful dark-themed modal popup displaying generated AI Coach advice (Small/Deep).
    """
    def __init__(self, parent, date_str, advice_type, advice_text):
        super().__init__(parent)
        advice_type_tr = tm.tr("small_tag") if advice_type == "small" else tm.tr("deep_tag")
        self.title(tm.tr("ai_coach_advice_title").format(type=advice_type_tr))
        self.configure(bg=BG_DARK)
        self.geometry("640x550")
        self.transient(parent)
        
        # Center relative to parent
        x = parent.winfo_rootx() + (parent.winfo_width() / 2) - 320
        y = parent.winfo_rooty() + (parent.winfo_height() / 2) - 275
        self.geometry(f"+{int(x)}+{int(y)}")
        
        color = ACCENT_CYAN if advice_type == "small" else ACCENT_PURPLE
        
        # Top color accent border
        top_bar = tk.Frame(self, bg=color, height=4)
        top_bar.pack(fill="x", side="top")
        
        # Header Row
        header = tk.Frame(self, bg=BG_DARK)
        header.pack(fill="x", padx=25, pady=(20, 10))
        
        icon = "💡" if advice_type == "small" else "🧠"
        title_lbl = tk.Label(header, text=f"{icon} {tm.tr('personal_ai_advice')} ({advice_type_tr})", bg=BG_DARK, fg=color, font=("Helvetica", 14, "bold"))
        title_lbl.pack(side="left")
        
        date_lbl = tk.Label(header, text=date_str, bg=BG_DARK, fg=TEXT_MUTED, font=("Helvetica", 10, "bold"))
        date_lbl.pack(side="right")
        
        # Text container holding the Text widget and modern Scrollbar
        content_frame = tk.Frame(self, bg=BG_CARD, highlightbackground=BORDER_COLOR, highlightthickness=1)
        content_frame.pack(fill="both", expand=True, padx=25, pady=10)
        
        accent_bar = tk.Frame(content_frame, bg=color, width=4)
        accent_bar.pack(side="left", fill="y")
        
        # The Scrollable Text Box (instantiated first for command binding, packed second for layout priority)
        _ar = tm._current_language == "Arabic"
        base_font = ("Amiri", 11) if _ar else ("Helvetica", 10)
        h_font = ("Amiri", 12, "bold") if _ar else ("Helvetica", 11, "bold")
        b_font = ("Amiri", 11, "bold") if _ar else ("Helvetica", 10, "bold")
        body_font = ("Amiri", 11) if _ar else ("Helvetica", 10)
        hl_font = ("Amiri", 11, "bold") if _ar else ("Helvetica", 10, "bold")

        text_box = tk.Text(content_frame, bg=BG_CARD, fg="#e4e4e7", insertbackground=TEXT_WHITE,
                           relief="flat", font=base_font, wrap="word", borderwidth=0, highlightthickness=0,
                           padx=15, pady=15, spacing1=6, spacing2=3)
        
        scrollbar = ttk.Scrollbar(content_frame, orient="vertical", command=text_box.yview)
        scrollbar.pack(side="right", fill="y")
        
        text_box.pack(side="left", fill="both", expand=True)
        text_box.configure(yscrollcommand=scrollbar.set)
        
        # Tag Configurations for beautiful styling hierarchy
        _justify = "right" if _ar else "left"
        text_box.tag_configure("section_header", font=h_font, foreground=color, justify=_justify)
        text_box.tag_configure("bullet", font=b_font, foreground=ACCENT_CYAN, justify=_justify)
        text_box.tag_configure("body", font=body_font, foreground="#e4e4e7", justify=_justify)
        text_box.tag_configure("highlight", font=hl_font, foreground=TEXT_WHITE, justify=_justify)
        
        # Format and insert the advice text
        self.parse_and_insert_text(text_box, advice_text, color)
        
        # Prevent text selection, cursor placement, and focus grab (returns "break" to halt Tkinter event propagation)
        text_box.bind("<Button-1>", lambda e: "break")
        text_box.bind("<B1-Motion>", lambda e: "break")
        text_box.bind("<KeyPress>", lambda e: "break")
        text_box.bind("<FocusIn>", lambda e: "break")
        
        # Make read-only
        text_box.config(state="disabled")
        
        # Footer dismiss button
        close_btn = tk.Button(self, text=tm.tr("acknowledge_close"), bg=BG_CARD, fg=TEXT_WHITE, relief="flat", font=("Helvetica", 10, "bold"),
                              padx=20, pady=8, command=self.destroy)
        close_btn.pack(pady=20)
        close_btn.bind("<Enter>", lambda e: close_btn.config(bg=color, fg=BG_DARK))
        close_btn.bind("<Leave>", lambda e: close_btn.config(bg=BG_CARD, fg=TEXT_WHITE))
        
        self.wait_visibility()
        
    def parse_and_insert_text(self, widget, text, color):
        lines = text.split("\n")
        for line in lines:
            stripped = line.strip()
            if not stripped:
                widget.insert(tk.END, "\n")
                continue
                
            # Detect section headers — works for English, French, and Arabic numbered sections
            _lang = tm._current_language
            is_header = (
                stripped.startswith(("#", "SECTION", "1. ", "2. ", "3. ", "4. ")) or
                stripped.startswith(("١.", "٢.", "٣.", "٤.")) or  # Arabic-Indic numerals
                stripped.startswith(("1.", "2.", "3.", "4.")) or  # catch any numeric prefix
                (stripped.isupper() and len(stripped) < 40 and _lang == "English") or
                stripped.endswith(":")
            )
            
            if is_header:
                clean_header = stripped.lstrip("# ").strip()
                widget.insert(tk.END, shape_for_display(clean_header) + "\n", "section_header")
            elif stripped.startswith(("-", "*", "•")):
                widget.insert(tk.END, "  • ", "bullet")
                self.insert_formatted_line(widget, stripped[1:].strip() + "\n")
            else:
                self.insert_formatted_line(widget, line + "\n")
                
    def insert_formatted_line(self, widget, text_line):
        parts = text_line.split("**")
        for idx, part in enumerate(parts):
            shaped_part = shape_for_display(part)
            if idx % 2 == 1:
                widget.insert(tk.END, shaped_part, "highlight")
            else:
                widget.insert(tk.END, shaped_part, "body")


class StarredPacksSelectionDialog(tk.Toplevel):
    """
    A beautiful modal scrollable popup listing all starred tasks packs to load from.
    """
    def __init__(self, parent, is_main):
        super().__init__(parent)
        self.parent_tracker = parent
        self.is_main = is_main
        self.title(tm.tr("load_starred_pack_title"))
        self.configure(bg=BG_DARK)
        self.geometry("420x400")
        self.transient(parent)
        
        # Center relative to parent
        x = parent.winfo_rootx() + (parent.winfo_width() / 2) - 210
        y = parent.winfo_rooty() + (parent.winfo_height() / 2) - 200
        self.geometry(f"+{int(x)}+{int(y)}")
        
        self.result = None
        color = ACCENT_PURPLE if is_main else ACCENT_CYAN
        
        # Top color accent border
        top_bar = tk.Frame(self, bg=color, height=4)
        top_bar.pack(fill="x", side="top")
        
        # Title Header
        header = tk.Frame(self, bg=BG_DARK)
        header.pack(fill="x", padx=25, pady=(20, 10))
        
        title_lbl = tk.Label(header, text=f"⭐ {tm.tr('starred_packs_title')}", bg=BG_DARK, fg=color, font=("Helvetica", 12, "bold"))
        title_lbl.pack(side="left")
        
        # Scrollable container for the packs list
        scroll_frame = ScrollableFrame(self, bg=BG_DARK)
        scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Fetch from database
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT title, stars, items FROM starred_packs")
        rows = c.fetchall()
        conn.close()
        
        if not rows:
            lbl = tk.Label(scroll_frame.scrollable_frame, text=tm.tr("no_starred_packs"), 
                            bg=BG_DARK, fg=TEXT_MUTED, font=("Helvetica", 10, "italic"), justify="center")
            lbl.pack(pady=50, fill="both", expand=True)
        else:
            for r_title, r_stars, r_items_json in rows:
                items = json.loads(r_items_json)
                pack_card = tk.Frame(scroll_frame.scrollable_frame, bg=BG_CARD, bd=1, highlightbackground=BORDER_COLOR, highlightthickness=1, cursor="hand2")
                pack_card.pack(fill="x", pady=5, padx=5)
                
                # Header row inside card
                card_header = tk.Frame(pack_card, bg=BG_CARD)
                card_header.pack(fill="x", padx=10, pady=(8, 2))
                
                lbl_title = tk.Label(card_header, text=r_title, bg=BG_CARD, fg=TEXT_WHITE, font=("Helvetica", 10, "bold"), anchor="w")
                lbl_title.pack(side="left")
                
                # Delete handler button
                btn_delete = tk.Label(card_header, text="❌", bg=BG_CARD, fg=TEXT_MUTED, font=("Helvetica", 8, "bold"), cursor="hand2")
                btn_delete.pack(side="right", padx=(10, 0))
                
                lbl_stars = tk.Label(card_header, text=f"⭐ {r_stars:.1f}" if r_stars else "⭐ 0", bg=BG_CARD, fg=color, font=("Helvetica", 9, "bold"))
                lbl_stars.pack(side="right")
                
                # Preview of items
                item_names = [i.get("name") for i in items]
                preview_text = ", ".join(item_names) if item_names else f"({tm.tr('empty_pack_label')})"
                if len(preview_text) > 45:
                    preview_text = preview_text[:42] + "..."
                    
                lbl_preview = tk.Label(pack_card, text=preview_text, bg=BG_CARD, fg=TEXT_MUTED, font=("Helvetica", 8), anchor="w")
                lbl_preview.pack(fill="x", padx=10, pady=(0, 8))
                
                # Selection handlers
                def make_select_handler(title=r_title, stars=r_stars, items_list=items):
                    return lambda e: self.select_pack(title, stars, items_list)
                    
                select_cb = make_select_handler()
                pack_card.bind("<Button-1>", select_cb)
                lbl_title.bind("<Button-1>", select_cb)
                lbl_stars.bind("<Button-1>", select_cb)
                lbl_preview.bind("<Button-1>", select_cb)
                
                # Delete handler
                def make_delete_handler(title=r_title, c_box=pack_card):
                    def delete_pack(e):
                        if messagebox.askyesno(tm.tr("delete_starred_pack_title"), tm.tr("delete_starred_pack_confirm").format(title=title)):
                            conn = sqlite3.connect(DB_PATH)
                            c = conn.cursor()
                            c.execute("DELETE FROM starred_packs WHERE title = ?", (title,))
                            conn.commit()
                            conn.close()
                            c_box.destroy()
                    return delete_pack
                    
                btn_delete.bind("<Button-1>", make_delete_handler())
                btn_delete.bind("<Enter>", lambda e, b=btn_delete: b.config(fg="#ef4444"))
                btn_delete.bind("<Leave>", lambda e, b=btn_delete: b.config(fg=TEXT_MUTED))
                
                # Hover feedback
                def make_hover_handlers(card=pack_card):
                    enter = lambda e: card.config(highlightbackground=color)
                    leave = lambda e: card.config(highlightbackground=BORDER_COLOR)
                    return enter, leave
                    
                h_enter, h_leave = make_hover_handlers()
                pack_card.bind("<Enter>", h_enter)
                pack_card.bind("<Leave>", h_leave)
                lbl_title.bind("<Enter>", h_enter)
                lbl_title.bind("<Leave>", h_leave)
                lbl_stars.bind("<Enter>", h_enter)
                lbl_stars.bind("<Leave>", h_leave)
                lbl_preview.bind("<Enter>", h_enter)
                lbl_preview.bind("<Leave>", h_leave)
                
        # Cancel Button
        cancel_btn = tk.Button(self, text=tm.tr("close"), bg=BG_CARD, fg=TEXT_WHITE, relief="flat", font=("Helvetica", 10, "bold"),
                               padx=15, pady=8, command=self.destroy)
        cancel_btn.pack(pady=15)
        cancel_btn.bind("<Enter>", lambda e: cancel_btn.config(bg="#ef4444", fg=TEXT_WHITE))
        cancel_btn.bind("<Leave>", lambda e: cancel_btn.config(bg=BG_CARD, fg=TEXT_WHITE))
        
        
        
    def select_pack(self, title, stars, items):
        selected = {
            "title": title,
            "stars": stars,
            "items": items
        }
        self.parent_tracker.add_starred_pack(selected, self.is_main)


class StarredPacksManagerDialog(tk.Toplevel):
    """
    A beautiful management window to view, edit, or delete starred tasks packs.
    """
    def __init__(self, parent):
        super().__init__(parent)
        self.title(tm.tr("manage_starred_packs"))
        self.configure(bg=BG_DARK)
        self.geometry("450x450")
        self.transient(parent)
        
        # Center relative to parent
        x = parent.winfo_rootx() + (parent.winfo_width() / 2) - 225
        y = parent.winfo_rooty() + (parent.winfo_height() / 2) - 225
        self.geometry(f"+{int(x)}+{int(y)}")
        
        # Top color accent border
        top_bar = tk.Frame(self, bg=ACCENT_PURPLE, height=4)
        top_bar.pack(fill="x", side="top")
        
        # Title Header
        header = tk.Frame(self, bg=BG_DARK)
        header.pack(fill="x", padx=25, pady=(20, 10))
        
        title_lbl = tk.Label(header, text=f"⭐ {tm.tr('starred_packs_manager')}", bg=BG_DARK, fg=ACCENT_PURPLE, font=("Helvetica", 13, "bold"))
        title_lbl.pack(side="left")
        
        # Scrollable list container
        self.scroll_frame = ScrollableFrame(self, bg=BG_DARK)
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.load_packs()
        
        # Bottom Close Button
        close_btn = tk.Button(self, text=tm.tr("close_manager"), bg=BG_CARD, fg=TEXT_WHITE, relief="flat", font=("Helvetica", 10, "bold"),
                               padx=20, pady=8, command=self.destroy)
        close_btn.pack(pady=15)
        close_btn.bind("<Enter>", lambda e: close_btn.config(bg=ACCENT_PURPLE, fg=BG_DARK))
        close_btn.bind("<Leave>", lambda e: close_btn.config(bg=BG_CARD, fg=TEXT_WHITE))
        
        self.wait_visibility()
        self.grab_set()
        
    def load_packs(self):
        # Clear scrollable frame
        for w in self.scroll_frame.scrollable_frame.winfo_children():
            w.destroy()
            
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT title, stars, items FROM starred_packs")
        rows = c.fetchall()
        conn.close()
        
        if not rows:
            lbl = tk.Label(self.scroll_frame.scrollable_frame, text=tm.tr("no_starred_packs_desc"), 
                            bg=BG_DARK, fg=TEXT_MUTED, font=("Helvetica", 10, "italic"), justify="center")
            lbl.pack(pady=70, fill="both", expand=True)
            return
            
        for r_title, r_stars, r_items_json in rows:
            items = json.loads(r_items_json)
            pack_card = tk.Frame(self.scroll_frame.scrollable_frame, bg=BG_CARD, bd=1, highlightbackground=BORDER_COLOR, highlightthickness=1)
            pack_card.pack(fill="x", pady=6, padx=5)
            
            card_header = tk.Frame(pack_card, bg=BG_CARD)
            card_header.pack(fill="x", padx=10, pady=(8, 2))
            
            lbl_title = tk.Label(card_header, text=r_title, bg=BG_CARD, fg=TEXT_WHITE, font=("Helvetica", 10, "bold"), anchor="w")
            lbl_title.pack(side="left")
            
            # Action Buttons Row
            actions = tk.Frame(card_header, bg=BG_CARD)
            actions.pack(side="right")
            
            # Delete button
            btn_delete = tk.Label(actions, text="❌", bg=BG_CARD, fg=TEXT_MUTED, font=("Helvetica", 9, "bold"), cursor="hand2")
            btn_delete.pack(side="right", padx=(8, 0))
            
            # Edit button
            btn_edit = tk.Label(actions, text=f"✏️ {tm.tr('edit_label')}", bg=BG_CARD, fg=ACCENT_CYAN, font=("Helvetica", 9, "bold"), cursor="hand2")
            btn_edit.pack(side="right", padx=5)
            
            lbl_stars = tk.Label(card_header, text=f"⭐ {r_stars:.1f}" if r_stars else "⭐ 0", bg=BG_CARD, fg=ACCENT_PURPLE, font=("Helvetica", 9, "bold"))
            lbl_stars.pack(side="right", padx=5)
            
            # Task list items preview text
            item_names = [i.get("name") for i in items]
            preview_text = ", ".join(item_names) if item_names else f"({tm.tr('empty_pack_label')})"
            if len(preview_text) > 50:
                preview_text = preview_text[:47] + "..."
                
            lbl_preview = tk.Label(pack_card, text=preview_text, bg=BG_CARD, fg=TEXT_MUTED, font=("Helvetica", 8), anchor="w")
            lbl_preview.pack(fill="x", padx=10, pady=(0, 8))
            
            # Handlers
            def make_delete_handler(title=r_title):
                return lambda e: self.delete_pack(title)
                
            def make_edit_handler(title=r_title, stars=r_stars, items_list=items):
                return lambda e: self.edit_pack(title, stars, items_list)
                
            btn_delete.bind("<Button-1>", make_delete_handler())
            btn_edit.bind("<Button-1>", make_edit_handler())
            
            # Hover styling
            btn_delete.bind("<Enter>", lambda e, b=btn_delete: b.config(fg="#ef4444"))
            btn_delete.bind("<Leave>", lambda e, b=btn_delete: b.config(fg=TEXT_MUTED))
            btn_edit.bind("<Enter>", lambda e, b=btn_edit: b.config(fg=TEXT_WHITE))
            btn_edit.bind("<Leave>", lambda e, b=btn_edit: b.config(fg=ACCENT_CYAN))
            
    def delete_pack(self, title):
        if messagebox.askyesno(tm.tr("delete_starred_pack_title"), tm.tr("delete_starred_pack_confirm").format(title=title)):
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("DELETE FROM starred_packs WHERE title = ?", (title,))
            conn.commit()
            conn.close()
            self.load_packs()
            
    def edit_pack(self, title, stars, items):
        self.grab_release() # Temporarily release manager grab to prevent X11/Linux nested grab freeze
        editor = EditStarredPackDialog(self, title, stars, items)
        self.wait_window(editor)
        self.grab_set() # Restore global grab on manager
        self.load_packs()


class EditStarredPackDialog(tk.Toplevel):
    """
    A dialog allowing users to rename the pack, adjust total stars, add/remove tasks, and set percentages.
    """
    def __init__(self, parent, title, stars, items):
        super().__init__(parent)
        self.title(f"{tm.tr('edit_starred_pack')} : {title}")
        self.configure(bg=BG_DARK)
        self.geometry("460x500")
        self.transient(parent)
        
        # Center relative to parent
        x = parent.winfo_rootx() + (parent.winfo_width() / 2) - 230
        y = parent.winfo_rooty() + (parent.winfo_height() / 2) - 250
        self.geometry(f"+{int(x)}+{int(y)}")
        
        self.orig_title = title
        self.items = list(items) # Make copy
        
        # Top Accent Border
        top_bar = tk.Frame(self, bg=ACCENT_CYAN, height=4)
        top_bar.pack(fill="x", side="top")
        
        # Header title
        header = tk.Frame(self, bg=BG_DARK)
        header.pack(fill="x", padx=25, pady=(20, 10))
        
        tk.Label(header, text=f"✏️ {tm.tr('edit_starred_pack')}", bg=BG_DARK, fg=ACCENT_CYAN, font=("Helvetica", 12, "bold")).pack(side="left")
        
        # Fields container
        fields = tk.Frame(self, bg=BG_DARK)
        fields.pack(fill="x", padx=25, pady=5)
        
        # 1. Pack Title
        tk.Label(fields, text=tm.tr("pack_title_label"), bg=BG_DARK, fg=TEXT_MUTED, font=("Helvetica", 9, "bold")).grid(row=0, column=0, sticky="w", pady=5)
        self.title_entry = tk.Entry(fields, bg=BG_CARD, fg=TEXT_WHITE, relief="flat", font=("Helvetica", 10), insertbackground=TEXT_WHITE)
        self.title_entry.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=5)
        self.title_entry.insert(0, title)
        
        # 2. Total Stars
        tk.Label(fields, text=tm.tr("total_stars_alloc_label"), bg=BG_DARK, fg=TEXT_MUTED, font=("Helvetica", 9, "bold")).grid(row=1, column=0, sticky="w", pady=5)
        self.stars_entry = tk.Entry(fields, bg=BG_CARD, fg=TEXT_WHITE, relief="flat", font=("Helvetica", 10), insertbackground=TEXT_WHITE)
        self.stars_entry.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=5)
        self.stars_entry.insert(0, str(stars))
        
        fields.grid_columnconfigure(1, weight=1)
        
        # Tasks List Label & Header Row
        tasks_header = tk.Frame(self, bg=BG_DARK)
        tasks_header.pack(fill="x", padx=25, pady=(15, 2))
        tk.Label(tasks_header, text=tm.tr("task_items_in_pack_label"), bg=BG_DARK, fg=TEXT_WHITE, font=("Helvetica", 10, "bold")).pack(side="left")
        
        # Add Item Button
        btn_add = tk.Button(tasks_header, text=tm.tr("add_task_item"), bg=BG_CARD, fg=ACCENT_CYAN, font=("Helvetica", 8, "bold"), relief="flat",
                            padx=8, pady=2, command=self.add_blank_item)
        btn_add.pack(side="right")
        btn_add.bind("<Enter>", lambda e: btn_add.config(bg=ACCENT_CYAN, fg=BG_DARK))
        btn_add.bind("<Leave>", lambda e: btn_add.config(bg=BG_CARD, fg=ACCENT_CYAN))
        
        # Scrollable Task Items list
        self.scroll_frame = ScrollableFrame(self, bg=BG_DARK)
        self.scroll_frame.pack(fill="both", expand=True, padx=25, pady=5)
        
        # Footer Action Buttons
        footer = tk.Frame(self, bg=BG_DARK)
        footer.pack(fill="x", pady=20)
        
        btn_save = tk.Button(footer, text=f"💾 {tm.tr('save_changes')}", bg=BG_CARD, fg=SUCCESS_GREEN, font=("Helvetica", 10, "bold"), relief="flat",
                             padx=15, pady=8, command=self.save_changes)
        btn_save.pack(side="left", padx=(30, 10), expand=True, fill="x")
        btn_save.bind("<Enter>", lambda e: btn_save.config(bg=SUCCESS_GREEN, fg=BG_DARK))
        btn_save.bind("<Leave>", lambda e: btn_save.config(bg=BG_CARD, fg=SUCCESS_GREEN))
        
        btn_cancel = tk.Button(footer, text=tm.tr("cancel"), bg=BG_CARD, fg=TEXT_WHITE, font=("Helvetica", 10, "bold"), relief="flat",
                               padx=15, pady=8, command=self.destroy)
        btn_cancel.pack(side="right", padx=(10, 30), expand=True, fill="x")
        btn_cancel.bind("<Enter>", lambda e: btn_cancel.config(bg="#ef4444", fg=TEXT_WHITE))
        btn_cancel.bind("<Leave>", lambda e: btn_cancel.config(bg=BG_CARD, fg=TEXT_WHITE))
        
        self.render_items()
        self.update_idletasks() # Force paint all child widgets immediately on mapping
        
        self.wait_visibility()
        self.grab_set()
        
    def render_items(self):
        for w in self.scroll_frame.scrollable_frame.winfo_children():
            w.destroy()
            
        for index, item in enumerate(self.items):
            row = tk.Frame(self.scroll_frame.scrollable_frame, bg=BG_CARD, pady=4, padx=5, bd=1, highlightbackground=BORDER_COLOR, highlightthickness=1)
            row.pack(fill="x", pady=3)
            
            # Entry for task name
            name_entry = tk.Entry(row, bg=BG_DARK, fg=TEXT_WHITE, font=("Helvetica", 10), relief="flat", insertbackground=TEXT_WHITE)
            name_entry.pack(side="left", fill="x", expand=True, padx=(5, 10))
            name_entry.insert(0, item.get("name", ""))
            
            # Label for %
            tk.Label(row, text=tm.tr("weight_label"), bg=BG_CARD, fg=TEXT_MUTED, font=("Helvetica", 8, "bold")).pack(side="left")
            
            # Entry for percentage weight
            pct_entry = tk.Entry(row, bg=BG_DARK, fg=TEXT_WHITE, font=("Helvetica", 10), width=6, relief="flat", justify="center", insertbackground=TEXT_WHITE)
            pct_entry.pack(side="left", padx=5)
            pct_entry.insert(0, str(item.get("percent", 0)))
            
            tk.Label(row, text="%", bg=BG_CARD, fg=TEXT_MUTED, font=("Helvetica", 10)).pack(side="left", padx=(0, 10))
            
            # Track values in bindings
            def make_binds(idx=index, ne=name_entry, pe=pct_entry):
                ne.bind("<FocusOut>", lambda e: self.update_item_field(idx, "name", ne.get()))
                pe.bind("<FocusOut>", lambda e: self.update_item_field(idx, "percent", pe.get()))
            make_binds()
            
            # Delete task item button
            btn_del = tk.Label(row, text="❌", bg=BG_CARD, fg=TEXT_MUTED, font=("Helvetica", 8, "bold"), cursor="hand2")
            btn_del.pack(side="right", padx=5)
            
            def make_del_handler(idx=index):
                return lambda e: self.delete_item(idx)
                
            btn_del.bind("<Button-1>", make_del_handler())
            btn_del.bind("<Enter>", lambda e, b=btn_del: b.config(fg="#ef4444"))
            btn_del.bind("<Leave>", lambda e, b=btn_del: b.config(fg=TEXT_MUTED))
            
    def update_item_field(self, idx, key, val):
        if idx < len(self.items):
            if key == "percent":
                try:
                    self.items[idx]["percent"] = float(val)
                except ValueError:
                    self.items[idx]["percent"] = 0.0
            else:
                self.items[idx]["name"] = val
                
    def delete_item(self, idx):
        if idx < len(self.items):
            self.items.pop(idx)
            self.render_items()
            
    def add_blank_item(self):
        self.items.append({"name": tm.tr("new_task_placeholder"), "percent": 0.0, "done": False})
        self.render_items()
        
    def save_changes(self):
        new_title = self.title_entry.get().strip()
        if not new_title:
            messagebox.showerror(tm.tr("error"), tm.tr("pack_title_empty"))
            return
            
        try:
            new_stars = float(self.stars_entry.get().strip())
        except ValueError:
            messagebox.showerror(tm.tr("error"), tm.tr("stars_alloc_numeric"))
            return
            
        clean_items = []
        for itm in self.items:
            name = itm.get("name", "").strip()
            if name:
                clean_items.append({
                    "name": name,
                    "percent": float(itm.get("percent", 0.0)),
                    "done": False
                })
                
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        try:
            if new_title != self.orig_title:
                c.execute("DELETE FROM starred_packs WHERE title = ?", (self.orig_title,))
                
            c.execute("""
                INSERT OR REPLACE INTO starred_packs (title, stars, items)
                VALUES (?, ?, ?)
            """, (new_title, new_stars, json.dumps(clean_items)))
            conn.commit()
            self.destroy()
        except Exception as e:
            messagebox.showerror(tm.tr("error"), f"{tm.tr('failed_save_changes')}{e}")
        finally:
            conn.close()


class MissionApp(tk.Tk):
    """
    Main Application class that manages routes (Start Screen, CalendarScreen, Daily Tracker).
    Connects database settings on launch.
    """
    def __init__(self):
        super().__init__()
        self.title("Mission Ui")
        self.geometry("1200x800")
        self.configure(bg=BG_DARK)
        self.minsize(1024, 700)
        
        # Init DB and migrate legacy JSONs
        init_db()
        
        self.current_frame = None
        self.running_ai_jobs = {} # Key: (date_str, job_type) -> {"status": "running"|"completed"|"error", "result": str, "error": str}
        
        # Quran Bg Player State
        self.bg_music_active = False
        self.bg_music_paused = False
        self.bg_current_surah = None
        self.bg_start_time_offset = 0.0
        self.bg_total_duration = 0.0
        self.bg_play_mode = "next"  # "single", "loop", "next", "shuffle"
        self.mini_player = None     # Reference to Toplevel mini player
        
        self.protocol("WM_DELETE_WINDOW", self.on_app_close)

        self.show_start_screen()

    def on_app_close(self):
        if hasattr(self, 'current_frame') and self.current_frame is not None:
            if hasattr(self.current_frame, 'save_diary_data'):
                try:
                    self.current_frame.save_diary_data()
                except Exception as e:
                    print(f"Error auto-saving diary on app close: {e}")
            elif hasattr(self.current_frame, 'save_day_data'):
                try:
                    self.current_frame.save_day_data()
                except Exception as e:
                    print(f"Error auto-saving day data on app close: {e}")
        self.destroy()
        
    def show_frame(self, frame_class, *args, **kwargs):
        if self.current_frame is not None:
            self.current_frame.destroy()
        # Set root background to match current theme
        self.configure(bg=BG_DARK)
        self.current_frame = frame_class(self, *args, **kwargs)
        self.current_frame.pack(fill="both", expand=True)

    def show_start_screen(self, show_tools=False):
        self.show_frame(StartScreen, show_tools=show_tools)
        
    def show_calendar_screen(self):
        self.show_frame(CalendarScreen)
        
    def show_graphs_screen(self):
        from graphs_screen import GraphsScreen
        self.show_frame(GraphsScreen)

    def refresh_graphs_if_open(self):
        from graphs_screen import GraphsScreen
        if isinstance(self.current_frame, GraphsScreen):
            self.current_frame.refresh()
            
    def show_settings_screen(self):
        self.show_frame(SettingsScreen)

    def show_about_screen(self):
        self.show_frame(AboutScreen)
        
    def show_daily_tracker(self, date_str, blueprint_data=None, return_screen=None):
        self.show_frame(DailyTrackerScreen, date_str=date_str, blueprint_data=blueprint_data, return_screen=return_screen)

    def show_diary_screen(self, date_str=None, return_screen=None):
        self.show_frame(DailyDiaryScreen, date_str=date_str, return_screen=return_screen)

    def show_export_dialog(self, date_str, day_data, export_type="both"):
        diag = FormatSelectionDialog(self, date_str)
        self.wait_window(diag)
        if not diag.result:
            return
        file_format = diag.result
        
        if export_type == "memo_only":
            self.export_day_to_file(date_str, {}, file_format, export_type="memo_only")
            return

        default_ai = day_data.get("ai_comment") or day_data.get("small_advice") or ""
        chosen_comment = None
        
        while chosen_comment is None:
            opt_diag = CommentOptionsDialog(self, default_ai)
            self.wait_window(opt_diag)
            
            if opt_diag.result_type is None:
                return # Cancelled entire flow
                
            if opt_diag.result_type == "ai":
                chosen_comment = default_ai
            elif opt_diag.result_type == "custom":
                write_diag = WriteCommentDialog(self, "")
                self.wait_window(write_diag)
                if write_diag.result is None:
                    # Loop back
                    continue
                chosen_comment = write_diag.result
            elif opt_diag.result_type == "blank":
                chosen_comment = ""
            
        export_data = day_data.copy()
        export_data["ai_comment"] = chosen_comment
        if "small_advice" in export_data:
            export_data["small_advice"] = ""
            
        self.export_day_to_file(date_str, export_data, file_format, export_type)

    def export_day_to_file(self, date_str, day_data, file_format, export_type="both"):
        from tkinter import filedialog
        import json as _json
        
        file_types = [("PNG Image", "*.png")] if file_format == "png" else [("PDF Document", "*.pdf")]
        default_ext = f".{file_format}"
        
        # Load last-used export directory
        prefs_path = os.path.join(APP_DIR, "data", "prefs.json")
        last_dir = os.path.expanduser("~")
        try:
            if os.path.exists(prefs_path):
                with open(prefs_path, "r", encoding="utf-8") as _f:
                    prefs = _json.load(_f)
                last_dir = prefs.get("last_export_dir", last_dir)
        except Exception:
            pass
        
        # Format filename as DD-MM (e.g. "15-08.png" or "15-08_memo.png")
        try:
            _dt = datetime.date.fromisoformat(date_str)
            suffix = "_memo" if export_type == "memo_only" else ""
            short_name = f"{_dt.day:02d}-{_dt.month:02d}{suffix}{default_ext}"
        except Exception:
            suffix = "_memo" if export_type == "memo_only" else ""
            short_name = f"{date_str}{suffix}{default_ext}"
        
        # Check if memo exists when memo_only is selected
        diary_data = None
        if export_type in ("memo_only", "both"):
            try:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("SELECT content FROM daily_diary WHERE date = ?", (date_str,))
                row = c.fetchone()
                conn.close()
                if row:
                    diary_data = _json.loads(row[0])
            except Exception as e:
                print(f"Error reading diary: {e}")
                
        has_memo = diary_data and diary_data.get("text", "").strip()
        
        if export_type == "memo_only" and not has_memo:
            messagebox.showwarning(tm.tr("empty") if hasattr(tm, "tr") else "Empty", 
                                   "No memo found for this day to download.")
            return

        filename = filedialog.asksaveasfilename(
            parent=self,
            title=f"{tm.tr('save_daily_paper')} {file_format.upper()}",
            initialdir=last_dir,
            initialfile=short_name,
            defaultextension=default_ext,
            filetypes=file_types
        )
        
        if not filename:
            return
        
        # Save the chosen directory for next time
        try:
            chosen_dir = os.path.dirname(filename)
            prefs = {}
            if os.path.exists(prefs_path):
                with open(prefs_path, "r", encoding="utf-8") as _f:
                    prefs = _json.load(_f)
            prefs["last_export_dir"] = chosen_dir
            with open(prefs_path, "w", encoding="utf-8") as _f:
                _json.dump(prefs, _f)
        except Exception:
            pass
            
        if tm._current_language == "Arabic":
            try:
                import arabic_reshaper
                from bidi.algorithm import get_display
            except ImportError:
                import sys
                import subprocess
                try:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", "arabic-reshaper", "python-bidi"])
                except Exception as err:
                    messagebox.showerror("Dependencies Missing", 
                                         f"Could not automatically install Arabic shaping libraries: {err}\n\n"
                                         "Please manually run:\npip install arabic-reshaper python-bidi")
        try:
            from export_helper import generate_paper_image, generate_memo_page_images
            
            # Generate tasks paper if needed
            img = None
            if export_type in ("tasks_only", "both"):
                img = generate_paper_image(date_str, day_data, APP_DIR)
                
            # Determine actual has_memo usage based on export_type
            use_memo = has_memo and (export_type in ("memo_only", "both"))
            
            if file_format == "png":
                if export_type == "memo_only":
                    memo_imgs = generate_memo_page_images(date_str, diary_data, APP_DIR)
                    if len(memo_imgs) == 1:
                        memo_imgs[0].save(filename, "PNG")
                    else:
                        base, ext = os.path.splitext(filename)
                        for p_idx, p_img in enumerate(memo_imgs):
                            p_img.save(f"{base}_page_{p_idx + 1}{ext}", "PNG")
                else: # tasks_only or both
                    img.save(filename, "PNG")
                    if use_memo:
                        memo_imgs = generate_memo_page_images(date_str, diary_data, APP_DIR)
                        base, ext = os.path.splitext(filename)
                        if len(memo_imgs) == 1:
                            memo_imgs[0].save(f"{base}_memo{ext}", "PNG")
                        else:
                            for p_idx, p_img in enumerate(memo_imgs):
                                p_img.save(f"{base}_memo_page_{p_idx + 1}{ext}", "PNG")
                                
            elif file_format == "pdf":
                if export_type == "memo_only":
                    memo_imgs = generate_memo_page_images(date_str, diary_data, APP_DIR)
                    if len(memo_imgs) == 1:
                        memo_imgs[0].save(filename, "PDF", resolution=150.0)
                    else:
                        memo_imgs[0].save(filename, "PDF", save_all=True, append_images=memo_imgs[1:], resolution=150.0)
                elif export_type == "tasks_only":
                    img.save(filename, "PDF", resolution=150.0)
                else: # both
                    if use_memo:
                        memo_imgs = generate_memo_page_images(date_str, diary_data, APP_DIR)
                        img.save(filename, "PDF", save_all=True, append_images=memo_imgs, resolution=150.0)
                    else:
                        img.save(filename, "PDF", resolution=150.0)
                
            messagebox.showinfo(tm.tr("export_success"), f"{tm.tr('export_success_msg')}{filename}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror(tm.tr("export_error"), f"{tm.tr('export_error_msg')}{e}")

    def start_ai_job(self, date_str, job_type, model_path, today_tasks_text="", prompt=""):
        job_key = (date_str, job_type)
        if job_key in self.running_ai_jobs and self.running_ai_jobs[job_key]["status"] == "running":
            return
            
        self.running_ai_jobs[job_key] = {
            "status": "running",
            "result": None,
            "error": None
        }
        
        import threading
        threading.Thread(
            target=self._run_ai_job_thread,
            args=(date_str, job_type, model_path, today_tasks_text, prompt),
            daemon=True
        ).start()

    def _run_ai_job_thread(self, date_str, job_type, model_path, today_tasks_text, prompt):
        try:
            from llama_cpp import Llama
            llm = Llama(
                model_path=model_path,
                n_ctx=4096,
                verbose=False,
                seed=-1
            )
            
            if job_type in ("small_advice", "deep_advice"):
                import sqlite3
                import json
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                
                # Fetch target day tasks to filter historical logs
                c.execute("SELECT main_tasks, side_tasks FROM days WHERE date = ?", (date_str,))
                target_day_row = c.fetchone()
                active_group_titles = set()
                if target_day_row:
                    target_main = json.loads(target_day_row[0]) if target_day_row[0] else []
                    target_side = json.loads(target_day_row[1]) if target_day_row[1] else []
                    for g in target_main + target_side:
                        title = g.get("title")
                        if title:
                            active_group_titles.add(title.strip().lower())
                
                c.execute("SELECT date, main_tasks, side_tasks, ai_comment FROM days ORDER BY date DESC LIMIT 14")
                rows = c.fetchall()
                conn.close()
                
                num_days = len(rows)
                
                history_text = ""
                if tm._current_language == "French":
                    days_word = "jour" if num_days == 1 else "jours"
                    for r_date, r_main, r_side, r_ai in reversed(rows):
                        main_tasks = json.loads(r_main) if r_main else []
                        side_tasks = json.loads(r_side) if r_side else []
                        
                        tot = 0
                        done = 0
                        group_stats = []
                        pending_names = []
                        for g in main_tasks + side_tasks:
                            g_title = g.get("title")
                            if not g_title or g_title.strip().lower() not in active_group_titles:
                                continue
                            g_items = g.get("items", [])
                            if g_items:
                                g_tot = len(g_items)
                                g_done = sum(1 for i in g_items if i.get("done"))
                                for i in g_items:
                                    if not i.get("done"):
                                        pending_names.append(f"{g_title} : {i.get('name')}")
                            else:
                                g_tot = 1
                                g_done = 1 if g.get("done", False) else 0
                                if not g_done:
                                    pending_names.append(f"{g_title} : {g_title}")
                                    
                            tot += g_tot
                            done += g_done
                            group_stats.append(f"'{g_title}' : {g_done} sur {g_tot} complétés")
                            
                        # Only add history for days that actually had matching tasks
                        if tot > 0:
                            history_text += f"Date : {r_date} | Global : {done} sur {tot} tâches complétées. Détail : {', '.join(group_stats)}. Commentaire IA : {r_ai or 'Aucun'}\n"
                            if pending_names:
                                history_text += f"  - Éléments en attente : {', '.join(pending_names)}\n"
                elif tm._current_language == "Arabic":
                    days_word = "يوم" if num_days == 1 else "أيام"
                    for r_date, r_main, r_side, r_ai in reversed(rows):
                        main_tasks = json.loads(r_main) if r_main else []
                        side_tasks = json.loads(r_side) if r_side else []
                        
                        tot = 0
                        done = 0
                        group_stats = []
                        pending_names = []
                        for g in main_tasks + side_tasks:
                            g_title = g.get("title")
                            if not g_title or g_title.strip().lower() not in active_group_titles:
                                continue
                            g_items = g.get("items", [])
                            if g_items:
                                g_tot = len(g_items)
                                g_done = sum(1 for i in g_items if i.get("done"))
                                for i in g_items:
                                    if not i.get("done"):
                                        pending_names.append(f"{g_title}: {i.get('name')}")
                            else:
                                g_tot = 1
                                g_done = 1 if g.get("done", False) else 0
                                if not g_done:
                                    pending_names.append(f"{g_title}: {g_title}")
                                    
                            tot += g_tot
                            done += g_done
                            group_stats.append(f"'{g_title}': تم إكمال {g_done} من أصل {g_tot}")
                            
                        if tot > 0:
                            history_text += f"التاريخ: {r_date} | إجمالي: تم إكمال {done} من أصل {tot} مهمة. تفصيل المجموعات: {', '.join(group_stats)}. تعليق الذكاء الاصطناعي: {r_ai or 'لا يوجد'}\n"
                            if pending_names:
                                history_text += f"  - العناصر المعلقة: {', '.join(pending_names)}\n"
                else:
                    days_word = "day" if num_days == 1 else "days"
                    for r_date, r_main, r_side, r_ai in reversed(rows):
                        main_tasks = json.loads(r_main) if r_main else []
                        side_tasks = json.loads(r_side) if r_side else []
                        
                        tot = 0
                        done = 0
                        group_stats = []
                        pending_names = []
                        for g in main_tasks + side_tasks:
                            g_title = g.get("title")
                            if not g_title or g_title.strip().lower() not in active_group_titles:
                                continue
                            g_items = g.get("items", [])
                            if g_items:
                                g_tot = len(g_items)
                                g_done = sum(1 for i in g_items if i.get("done"))
                                for i in g_items:
                                    if not i.get("done"):
                                        pending_names.append(f"{g_title}: {i.get('name')}")
                            else:
                                g_tot = 1
                                g_done = 1 if g.get("done", False) else 0
                                if not g_done:
                                    pending_names.append(f"{g_title}: {g_title}")
                                    
                            tot += g_tot
                            done += g_done
                            group_stats.append(f"'{g_title}': {g_done} out of {g_tot} completed")
                            
                        if tot > 0:
                            history_text += f"Date: {r_date} | Overall: {done} out of {tot} tasks completed. Group breakdown: {', '.join(group_stats)}. AI Comment: {r_ai or 'None'}\n"
                            if pending_names:
                                history_text += f"  - Pending Items: {', '.join(pending_names)}\n"
                
                advice_type = "small" if job_type == "small_advice" else "deep"
                day_constraint = ""
                if num_days == 1:
                    if tm._current_language == "French":
                        day_constraint = (
                            "\nCONTRAINTE CRITIQUE : L'utilisateur n'a qu'UN SEUL jour d'historique dans la base de données. "
                            "C'est son tout premier jour d'utilisation. Ne fais pas référence à '14 jours d'historique', "
                            "et analyse ses performances uniquement sur la base de cette seule journée d'aujourd'hui."
                        )
                    elif tm._current_language == "Arabic":
                        day_constraint = (
                            "\nقيد حرج: سجل المستخدم يحتوي على يوم واحد فقط في قاعدة البيانات. "
                            "هذا هو يومهم الأول في استخدام التطبيق. لا تشر إلى 'سجل الـ 14 يومًا'، "
                            "وقم بتحليل أدائهم بناءً على سجل اليوم الواحد فقط."
                        )
                    else:
                        day_constraint = (
                            "\nCRITICAL CONSTRAINT: The user has ONLY 1 day of history logged in the database. "
                            "This is their first day using the app. Do NOT refer to '14 days of history', do not assume they have any historical average/patterns, "
                            "and analyze their performance strictly based on today's single day of logs."
                        )

                if tm._current_language == "French":
                    if advice_type == "small":
                        system_prompt = (
                            "MANDATORY: YOU MUST WRITE YOUR RESPONSE ONLY IN FRENCH. RÉPONDEZ UNIQUEMENT EN FRANÇAIS.\n\n"
                            f"Tu es un analyste de données de productivité strict et factuel. Lis toutes les activités de la journée sélectionnée dans les journaux d'aujourd'hui et suggère uniquement ce que l'utilisateur peut faire pour s'améliorer avec précision. "
                            "En exactement 2 phrases, formule des recommandations concrètes et des ajustements d'horaires spécifiques basés uniquement sur ces données. "
                            "RÈGLES CRITIQUES : Ne suggère ni ne mentionne aucun groupe de tâches ou élément qui n'est pas présent dans les JOURNAUX D'AUJOURD'HUI. Limite le conseil à moins de 50 mots. "
                            f"LANGUE : Rédige obligatoirement ta réponse en français."
                            f"{day_constraint}"
                        )
                    else:
                        system_prompt = (
                            "MANDATORY: YOU MUST WRITE YOUR RESPONSE ONLY IN FRENCH. RÉPONDEZ UNIQUEMENT EN FRANÇAIS.\n\n"
                            "Tu es un analyste de données de productivité strict et factuel. "
                            f"Analyse l'historique de l'utilisateur sur {num_days}-{days_word} et le statut d'aujourd'hui. "
                            "Fournis une analyse hautement objective, professionnelle et strictement factuelle de ses performances. "
                            "N'utilise pas de langage superflu ou de clichés de coaching. "
                            "Ne crée pas de relations inventées entre les tâches.\n\n"
                            f"{day_constraint}\n\n"
                            "Structure ta réponse dans les sections suivantes :\n\n"
                            "1. RÉSUMÉ STATISTIQUE DES PERFORMANCES :\n"
                            f"Affiche les statistiques globales de complétion des groupes de tâches calculées à partir des journaux de {num_days}-{days_word}. CRITIQUE : Tu dois UNIQUEMENT utiliser les taux de complétion exacts déjà pré-calculés dans les journaux. Ne fais aucun calcul de division ou de pourcentage toi-même. N'affiche que les groupes de tâches présents dans les JOURNAUX D'AUJOURD'HUI.\n\n"
                            "2. DIAGNOSTIC LOGIQUE DES GOULOTS D'ÉTRANGLEMENT :\n"
                            "Identifie les modèles récurrents de tâches ignorées basés strictement sur l'historique. S'il y a moins de 5 jours d'historique, indique qu'il n'y a pas assez de données historiques pour établir des modèles récurrents, et concentre ton diagnostic uniquement sur les tâches actives d'aujourd'hui. CRITIQUE : Ne mentionne aucune tâche absente d'aujourd'hui.\n\n"
                            "3. ÉTAPES D'ACTION DIRECTES POUR DEMAIN :\n"
                            "Suggère d'autres activités à faire pour compléter la routine actuelle de l'utilisateur et explique comment ces nouvelles activités amélioreront ses activités réelles enregistrées aujourd'hui.\n\n"
                            "LANGUE : Tu dois obligatoirement rédiger ta réponse en français et ne jamais utiliser l'anglais."
                        )
                elif tm._current_language == "Arabic":
                    if advice_type == "small":
                        system_prompt = (
                            "MANDATORY: YOU MUST WRITE YOUR RESPONSE ONLY IN ARABIC. يجب عليك كتابة الرد باللغة العربية فقط. لا تستخدم الإنجليزية أبداً.\n\n"
                            f"أنت محلل بيانات إنتاجية صارم وواقعي. راجع جميع الأنشطة والمهام لليوم المحدد في سجلات اليوم واقترح فقط وبدقة ما يمكن للمستخدم فعله لتحسين أدائه. "
                            "في جملتين بالضبط، حدد نصيحة عملية وتعديلًا واقعيًا للجدول الزمني. "
                            "قواعد صارمة: لا تقترح أو تذكر أي مجموعات مهام أو عناصر غير موجودة في سجلات اليوم. اجعلها أقل من 50 كلمة. "
                            "اللغة: يجب أن تكتب ردك باللغة العربية فقط وبشكل صحيح.\n\n"
                            f"{day_constraint}"
                        )
                    else:
                        system_prompt = (
                            "MANDATORY: YOU MUST WRITE YOUR RESPONSE ONLY IN ARABIC. يجب عليك كتابة الرد باللغة العربية فقط. لا تستخدم الإنجليزية أبداً.\n\n"
                            "أنت محلل بيانات إنتاجية صارم وواقعي. "
                            f"قم بتحليل سجل المستخدم المكون من {num_days} {days_word} وحالة اليوم. "
                            "قدم تحليلاً موضوعيًا ومهنيًا وواقعيًا للغاية لأدائهم. "
                            "لا تستخدم لغة إنشائية أو كليشيهات تدريبية أو تفترض مشاعر/حالات شخصية. "
                            "لا تخترع علاقات بين المهام.\n\n"
                            f"{day_constraint}\n\n"
                            "نظم مخرجاتك في الأقسام التالية:\n\n"
                            "1. ملخص الأداء الإحصائي:\n"
                            f"اذكر إحصائيات الإكمال الإجمالية ومعدلات إكمال مجموعات المهام المحسوبة من سجل {num_days} {days_word}. هام: يجب عليك فقط استخدام معدلات وأرقام الإكمال الدقيقة المحسوبة مسبقًا في السجلات. لا تقم بأي عمليات حسابية بنفسك. أدرج فقط مجموعات المهام الموجودة في سجلات اليوم.\n\n"
                            "2. تشخيص عقبات الأداء المنطقية:\n"
                            "حدد الأنماط المتكررة الفعلية للمهام التي تم تخطيها استنادًا إلى السجل فقط. إذا كان هناك أقل من 5 أيام من السجل، فاذكر أنه لا توجد بيانات تاريخية كافية لتحديد أنماط متكررة بعد، وركز تشخيصك بدقة على مهام اليوم النشطة. هام: لا تشخص أو تذكر أي مجموعات مهام أو عناصر غير موجودة في سجلات اليوم.\n\n"
                            "3. خطوات عملية مباشرة للغد:\n"
                            "اقترح المزيد من الأنشطة الإضافية للقيام بها، واشرح كيف يمكن لهذه الأنشطة الجديدة أن تحسن وتدعم أنشطتك الحالية المسجلة اليوم.\n\n"
                            "اللغة: يجب أن تكتب ردك باللغة العربية فقط وبشكل صحيح."
                        )
                else:
                    if advice_type == "small":
                        system_prompt = (
                            f"You are a strict, factual productivity data analyst. Read all activities of the selected day in today's logs and suggest only what the user can do better with accuracy. "
                            "In exactly 2 sentences, provide concrete, action-oriented recommendations based strictly on these tasks. "
                            "CRITICAL RULES: Do NOT suggest or mention any task groups or items that are not present in TODAY'S LOGS. Rely ONLY on the provided activities. Keep it under 50 words. "
                            f"LANGUAGE: {tm.tr('ai_language_prompt')} "
                            f"{day_constraint}"
                        )
                    else:
                        system_prompt = (
                            "You are a strict, factual productivity data analyst. "
                            f"Analyze the user's {num_days}-{days_word} history and today's status. "
                            "Provide a highly objective, professional, and strictly factual analysis of their performance. "
                            "Do NOT use fluffy language, coaching clichés, or assume personal feelings/states. "
                            "Do NOT invent relationships between tasks.\n\n"
                            f"{day_constraint}\n\n"
                            "Structure your output into the following sections:\n\n"
                            "1. STATISTICAL PERFORMANCE SUMMARY:\n"
                            f"List overall completion statistics and task group completion rates calculated from the {num_days}-{days_word} log data. CRITICAL: You must ONLY use the exact completion rates and numbers pre-calculated in the logs. Do NOT perform any math or division yourself. If a task group has 1 out of 4 completed, write '1 out of 4 completed', do NOT make up other numbers. Only list task groups that are present in TODAY'S LOGS.\n\n"
                            "2. LOGICAL BOTTLENECK DIAGNOSTICS:\n"
                            "Identify actual recurring patterns of skipped tasks based strictly on the history. If there are fewer than 5 days of history in the logs, state that there is not enough historical data to establish recurring patterns yet, and focus your diagnostics strictly on today's active tasks. CRITICAL: Do NOT diagnose or mention any task groups or items that are not present in TODAY'S LOGS. If a task was present in the history but is absent from today's logs, ignore it completely.\n\n"
                            "3. DIRECT ACTIONABLE STEPS FOR TOMORROW:\n"
                            "Suggest more activities to do that can complement the user's existing routine, and explain how these new activities will improve their actual activities logged today.\n\n"
                            f"LANGUAGE: {tm.tr('ai_language_prompt')}"
                        )
                
                full_prompt = (
                    f"<start_of_turn>user\n"
                    f"System Instruction: {system_prompt}\n\n"
                    f"=== HISTORICAL LOGS ===\n{history_text}\n"
                    f"=== TODAY'S LOGS ===\n{today_tasks_text}\n"
                    f"<end_of_turn>\n<start_of_turn>model\n"
                )
                
                response = llm(
                    full_prompt,
                    max_tokens=1000 if advice_type == "deep" else 200,
                    temperature=0.0, # Complete determinism to eliminate hallucinations
                    repeat_penalty=1.15,
                    top_p=0.9,
                    stop=["<end_of_turn>", "<|im_end|>"]
                )
                result_text = response["choices"][0]["text"].strip()
                
            else:
                response = llm(
                    prompt,
                    max_tokens=256,
                    temperature=0.0, # Complete determinism to eliminate hallucinations
                    repeat_penalty=1.1,
                    top_p=0.9,
                    stop=["<end_of_turn>", "<|im_end|>"]
                )
                result_text = response["choices"][0]["text"].strip()
                
            # STRICT HALLUCINATION FILTER AND PROGRAMMATIC FALLBACK FOR ALL JOBS
            text_lower = result_text.lower()
            has_placeholders = any(x in text_lower for x in ["task a", "task b", "task c", "group 1", "group 2", "group 3"])
            
            import sqlite3
            import json
            conn_v = sqlite3.connect(DB_PATH)
            c_v = conn_v.cursor()
            c_v.execute("SELECT main_tasks, side_tasks FROM days WHERE date = ?", (date_str,))
            row_v = c_v.fetchone()
            conn_v.close()
            
            total_items = 0
            done_items = 0
            completed_groups = []
            pending_groups = []
            pending_items = []
            valid_today_names = set()
            
            if row_v:
                main_tasks = json.loads(row_v[0]) if row_v[0] else []
                side_tasks = json.loads(row_v[1]) if row_v[1] else []
                for g in main_tasks + side_tasks:
                    title = g.get("title")
                    if title:
                        valid_today_names.add(title.strip().lower())
                    items = g.get("items", [])
                    if items:
                        total_items += len(items)
                        done_g = sum(1 for i in items if i.get("done"))
                        done_items += done_g
                        if done_g == len(items):
                            completed_groups.append(g.get("title"))
                        else:
                            pending_groups.append(g.get("title"))
                            for i in items:
                                if not i.get("done"):
                                    pending_items.append(i.get("name"))
                                    valid_today_names.add(i.get("name").strip().lower())
                    else:
                        total_items += 1
                        is_done = g.get("done", False)
                        done_items += 1 if is_done else 0
                        if is_done:
                            completed_groups.append(g.get("title"))
                        else:
                            pending_groups.append(g.get("title"))
                            pending_items.append(g.get("title"))
                                    
            has_math_hallucination = False
            if done_items > 0 and ("0.0%" in result_text or "0%" in result_text):
                has_math_hallucination = True
                
            # Gather historical task names not present today to detect old task hallucinations
            historical_only_names = set()
            try:
                conn_h = sqlite3.connect(DB_PATH)
                c_h = conn_h.cursor()
                c_h.execute("SELECT main_tasks, side_tasks FROM days WHERE date != ?", (date_str,))
                h_rows = c_h.fetchall()
                conn_h.close()
                for h_row in h_rows:
                    h_main = json.loads(h_row[0]) if h_row[0] else []
                    h_side = json.loads(h_row[1]) if h_row[1] else []
                    for g in h_main + h_side:
                        h_title = g.get("title")
                        if h_title:
                            h_title_clean = h_title.strip().lower()
                            if h_title_clean not in valid_today_names:
                                historical_only_names.add(h_title_clean)
                        for item in g.get("items", []):
                            h_name = item.get("name")
                            if h_name:
                                h_name_clean = h_name.strip().lower()
                                if h_name_clean not in valid_today_names:
                                    historical_only_names.add(h_name_clean)
            except Exception as e:
                print(f"Error loading historical tasks for validation: {e}")
                
            mentions_old_task = False
            import re
            for name in historical_only_names:
                if not name.strip():
                    continue
                escaped_name = re.escape(name)
                pattern = r'\b' + escaped_name + r'\b'
                if re.search(pattern, text_lower):
                    mentions_old_task = True
                    break

            # Math validation - find all percentages in LLM output and ensure they are valid for today
            found_pcts = re.findall(r'(\d+(?:\.\d+)?)\s*%', result_text)
            valid_pcts = set()
            if total_items > 0:
                overall_pct = (done_items / total_items) * 100.0
                valid_pcts.add(round(overall_pct, 1))
                valid_pcts.add(round(overall_pct, 0))
                valid_pcts.add(int(overall_pct))
            
            if row_v:
                main_tasks = json.loads(row_v[0]) if row_v[0] else []
                side_tasks = json.loads(row_v[1]) if row_v[1] else []
                for g in main_tasks + side_tasks:
                    items = g.get("items", [])
                    if items:
                        gp = (sum(1 for i in items if i.get("done")) / len(items)) * 100.0
                        valid_pcts.add(round(gp, 1))
                        valid_pcts.add(round(gp, 0))
                        valid_pcts.add(int(gp))
                    else:
                        is_done = g.get("done", False)
                        gp = 100.0 if is_done else 0.0
                        valid_pcts.add(gp)
                        valid_pcts.add(int(gp))
                        
            has_incorrect_percentage = False
            for pct_str in found_pcts:
                try:
                    pct_val = float(pct_str)
                    if not any(abs(pct_val - vp) < 0.1 for vp in valid_pcts):
                        has_incorrect_percentage = True
                        break
                except ValueError:
                    pass
                
            is_arabic = (tm._current_language == "Arabic")
            def contains_arabic(text):
                return any('\u0600' <= char <= '\u06FF' or '\u0750' <= char <= '\u077F' or '\u08A0' <= char <= '\u08FF' for char in text)
            
            has_language_hallucination = is_arabic and not contains_arabic(result_text)
            
            has_bad_structure = False
            if job_type == "deep_advice":
                has_headers = (
                    ("1." in result_text and "2." in result_text and "3." in result_text) or
                    ("ملخص" in result_text and "تشخيص" in result_text and "خطوات" in result_text)
                )
                if not has_headers:
                    has_bad_structure = True
            
            has_factual_error = False
            if job_type == "comment":
                # Check for factual contradictions in the commentary
                text_lower = result_text.lower()
                sentences = re.split(r'[.!?•\n]', text_lower)
                
                pending_keywords = ["pending", "remain", "incomplete", "not completed", "en attente", "restent", "معلقة", "ظلت معلقة", "غير مكتمل"]
                completed_keywords = ["completed", "done", "finished", "executed", "complété", "faits", "مكتمل", "اكتملت", "نجاح", "كامل"]
                
                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence:
                        continue
                        
                    # Split sentence into clauses to check specific assertions
                    clauses = re.split(r'[,;]|\bwhile\b|\bwhereas\b|\bbut\b|\balthough\b|\bmais\b|\bبينما\b|\bلكن\b', sentence)
                    for clause in clauses:
                        clause = clause.strip()
                        if not clause:
                            continue
                            
                        # Check completed groups
                        for cg in completed_groups:
                            cg_lower = cg.lower()
                            if cg_lower in clause:
                                has_pending = any(pw in clause for pw in pending_keywords)
                                has_completed = any(cw in clause for cw in completed_keywords)
                                if has_pending and not has_completed:
                                    has_factual_error = True
                                    break
                                    
                        if has_factual_error:
                            break
                            
                        # Check pending groups
                        for pg in pending_groups:
                            pg_lower = pg.lower()
                            if pg_lower in clause:
                                has_pending = any(pw in clause for pw in pending_keywords)
                                has_completed = any(cw in clause for cw in completed_keywords)
                                if has_completed and not has_pending:
                                    has_factual_error = True
                                    break
                                    
                        if has_factual_error:
                            break
                            
                        # Check pending items
                        for pi in pending_items:
                            pi_lower = pi.lower()
                            if pi_lower in clause:
                                has_pending = any(pw in clause for pw in pending_keywords)
                                has_completed = any(cw in clause for cw in completed_keywords)
                                if has_completed and not has_pending:
                                    has_factual_error = True
                                    break
                                    
                        if has_factual_error:
                            break
                    if has_factual_error:
                        break
            
            if (has_placeholders or 
                has_math_hallucination or 
                has_incorrect_percentage or 
                mentions_old_task or 
                has_language_hallucination or 
                has_bad_structure or 
                has_factual_error or 
                len(result_text.strip()) < 10):
                import datetime
                today_str = datetime.date.today().isoformat()
                is_today = (date_str == today_str)
                _lang = tm._current_language
                
                if job_type == "comment":
                    if _lang == "French":
                        tense_completed = "a complété" if is_today else "a complété"
                        tense_pending = "sont en attente" if is_today else "étaient en attente"
                        if total_items == 0:
                            s1 = f"Aucune tâche n'est enregistrée pour le {date_str}."
                        else:
                            pct = (done_items / total_items) * 100.0
                            s1 = f"L'utilisateur {tense_completed} {done_items} sur {total_items} tâches, atteignant un taux d'achèvement global de {pct:.1f}%."
                        if completed_groups:
                            s2 = f"Les groupes de tâches {', '.join(completed_groups)} ont été entièrement complétés."
                        else:
                            s2 = "Aucun groupe de tâches n'a été entièrement complété."
                        if pending_items:
                            if len(pending_items) > 3:
                                s3 = f"Les éléments {', '.join(pending_items[:3])} et {len(pending_items)-3} autres {tense_pending}."
                            else:
                                s3 = f"Les éléments {', '.join(pending_items)} {tense_pending}."
                        else:
                            s3 = "Tous les éléments de tâches sont complétés."
                    elif _lang == "Arabic":
                        if total_items == 0:
                            s1 = f"لا توجد مهام مسجلة ليوم {date_str}."
                        else:
                            pct = (done_items / total_items) * 100.0
                            completed_word = "أكمل" if is_today else "أكمل"
                            s1 = f"{completed_word} المستخدم {done_items} من أصل {total_items} مهمة، محققاً معدل إنجاز إجمالي {pct:.1f}%."
                        if completed_groups:
                            s2 = f"مجموعات المهام {', '.join(completed_groups)} اكتملت بالكامل."
                        else:
                            s2 = "لم تكتمل أي مجموعة مهام بالكامل."
                        if pending_items:
                            if len(pending_items) > 3:
                                s3 = f"العناصر {', '.join(pending_items[:3])} و{len(pending_items)-3} أخرى {'معلقة' if is_today else 'ظلت معلقة'}."
                            else:
                                s3 = f"العناصر {', '.join(pending_items)} {'معلقة' if is_today else 'ظلت معلقة'}."
                        else:
                            s3 = "جميع عناصر المهام مكتملة."
                    else:
                        tense_completed = "has completed" if is_today else "completed"
                        tense_pending = "are pending" if is_today else "remained pending"
                        if total_items == 0:
                            s1 = f"No tasks are logged for {date_str}."
                        else:
                            pct = (done_items / total_items) * 100.0
                            s1 = f"The user {tense_completed} {done_items} out of {total_items} task items today, achieving an overall completion rate of {pct:.1f}%."
                        if completed_groups:
                            s2 = f"The task groups {', '.join([f'{cg}' for cg in completed_groups])} were fully completed."
                        else:
                            s2 = f"No task groups were fully completed."
                        if pending_items:
                            if len(pending_items) > 3:
                                s3 = f"The items {', '.join(pending_items[:3])} and {len(pending_items)-3} others {tense_pending}."
                            else:
                                s3 = f"The items {', '.join(pending_items)} {tense_pending}."
                        else:
                            s3 = f"All task items are complete."
                    result_text = f"{s1} {s2} {s3}"
                    
                elif job_type == "small_advice":
                    if _lang == "French":
                        if total_items == 0:
                            result_text = f"Aucune tâche enregistrée pour le {date_str}."
                        else:
                            pct = (done_items / total_items) * 100.0
                            if pct == 100.0:
                                result_text = "Excellente performance ! Toutes les tâches sont complétées aujourd'hui. Continuez ainsi."
                            elif pct >= 70.0:
                                result_text = f"Bonne progression avec {pct:.1f}% de complétion. Concentrez-vous sur la finition des tâches restantes demain."
                            else:
                                pending_names_str = ", ".join(pending_items[:2]) if pending_items else ""
                                result_text = f"Le taux de complétion est de {pct:.1f}%. Il est recommandé de prioriser les tâches en suspens comme {pending_names_str} demain."
                    elif _lang == "Arabic":
                        if total_items == 0:
                            result_text = f"لا توجد مهام مسجلة ليوم {date_str}."
                        else:
                            pct = (done_items / total_items) * 100.0
                            if pct == 100.0:
                                result_text = "أداء ممتاز! لقد تم إكمال جميع المهام بنسبة 100% اليوم، استمر في الحفاظ على هذا المستوى."
                            elif pct >= 70.0:
                                result_text = f"أداء جيد جداً بإكمال {pct:.1f}% من المهام. ركز على إنهاء المهام المتبقية غداً."
                            else:
                                pending_names_str = ", ".join(pending_items[:2]) if pending_items else ""
                                result_text = f"معدل الإنجاز اليوم هو {pct:.1f}%. يُنصح بالتركيز على المهام المعلقة مثل {pending_names_str} غداً."
                    else:
                        if total_items == 0:
                            result_text = f"No tasks are logged for {date_str}."
                        else:
                            pct = (done_items / total_items) * 100.0
                            if pct == 100.0:
                                result_text = "Excellent performance! All tasks are completed today. Keep maintaining this level."
                            elif pct >= 70.0:
                                result_text = f"Good progress with {pct:.1f}% task completion. Focus on finishing the remaining items tomorrow."
                            else:
                                pending_names_str = ", ".join(pending_items[:2]) if pending_items else ""
                                result_text = f"Today's completion rate is {pct:.1f}%. It is advised to focus on pending tasks like {pending_names_str} tomorrow."
                                
                elif job_type == "deep_advice":
                    if _lang == "French":
                        if total_items == 0:
                            result_text = f"Aucune tâche enregistrée pour le {date_str}."
                        else:
                            pct = (done_items / total_items) * 100.0
                            s1 = f"1. RÉSUMÉ STATISTIQUE DES PERFORMANCES :\nL'utilisateur a complété {done_items} sur {total_items} tâches aujourd'hui, avec un taux de réussite global de {pct:.1f}%."
                            if completed_groups:
                                s1 += f" Les groupes de tâches complétés sont : {', '.join(completed_groups)}."
                            
                            s2 = "\n\n2. DIAGNOSTIC LOGIQUE DES GOULOTS D'ÉTRANGLEMENT :\n"
                            if pending_items:
                                s2 += f"Le principal goulot d'étranglement réside dans les tâches en suspens : {', '.join(pending_items[:3])}."
                            else:
                                s2 += "Aucun goulot d'étranglement détecté puisque toutes les tâches ont été complétées."
                                
                            s3 = "\n\n3. ÉTAPES D'ACTION DIRECTES POUR DEMAIN :\n"
                            if pending_items:
                                s3 += f"Planifiez la tâche '{pending_items[0]}' en priorité demain matin pour créer de l'élan."
                            else:
                                s3 += "Maintenez cette dynamique positive et planifiez vos tâches de la même manière pour demain."
                            result_text = f"{s1}{s2}{s3}"
                    elif _lang == "Arabic":
                        if total_items == 0:
                            result_text = f"لا توجد مهام مسجلة ليوم {date_str}."
                        else:
                            pct = (done_items / total_items) * 100.0
                            s1 = f"1. ملخص الأداء الإحصائي:\nتم تسجيل {total_items} مهمة اليوم وتم إكمال {done_items} منها، بمعدل إنجاز إجمالي بلغ {pct:.1f}%."
                            if completed_groups:
                                s1 += f" اكتملت المجموعات التالية بالكامل: {', '.join(completed_groups)}."
                            
                            s2 = "\n\n2. تشخيص عقبات الأداء المنطقية:\n"
                            if pending_items:
                                s2 += f"تتمثل العقبة الأساسية اليوم في المهام المعلقة: {', '.join(pending_items[:3])}."
                                if len(pending_items) > 3:
                                    s2 += f" بالإضافة إلى {len(pending_items)-3} مهام أخرى."
                            else:
                                s2 += "لم يتم رصد أي عقبات أداء اليوم نظراً لإكمال جميع المهام."
                                
                            s3 = "\n\n3. خطوات عملية مباشرة للغد:\n"
                            if pending_items:
                                s3 += f"يُنصح بالبدء بإنهاء المهام المعلقة: {pending_items[0]} غداً صباحاً لبناء الزخم."
                            else:
                                s3 += "استمر في الحفاظ على نفس نمط الإنتاجية المرتفع وجدول مهامك للغد بنفس الطريقة."
                            result_text = f"{s1}{s2}{s3}"
                    else:
                        if total_items == 0:
                            result_text = f"No tasks are logged for {date_str}."
                        else:
                            pct = (done_items / total_items) * 100.0
                            s1 = f"1. STATISTICAL PERFORMANCE SUMMARY:\nThe user completed {done_items} out of {total_items} tasks today, achieving an overall completion rate of {pct:.1f}%."
                            if completed_groups:
                                s1 += f" Fully completed task groups: {', '.join(completed_groups)}."
                                
                            s2 = "\n\n2. LOGICAL BOTTLENECK DIAGNOSTICS:\n"
                            if pending_items:
                                s2 += f"The main bottleneck today is the pending tasks: {', '.join(pending_items[:3])}."
                            else:
                                s2 += "No performance bottlenecks detected today since all tasks were completed."
                                
                            s3 = "\n\n3. DIRECT ACTIONABLE STEPS FOR TOMORROW:\n"
                            if pending_items:
                                s3 += f"Schedule the pending task '{pending_items[0]}' first thing tomorrow to build early momentum."
                            else:
                                s3 += "Maintain this positive momentum and structure tomorrow's tasks in a similar fashion."
                            result_text = f"{s1}{s2}{s3}"
                
            import sqlite3
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            if job_type == "comment":
                c.execute("UPDATE days SET ai_comment = ? WHERE date = ?", (result_text, date_str))
            elif job_type == "small_advice":
                c.execute("UPDATE days SET small_advice = ? WHERE date = ?", (result_text, date_str))
            elif job_type == "deep_advice":
                c.execute("UPDATE days SET deep_advice = ? WHERE date = ?", (result_text, date_str))
            conn.commit()
            conn.close()
            
            self.running_ai_jobs[(date_str, job_type)] = {
                "status": "completed",
                "result": result_text,
                "error": None
            }
            
            self.after(0, lambda: self._on_job_success(date_str, job_type, result_text))
            
        except Exception as e:
            error_msg = str(e)
            self.running_ai_jobs[(date_str, job_type)] = {
                "status": "error",
                "result": None,
                "error": error_msg
            }
            self.after(0, lambda: self._on_job_error(date_str, job_type, error_msg))

    def _on_job_success(self, date_str, job_type, result_text):
        if (self.current_frame is not None and 
            self.current_frame.winfo_exists() and
            hasattr(self.current_frame, "date_str") and 
            self.current_frame.date_str == date_str and 
            hasattr(self.current_frame, "handle_ai_job_success")):
            self.current_frame.handle_ai_job_success(job_type, result_text)
            
    def _on_job_error(self, date_str, job_type, error_msg):
        if (self.current_frame is not None and 
            self.current_frame.winfo_exists() and
            hasattr(self.current_frame, "date_str") and 
            self.current_frame.date_str == date_str and 
            hasattr(self.current_frame, "handle_ai_job_error")):
            self.current_frame.handle_ai_job_error(job_type, error_msg)

    def get_available_surahs(self):
        import os
        audio_dir = os.path.join(APP_DIR, "data", "dos_6")
        available = []
        if os.path.exists(audio_dir):
            try:
                for filename in os.listdir(audio_dir):
                    if filename.endswith(".mp3"):
                        try:
                            num = int(filename.split(".")[0])
                            available.append(num)
                        except ValueError:
                            pass
            except Exception:
                pass
        # Match with SURAH_MAPPING
        surahs = [s for s in SURAH_MAPPING if s['num'] in available]
        return sorted(surahs, key=lambda x: x['num'])

    def play_surah_bg(self, surah, start_offset=None):
        import pygame
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
        except Exception as e:
            print(f"Mixer init error: {e}")
            return
            
        self.bg_current_surah = surah
        num = surah['num']
        file_name = f"{num:03d}.mp3"
        file_path = os.path.join(APP_DIR, "data", "dos_6", file_name)
        
        if not os.path.exists(file_path):
            self.stop_surah_bg()
            return
            
        # Get saved position if start_offset is not specified
        if start_offset is None:
            start_offset = 0.0
            try:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("SELECT last_position FROM quran_audio_progress WHERE surah_number = ?", (num,))
                row = c.fetchone()
                if row:
                    start_offset = row[0]
                conn.close()
            except Exception:
                pass
                
        self.bg_start_time_offset = start_offset
        
        self.bg_total_duration = get_mp3_duration(file_path)
            
        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play(start=start_offset)
            
            self.bg_music_active = True
            self.bg_music_paused = False
            
            # Start background loop
            self.bg_playback_loop()
            
            # Show mini-player if QuranAudioScreen is NOT current frame
            if not isinstance(self.current_frame, QuranAudioScreen):
                self.show_mini_player()
            else:
                self.hide_mini_player()
                
            # If active screen is QuranAudioScreen, sync it immediately
            if isinstance(self.current_frame, QuranAudioScreen):
                self.current_frame.sync_play_state_ui()
                
        except Exception as e:
            print(f"Error playing surah: {e}")

    def stop_surah_bg(self):
        import pygame
        # Save position before stopping
        if self.bg_current_surah and self.bg_music_active:
            try:
                pos_ms = pygame.mixer.music.get_pos()
                if pos_ms >= 0:
                    curr_pos = self.bg_start_time_offset + (pos_ms / 1000.0)
                    if curr_pos >= self.bg_total_duration - 1.0:
                        curr_pos = 0.0
                    self.save_audio_position(self.bg_current_surah['num'], curr_pos)
                    if hasattr(self.current_frame, "update_row_last_position"):
                        self.current_frame.update_row_last_position(self.bg_current_surah['num'], curr_pos)
            except Exception:
                pass
                
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
            
        self.bg_music_active = False
        self.bg_music_paused = False
        self.hide_mini_player()
        
        if isinstance(self.current_frame, QuranAudioScreen):
            self.current_frame.sync_play_state_ui()

    def toggle_play_pause_bg(self):
        import pygame
        if not self.bg_music_active:
            return
            
        if self.bg_music_paused:
            try:
                pygame.mixer.music.unpause()
                self.bg_music_paused = False
            except Exception:
                pass
        else:
            try:
                pygame.mixer.music.pause()
                self.bg_music_paused = True
            except Exception:
                pass
                
        self.update_mini_player_ui()
        if isinstance(self.current_frame, QuranAudioScreen):
            self.current_frame.sync_play_state_ui()

    def seek_bg(self, seconds):
        if not self.bg_current_surah:
            return
        try:
            import pygame
            pygame.mixer.music.stop()
            self.bg_start_time_offset = seconds
            file_name = f"{self.bg_current_surah['num']:03d}.mp3"
            file_path = os.path.join(APP_DIR, "data", "dos_6", file_name)
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play(start=seconds)
            self.bg_music_active = True
            self.bg_music_paused = False
            self.save_audio_position(self.bg_current_surah['num'], seconds)
            if hasattr(self.current_frame, "update_row_last_position"):
                self.current_frame.update_row_last_position(self.bg_current_surah['num'], seconds)
        except Exception as e:
            print(f"Error seeking: {e}")

    def save_audio_position(self, surah_num, pos):
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO quran_audio_progress (surah_number, last_position) VALUES (?, ?)", (surah_num, pos))
            conn.commit()
            conn.close()
            if hasattr(self.current_frame, "progress_map"):
                self.current_frame.progress_map[surah_num] = pos
        except Exception as e:
            print(f"Error saving audio progress: {e}")

    def bg_playback_loop(self):
        if not self.bg_music_active:
            return
            
        import pygame
        if pygame.mixer.music.get_busy():
            pos_ms = pygame.mixer.music.get_pos()
            if pos_ms >= 0:
                curr_sec = self.bg_start_time_offset + (pos_ms / 1000.0)
                if curr_sec >= self.bg_total_duration - 0.5:
                    self.bg_on_music_finished()
                else:
                    if isinstance(self.current_frame, QuranAudioScreen):
                        self.current_frame.sync_playback_state(curr_sec)
        else:
            if not self.bg_music_paused:
                self.bg_on_music_finished()
                
        self.after(500, self.bg_playback_loop)

    def bg_on_music_finished(self):
        if self.bg_current_surah:
            self.save_audio_position(self.bg_current_surah['num'], 0.0)
            if hasattr(self.current_frame, "update_row_last_position"):
                self.current_frame.update_row_last_position(self.bg_current_surah['num'], 0.0)
                
        mode = self.bg_play_mode
        if mode == "loop":
            self.play_surah_bg(self.bg_current_surah, start_offset=0.0)
        elif mode == "next":
            self.play_next_surah_bg()
        elif mode == "shuffle":
            self.play_random_surah_bg()
        else:
            self.stop_surah_bg()

    def play_next_surah_bg(self):
        available = self.get_available_surahs()
        if not available:
            self.stop_surah_bg()
            return
        if not self.bg_current_surah:
            self.play_surah_bg(available[0])
            return
        curr_num = self.bg_current_surah['num']
        next_surah = None
        for s in available:
            if s['num'] > curr_num:
                next_surah = s
                break
        if next_surah is None:
            next_surah = available[0]
        self.play_surah_bg(next_surah)

    def play_random_surah_bg(self):
        import random
        available = self.get_available_surahs()
        if not available:
            self.stop_surah_bg()
            return
        if len(available) > 1 and self.bg_current_surah:
            options = [s for s in available if s['num'] != self.bg_current_surah['num']]
        else:
            options = available
        self.play_surah_bg(random.choice(options))

    def show_mini_player(self):
        if self.mini_player and self.mini_player.winfo_exists():
            self.update_mini_player_ui()
            return
            
        self.mini_player = tk.Toplevel(self)
        self.mini_player.overrideredirect(True)
        self.mini_player.attributes("-topmost", True)
        self.mini_player.configure(bg=BG_CARD, highlightbackground=ACCENT_PURPLE, highlightthickness=1)
        
        self.align_mini_player()
        self.bind("<Configure>", lambda e: self.align_mini_player())
        
        lbl_text = self.get_mini_player_label_text()
        self.mini_title = tk.Label(self.mini_player, text=lbl_text, bg=BG_CARD, fg=TEXT_WHITE, font=("Helvetica", 9, "bold"))
        self.mini_title.pack(side="left", padx=10, fill="x", expand=True)
        
        play_char = "▶" if self.bg_music_paused else "⏸"
        self.mini_play_btn = tk.Button(self.mini_player, text=play_char, bg=BG_DARK, fg=TEXT_WHITE, relief="flat", font=("Helvetica", 9, "bold"), width=3, command=self.toggle_play_pause_bg)
        self.mini_play_btn.pack(side="left", padx=5)
        
        close_btn = tk.Button(self.mini_player, text="✕", bg=BG_DARK, fg=TEXT_MUTED, relief="flat", font=("Helvetica", 9, "bold"), width=3, command=self.stop_surah_bg)
        close_btn.pack(side="left", padx=(5, 10))
        
        self.mini_play_btn.bind("<Enter>", lambda e: self.mini_play_btn.config(bg=ACCENT_PURPLE, fg=BG_DARK))
        self.mini_play_btn.bind("<Leave>", lambda e: self.mini_play_btn.config(bg=BG_DARK, fg=TEXT_WHITE))
        close_btn.bind("<Enter>", lambda e: close_btn.config(bg="#ef4444", fg=TEXT_WHITE))
        close_btn.bind("<Leave>", lambda e: close_btn.config(bg=BG_DARK, fg=TEXT_MUTED))

    def align_mini_player(self):
        if not self.mini_player or not self.mini_player.winfo_exists():
            return
        w, h = 280, 42
        x = self.winfo_rootx() + self.winfo_width() - w - 30
        y = self.winfo_rooty() + 10
        self.mini_player.geometry(f"{w}x{h}+{x}+{y}")

    def update_mini_player_ui(self):
        if not self.mini_player or not self.mini_player.winfo_exists():
            return
        lbl_text = self.get_mini_player_label_text()
        self.mini_title.config(text=lbl_text)
        play_char = "▶" if self.bg_music_paused else "⏸"
        self.mini_play_btn.config(text=play_char)

    def get_mini_player_label_text(self):
        if not self.bg_current_surah:
            return ""
        ar_name = get_arabic_text(self.bg_current_surah['arabic'])
        return f"{self.bg_current_surah['num']:03d}. {self.bg_current_surah['english']} ({ar_name})"

    def hide_mini_player(self):
        if self.mini_player:
            try:
                self.mini_player.destroy()
            except Exception:
                pass
            self.mini_player = None


class StartScreen(tk.Frame):
    """
    The landing screen - A glowing blank page with Calendar navigation integrations.
    """
    def __init__(self, parent, show_tools=False):
        super().__init__(parent, bg=BG_DARK)
        self.parent = parent
        self._logo_img = None  # keep PIL reference alive

        # Grid layout
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ── Date label – top-left overlay ─────────────────────────────────────
        date_str_fmt = tm.format_date_labeled("today_lbl", datetime.date.today())
        date_lbl = tk.Label(self, text=date_str_fmt, bg=BG_DARK, fg=TEXT_MUTED,
                            font=("Helvetica", 10))
        date_lbl.place(x=18, y=12)

        # ── Logo Canvas ────────────────────────────────────────────────────────
        self.title_canvas = tk.Canvas(self, width=600, height=200,
                                      bg=BG_DARK, highlightthickness=0)
        self.title_canvas.grid(row=0, column=0, pady=(30, 0), sticky="n")
        self.draw_glow_title()

        # ── Middle Frame for choices ───────────────────────────────────────────
        self.choices_frame = tk.Frame(self, bg=BG_DARK)
        self.choices_frame.grid(row=1, column=0, sticky="n")

        # Today's date details
        self.today_str = datetime.date.today().isoformat()

        # Check today's status from SQLite
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT 1 FROM days WHERE date = ?", (self.today_str,))
        self.today_exists = bool(c.fetchone())
        conn.close()

        self.setup_choices()
        if show_tools:
            self.show_tools_options()

        # Footer
        footer_lbl = tk.Label(self, text=tm.tr("made_by"), bg=BG_DARK, fg=TEXT_MUTED,
                              font=("Helvetica", 10, "italic"))
        footer_lbl.grid(row=2, column=0, pady=30, sticky="s")

        # ── Floating "Support the Project" glowing bubble ─────────────────────
        self._bubble_glow_step = 0
        self._bubble_colors = self._generate_bubble_glow_colors()

        bubble_text = tm.tr("support_project")
        self.support_bubble = tk.Label(
            self,
            text=bubble_text,
            bg="#1a0a2e",
            fg="#e0aaff",
            font=("Helvetica", 10, "bold"),
            padx=14,
            pady=8,
            cursor="hand2",
            relief="flat",
            bd=0,
        )
        # Place bottom-right corner, floating above everything
        self.support_bubble.place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)

        # Glow border via a highlight frame trick
        self.support_bubble.config(
            highlightbackground=GLOW_COLOR,
            highlightthickness=2,
        )

        self.support_bubble.bind("<Button-1>", self._open_kofi)
        self.support_bubble.bind("<Enter>", self._bubble_hover_in)
        self.support_bubble.bind("<Leave>", self._bubble_hover_out)

        # Start pulse animation
        self._animate_bubble()

    def _generate_bubble_glow_colors(self):
        """Generate a smooth list of border colors for the glow pulse."""
        import colorsys
        colors = []
        steps = 30
        for i in range(steps):
            t = i / steps
            # Oscillate hue between purple and cyan
            h = 0.75 + 0.17 * abs((t * 2) - 1)  # ~0.75 purple → ~0.58 cyan
            r, g, b = colorsys.hsv_to_rgb(h % 1.0, 0.9, 1.0)
            colors.append(f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}")
        return colors

    def _animate_bubble(self):
        if not self.winfo_exists():
            return
        color = self._bubble_colors[self._bubble_glow_step % len(self._bubble_colors)]
        try:
            self.support_bubble.config(highlightbackground=color)
        except Exception:
            return
        self._bubble_glow_step += 1
        self.after(60, self._animate_bubble)

    def _bubble_hover_in(self, e=None):
        self.support_bubble.config(bg="#2d0a52", fg="#ffffff")

    def _bubble_hover_out(self, e=None):
        self.support_bubble.config(bg="#1a0a2e", fg="#e0aaff")

    def _open_kofi(self, e=None):
        import webbrowser
        webbrowser.open("https://ko-fi.com/yakomodev")

    def draw_glow_title(self):
        """Show the app logo (white bg + black corners removed) centred on canvas."""
        icon_src  = os.path.join(APP_DIR, "data", "icone", "Mission Ui.png")
        icon_dest = os.path.join(APP_DIR, "data", "icone", "icon_transparent.png")

        # ── Background removal using PIL Flood-fill ────────────────────────────
        if not os.path.exists(icon_dest):
            try:
                from PIL import Image, ImageDraw
                img  = Image.open(icon_src).convert("RGBA")
                w, h = img.size

                # 1. Flood-fill the four corners (dark background) with transparency
                for seed in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
                    seed_color = img.getpixel(seed)
                    if seed_color[3] > 0:  # If not already transparent
                        ImageDraw.floodfill(img, seed, (0, 0, 0, 0), thresh=60)

                # 2. Flood-fill the white card background with transparency
                # Scan top-to-middle along the vertical centerline to find a white card pixel
                white_seed = None
                for y_offset in range(10, h // 2, 5):
                    p = (w // 2, y_offset)
                    color = img.getpixel(p)
                    # If it's a solid white/near-white pixel
                    if color[0] > 220 and color[1] > 220 and color[2] > 220 and color[3] > 0:
                        white_seed = p
                        break

                if white_seed:
                    ImageDraw.floodfill(img, white_seed, (0, 0, 0, 0), thresh=50)

                # 3. Erase the card boundary outline (outer 14% margins)
                import numpy as np
                data = np.array(img)
                margin_x = int(w * 0.14)
                margin_y = int(h * 0.14)
                data[:, :margin_x, 3] = 0
                data[:, w - margin_x:, 3] = 0
                data[:margin_y, :, 3] = 0
                data[h - margin_y:, :, 3] = 0
                img = Image.fromarray(data)

                img.save(icon_dest)
            except Exception as e:
                print(f"[icon] bg removal failed: {e}")
                icon_dest = icon_src  # fall back to original
        else:
            # Already created, use the existing file
            pass

        # ── Display on canvas ──────────────────────────────────────────────────
        try:
            from PIL import Image, ImageTk
            img = Image.open(icon_dest).convert("RGBA")
            w_orig, h_orig = img.size
            new_h = 160
            new_w = int(w_orig * new_h / h_orig)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            self._logo_img = ImageTk.PhotoImage(img)
            cx, cy = 300, 90
            self.title_canvas.create_image(cx, cy, image=self._logo_img, anchor="center")
            self.title_canvas.create_text(cx, cy + 90, text=tm.tr("subtitle"),
                                          fill=TEXT_WHITE, font=("Helvetica", 12, "bold"))
            # Set window taskbar icon
            try:
                small = img.resize((64, 64), Image.LANCZOS)
                self._wm_icon = ImageTk.PhotoImage(small)
                self.parent.wm_iconphoto(True, self._wm_icon)
            except Exception:
                pass

        except Exception as e:
            # PIL unavailable — fallback neon-glow text
            print(f"[icon] PIL load failed: {e}")
            x, y = 300, 80
            text = tm.tr("title")
            for dx, dy, col in [(-3,-3,"#3b0764"),(3,3,"#3b0764"),(0,2,"#581c87"),
                                 (0,-2,"#701a75"),(-2,0,"#042f2e"),(2,0,"#06b6d4")]:
                self.title_canvas.create_text(x+dx, y+dy, text=text,
                                              fill=col, font=("Helvetica", 42, "bold"))
            self.title_canvas.create_text(x, y, text=text,
                                          fill="#a855f7", font=("Helvetica", 40, "bold"))
            self.title_canvas.create_text(x, y+50, text=tm.tr("subtitle"),
                                          fill=TEXT_WHITE, font=("Helvetica", 12, "bold"))



    def setup_choices(self):
        # Button 1: Create Today's Task List or Edit & Continue
        if self.today_exists:
            track_btn_text = tm.tr("edit_list")
            cmd = lambda: self.parent.show_daily_tracker(self.today_str)
            glow_color = SUCCESS_GREEN
        else:
            track_btn_text = tm.tr("create_list")
            cmd = self.create_blank_day
            glow_color = ACCENT_PURPLE
            
        self.track_btn = tk.Button(self.choices_frame, text=track_btn_text, bg=BG_CARD, fg=TEXT_WHITE,
                                   activebackground=glow_color, activeforeground=BG_DARK,
                                   highlightbackground=BORDER_COLOR, highlightcolor=glow_color, highlightthickness=1,
                                   relief="flat", font=("Helvetica", 13, "bold"), width=32, height=2, command=cmd)
        self.track_btn.pack(pady=12)
        self.bind_button_hover(self.track_btn, glow_color, BG_CARD, TEXT_WHITE, BG_DARK)
        
        # Button 2: Calendar Dashboard
        self.calendar_btn = tk.Button(self.choices_frame, text=tm.tr("calendar_dashboard"), bg=BG_CARD, fg=TEXT_MUTED,
                                       activebackground=ACCENT_CYAN, activeforeground=BG_DARK,
                                       highlightbackground=BORDER_COLOR, highlightcolor=ACCENT_CYAN, highlightthickness=1,
                                       relief="flat", font=("Helvetica", 13, "bold"), width=32, height=2,
                                       command=self.parent.show_calendar_screen)
        self.calendar_btn.pack(pady=12)
        self.bind_button_hover(self.calendar_btn, ACCENT_CYAN, BG_CARD, TEXT_MUTED, BG_DARK)

        # Button 3: Graphs Dashboard
        self.graphs_btn = tk.Button(self.choices_frame, text=tm.tr("graphs_dashboard"), bg=BG_CARD, fg=TEXT_MUTED,
                                     activebackground=ACCENT_CYAN, activeforeground=BG_DARK,
                                     highlightbackground=BORDER_COLOR, highlightcolor=ACCENT_CYAN, highlightthickness=1,
                                     relief="flat", font=("Helvetica", 13, "bold"), width=32, height=2,
                                     command=self.parent.show_graphs_screen)
        self.graphs_btn.pack(pady=12)
        self.bind_button_hover(self.graphs_btn, ACCENT_CYAN, BG_CARD, TEXT_MUTED, BG_DARK)

        # Button 3.5: Daily Diary
        self.diary_btn = tk.Button(self.choices_frame, text=tm.tr("daily_diary"), bg=BG_CARD, fg=TEXT_MUTED,
                                   activebackground=ACCENT_CYAN, activeforeground=BG_DARK,
                                   highlightbackground=BORDER_COLOR, highlightcolor=ACCENT_CYAN, highlightthickness=1,
                                   relief="flat", font=("Helvetica", 13, "bold"), width=32, height=2,
                                   command=self.parent.show_diary_screen)
        self.diary_btn.pack(pady=12)
        self.bind_button_hover(self.diary_btn, ACCENT_CYAN, BG_CARD, TEXT_MUTED, BG_DARK)

        # Button 4: Tools
        self.tools_btn = tk.Button(self.choices_frame, text=tm.tr("tools"), bg=BG_CARD, fg=TEXT_MUTED,
                                   activebackground=ACCENT_PURPLE, activeforeground=BG_DARK,
                                   highlightbackground=BORDER_COLOR, highlightcolor=ACCENT_PURPLE, highlightthickness=1,
                                   relief="flat", font=("Helvetica", 13, "bold"), width=32, height=2,
                                   command=self.show_tools_options)
        self.tools_btn.pack(pady=12)
        self.bind_button_hover(self.tools_btn, ACCENT_PURPLE, BG_CARD, TEXT_MUTED, BG_DARK)

        # Button 5: Settings
        self.settings_btn = tk.Button(self.choices_frame, text=tm.tr("settings"), bg=BG_CARD, fg=TEXT_MUTED,
                                      activebackground=ACCENT_PURPLE, activeforeground=BG_DARK,
                                      highlightbackground=BORDER_COLOR, highlightcolor=ACCENT_PURPLE, highlightthickness=1,
                                      relief="flat", font=("Helvetica", 13, "bold"), width=32, height=2,
                                      command=self.parent.show_settings_screen)
        self.settings_btn.pack(pady=12)
        self.bind_button_hover(self.settings_btn, ACCENT_PURPLE, BG_CARD, TEXT_MUTED, BG_DARK)

    def show_tools_options(self):
        # Hide main buttons
        self.track_btn.pack_forget()
        self.calendar_btn.pack_forget()
        self.graphs_btn.pack_forget()
        if hasattr(self, 'diary_btn'):
            self.diary_btn.pack_forget()
        self.tools_btn.pack_forget()
        self.settings_btn.pack_forget()
        
        back_btn = tk.Button(self.choices_frame, text=tm.tr("back"), bg=BG_DARK, fg=TEXT_MUTED, relief="flat", font=("Helvetica", 10), command=self.reset_choices)
        back_btn.pack(anchor="w", pady=(0, 10))
        
        lbl = tk.Label(self.choices_frame, text=tm.tr("tools_title"), bg=BG_DARK, fg=TEXT_WHITE, font=("Helvetica", 11, "bold"))
        lbl.pack(pady=(0, 15))
        
        starred_btn = tk.Button(self.choices_frame, text=tm.tr("inspect_starred"), bg=BG_CARD, fg=TEXT_WHITE,
                                activebackground=ACCENT_PURPLE, activeforeground=BG_DARK,
                                highlightbackground=BORDER_COLOR, highlightthickness=1, relief="flat",
                                font=("Helvetica", 12, "bold"), width=28, height=2, command=self.show_starred_packs_manager)
        starred_btn.pack(pady=8)
        self.bind_button_hover(starred_btn, ACCENT_PURPLE, BG_CARD, TEXT_WHITE, BG_DARK)
        
        quran_btn = tk.Button(self.choices_frame, text=tm.tr("read_quran"), bg=BG_CARD, fg=TEXT_WHITE,
                              activebackground=ACCENT_CYAN, activeforeground=BG_DARK,
                              highlightbackground=BORDER_COLOR, highlightthickness=1, relief="flat",
                              font=("Helvetica", 12, "bold"), width=28, height=2, command=self.read_quran)
        quran_btn.pack(pady=8)
        self.bind_button_hover(quran_btn, ACCENT_CYAN, BG_CARD, TEXT_WHITE, BG_DARK)
        
        listen_btn = tk.Button(self.choices_frame, text=tm.tr("listen_quran"), bg=BG_CARD, fg=TEXT_WHITE,
                               activebackground=ACCENT_PURPLE, activeforeground=BG_DARK,
                               highlightbackground=BORDER_COLOR, highlightthickness=1, relief="flat",
                               font=("Helvetica", 12, "bold"), width=28, height=2, command=self.listen_quran)
        listen_btn.pack(pady=8)
        self.bind_button_hover(listen_btn, ACCENT_PURPLE, BG_CARD, TEXT_WHITE, BG_DARK)
        
        azkar_btn = tk.Button(self.choices_frame, text="📿 Addkar", bg=BG_CARD, fg=TEXT_WHITE,
                              activebackground=ACCENT_CYAN, activeforeground=BG_DARK,
                              highlightbackground=BORDER_COLOR, highlightthickness=1, relief="flat",
                              font=("Helvetica", 12, "bold"), width=28, height=2, command=self.show_azkar)
        azkar_btn.pack(pady=8)
        self.bind_button_hover(azkar_btn, ACCENT_CYAN, BG_CARD, TEXT_WHITE, BG_DARK)
        
        self.sub_widgets = [back_btn, lbl, starred_btn, quran_btn, listen_btn, azkar_btn]

    def listen_quran(self):
        try:
            import pygame
            from PIL import Image, ImageTk
            import arabic_reshaper
            from bidi.algorithm import get_display
        except ImportError:
            import sys
            import subprocess
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "pygame", "arabic-reshaper", "python-bidi"])
            except Exception as err:
                messagebox.showerror("Dependencies Missing", 
                                     f"Could not automatically install audio dependencies: {err}\n\n"
                                     "Please manually run:\npip install pygame arabic-reshaper python-bidi")
                return
                
        self.parent.show_frame(QuranAudioScreen)

    def reset_choices(self):
        for w in self.sub_widgets:
            w.destroy()
        self.setup_choices()

    def show_starred_packs_manager(self):
        StarredPacksManagerDialog(self)

    def read_quran(self):
        output_dir = os.path.join(APP_DIR, "data", "quran_pages")
        
        # Self-healing dependency check & auto-installer
        try:
            from PIL import Image, ImageTk
            import arabic_reshaper
            from bidi.algorithm import get_display
        except ImportError:
            import sys
            import subprocess
            
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow", "arabic-reshaper", "python-bidi"])
                from PIL import Image, ImageTk
                import arabic_reshaper
                from bidi.algorithm import get_display
            except Exception as err:
                messagebox.showerror("Dependencies Missing", 
                                     f"Could not automatically install required libraries: {err}\n\n"
                                     "Please install them manually via terminal:\n"
                                     "pip install pillow arabic-reshaper python-bidi")
                return
            
        if os.path.exists(output_dir):
            try:
                jpg_files = [f for f in os.listdir(output_dir) if f.endswith(".jpg")]
                if len(jpg_files) >= 600:
                    QuranViewerDialog(self, output_dir)
                    return
            except Exception:
                pass
                
        messagebox.showerror("Quran Pages Not Found", 
                             "No converted Quran pages found in data/quran_pages/.\n"
                             "Please ensure the page JPEGs are placed inside that directory.")

    def show_azkar(self):
        try:
            import arabic_reshaper
            from bidi.algorithm import get_display
        except ImportError:
            import sys
            import subprocess
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "arabic-reshaper", "python-bidi"])
            except Exception as err:
                messagebox.showerror("Dependencies Missing", 
                                     f"Could not automatically install required libraries: {err}\n\n"
                                     "Please install them manually via terminal:\n"
                                     "pip install arabic-reshaper python-bidi")
                return
        self.parent.show_frame(AzkarScreen)

    def bind_button_hover(self, btn, active_bg, normal_bg, normal_fg, active_fg):
        btn.bind("<Enter>", lambda e=None: btn.config(bg=active_bg, fg=active_fg, highlightbackground=active_bg))
        btn.bind("<Leave>", lambda e=None: btn.config(bg=normal_bg, fg=normal_fg, highlightbackground=BORDER_COLOR))

    def create_blank_day(self):
        choice_diag = InitializeDayDialog(self, self.today_str)
        self.wait_window(choice_diag)
        if choice_diag.result == "blank":
            self.parent.show_daily_tracker(self.today_str, blueprint_data={"main_tasks": [], "side_tasks": []})
        elif choice_diag.result == "blueprint" and choice_diag.result_blueprint:
            self.parent.show_daily_tracker(self.today_str, blueprint_data=choice_diag.result_blueprint)


class CalendarScreen(tk.Frame):
    """
    Calendar dashboard showing month-by-month grid, task completion ratios,
    historic highlights, and detailed task summaries on hovering days.
    """
    def __init__(self, parent):
        super().__init__(parent, bg=BG_DARK)
        self.parent = parent
        
        # Grid configs
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=4) # Calendar Grid
        self.grid_columnconfigure(1, weight=2) # Details card
        
        # Header
        header = tk.Frame(self, bg=BG_DARK, height=60)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=10)
        
        back_btn = tk.Button(header, text=tm.tr("menu_back"), bg=BG_CARD, fg=TEXT_WHITE, relief="flat",
                             activebackground=ACCENT_PURPLE, activeforeground=BG_DARK, font=("Helvetica", 10, "bold"),
                             padx=12, pady=6, command=parent.show_start_screen)
        back_btn.pack(side="left")
        back_btn.bind("<Enter>", lambda e=None: back_btn.config(bg=ACCENT_PURPLE, fg=BG_DARK))
        back_btn.bind("<Leave>", lambda e=None: back_btn.config(bg=BG_CARD, fg=TEXT_WHITE))
        
        lbl = tk.Label(header, text=tm.tr("calendar_dashboard"), bg=BG_DARK, fg=ACCENT_CYAN, font=("Helvetica", 14, "bold"))
        lbl.pack(side="right")
        
        # Current navigating year/month
        self.today = datetime.date.today()
        self.current_year = self.today.year
        self.current_month = self.today.month
        
        # Left Panel - Grid
        self.cal_frame = tk.Frame(self, bg=BG_DARK)
        self.cal_frame.grid(row=1, column=0, padx=(20, 10), pady=10, sticky="nsew")
        self.cal_frame.grid_rowconfigure(1, weight=1)
        self.cal_frame.grid_columnconfigure(0, weight=1)
        
        # Right Panel - Hover Details Sidebar
        self.details_card = tk.LabelFrame(self, text=tm.tr("day_details_preview"), bg=BG_DARK, fg=TEXT_WHITE,
                                          font=("Helvetica", 11, "bold"), highlightbackground=BORDER_COLOR, highlightthickness=1, relief="flat")
        self.details_card.grid(row=1, column=1, padx=(10, 20), pady=15, sticky="nsew")
        
        self.setup_details_sidebar()
        self.render_calendar()
        
    def setup_details_sidebar(self):
        self.details_scroll = ScrollableFrame(self.details_card, bg=BG_DARK)
        self.details_scroll.pack(fill="both", expand=True, padx=10, pady=10)
        self.clear_details_sidebar()
        
    def clear_details_sidebar(self):
        for w in self.details_scroll.scrollable_frame.winfo_children():
            w.destroy()
        lbl = tk.Label(self.details_scroll.scrollable_frame, text=tm.tr("hover_day_preview"), 
                       bg=BG_DARK, fg=TEXT_MUTED, font=("Helvetica", 10, "italic"), justify="center", wraplength=250)
        lbl.pack(pady=60)

    # ── Calendar Adjustment Helpers ───────────────────────────────────────
    def get_day_delta(self, year, month):
        """Return the stored day_delta for the given year-month (0 if none)."""
        key = f"{year}-{month:02d}"
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT day_delta FROM calendar_adjustments WHERE year_month = ?", (key,))
            row = c.fetchone()
            conn.close()
            return row[0] if row else 0
        except Exception:
            return 0

    def set_day_delta(self, year, month, delta):
        """Persist day_delta for the given year-month."""
        key = f"{year}-{month:02d}"
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute(
                "INSERT INTO calendar_adjustments (year_month, day_delta) VALUES (?, ?) "
                "ON CONFLICT(year_month) DO UPDATE SET day_delta = excluded.day_delta",
                (key, delta)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error saving calendar adjustment: {e}")

    def get_effective_days(self, year, month):
        """Return standard month length plus any stored adjustment delta."""
        _, standard_days = calendar.monthrange(year, month)
        delta = self.get_day_delta(year, month)
        return max(1, standard_days + delta)

    def adjust_days(self, direction):
        """
        direction: +1 to add a day, -1 to remove a day.
        Confirms with the user before applying.
        """
        year, month = self.current_year, self.current_month
        _, standard_days = calendar.monthrange(year, month)
        current_delta = self.get_day_delta(year, month)
        new_delta = current_delta + direction
        effective = standard_days + new_delta

        if effective < 1:
            messagebox.showwarning(tm.tr("limit_reached"), tm.tr("cannot_remove_days"))
            return
        if new_delta > 7:
            messagebox.showwarning(tm.tr("limit_reached"), tm.tr("cannot_add_days"))
            return

        month_name = calendar.month_name[month]
        if direction == -1:
            action = tm.tr("remove_day_prompt").format(day=effective + 1, month=month_name, year=year)
        else:
            action = tm.tr("add_day_prompt").format(day=effective, month=month_name, year=year)

        if not messagebox.askyesno(tm.tr("confirm_cal_adjustment"), action):
            return

        self.set_day_delta(year, month, new_delta)
        self.render_calendar()
        self.clear_details_sidebar()

    def render_calendar(self):
        # Clear frame
        for w in self.cal_frame.winfo_children():
            w.destroy()
            
        # Month/Year Navigation Header
        nav_row = tk.Frame(self.cal_frame, bg=BG_DARK)
        nav_row.pack(fill="x", pady=(0, 10))
        
        prev_btn = tk.Button(nav_row, text="◀", bg=BG_CARD, fg=TEXT_WHITE, relief="flat", font=("Helvetica", 11, "bold"), padx=12, command=self.prev_month)
        prev_btn.pack(side="left")
        prev_btn.bind("<Enter>", lambda e=None: prev_btn.config(bg=ACCENT_CYAN, fg=BG_DARK))
        prev_btn.bind("<Leave>", lambda e=None: prev_btn.config(bg=BG_CARD, fg=TEXT_WHITE))
        
        month_lbl = tk.Label(nav_row, text=tm.format_month(self.current_year, self.current_month).upper(), bg=BG_DARK, fg=TEXT_WHITE, font=("Helvetica", 13, "bold"), width=22)
        month_lbl.pack(side="left", padx=10)
        
        next_btn = tk.Button(nav_row, text="▶", bg=BG_CARD, fg=TEXT_WHITE, relief="flat", font=("Helvetica", 11, "bold"), padx=12, command=self.next_month)
        next_btn.pack(side="left")
        next_btn.bind("<Enter>", lambda e=None: next_btn.config(bg=ACCENT_CYAN, fg=BG_DARK))
        next_btn.bind("<Leave>", lambda e=None: next_btn.config(bg=BG_CARD, fg=TEXT_WHITE))

        # Day-adjustment buttons (spacer pushes them to right)
        tk.Frame(nav_row, bg=BG_DARK).pack(side="left", expand=True)

        _, std_days = calendar.monthrange(self.current_year, self.current_month)
        delta = self.get_day_delta(self.current_year, self.current_month)
        effective = std_days + delta
        if tm._current_language == "Arabic":
            label_text = f"{effective} : {tm.tr('days_lbl').replace(':', '').strip()}"
        else:
            label_text = f"{tm.tr('days_lbl')}{effective}"
        if delta != 0:
            label_text += f" ({delta:+d})"
            
        adj_label = tk.Label(
            nav_row,
            text=label_text,
            bg=BG_DARK,
            fg=ACCENT_CYAN if delta != 0 else TEXT_MUTED,
            font=("Helvetica", 9, "bold")
        )
        adj_label.pack(side="left", padx=(0, 8))

        remove_day_btn = tk.Button(
            nav_row, text=tm.tr("remove_day"), bg=BG_CARD, fg=TEXT_MUTED,
            relief="flat", font=("Helvetica", 9, "bold"), padx=8, pady=4,
            command=lambda: self.adjust_days(-1)
        )
        remove_day_btn.pack(side="left", padx=2)
        remove_day_btn.bind("<Enter>", lambda e=None: remove_day_btn.config(bg="#7f1d1d", fg=TEXT_WHITE))
        remove_day_btn.bind("<Leave>", lambda e=None: remove_day_btn.config(bg=BG_CARD, fg=TEXT_MUTED))

        add_day_btn = tk.Button(
            nav_row, text=tm.tr("add_day"), bg=BG_CARD, fg=TEXT_MUTED,
            relief="flat", font=("Helvetica", 9, "bold"), padx=8, pady=4,
            command=lambda: self.adjust_days(+1)
        )
        add_day_btn.pack(side="left", padx=2)
        add_day_btn.bind("<Enter>", lambda e=None: add_day_btn.config(bg="#14532d", fg=TEXT_WHITE))
        add_day_btn.bind("<Leave>", lambda e=None: add_day_btn.config(bg=BG_CARD, fg=TEXT_MUTED))
        
        # Grid Container
        grid_container = tk.Frame(self.cal_frame, bg=BG_DARK)
        grid_container.pack(fill="both", expand=True)
        
        for i in range(7):
            grid_container.grid_columnconfigure(i, weight=1)
        for i in range(7): # 1 header row + 6 days rows
            grid_container.grid_rowconfigure(i, weight=1)
            
        # Weekdays header
        weekdays = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]
        for col, day in enumerate(weekdays):
            lbl = tk.Label(grid_container, text=day, bg=BG_DARK, fg=TEXT_MUTED, font=("Helvetica", 9, "bold"), pady=6)
            lbl.grid(row=0, column=col, sticky="ew")
            
        # Query SQLite for logged entries in selected month
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        month_pattern = f"{self.current_year}-{self.current_month:02d}-%"
        c.execute("SELECT date, main_tasks, side_tasks, ai_comment, small_advice, deep_advice FROM days WHERE date LIKE ?", (month_pattern,))
        rows = c.fetchall()
        conn.close()
        
        month_data = {}
        for r in rows:
            month_data[r[0]] = {
                "main_tasks": json.loads(r[1]),
                "side_tasks": json.loads(r[2]),
                "ai_comment": tm.unshape_arabic_text(r[3]),
                "small_advice": tm.unshape_arabic_text(r[4] or ""),
                "deep_advice": tm.unshape_arabic_text(r[5] or "")
            }
            
        # Draw cells
        first_weekday, _ = calendar.monthrange(self.current_year, self.current_month)
        # Shift Monday=0 to Sunday=0
        first_weekday = (first_weekday + 1) % 7
        # Use effective days (includes any +/- adjustments stored in calendar_adjustments)
        effective_num_days = self.get_effective_days(self.current_year, self.current_month)

        row = 1
        col = first_weekday

        for day_num in range(1, effective_num_days + 1):
            date_str = f"{self.current_year}-{self.current_month:02d}-{day_num:02d}"
            day_data = month_data.get(date_str)
            self.create_day_card(grid_container, day_num, date_str, day_data, row, col)
            
            col += 1
            if col > 6:
                col = 0
                row += 1
                
    def create_day_card(self, parent, day_num, date_str, day_data, row, col):
        card = tk.Frame(parent, bg=BG_DARK, bd=1, highlightthickness=1)
        card.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")
        
        is_today = (date_str == self.today.isoformat())
        
        done_items = 0
        tot_items = 0
        earned_stars = 0.0
        tot_stars = 0.0
        
        if day_data:
            # Calculate stats
            for g in day_data["main_tasks"] + day_data["side_tasks"]:
                g_stars = float(g.get("stars", 0))
                tot_stars += g_stars
                tot_items += len(g.get("items", []))
                for item in g.get("items", []):
                    item_stars = g_stars * (float(item.get("percent", 0.0)) / 100.0)
                    if item.get("done"):
                        done_items += 1
                        earned_stars += item_stars
            
            card.config(bg=BG_CARD)
            
            # Neon border highlight: Green if 100% completed, Purple if in progress/empty
            if tot_items > 0 and done_items == tot_items:
                border_color = SUCCESS_GREEN
            else:
                border_color = ACCENT_PURPLE
                
            card.config(highlightbackground=border_color)
            
            day_lbl = tk.Label(card, text=str(day_num), bg=BG_CARD, fg=TEXT_WHITE, font=("Helvetica", 10, "bold"), anchor="nw")
            day_lbl.pack(anchor="nw", padx=6, pady=4)
            
            if tot_items > 0:
                prog_lbl = tk.Label(card, text=f"{done_items}/{tot_items}", bg=BG_CARD, fg=TEXT_MUTED, font=("Helvetica", 8, "bold"))
                prog_lbl.pack(anchor="sw", padx=6, pady=(0, 1))
                
                stars_lbl = tk.Label(card, text=f"⭐ {earned_stars:.0f}/{tot_stars:.0f}", bg=BG_CARD, fg=ACCENT_CYAN, font=("Helvetica", 8, "bold"))
                stars_lbl.pack(anchor="sw", padx=6, pady=(0, 4))
            else:
                empty_lbl = tk.Label(card, text=tm.tr("empty"), bg=BG_CARD, fg=TEXT_MUTED, font=("Helvetica", 8, "italic"))
                empty_lbl.pack(anchor="sw", padx=6, pady=(0, 4))
        else:
            card.config(bg=BG_DARK, highlightbackground=BORDER_COLOR)
            day_lbl = tk.Label(card, text=str(day_num), bg=BG_DARK, fg=TEXT_MUTED, font=("Helvetica", 10))
            day_lbl.pack(anchor="nw", padx=6, pady=4)
            
        if is_today:
            card.config(highlightthickness=2, highlightcolor=SUCCESS_GREEN)
            today_badge = tk.Label(card, text=tm.tr("today_badge"), bg=SUCCESS_GREEN, fg=BG_DARK, font=("Helvetica", 7, "bold"), padx=3)
            today_badge.place(relx=1.0, rely=0.0, anchor="ne")
        else:
            today_badge = None
            
        def on_enter(e):
            if day_data:
                card.config(bg=BG_CARD_HEADER)
                for w in card.winfo_children():
                    if w != today_badge:
                        w.config(bg=BG_CARD_HEADER)
            else:
                card.config(highlightbackground=ACCENT_CYAN)
            
        def on_leave(e):
            if day_data:
                card.config(bg=BG_CARD)
                for w in card.winfo_children():
                    if w != today_badge:
                        w.config(bg=BG_CARD)
            else:
                card.config(highlightbackground=BORDER_COLOR)
                
        def on_single_click(e):
            self.show_day_details_sidebar(date_str, day_data)
            
        def on_double_click(e):
            self.on_day_clicked(date_str, day_data)
            
        def on_right_click(e):
            self.show_context_menu(e, date_str, day_data)
            
        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)
        card.bind("<Button-1>", on_single_click)
        card.bind("<Double-Button-1>", on_double_click)
        card.bind("<Button-2>", on_right_click)
        card.bind("<Button-3>", on_right_click)
        for w in card.winfo_children():
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
            w.bind("<Button-1>", on_single_click)
            w.bind("<Double-Button-1>", on_double_click)
            w.bind("<Button-2>", on_right_click)
            w.bind("<Button-3>", on_right_click)
            
    def fmt_stat(self, key, val_str):
        return fmt_stat(key, val_str)

    def show_day_details_sidebar(self, date_str, day_data):
        for w in self.details_scroll.scrollable_frame.winfo_children():
            w.destroy()
            
        try:
            dt = datetime.date.fromisoformat(date_str)
            formatted_date = tm.format_date_multiline(dt)
        except:
            formatted_date = date_str
            
        date_lbl = tk.Label(self.details_scroll.scrollable_frame, text=formatted_date, bg=BG_DARK, fg=TEXT_WHITE, font=("Helvetica", 12, "bold"), justify="center")
        date_lbl.pack(pady=(10, 15))
        
        if not day_data:
            lbl = tk.Label(self.details_scroll.scrollable_frame, text=tm.tr("no_task_logs_click"), bg=BG_DARK, fg=TEXT_MUTED, font=("Helvetica", 10, "italic"), justify="center", wraplength=250)
            lbl.pack(pady=50)
            return
        # Draw stats summary
        done_items = 0
        tot_items = 0
        earned_stars = 0.0
        tot_stars = 0.0
        for g in day_data["main_tasks"] + day_data["side_tasks"]:
            g_stars = float(g.get("stars", 0))
            tot_stars += g_stars
            tot_items += len(g.get("items", []))
            for item in g.get("items", []):
                item_stars = g_stars * (float(item.get("percent", 0.0)) / 100.0)
                if item.get("done"):
                    done_items += 1
                    earned_stars += item_stars
                    
        l1 = self.fmt_stat("tasks_done", f"{done_items}/{tot_items}")
        l2 = self.fmt_stat("stars_earned", f"⭐ {earned_stars:.1f} / {tot_stars:.0f}")
        stats_txt = f"{l1}\n{l2}"
        stats_lbl = tk.Label(self.details_scroll.scrollable_frame, text=shape_for_display(stats_txt), bg=BG_DARK, fg=ACCENT_CYAN, font=("Helvetica", 10, "bold"), justify="center")
        stats_lbl.pack(pady=5)
        
        # Divider line
        div = tk.Frame(self.details_scroll.scrollable_frame, bg=BORDER_COLOR, height=1)
        div.pack(fill="x", pady=10)
        
        # Display Tasks List
        if day_data["main_tasks"]:
            lbl = tk.Label(self.details_scroll.scrollable_frame, text=tm.tr("main_missions"), bg=BG_DARK, fg=ACCENT_PURPLE, font=("Helvetica", 9, "bold"))
            lbl.pack(anchor="w", pady=(5, 2))
            for g in day_data["main_tasks"]:
                disp_g_title = shape_for_display(g['title']) if tm._current_language == "Arabic" else g['title']
                g_lbl = tk.Label(self.details_scroll.scrollable_frame, text=f"• {disp_g_title} (⭐ {g['stars']})", bg=BG_DARK, fg=TEXT_WHITE, font=("Helvetica", 9, "bold"), anchor="w")
                g_lbl.pack(fill="x", padx=10)
                for item in g.get("items", []):
                    check = "✓" if item.get("done") else "○"
                    disp_it_name = shape_for_display(item.get('name', '')) if tm._current_language == "Arabic" else item.get('name', '')
                    item_lbl = tk.Label(self.details_scroll.scrollable_frame, text=f"  {check} {disp_it_name} ({item.get('percent')}%)", 
                                        bg=BG_DARK, fg=SUCCESS_GREEN if item.get("done") else TEXT_MUTED, font=("Helvetica", 9), anchor="w", justify="left")
                    item_lbl.pack(fill="x", padx=15)
                    
        if day_data["side_tasks"]:
            lbl = tk.Label(self.details_scroll.scrollable_frame, text=tm.tr("side_missions"), bg=BG_DARK, fg=ACCENT_CYAN, font=("Helvetica", 9, "bold"))
            lbl.pack(anchor="w", pady=(10, 2))
            for g in day_data["side_tasks"]:
                disp_g_title = shape_for_display(g['title']) if tm._current_language == "Arabic" else g['title']
                g_lbl = tk.Label(self.details_scroll.scrollable_frame, text=f"• {disp_g_title} (⭐ {g['stars']})", bg=BG_DARK, fg=TEXT_WHITE, font=("Helvetica", 9, "bold"), anchor="w")
                g_lbl.pack(fill="x", padx=10)
                for item in g.get("items", []):
                    check = "✓" if item.get("done") else "○"
                    disp_it_name = shape_for_display(item.get('name', '')) if tm._current_language == "Arabic" else item.get('name', '')
                    item_lbl = tk.Label(self.details_scroll.scrollable_frame, text=f"  {check} {disp_it_name} ({item.get('percent')}%)", 
                                        bg=BG_DARK, fg=SUCCESS_GREEN if item.get("done") else TEXT_MUTED, font=("Helvetica", 9), anchor="w", justify="left")
                    item_lbl.pack(fill="x", padx=15)
                    
        # Divider line for AI comment
        if day_data.get("ai_comment"):
            div2 = tk.Frame(self.details_scroll.scrollable_frame, bg=BORDER_COLOR, height=1)
            div2.pack(fill="x", pady=15)
            
            lbl = tk.Label(self.details_scroll.scrollable_frame, text=tm.tr("ai_daily_insight"), bg=BG_DARK, fg=ACCENT_CYAN, font=("Helvetica", 10, "bold"), anchor="w")
            lbl.pack(fill="x", pady=(0, 8))
            
            # Professional Callout Card
            comment_card = tk.Frame(self.details_scroll.scrollable_frame, bg=BG_CARD, bd=0, highlightbackground=BORDER_COLOR, highlightthickness=1)
            comment_card.pack(fill="x", pady=5)
            
            accent_bar = tk.Frame(comment_card, bg=ACCENT_CYAN, width=3)
            accent_bar.pack(side="left", fill="y")
            
            _ar = tm._current_language == "Arabic"
            _justify = "right" if _ar else "left"
            _anchor = "ne" if _ar else "nw"
            
            comment_lbl = tk.Label(comment_card, text=shape_for_display(day_data["ai_comment"]), bg=BG_CARD, fg=TEXT_WHITE, 
                                   font=("Helvetica", 9, "italic"), justify=_justify, anchor=_anchor)
            comment_lbl.pack(side="left", fill="both", expand=True, padx=12, pady=12)
            comment_card.bind("<Configure>", lambda event, l=comment_lbl: l.config(wraplength=event.width - 30))
            
        # Render Coach Small Advice if present
        if day_data.get("small_advice"):
            div3 = tk.Frame(self.details_scroll.scrollable_frame, bg=BORDER_COLOR, height=1)
            div3.pack(fill="x", pady=15)
            
            lbl = tk.Label(self.details_scroll.scrollable_frame, text=tm.tr("coach_small_advice"), bg=BG_DARK, fg=ACCENT_CYAN, font=("Helvetica", 10, "bold"), anchor="w")
            lbl.pack(fill="x", pady=(0, 8))
            
            card = tk.Frame(self.details_scroll.scrollable_frame, bg=BG_CARD, bd=0, highlightbackground=BORDER_COLOR, highlightthickness=1)
            card.pack(fill="x", pady=5)
            
            bar = tk.Frame(card, bg=ACCENT_CYAN, width=3)
            bar.pack(side="left", fill="y")
            
            _ar = tm._current_language == "Arabic"
            _justify = "right" if _ar else "left"
            _anchor = "ne" if _ar else "nw"
            
            txt = tk.Label(card, text=shape_for_display(day_data["small_advice"]), bg=BG_CARD, fg=TEXT_WHITE, 
                           font=("Helvetica", 9), justify=_justify, anchor=_anchor)
            txt.pack(side="left", fill="both", expand=True, padx=12, pady=12)
            card.bind("<Configure>", lambda event, l=txt: l.config(wraplength=event.width - 30))
            
        # Render Coach Deep Advice if present
        if day_data.get("deep_advice"):
            div4 = tk.Frame(self.details_scroll.scrollable_frame, bg=BORDER_COLOR, height=1)
            div4.pack(fill="x", pady=15)
            
            lbl = tk.Label(self.details_scroll.scrollable_frame, text=tm.tr("coach_deep_advice"), bg=BG_DARK, fg=ACCENT_PURPLE, font=("Helvetica", 10, "bold"), anchor="w")
            lbl.pack(fill="x", pady=(0, 8))
            
            card = tk.Frame(self.details_scroll.scrollable_frame, bg=BG_CARD, bd=0, highlightbackground=BORDER_COLOR, highlightthickness=1)
            card.pack(fill="x", pady=5)
            
            bar = tk.Frame(card, bg=ACCENT_PURPLE, width=3)
            bar.pack(side="left", fill="y")
            
            _ar = tm._current_language == "Arabic"
            _justify = "right" if _ar else "left"
            _anchor = "ne" if _ar else "nw"
            
            txt = tk.Label(card, text=shape_for_display(day_data["deep_advice"]), bg=BG_CARD, fg=TEXT_WHITE, 
                           font=("Helvetica", 9), justify=_justify, anchor=_anchor)
            txt.pack(side="left", fill="both", expand=True, padx=12, pady=12)
            card.bind("<Configure>", lambda event, l=txt: l.config(wraplength=event.width - 30))
            
    def on_day_clicked(self, date_str, day_data):
        if day_data:
            # Directly open tracker screen
            self.parent.show_daily_tracker(date_str, return_screen="calendar")
        else:
            # Initialize dialog choice
            choice_diag = InitializeDayDialog(self, date_str)
            self.wait_window(choice_diag)
            if choice_diag.result == "blank":
                self.parent.show_daily_tracker(date_str, blueprint_data={"main_tasks": [], "side_tasks": []}, return_screen="calendar")
            elif choice_diag.result == "blueprint" and choice_diag.result_blueprint:
                self.parent.show_daily_tracker(date_str, blueprint_data=choice_diag.result_blueprint, return_screen="calendar")
        
    def prev_month(self):
        self.current_month -= 1
        if self.current_month < 1:
            self.current_month = 12
            self.current_year -= 1
        self.render_calendar()
        self.clear_details_sidebar()
        
    def next_month(self):
        self.current_month += 1
        if self.current_month > 12:
            self.current_month = 1
            self.current_year += 1
        self.render_calendar()
        self.clear_details_sidebar()

    def show_context_menu(self, event, date_str, day_data):
        menu = tk.Menu(self, tearoff=0, bg=BG_CARD, fg=TEXT_WHITE, activebackground=ACCENT_PURPLE, activeforeground=BG_DARK)
        if day_data:
            menu.add_command(label=tm.tr("download_paper"), command=lambda: self.parent.show_export_dialog(date_str, day_data, export_type="both"))
        menu.add_command(label=tm.tr("view_memo"), command=lambda: self.parent.show_diary_screen(date_str, return_screen="calendar"))
        menu.tk_popup(event.x_root, event.y_root)


class FormatSelectionDialog(tk.Toplevel):
    def __init__(self, parent, date_str):
        super().__init__(parent)
        self.title(tm.tr("choose_format"))
        self.configure(bg=BG_DARK)
        self.geometry("320x180")
        self.resizable(False, False)
        self.transient(parent)
        
        # Center
        x = parent.winfo_rootx() + (parent.winfo_width() / 2) - 160
        y = parent.winfo_rooty() + (parent.winfo_height() / 2) - 90
        self.geometry(f"+{int(x)}+{int(y)}")
        
        self.result = None
        
        lbl = tk.Label(self, text=f"{tm.tr('export_sheet_for')}\n{date_str}", bg=BG_DARK, fg=TEXT_WHITE, font=("Helvetica", 11, "bold"), justify="center")
        lbl.pack(pady=15)
        
        btn_frame = tk.Frame(self, bg=BG_DARK)
        btn_frame.pack(pady=10)
        
        png_btn = tk.Button(btn_frame, text=tm.tr("png_image"), width=12, bg=ACCENT_PURPLE, fg=TEXT_WHITE, activebackground=GLOW_COLOR, activeforeground=TEXT_WHITE, relief="flat", font=("Helvetica", 10, "bold"), command=self.on_png)
        png_btn.pack(side="left", padx=10)
        
        pdf_btn = tk.Button(btn_frame, text=tm.tr("pdf_document"), width=12, bg=ACCENT_CYAN, fg=BG_DARK, activebackground=GLOW_COLOR, activeforeground=BG_DARK, relief="flat", font=("Helvetica", 10, "bold"), command=self.on_pdf)
        pdf_btn.pack(side="right", padx=10)
        
        cancel_btn = tk.Button(self, text=tm.tr("cancel"), bg=BG_DARK, fg=TEXT_MUTED, relief="flat", font=("Helvetica", 9), command=self.destroy)
        cancel_btn.pack(pady=(5, 0))
        
        self.wait_visibility()
        self.grab_set()
        
    def on_png(self):
        self.result = "png"
        self.destroy()
        
    def on_pdf(self):
        self.result = "pdf"
        self.destroy()


class DailyDiaryScreen(tk.Frame):
    """
    Rich Text Daily Diary / Memo Screen.
    Saves formatted notes to SQLite with navigation and styling toolbars.
    """
    def __init__(self, parent, date_str=None, return_screen=None):
        super().__init__(parent, bg=BG_DARK)
        self.parent = parent
        self.date_str = date_str or datetime.date.today().isoformat()
        self.return_screen = return_screen
        
        self.active_typing_tags = {"bold": False, "italic": False, "size": 12, "color": None}
        self.preset_btns = {}
        self.logical_lines = [""]
        self.line_styles = [[]]
        self._updating_size = False  # Guard to prevent recursive size apply
        
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self.setup_header()
        self.setup_toolbar()
        self.setup_text_area()
        self.load_diary_data()
        
    def setup_header(self):
        header = tk.Frame(self, bg=BG_DARK, height=65)
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 5))
        header.grid_columnconfigure(1, weight=1)
        
        back_btn = tk.Button(header, text=tm.tr("menu_back"), bg=BG_CARD, fg=TEXT_WHITE, relief="flat",
                             activebackground=ACCENT_PURPLE, activeforeground=BG_DARK, font=("Helvetica", 10, "bold"),
                             padx=12, pady=6, command=self.confirm_and_exit)
        back_btn.grid(row=0, column=0, sticky="w")
        back_btn.bind("<Enter>", lambda e=None: back_btn.config(bg=ACCENT_PURPLE, fg=BG_DARK))
        back_btn.bind("<Leave>", lambda e=None: back_btn.config(bg=BG_CARD, fg=TEXT_WHITE))
        
        # Center Date Navigator
        nav_frame = tk.Frame(header, bg=BG_DARK)
        nav_frame.grid(row=0, column=1)
        
        prev_btn = tk.Button(nav_frame, text="◀", bg=BG_DARK, fg=TEXT_MUTED, relief="flat",
                             font=("Helvetica", 12, "bold"), command=self.prev_day)
        prev_btn.pack(side="left", padx=10)
        prev_btn.bind("<Enter>", lambda e: prev_btn.config(fg=ACCENT_CYAN))
        prev_btn.bind("<Leave>", lambda e: prev_btn.config(fg=TEXT_MUTED))
        
        self.date_lbl = tk.Label(nav_frame, text="", bg=BG_DARK, fg=TEXT_WHITE, font=("Helvetica", 14, "bold"))
        self.date_lbl.pack(side="left", padx=10)
        self.update_date_label()
        
        next_btn = tk.Button(nav_frame, text="▶", bg=BG_DARK, fg=TEXT_MUTED, relief="flat",
                             font=("Helvetica", 12, "bold"), command=self.next_day)
        next_btn.pack(side="left", padx=10)
        next_btn.bind("<Enter>", lambda e: next_btn.config(fg=ACCENT_CYAN))
        next_btn.bind("<Leave>", lambda e: next_btn.config(fg=TEXT_MUTED))
        
        # Download Button
        dl_btn = tk.Button(header, text="📥", bg=BG_CARD, fg=TEXT_WHITE, relief="flat",
                           activebackground=ACCENT_CYAN, activeforeground=BG_DARK, font=("Helvetica", 10, "bold"),
                           padx=12, pady=6, command=lambda: self.parent.show_export_dialog(self.date_str, {}, export_type="memo_only"))
        dl_btn.grid(row=0, column=2, sticky="e", padx=(0, 5))
        dl_btn.bind("<Enter>", lambda e=None: dl_btn.config(bg=ACCENT_CYAN, fg=BG_DARK))
        dl_btn.bind("<Leave>", lambda e=None: dl_btn.config(bg=BG_CARD, fg=TEXT_WHITE))
        
        # Save Button
        save_btn = tk.Button(header, text=tm.tr("save") if hasattr(tm, "tr") and tm.tr("save") else "Save", bg=BG_CARD, fg=TEXT_WHITE, relief="flat",
                             activebackground=SUCCESS_GREEN, activeforeground=BG_DARK, font=("Helvetica", 10, "bold"),
                             padx=12, pady=6, command=self.save_diary_data)
        save_btn.grid(row=0, column=3, sticky="e")
        save_btn.bind("<Enter>", lambda e: save_btn.config(bg=SUCCESS_GREEN, fg=BG_DARK))
        save_btn.bind("<Leave>", lambda e: save_btn.config(bg=BG_CARD, fg=TEXT_WHITE))
        
    def setup_toolbar(self):
        self.toolbar = tk.Frame(self, bg=BG_CARD, height=40, highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.toolbar.grid(row=1, column=0, sticky="ew", padx=20, pady=(5, 5))
        
        # Style buttons
        self.bold_btn = tk.Button(self.toolbar, text="𝐁", bg=BG_DARK, fg=TEXT_WHITE, relief="flat",
                             font=("Helvetica", 10, "bold"), padx=10, command=self.toggle_bold)
        self.bold_btn.pack(side="left", padx=5, pady=5)
        
        self.italic_btn = tk.Button(self.toolbar, text="𝑰", bg=BG_DARK, fg=TEXT_WHITE, relief="flat",
                               font=("Helvetica", 10, "bold"), padx=10, command=self.toggle_italic)
        self.italic_btn.pack(side="left", padx=5, pady=5)
        
        self.color_btn = tk.Button(self.toolbar, text="🎨", bg=BG_DARK, fg=TEXT_WHITE, relief="flat",
                              font=("Helvetica", 10), padx=8, command=self.choose_color)
        self.color_btn.pack(side="left", padx=(5, 2), pady=5)
        
        # Color swatch — shows currently selected color
        self.color_swatch = tk.Canvas(self.toolbar, width=22, height=22, bg=BG_CARD,
                                      highlightbackground=BORDER_COLOR, highlightthickness=1,
                                      cursor="hand2")
        self.color_swatch.pack(side="left", padx=(0, 5), pady=5)
        self.color_swatch.bind("<Button-1>", lambda e: self.choose_color())
        self._draw_color_swatch(None)
        
        # Preset colors
        presets = [
            ("#ff4d6d", "Red/Pink"),
            ("#2ecc71", "Green"),
            ("#00d2d3", "Cyan"),
            ("#ff9f43", "Orange"),
            ("#ffffff", "White")
        ]
        tk.Label(self.toolbar, text="|", bg=BG_CARD, fg=TEXT_MUTED).pack(side="left", padx=5)
        for color, name in presets:
            btn = tk.Button(self.toolbar, text="●", bg=BG_DARK, fg=color, relief="flat",
                            font=("Helvetica", 12), command=lambda c=color: self.apply_color(c))
            btn.pack(side="left", padx=2)
            self.preset_btns[color] = btn
            
        # Font size dropdown menu
        tk.Label(self.toolbar, text="|", bg=BG_CARD, fg=TEXT_MUTED).pack(side="left", padx=5)
        self.size_var = tk.StringVar(value="12")
        self.size_menu = tk.OptionMenu(self.toolbar, self.size_var, "10", "12", "14", "16", "18", "20", "24", "28", "32", command=self.apply_size)
        self.size_menu.config(bg=BG_DARK, fg=TEXT_WHITE, activebackground=ACCENT_PURPLE, activeforeground=BG_DARK, relief="flat", highlightthickness=0, font=("Helvetica", 9, "bold"))
        self.size_menu["menu"].config(bg=BG_CARD, fg=TEXT_WHITE, activebackground=ACCENT_PURPLE, activeforeground=BG_DARK)
        self.size_menu.pack(side="left", padx=5, pady=5)
            
        # Warning/Info label inside toolbar right-aligned
        self.status_lbl = tk.Label(self.toolbar, text="", bg=BG_CARD, fg=GLOW_COLOR, font=("Helvetica", 9, "italic"))
        self.status_lbl.pack(side="right", padx=15)
        
    def setup_text_area(self):
        container = tk.Frame(self, bg=BG_DARK)
        container.grid(row=2, column=0, sticky="nsew", padx=20, pady=(5, 15))
        
        self.memo_text = tk.Text(container, bg=BG_CARD, fg=TEXT_WHITE, insertbackground=ACCENT_CYAN,
                                 selectbackground=ACCENT_PURPLE, selectforeground=TEXT_WHITE,
                                 borderwidth=1, highlightbackground=BORDER_COLOR, highlightthickness=1,
                                 relief="flat", font=("DejaVu Sans", 12), wrap="word", padx=15, pady=15)
        self.memo_text.pack(side="left", fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.memo_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.memo_text.configure(yscrollcommand=scrollbar.set)
        
        # Configure standard formatting tags
        self.memo_text.tag_configure("bold", font=("DejaVu Sans", 12, "bold"))
        self.memo_text.tag_configure("italic", font=("DejaVu Sans", 12, "italic"))
        self.memo_text.tag_configure("bold_italic", font=("DejaVu Sans", 12, "bold italic"))
        self.memo_text.tag_configure("rtl", justify="right")
        self.memo_text.tag_configure("ltr", justify="left")
        
        self.memo_text.bind("<KeyRelease>", self.on_text_modified)
        self.memo_text.bind("<ButtonRelease-1>", self.update_toolbar_active_states)
        self.memo_text.bind("<KeyPress>", self.on_key_pressed)
        self.memo_text.bind("<<Copy>>", lambda e: (self.handle_copy(), "break")[1])
        self.memo_text.bind("<<Cut>>", lambda e: (self.handle_cut(), "break")[1])
        self.memo_text.bind("<<Paste>>", lambda e: (self.handle_paste(), "break")[1])
        
    def update_date_label(self):
        try:
            dt = datetime.date.fromisoformat(self.date_str)
            lbl_text = tm.format_date(dt)
        except:
            lbl_text = self.date_str
        self.date_lbl.config(text=lbl_text)
        
    def on_text_modified(self, event=None):
        self.update_all_line_justifications()

    def prev_day(self):
        if self.save_diary_data() is False:
            return
        try:
            curr_d = datetime.date.fromisoformat(self.date_str)
            prev_d = curr_d - datetime.timedelta(days=1)
            self.date_str = prev_d.isoformat()
            self.update_date_label()
            self.load_diary_data()
        except Exception as e:
            print(f"Error navigating to prev day: {e}")

    def next_day(self):
        if self.save_diary_data() is False:
            return
        try:
            curr_d = datetime.date.fromisoformat(self.date_str)
            next_d = curr_d + datetime.timedelta(days=1)
            self.date_str = next_d.isoformat()
            self.update_date_label()
            self.load_diary_data()
        except Exception as e:
            print(f"Error navigating to next day: {e}")

    def get_default_style(self):
        return {
            "bold": bool(self.active_typing_tags["bold"]),
            "italic": bool(self.active_typing_tags["italic"]),
            "size": int(self.active_typing_tags["size"]),
            "color": self.active_typing_tags["color"]
        }

    def ensure_line_styles(self):
        while len(self.line_styles) < len(self.logical_lines):
            self.line_styles.append([])
        for line_idx, raw_line in enumerate(self.logical_lines):
            styles = self.line_styles[line_idx]
            while len(styles) < len(raw_line):
                styles.append(self.get_default_style())
            if len(styles) > len(raw_line):
                self.line_styles[line_idx] = styles[:len(raw_line)]

    def load_diary_data(self):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT content FROM daily_diary WHERE date = ?", (self.date_str,))
        row = c.fetchone()
        conn.close()
        
        self.memo_text.delete("1.0", "end")
        
        # Configure language-specific details
        _ar = tm._current_language == "Arabic"
        font_family = "Amiri" if _ar else "DejaVu Sans"
        self.memo_text.config(font=(font_family, 12))
        
        # Configure standard formatting tags dynamically to match font family
        self.memo_text.tag_configure("bold", font=(font_family, 12, "bold"))
        self.memo_text.tag_configure("italic", font=(font_family, 12, "italic"))
        self.memo_text.tag_configure("bold_italic", font=(font_family, 12, "bold italic"))
        
        if row:
            try:
                data = json.loads(row[0])
                plain_text = data.get("text", "")
                self.logical_lines = plain_text.split('\n')
                self.line_styles = []
                for line_idx, raw_line in enumerate(self.logical_lines):
                    line_styles = [{
                        "bold": False, "italic": False, "size": 12, "color": None
                    } for _ in range(len(raw_line))]
                    self.line_styles.append(line_styles)
                    
                tags_dict = data.get("tags", {})
                for tag_name, ranges in tags_dict.items():
                    if tag_name.startswith("style_"):
                        parts = tag_name.split('_')
                        if len(parts) == 5:
                            bold = parts[1] == "1"
                            italic = parts[2] == "1"
                            size = int(parts[3])
                            color = parts[4] if parts[4] != "default" else None
                            for idx in range(0, len(ranges), 2):
                                if idx + 1 < len(ranges):
                                    try:
                                        l_num, c_num = map(int, ranges[idx].split('.'))
                                        l_end_num, c_end_num = map(int, ranges[idx+1].split('.'))
                                        l_idx = l_num - 1
                                        c1, c2 = min(c_num, c_end_num), max(c_num, c_end_num)
                                        if 0 <= l_idx < len(self.line_styles):
                                            for c in range(c1, min(c2, len(self.line_styles[l_idx]))):
                                                self.line_styles[l_idx][c]["bold"] = bold
                                                self.line_styles[l_idx][c]["italic"] = italic
                                                self.line_styles[l_idx][c]["size"] = size
                                                self.line_styles[l_idx][c]["color"] = color
                                    except:
                                        pass
                self.sync_all_display()
                self.status_lbl.config(text=tm.tr("diary_loaded") if hasattr(tm, "tr") and tm.tr("diary_loaded") else "Diary loaded", fg=SUCCESS_GREEN)
            except Exception as e:
                print(f"Error loading diary JSON: {e}")
        else:
            self.logical_lines = [""]
            self.line_styles = [[]]
            self.sync_all_display()
            warning_msg = tm.tr("no_memo_warning") if hasattr(tm, "tr") and tm.tr("no_memo_warning") else "No memo recorded for this day."
            self.status_lbl.config(text=warning_msg, fg=GLOW_COLOR)

    def save_diary_data(self):
        plain_text = "\n".join(self.logical_lines)
        if plain_text.strip() and not is_english_or_french(plain_text):
            err_msg = "The memo only supports English and French. You cannot save other languages."
            if tm._current_language == "French":
                err_msg = "Le mémo ne prend en charge que l'anglais et le français. Vous ne pouvez pas enregistrer dans d'autres langues."
            messagebox.showerror(tm.tr("error") or "Error", err_msg)
            self.status_lbl.config(text="Validation error", fg="#ff4d4d")
            return False
            
        tags_dict = {}
        for line_idx, styles in enumerate(self.line_styles):
            line_num = line_idx + 1
            for col_idx, st in enumerate(styles):
                tag_name = self.get_or_create_style_tag(st["bold"], st["italic"], st["size"], st["color"])
                if tag_name not in tags_dict:
                    tags_dict[tag_name] = []
                tags_dict[tag_name].extend([f"{line_num}.{col_idx}", f"{line_num}.{col_idx+1}"])
                    
        content_json = json.dumps({
            "text": plain_text,
            "tags": tags_dict
        })
        
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO daily_diary (date, content) VALUES (?, ?)", (self.date_str, content_json))
            conn.commit()
            conn.close()
            self.status_lbl.config(text=tm.tr("diary_saved") if hasattr(tm, "tr") and tm.tr("diary_saved") else "Diary saved", fg=SUCCESS_GREEN)
            self.after(2000, lambda: self.status_lbl.config(text=""))
        except Exception as e:
            print(f"Error saving diary: {e}")
            self.status_lbl.config(text="Error saving diary", fg="#ff4d4d")

    def get_or_create_style_tag(self, bold, italic, size, color):
        tag_name = f"style_{1 if bold else 0}_{1 if italic else 0}_{size}_{color or 'default'}"
        
        if tag_name not in self.memo_text.tag_names():
            _ar = tm._current_language == "Arabic"
            family = "Amiri" if _ar else "DejaVu Sans"
            
            style_parts = []
            if bold: style_parts.append("bold")
            if italic: style_parts.append("italic")
            style_str = " ".join(style_parts)
            
            self.memo_text.tag_configure(tag_name, font=(family, size, style_str))
            if color:
                self.memo_text.tag_configure(tag_name, foreground=color)
            else:
                self.memo_text.tag_configure(tag_name, foreground=TEXT_WHITE)
                
        return tag_name

    def get_char_style(self, index):
        tags = self.memo_text.tag_names(index)
        for t in tags:
            if t.startswith("style_"):
                parts = t.split('_')
                if len(parts) == 5:
                    bold = parts[1] == "1"
                    italic = parts[2] == "1"
                    size = int(parts[3])
                    color = parts[4] if parts[4] != "default" else None
                    return bold, italic, size, color
        return False, False, 12, None

    def apply_style_action(self, action_type, value=None):
        try:
            sel_first = self.memo_text.index("sel.first")
            sel_last = self.memo_text.index("sel.last")
            has_sel = True
        except tk.TclError:
            has_sel = False

        if not has_sel:
            if action_type == "bold":
                self.active_typing_tags["bold"] = not self.active_typing_tags["bold"]
            elif action_type == "italic":
                self.active_typing_tags["italic"] = not self.active_typing_tags["italic"]
            elif action_type == "size":
                self.active_typing_tags["size"] = value
            elif action_type == "color":
                if self.active_typing_tags["color"] == value:
                    self.active_typing_tags["color"] = None
                else:
                    self.active_typing_tags["color"] = value
            self.update_button_visuals()
            return

        first_line_num = int(sel_first.split('.')[0])
        first_vis_col = int(sel_first.split('.')[1])
        last_line_num = int(sel_last.split('.')[0])
        last_vis_col = int(sel_last.split('.')[1])

        first_idx = max(0, min(len(self.logical_lines) - 1, first_line_num - 1))
        last_idx = max(0, min(len(self.logical_lines) - 1, last_line_num - 1))

        self.ensure_line_styles()

        for line_idx in range(first_idx, last_idx + 1):
            raw_line = self.logical_lines[line_idx]
            direction = self.get_line_direction(raw_line)

            if line_idx == first_idx and line_idx == last_idx:
                c1 = self.visual_to_logical_col(raw_line, first_vis_col, direction)
                c2 = self.visual_to_logical_col(raw_line, last_vis_col, direction)
                start_c, end_c = min(c1, c2), max(c1, c2)
            elif line_idx == first_idx:
                c1 = self.visual_to_logical_col(raw_line, first_vis_col, direction)
                start_c, end_c = c1, len(raw_line)
            elif line_idx == last_idx:
                c2 = self.visual_to_logical_col(raw_line, last_vis_col, direction)
                start_c, end_c = 0, c2
            else:
                start_c, end_c = 0, len(raw_line)

            for c in range(start_c, end_c):
                if c < len(self.line_styles[line_idx]):
                    st = self.line_styles[line_idx][c]
                    if action_type == "bold":
                        st["bold"] = not st["bold"]
                    elif action_type == "italic":
                        st["italic"] = not st["italic"]
                    elif action_type == "size":
                        st["size"] = value
                    elif action_type == "color":
                        st["color"] = value

        self.sync_all_display()
        self.update_button_visuals()

    def toggle_bold(self):
        self.apply_style_action("bold")

    def toggle_italic(self):
        self.apply_style_action("italic")

    def _draw_color_swatch(self, color_hex):
        """Draw the color preview square inside the swatch canvas."""
        self.color_swatch.delete("all")
        fill = color_hex if color_hex else BG_DARK
        self.color_swatch.create_rectangle(2, 2, 20, 20, fill=fill, outline=BORDER_COLOR, width=1)
        # Draw a small 'X' if no color active
        if not color_hex:
            self.color_swatch.create_line(4, 4, 18, 18, fill=TEXT_MUTED, width=1)
            self.color_swatch.create_line(18, 4, 4, 18, fill=TEXT_MUTED, width=1)

    def choose_color(self):
        from tkinter import colorchooser
        color = colorchooser.askcolor(title="Choose Text Color", initialcolor=self.active_typing_tags.get("color") or "#ffffff")[1]
        if color:
            self.apply_color(color)

    def apply_color(self, color_hex):
        self.apply_style_action("color", color_hex)
        # Swatch is updated by update_button_visuals called inside apply_style_action

    def apply_size(self, size_str):
        if self._updating_size:
            return
        try:
            self.apply_style_action("size", int(size_str))
        except:
            pass

    def handle_select_all(self):
        try:
            self.memo_text.tag_add("sel", "1.0", "end-1c")
            self.memo_text.mark_set("insert", "1.0")
            return "break"
        except Exception as e:
            print(f"Error handling select all: {e}")

    def on_key_pressed(self, event):
        is_ctrl = bool(event.state & 0x4)
        k_lower = event.keysym.lower() if event.keysym else ""
        code = getattr(event, "keycode", None)

        if is_ctrl:
            # Select All: 'a', keycode 38 (physical A on QWERTY), or Arabic sheen
            if k_lower in ("a", "arabic_sheen", "sheen") or code == 38:
                self.handle_select_all()
                return "break"
            # Copy: 'c', keycode 54
            elif k_lower in ("c", "arabic_array", "array") or code == 54:
                self.handle_copy()
                return "break"
            # Cut: 'x', keycode 53
            elif k_lower in ("x", "arabic_hamzaonwaw", "hamzaonwaw") or code == 53:
                self.handle_cut()
                return "break"
            # Paste: 'v', keycode 55
            elif k_lower in ("v", "arabic_ra", "ra") or code == 55:
                self.handle_paste()
                return "break"
            return

        # Normal editing keys
        if k_lower in ("backspace", "backspace") or code == 22:
            self.handle_backspace()
            return "break"
        elif k_lower in ("return", "kp_enter") or code in (36, 104):
            self.handle_return()
            return "break"
        elif k_lower == "delete" or code == 119:
            self.handle_delete()
            return "break"
        elif event.char and event.char.isprintable():
            self.handle_char_input(event.char)
            return "break"

    def delete_selection(self):
        try:
            sel_first = self.memo_text.index("sel.first")
            sel_last = self.memo_text.index("sel.last")
        except tk.TclError:
            return None

        # 1. Select-All / Full document deletion check
        if self.memo_text.compare(sel_first, "==", "1.0") and self.memo_text.compare(sel_last, ">=", "end-1c"):
            self.logical_lines = [""]
            self.line_styles = [[]]
            self.sync_all_display()
            self.memo_text.mark_set("insert", "1.0")
            return "1.0"

        first_line_num = int(sel_first.split('.')[0])
        first_vis_col = int(sel_first.split('.')[1])
        last_line_num = int(sel_last.split('.')[0])
        last_vis_col = int(sel_last.split('.')[1])

        first_idx = max(0, min(len(self.logical_lines) - 1, first_line_num - 1))
        last_idx = max(0, min(len(self.logical_lines) - 1, last_line_num - 1))

        self.ensure_line_styles()

        if first_idx == last_idx:
            raw_line = self.logical_lines[first_idx]
            styles = self.line_styles[first_idx]
            direction = self.get_line_direction(raw_line)
            
            c1 = self.visual_to_logical_col(raw_line, first_vis_col, direction)
            c2 = self.visual_to_logical_col(raw_line, last_vis_col, direction)
            log_start = min(c1, c2)
            log_end = max(c1, c2)

            self.logical_lines[first_idx] = raw_line[:log_start] + raw_line[log_end:]
            self.line_styles[first_idx] = styles[:log_start] + styles[log_end:]
            self.sync_display_line(first_line_num)
            
            vis_pos = self.logical_to_visual_index(f"{first_line_num}.{log_start}")
            self.memo_text.mark_set("insert", vis_pos)
            return f"{first_line_num}.{log_start}"
        else:
            raw_first = self.logical_lines[first_idx]
            styles_first = self.line_styles[first_idx]
            dir_first = self.get_line_direction(raw_first)
            c_first = self.visual_to_logical_col(raw_first, first_vis_col, dir_first)
            kept_first = raw_first[:c_first]
            kept_styles_first = styles_first[:c_first]

            raw_last = self.logical_lines[last_idx]
            styles_last = self.line_styles[last_idx]
            dir_last = self.get_line_direction(raw_last)
            c_last = self.visual_to_logical_col(raw_last, last_vis_col, dir_last)

            if dir_last == "rtl":
                kept_last = raw_last[:c_last]
                kept_styles_last = styles_last[:c_last]
            else:
                kept_last = raw_last[c_last:]
                kept_styles_last = styles_last[c_last:]

            self.logical_lines[first_idx] = kept_first + kept_last
            self.line_styles[first_idx] = kept_styles_first + kept_styles_last
            del self.logical_lines[first_idx + 1 : last_idx + 1]
            del self.line_styles[first_idx + 1 : last_idx + 1]

            self.sync_all_display()
            vis_pos = self.logical_to_visual_index(f"{first_line_num}.{len(kept_first)}")
            self.memo_text.mark_set("insert", vis_pos)
            return f"{first_line_num}.{len(kept_first)}"

    def get_selected_logical_text(self):
        try:
            sel_first = self.memo_text.index("sel.first")
            sel_last = self.memo_text.index("sel.last")
        except tk.TclError:
            return ""

        first_line_num = int(sel_first.split('.')[0])
        first_vis_col = int(sel_first.split('.')[1])
        last_line_num = int(sel_last.split('.')[0])
        last_vis_col = int(sel_last.split('.')[1])

        first_idx = max(0, min(len(self.logical_lines) - 1, first_line_num - 1))
        last_idx = max(0, min(len(self.logical_lines) - 1, last_line_num - 1))

        if first_idx == last_idx:
            raw_line = self.logical_lines[first_idx]
            direction = self.get_line_direction(raw_line)
            c1 = self.visual_to_logical_col(raw_line, first_vis_col, direction)
            c2 = self.visual_to_logical_col(raw_line, last_vis_col, direction)
            log_start = min(c1, c2)
            log_end = max(c1, c2)
            return raw_line[log_start:log_end]
        else:
            copied_lines = []
            for idx in range(first_idx, last_idx + 1):
                raw_line = self.logical_lines[idx]
                direction = self.get_line_direction(raw_line)
                if idx == first_idx:
                    c = self.visual_to_logical_col(raw_line, first_vis_col, direction)
                    copied_lines.append(raw_line[c:])
                elif idx == last_idx:
                    c = self.visual_to_logical_col(raw_line, last_vis_col, direction)
                    copied_lines.append(raw_line[:c])
                else:
                    copied_lines.append(raw_line)
            return "\n".join(copied_lines)

    def handle_copy(self):
        try:
            sel_text = self.get_selected_logical_text()
            if sel_text:
                self.clipboard_clear()
                self.clipboard_append(sel_text)
        except Exception as e:
            print(f"Error handling copy: {e}")

    def handle_cut(self):
        try:
            sel_text = self.get_selected_logical_text()
            if sel_text:
                self.clipboard_clear()
                self.clipboard_append(sel_text)
                
            log_pos = self.delete_selection()
            if log_pos:
                self.sync_all_display()
                vis_pos = self.logical_to_visual_index(log_pos)
                self.memo_text.mark_set("insert", vis_pos)
        except Exception as e:
            print(f"Error handling cut: {e}")

    def handle_char_input(self, char):
        try:
            self.delete_selection()
            
            insert_idx = self.memo_text.index("insert")
            line_num = int(insert_idx.split('.')[0])
            col_idx = int(insert_idx.split('.')[1])
            
            line_idx = line_num - 1
            while len(self.logical_lines) <= line_idx:
                self.logical_lines.append("")
            while len(self.line_styles) <= line_idx:
                self.line_styles.append([])
                
            raw_line = self.logical_lines[line_idx]
            direction = self.get_line_direction(raw_line)
            
            logical_col = self.visual_to_logical_col(raw_line, col_idx, direction)
            self.logical_lines[line_idx] = raw_line[:logical_col] + char + raw_line[logical_col:]
            
            current_style = {
                "bold": bool(self.active_typing_tags["bold"]),
                "italic": bool(self.active_typing_tags["italic"]),
                "size": int(self.active_typing_tags["size"]),
                "color": self.active_typing_tags["color"]
            }
            self.line_styles[line_idx].insert(logical_col, current_style)
            
            self.sync_display_line(line_num)
            
            new_raw_line = self.logical_lines[line_idx]
            new_direction = self.get_line_direction(new_raw_line)
            new_logical_pos = logical_col + 1
            
            new_visual_col = self.logical_to_visual_col(new_raw_line, new_logical_pos, new_direction)
            self.memo_text.mark_set("insert", f"{line_num}.{new_visual_col}")
            self.memo_text.see("insert")
        except Exception as e:
            print(f"Error handling char input: {e}")

    def handle_backspace(self):
        try:
            log_pos = self.delete_selection()
            if log_pos:
                return
                
            insert_idx = self.memo_text.index("insert")
            line_num = int(insert_idx.split('.')[0])
            col_idx = int(insert_idx.split('.')[1])
            
            line_idx = line_num - 1
            raw_line = self.logical_lines[line_idx]
            direction = self.get_line_direction(raw_line)
            
            logical_col = self.visual_to_logical_col(raw_line, col_idx, direction)
            
            if logical_col > 0:
                del_col = logical_col - 1
                self.logical_lines[line_idx] = raw_line[:del_col] + raw_line[del_col + 1:]
                if line_idx < len(self.line_styles) and del_col < len(self.line_styles[line_idx]):
                    del self.line_styles[line_idx][del_col]
                    
                self.sync_display_line(line_num)
                
                new_raw_line = self.logical_lines[line_idx]
                new_direction = self.get_line_direction(new_raw_line)
                new_logical_pos = del_col
                
                new_visual_col = self.logical_to_visual_col(new_raw_line, new_logical_pos, new_direction)
                self.memo_text.mark_set("insert", f"{line_num}.{new_visual_col}")
                self.memo_text.see("insert")
            elif line_num > 1:
                self.merge_with_previous_line(line_num)
        except Exception as e:
            print(f"Error handling backspace: {e}")

    def handle_return(self):
        try:
            self.delete_selection()
            
            insert_idx = self.memo_text.index("insert")
            line_num = int(insert_idx.split('.')[0])
            col_idx = int(insert_idx.split('.')[1])
            
            line_idx = line_num - 1
            raw_line = self.logical_lines[line_idx]
            direction = self.get_line_direction(raw_line)
            
            logical_col = self.visual_to_logical_col(raw_line, col_idx, direction)
            styles = self.line_styles[line_idx] if line_idx < len(self.line_styles) else []
                
            self.logical_lines[line_idx] = raw_line[:logical_col]
            self.logical_lines.insert(line_idx + 1, raw_line[logical_col:])
            
            self.line_styles[line_idx] = styles[:logical_col]
            self.line_styles.insert(line_idx + 1, styles[logical_col:])
            
            self.sync_all_display()
            
            next_raw_line = self.logical_lines[line_idx + 1]
            next_direction = self.get_line_direction(next_raw_line)
            
            new_visual_col = self.logical_to_visual_col(next_raw_line, 0, next_direction)
            self.memo_text.mark_set("insert", f"{line_num + 1}.{new_visual_col}")
            self.memo_text.see("insert")
        except Exception as e:
            print(f"Error handling return: {e}")

    def handle_delete(self):
        try:
            log_pos = self.delete_selection()
            if log_pos:
                return
                
            insert_idx = self.memo_text.index("insert")
            line_num = int(insert_idx.split('.')[0])
            col_idx = int(insert_idx.split('.')[1])
            
            line_idx = line_num - 1
            raw_line = self.logical_lines[line_idx]
            direction = self.get_line_direction(raw_line)
            
            logical_col = self.visual_to_logical_col(raw_line, col_idx, direction)
            
            if logical_col < len(raw_line):
                del_col = logical_col
                self.logical_lines[line_idx] = raw_line[:del_col] + raw_line[del_col + 1:]
                if line_idx < len(self.line_styles) and del_col < len(self.line_styles[line_idx]):
                    del self.line_styles[line_idx][del_col]
                    
                self.sync_display_line(line_num)
                
                new_raw_line = self.logical_lines[line_idx]
                new_direction = self.get_line_direction(new_raw_line)
                
                new_visual_col = self.logical_to_visual_col(new_raw_line, logical_col, new_direction)
                self.memo_text.mark_set("insert", f"{line_num}.{new_visual_col}")
                self.memo_text.see("insert")
            elif line_num < len(self.logical_lines):
                self.merge_with_next_line(line_num)
        except Exception as e:
            print(f"Error handling delete: {e}")

    def merge_with_previous_line(self, line_num):
        try:
            line_idx = line_num - 1
            raw_line = self.logical_lines[line_idx]
            prev_line_idx = line_idx - 1
            prev_raw_line = self.logical_lines[prev_line_idx]
            prev_line_len = len(prev_raw_line)
            
            self.logical_lines[prev_line_idx] += raw_line
            while len(self.line_styles) <= line_idx:
                self.line_styles.append([])
            self.line_styles[prev_line_idx].extend(self.line_styles[line_idx])
            
            self.logical_lines.pop(line_idx)
            self.line_styles.pop(line_idx)
            
            self.sync_all_display()
            
            merged_raw_line = self.logical_lines[prev_line_idx]
            merged_direction = self.get_line_direction(merged_raw_line)
            
            new_visual_col = self.logical_to_visual_col(merged_raw_line, prev_line_len, merged_direction)
            self.memo_text.mark_set("insert", f"{line_num - 1}.{new_visual_col}")
            self.memo_text.see("insert")
        except Exception as e:
            print(f"Error merging with prev line: {e}")

    def merge_with_next_line(self, line_num):
        try:
            line_idx = line_num - 1
            raw_line = self.logical_lines[line_idx]
            line_len = len(raw_line)
            next_line_idx = line_idx + 1
            next_raw_line = self.logical_lines[next_line_idx]
            
            self.logical_lines[line_idx] += next_raw_line
            while len(self.line_styles) <= next_line_idx:
                self.line_styles.append([])
            self.line_styles[line_idx].extend(self.line_styles[next_line_idx])
            
            self.logical_lines.pop(next_line_idx)
            self.line_styles.pop(next_line_idx)
            
            self.sync_all_display()
            
            merged_raw_line = self.logical_lines[line_idx]
            merged_direction = self.get_line_direction(merged_raw_line)
            
            new_visual_col = self.logical_to_visual_col(merged_raw_line, line_len, merged_direction)
            self.memo_text.mark_set("insert", f"{line_num}.{new_visual_col}")
            self.memo_text.see("insert")
        except Exception as e:
            print(f"Error merging with next line: {e}")



    def handle_paste(self):
        try:
            self.delete_selection()
            pasted = self.clipboard_get()
            if not pasted:
                return
            
            pasted = pasted.replace('\r\n', '\n').replace('\r', '\n')
            pasted_lines = pasted.split('\n')
            
            insert_idx = self.memo_text.index("insert")
            line_num = int(insert_idx.split('.')[0])
            col_idx = int(insert_idx.split('.')[1])
            
            line_idx = line_num - 1
            while len(self.logical_lines) <= line_idx:
                self.logical_lines.append("")
            while len(self.line_styles) <= line_idx:
                self.line_styles.append([])
                
            orig_line = self.logical_lines[line_idx]
            direction = self.get_line_direction(orig_line)
            curr_col = self.visual_to_logical_col(orig_line, col_idx, direction)
            
            orig_styles = list(self.line_styles[line_idx])
            
            line_before = orig_line[:curr_col]
            styles_before = orig_styles[:curr_col]
            
            line_after = orig_line[curr_col:]
            styles_after = orig_styles[curr_col:]
            
            def make_paste_char_style():
                return {
                    "bold": bool(self.active_typing_tags.get("bold", False)),
                    "italic": bool(self.active_typing_tags.get("italic", False)),
                    "size": int(self.active_typing_tags.get("size", 12)),
                    "color": self.active_typing_tags.get("color", None)
                }

            if len(pasted_lines) == 1:
                paste_text = pasted_lines[0]
                paste_styles = [make_paste_char_style() for _ in range(len(paste_text))]
                
                new_line = line_before + paste_text + line_after
                new_styles = styles_before + paste_styles + styles_after
                
                self.logical_lines[line_idx] = new_line
                self.line_styles[line_idx] = new_styles
                
                self.sync_display_line(line_num)
                
                new_log_pos = curr_col + len(paste_text)
                new_dir = self.get_line_direction(new_line)
                new_vis_col = self.logical_to_visual_col(new_line, new_log_pos, new_dir)
                self.memo_text.mark_set("insert", f"{line_num}.{new_vis_col}")
                self.memo_text.see("insert")
            else:
                first_paste = pasted_lines[0]
                first_styles = [make_paste_char_style() for _ in range(len(first_paste))]
                
                last_paste = pasted_lines[-1]
                last_styles = [make_paste_char_style() for _ in range(len(last_paste))]
                
                self.logical_lines[line_idx] = line_before + first_paste
                self.line_styles[line_idx] = styles_before + first_styles
                
                middle_lines = []
                middle_styles = []
                for mid_text in pasted_lines[1:-1]:
                    middle_lines.append(mid_text)
                    middle_styles.append([make_paste_char_style() for _ in range(len(mid_text))])
                    
                final_line = last_paste + line_after
                final_styles = last_styles + styles_after
                
                insert_lines = middle_lines + [final_line]
                insert_styles = middle_styles + [final_styles]
                
                self.logical_lines[line_idx + 1:line_idx + 1] = insert_lines
                self.line_styles[line_idx + 1:line_idx + 1] = insert_styles
                
                target_line_num = line_num + len(pasted_lines) - 1
                target_line_idx = target_line_num - 1
                
                self.sync_all_display()
                
                target_line = self.logical_lines[target_line_idx]
                target_log_pos = len(last_paste)
                target_dir = self.get_line_direction(target_line)
                target_vis_col = self.logical_to_visual_col(target_line, target_log_pos, target_dir)
                self.memo_text.mark_set("insert", f"{target_line_num}.{target_vis_col}")
                self.memo_text.see("insert")
        except Exception as e:
            print(f"Error handling paste: {e}")

    def get_line_direction(self, text):
        if not text:
            return "rtl" if tm._current_language == "Arabic" else "ltr"
        for char in text:
            if '\u0600' <= char <= '\u06ff' or '\ufb50' <= char <= '\ufeff':
                return "rtl"
            elif 'a' <= char.lower() <= 'z':
                return "ltr"
        return "rtl" if tm._current_language == "Arabic" else "ltr"

    def shape_and_reverse_line_for_display(self, text):
        if not text:
            return ""
        direction = self.get_line_direction(text)
        try:
            from bidi.algorithm import get_display
            reshaper = get_shared_reshaper()
            base_d = 'R' if direction == "rtl" else 'L'
            return get_display(reshaper.reshape(text), base_dir=base_d)
        except Exception:
            return text

    def sync_display_line(self, line_num):
        line_idx = line_num - 1
        raw_line = self.logical_lines[line_idx]
        display_line = self.shape_and_reverse_line_for_display(raw_line)
        
        line_start = f"{line_num}.0"
        line_end = f"{line_num}.end"
        
        self.memo_text.delete(line_start, line_end)
        self.memo_text.insert(line_start, display_line)
        
        self.ensure_line_styles()
        styles = self.line_styles[line_idx]
        direction = self.get_line_direction(raw_line)
        
        for log_col in range(len(raw_line)):
            st = styles[log_col]
            tag_name = self.get_or_create_style_tag(st["bold"], st["italic"], st["size"], st["color"])
            
            vis_col = self.logical_to_visual_col(raw_line, log_col, direction)
            
            if direction == "rtl":
                vis_start = max(0, vis_col - 1)
                vis_end = vis_col
            else:
                vis_start = vis_col
                vis_end = min(len(display_line), vis_col + 1)
                
            self.memo_text.tag_add(tag_name, f"{line_num}.{vis_start}", f"{line_num}.{vis_end}")
            
        self.update_current_line_justification()

    def sync_all_display(self):
        self.memo_text.delete("1.0", "end")
        display_lines = []
        for raw_line in self.logical_lines:
            display_lines.append(self.shape_and_reverse_line_for_display(raw_line))
        self.memo_text.insert("1.0", "\n".join(display_lines))
        
        self.ensure_line_styles()
        for line_idx, raw_line in enumerate(self.logical_lines):
            line_num = line_idx + 1
            direction = self.get_line_direction(raw_line)
            styles = self.line_styles[line_idx]
            display_line = display_lines[line_idx]
            
            for log_col in range(len(raw_line)):
                st = styles[log_col]
                tag_name = self.get_or_create_style_tag(st["bold"], st["italic"], st["size"], st["color"])
                
                vis_col = self.logical_to_visual_col(raw_line, log_col, direction)
                
                if direction == "rtl":
                    vis_start = max(0, vis_col - 1)
                    vis_end = vis_col
                else:
                    vis_start = vis_col
                    vis_end = min(len(display_line), vis_col + 1)
                    
                self.memo_text.tag_add(tag_name, f"{line_num}.{vis_start}", f"{line_num}.{vis_end}")
                
        self.update_all_line_justifications()

    def visual_to_logical_col(self, raw_line, visual_col, direction):
        if direction == "ltr":
            return min(len(raw_line), max(0, visual_col))
        try:
            reshaped = get_shared_reshaper().reshape(raw_line)
            len_shaped = len(reshaped)
        except:
            len_shaped = len(raw_line)
        shaped_col = len_shaped - visual_col
        shaped_col = max(0, min(len_shaped, shaped_col))
        logical_col = 0
        s_idx = 0
        r_idx = 0
        while s_idx < shaped_col and r_idx < len(raw_line):
            if r_idx < len(raw_line) - 1 and raw_line[r_idx] == '\u0644' and raw_line[r_idx+1] in ('\u0622', '\u0623', '\u0625', '\u0627'):
                r_idx += 2
            else:
                r_idx += 1
            s_idx += 1
        return r_idx

    def logical_to_visual_col(self, raw_line, logical_col, direction):
        if direction == "ltr":
            return min(len(raw_line), max(0, logical_col))
        s_col = 0
        r_idx = 0
        while r_idx < logical_col and r_idx < len(raw_line):
            if r_idx < len(raw_line) - 1 and raw_line[r_idx] == '\u0644' and raw_line[r_idx+1] in ('\u0622', '\u0623', '\u0625', '\u0627'):
                r_idx += 2
            else:
                r_idx += 1
            s_col += 1
        try:
            reshaped = get_shared_reshaper().reshape(raw_line)
            len_shaped = len(reshaped)
        except:
            len_shaped = len(raw_line)
        visual_col = len_shaped - s_col
        return max(0, min(len_shaped, visual_col))

    def logical_to_visual_index(self, log_index):
        try:
            line_part, char_part = log_index.split('.')
            line_num = int(line_part)
            char_offset = int(char_part)
            
            line_idx = line_num - 1
            if 0 <= line_idx < len(self.logical_lines):
                raw_line = self.logical_lines[line_idx]
                direction = self.get_line_direction(raw_line)
                vis_col = self.logical_to_visual_col(raw_line, char_offset, direction)
                return f"{line_num}.{vis_col}"
            return log_index
        except:
            return log_index

    def visual_to_logical_index(self, vis_index):
        try:
            line_part, char_part = vis_index.split('.')
            line_num = int(line_part)
            char_offset = int(char_part)
            
            line_idx = line_num - 1
            if 0 <= line_idx < len(self.logical_lines):
                raw_line = self.logical_lines[line_idx]
                direction = self.get_line_direction(raw_line)
                log_col = self.visual_to_logical_col(raw_line, char_offset, direction)
                return f"{line_num}.{log_col}"
            return vis_index
        except:
            return vis_index

    def update_current_line_justification(self):
        try:
            insert_idx = self.memo_text.index("insert")
            line_num = insert_idx.split('.')[0]
            line_start = f"{line_num}.0"
            line_end = f"{line_num}.end"
            
            self.memo_text.tag_remove("rtl", line_start, line_end + " + 1 char")
            self.memo_text.tag_remove("ltr", line_start, line_end + " + 1 char")
            
            line_content = self.memo_text.get(line_start, line_end)
            if not line_content.strip():
                if tm._current_language == "Arabic":
                    self.memo_text.tag_add("rtl", line_start, line_end + " + 1 char")
                else:
                    self.memo_text.tag_add("ltr", line_start, line_end + " + 1 char")
                return
                
            has_arabic = any('\u0600' <= c <= '\u06ff' or '\ufb50' <= c <= '\ufeff' for c in line_content)
            if has_arabic:
                self.memo_text.tag_add("rtl", line_start, line_end + " + 1 char")
            else:
                self.memo_text.tag_add("ltr", line_start, line_end + " + 1 char")
        except Exception:
            pass

    def update_all_line_justifications(self):
        try:
            num_lines = int(self.memo_text.index("end-1c").split('.')[0])
            for line_num in range(1, num_lines + 1):
                line_start = f"{line_num}.0"
                line_end = f"{line_num}.end"
                
                self.memo_text.tag_remove("rtl", line_start, line_end + " + 1 char")
                self.memo_text.tag_remove("ltr", line_start, line_end + " + 1 char")
                
                line_content = self.memo_text.get(line_start, line_end)
                if not line_content.strip():
                    if tm._current_language == "Arabic":
                        self.memo_text.tag_add("rtl", line_start, line_end + " + 1 char")
                    else:
                        self.memo_text.tag_add("ltr", line_start, line_end + " + 1 char")
                    continue
                    
                has_arabic = any('\u0600' <= c <= '\u06ff' or '\ufb50' <= c <= '\ufeff' for c in line_content)
                if has_arabic:
                    self.memo_text.tag_add("rtl", line_start, line_end + " + 1 char")
                else:
                    self.memo_text.tag_add("ltr", line_start, line_end + " + 1 char")
        except Exception:
            pass

    def update_toolbar_active_states(self, event=None):
        try:
            start = self.memo_text.index("sel.first")
            bold, italic, size, color = self.get_char_style(start)
        except tk.TclError:
            index = self.memo_text.index("insert")
            try:
                if self.memo_text.compare(index, ">", "1.0"):
                    check_idx = f"{index} - 1 char"
                else:
                    check_idx = index
                bold, italic, size, color = self.get_char_style(check_idx)
            except:
                bold, italic, size, color = False, False, 12, None
                
        self.active_typing_tags["bold"] = bold
        self.active_typing_tags["italic"] = italic
        self.active_typing_tags["size"] = size
        self.active_typing_tags["color"] = color
        
        self.update_button_visuals()

    def update_button_visuals(self):
        if self.active_typing_tags["bold"]:
            self.bold_btn.config(bg=ACCENT_PURPLE, fg=BG_DARK)
        else:
            self.bold_btn.config(bg=BG_DARK, fg=TEXT_WHITE)
            
        if self.active_typing_tags["italic"]:
            self.italic_btn.config(bg=ACCENT_PURPLE, fg=BG_DARK)
        else:
            self.italic_btn.config(bg=BG_DARK, fg=TEXT_WHITE)
            
        # Update size dropdown without triggering apply_size callback
        active_size = str(self.active_typing_tags["size"])
        if self.size_var.get() != active_size:
            self._updating_size = True
            self.size_var.set(active_size)
            self._updating_size = False
            
        active_color = self.active_typing_tags["color"]
        preset_matched = False
        
        for c_hex, btn in self.preset_btns.items():
            if active_color == c_hex:
                btn.config(bg=ACCENT_CYAN, fg=BG_DARK)
                preset_matched = True
            else:
                btn.config(bg=BG_DARK, fg=c_hex)
        
        # Update swatch preview
        self._draw_color_swatch(active_color)
                
        if active_color and not preset_matched:
            self.color_btn.config(bg=ACCENT_CYAN, fg=BG_DARK)
        else:
            self.color_btn.config(bg=BG_DARK, fg=TEXT_WHITE)

    def confirm_and_exit(self):
        if self.save_diary_data() is False:
            return
        if self.return_screen == "calendar":
            self.parent.show_calendar_screen()
        else:
            self.parent.show_start_screen()


class DailyTrackerScreen(tk.Frame):
    """
    Main dynamic daily tracking screen.
    Divided into:
    - Left Column: Scrollable main task cards + Static summary.
    - Right Column: Scrollable side task cards + Static summary + Static date.
    - Bottom/Footer: Grand summary progress, AI text commentary box, sqlite saving mechanisms.
    """
    def __init__(self, parent, date_str, blueprint_data=None, return_screen=None):
        super().__init__(parent, bg=BG_DARK)
        self.parent = parent
        self.date_str = date_str
        self.return_screen = return_screen
        
        self.data = None
        self.load_day_data(blueprint_data)
        
        # Grid Configurations
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0) # Static summary row
        self.grid_rowconfigure(3, weight=0) # Grand footer
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        # Setup Top Header
        self.setup_header()
        
        # Setup Left Column Scrollable Container
        self.left_frame = tk.Frame(self, bg=BG_DARK)
        self.left_frame.grid(row=1, column=0, padx=(20, 10), pady=10, sticky="nsew")
        self.left_scroll = ScrollableFrame(self.left_frame, bg=BG_DARK)
        self.left_scroll.pack(fill="both", expand=True)
        
        # Setup Right Column Scrollable Container
        self.right_frame = tk.Frame(self, bg=BG_DARK)
        self.right_frame.grid(row=1, column=1, padx=(10, 20), pady=10, sticky="nsew")
        
        self.right_scroll = ScrollableFrame(self.right_frame, bg=BG_DARK)
        self.right_scroll.pack(fill="both", expand=True)
        
        # Bind right-click on empty areas for creating task groups
        self.bind_empty_area_menu(self.left_scroll, is_main=True)
        self.bind_empty_area_menu(self.right_scroll, is_main=False)
        
        # Setup Bottom Static Summary Containers (Above Grand Footer)
        self.setup_static_boxes()
        
        # Setup Footer
        self.setup_footer()
        
        # Render the task panels
        self.render_all_tasks()
        self.update_calculations()
        
        # Auto-regenerate daily commentary if language is English or French
        _ar = tm._current_language == "Arabic"
        if not _ar:
            self.after(500, self.run_local_ai_inference)
        
    def load_day_data(self, blueprint_data=None):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT blueprint_name, main_tasks, side_tasks, ai_comment, small_advice, deep_advice FROM days WHERE date = ?", (self.date_str,))
        row = c.fetchone()
        conn.close()
        
        if row:
            self.data = {
                "date": self.date_str,
                "blueprint_name": row[0],
                "main_tasks": json.loads(row[1]),
                "side_tasks": json.loads(row[2]),
                "ai_comment": tm.unshape_arabic_text(row[3]),
                "small_advice": tm.unshape_arabic_text(row[4] or ""),
                "deep_advice": tm.unshape_arabic_text(row[5] or "")
            }
            # Normalize any group whose items are all zero percent (old data or blueprint import)
            changed = self._normalize_all_group_percents()
            if changed:
                self.save_day_data()
        else:
            # Fresh day init using blueprint data or blank
            if blueprint_data:
                main_tasks = []
                for g in blueprint_data.get("main_tasks", []):
                    main_tasks.append({
                        "id": g.get("id", len(main_tasks)+1),
                        "title": g.get("title", ""),
                        "stars": g.get("stars", 0),
                        "items": []
                    })
                side_tasks = []
                for g in blueprint_data.get("side_tasks", []):
                    side_tasks.append({
                        "id": g.get("id", len(side_tasks)+1),
                        "title": g.get("title", ""),
                        "stars": g.get("stars", 0),
                        "items": []
                    })
                    
                self.data = {
                    "date": self.date_str,
                    "blueprint_name": blueprint_data.get("name", "Custom Blank"),
                    "main_tasks": main_tasks,
                    "side_tasks": side_tasks,
                    "ai_comment": ""
                }
            else:
                self.data = {
                    "date": self.date_str,
                    "blueprint_name": "Blank",
                    "main_tasks": [],
                    "side_tasks": [],
                    "ai_comment": ""
                }
            self.save_day_data()
        self.raw_ai_comment = self.data.get("ai_comment", "")

    def _normalize_all_group_percents(self):
        changed = False
        if not self.data:
            return False
        for category in ["main_tasks", "side_tasks"]:
            groups = self.data.get(category, [])
            for group in groups:
                items = group.get("items", [])
                if not items:
                    continue
                # Proactively ensure all items have a 'done' key (fixes legacy / corrupted data)
                for item in items:
                    if "done" not in item:
                        item["done"] = False
                        changed = True
                # Check if all items are zero percent or missing percent weight
                all_zero = all(float(item.get("percent", 0.0)) == 0.0 for item in items)
                if all_zero:
                    n = len(items)
                    base = round(100.0 / n, 1)
                    for item in items:
                        item["percent"] = base
                    diff = round(100.0 - (base * n), 1)
                    items[-1]["percent"] = round(base + diff, 1)
                    changed = True
        return changed

    def save_day_data(self):
        if not self.data:
            return
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("""
                INSERT OR REPLACE INTO days (date, blueprint_name, main_tasks, side_tasks, ai_comment, small_advice, deep_advice)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (self.date_str, self.data["blueprint_name"], json.dumps(self.data["main_tasks"]), json.dumps(self.data["side_tasks"]), self.data["ai_comment"], self.data.get("small_advice", ""), self.data.get("deep_advice", "")))
            conn.commit()
            conn.close()
            self.parent.refresh_graphs_if_open()
        except Exception as e:
            print(f"[-] Database autosaving error: {e}")

    def setup_header(self):
        header = tk.Frame(self, bg=BG_DARK, height=65)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(15, 5))
        
        back_btn = tk.Button(header, text=tm.tr("menu_back"), bg=BG_CARD, fg=TEXT_WHITE, relief="flat",
                             activebackground=ACCENT_PURPLE, activeforeground=BG_DARK, font=("Helvetica", 10, "bold"),
                             padx=12, pady=6, command=self.confirm_and_exit)
        back_btn.pack(side="left")
        back_btn.bind("<Enter>", lambda e=None: back_btn.config(bg=ACCENT_PURPLE, fg=BG_DARK))
        back_btn.bind("<Leave>", lambda e=None: back_btn.config(bg=BG_CARD, fg=TEXT_WHITE))
        
        # Human-friendly date formatting
        try:
            dt = datetime.date.fromisoformat(self.date_str)
            date_formatted = tm.format_date(dt)
        except:
            date_formatted = self.date_str
            
        date_lbl = tk.Label(header, text=date_formatted, bg=BG_DARK, fg=TEXT_WHITE, font=("Helvetica", 15, "bold"))
        date_lbl.pack(side="left", padx=20)
        
        brand_lbl = tk.Label(header, text="Made with love by YakomoDev", bg=BG_DARK, fg=ACCENT_CYAN, font=("Helvetica", 11, "italic"))
        brand_lbl.pack(side="right", padx=10)
        
        # Download Button (only daily tasks paper)
        dl_btn = tk.Button(header, text="📥", bg=BG_CARD, fg=TEXT_WHITE, relief="flat",
                           activebackground=ACCENT_CYAN, activeforeground=BG_DARK, font=("Helvetica", 10, "bold"),
                           padx=12, pady=6, command=lambda: self.parent.show_export_dialog(self.date_str, self.data, export_type="tasks_only"))
        dl_btn.pack(side="right", padx=5)
        dl_btn.bind("<Enter>", lambda e=None: dl_btn.config(bg=ACCENT_CYAN, fg=BG_DARK))
        dl_btn.bind("<Leave>", lambda e=None: dl_btn.config(bg=BG_CARD, fg=TEXT_WHITE))

    def setup_static_boxes(self):
        summary_row = tk.Frame(self, bg=BG_DARK)
        summary_row.grid(row=2, column=0, columnspan=2, sticky="ew", padx=20, pady=5)
        summary_row.grid_columnconfigure(0, weight=1)
        summary_row.grid_columnconfigure(1, weight=1)
        
        # Left Bottom Static Box
        self.left_static_card = tk.Frame(summary_row, bg=BG_CARD, bd=1, highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.left_static_card.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        
        header_l = tk.Frame(self.left_static_card, bg=BG_CARD_HEADER, height=30)
        header_l.pack(fill="x")
        tk.Label(header_l, text=f"{tm.tr('main_missions')} {tm.tr('summary')}", bg=BG_CARD_HEADER, fg=ACCENT_PURPLE, font=("Helvetica", 9, "bold")).pack(side="left", padx=10, pady=5)
        
        self.left_summary_lbl = tk.Label(self.left_static_card, text=f"{tm.tr('tasks_done')} 0/0 (0.0)\n{tm.tr('stars_earned')} 0/0 (0.0)", 
                                         bg=BG_CARD, fg=TEXT_WHITE, font=("Helvetica", 10, "bold"), justify="left", anchor="w")
        self.left_summary_lbl.pack(fill="x", padx=15, pady=12)
        
        # Right Bottom Static Box
        right_static_container = tk.Frame(summary_row, bg=BG_DARK)
        right_static_container.grid(row=0, column=1, padx=(10, 0), sticky="ew")
        right_static_container.grid_columnconfigure(0, weight=1)
        
        self.right_static_card = tk.Frame(right_static_container, bg=BG_CARD, bd=1, highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.right_static_card.grid(row=0, column=0, sticky="ew")
        
        header_r = tk.Frame(self.right_static_card, bg=BG_CARD_HEADER, height=30)
        header_r.pack(fill="x")
        tk.Label(header_r, text=f"{tm.tr('side_missions')} {tm.tr('summary')}", bg=BG_CARD_HEADER, fg=ACCENT_CYAN, font=("Helvetica", 9, "bold")).pack(side="left", padx=10, pady=5)
        
        self.right_summary_lbl = tk.Label(self.right_static_card, text=f"{tm.tr('tasks_done')} 0/0 (0.0)\n{tm.tr('stars_earned')} 0/0 (0.0)", 
                                          bg=BG_CARD, fg=TEXT_WHITE, font=("Helvetica", 10, "bold"), justify="left", anchor="w")
        self.right_summary_lbl.pack(fill="x", padx=15, pady=10)
        
        # Date Box
        date_box = tk.Frame(right_static_container, bg=BG_CARD, bd=1, highlightbackground=BORDER_COLOR, highlightthickness=1)
        date_box.grid(row=1, column=0, pady=(8, 0), sticky="ew")
        
        header_d = tk.Frame(date_box, bg=BG_CARD_HEADER, height=22)
        header_d.pack(fill="x")
        tk.Label(header_d, text=tm.tr("tracker_target_date"), bg=BG_CARD_HEADER, fg=TEXT_MUTED, font=("Helvetica", 8, "bold")).pack(side="left", padx=10, pady=3)
        
        date_display = tk.Label(date_box, text=f"📆 {self.date_str}", bg=BG_CARD, fg=SUCCESS_GREEN, font=("Helvetica", 11, "bold"))
        date_display.pack(fill="x", padx=15, pady=8)

    def setup_footer(self):
        footer = tk.Frame(self, bg=BG_CARD, bd=1, highlightbackground=BORDER_COLOR, highlightthickness=1)
        footer.grid(row=3, column=0, columnspan=2, sticky="ew", padx=20, pady=(10, 20))
        
        _ar = tm._current_language == "Arabic"
        if _ar:
            footer.grid_columnconfigure(0, weight=1)
            footer.grid_columnconfigure(1, weight=0)
        else:
            footer.grid_columnconfigure(0, weight=3) # Progress bar and grand stats
            footer.grid_columnconfigure(1, weight=4) # AI comment box
        
        # Stats and Progress Bar
        stats_frame = tk.Frame(footer, bg=BG_CARD)
        if _ar:
            stats_frame.grid(row=0, column=0, columnspan=2, padx=20, pady=15, sticky="nsew")
        else:
            stats_frame.grid(row=0, column=0, padx=20, pady=15, sticky="nsew")
        
        tk.Label(stats_frame, text=tm.tr("grand_total_overview"), bg=BG_CARD, fg=ACCENT_PURPLE, font=("Helvetica", 11, "bold")).pack(anchor="w")
        
        self.grand_tasks_lbl = tk.Label(stats_frame, text=f"{tm.tr('total_tasks')} 0/0 (0.0)", bg=BG_CARD, fg=TEXT_WHITE, font=("Helvetica", 10, "bold"))
        self.grand_tasks_lbl.pack(anchor="w", pady=(8, 2))
        
        self.grand_stars_lbl = tk.Label(stats_frame, text=f"{tm.tr('total_stars')} 0/0 (0.0)", bg=BG_CARD, fg=TEXT_WHITE, font=("Helvetica", 10, "bold"))
        self.grand_stars_lbl.pack(anchor="w", pady=(2, 2))
        
        self.grand_packs_lbl = tk.Label(stats_frame, text=f"{tm.tr('total_packs')} 0/0 (0.0)", bg=BG_CARD, fg=TEXT_WHITE, font=("Helvetica", 10, "bold"))
        self.grand_packs_lbl.pack(anchor="w", pady=(2, 10))
        
        # Progress Bar Widget (using Canvas for premium custom colors)
        pb_container = tk.Frame(stats_frame, bg=BG_CARD)
        pb_container.pack(fill="x", expand=True, pady=(2, 4))
        pb_container.columnconfigure(1, weight=1)
        
        # Row 0: Earned Stars Ratio
        tk.Label(pb_container, text=tm.tr("earned_stars_ratio"), bg=BG_CARD, fg=TEXT_MUTED, font=("Helvetica", 9, "bold")).grid(row=0, column=0, sticky="w", padx=(0, 10), pady=2)
        self.pb_canvas = tk.Canvas(pb_container, height=18, bg=BG_DARK, highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.pb_canvas.grid(row=0, column=1, sticky="ew", pady=2)
        
        # Row 1: Tasks Completion Ratio
        tk.Label(pb_container, text=tm.tr("tasks_completion_ratio"), bg=BG_CARD, fg=TEXT_MUTED, font=("Helvetica", 9, "bold")).grid(row=1, column=0, sticky="w", padx=(0, 10), pady=2)
        self.pb_tasks_canvas = tk.Canvas(pb_container, height=18, bg=BG_DARK, highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.pb_tasks_canvas.grid(row=1, column=1, sticky="ew", pady=2)
        
        # AI Comment Area
        ai_frame = tk.Frame(footer, bg=BG_CARD)
        if not _ar:
            ai_frame.grid(row=0, column=1, padx=20, pady=15, sticky="nsew")
        
        ai_title_row = tk.Frame(ai_frame, bg=BG_CARD)
        ai_title_row.pack(fill="x", pady=(0, 6))
        
        tk.Label(ai_title_row, text=tm.tr("local_ai_commentary"), bg=BG_CARD, fg=ACCENT_CYAN, font=("Helvetica", 11, "bold")).pack(side="left")
        
        # Inline status label (no popups!)
        self.ai_status_lbl = tk.Label(ai_title_row, text="", bg=BG_CARD, fg=SUCCESS_GREEN, font=("Helvetica", 9, "bold"))
        self.ai_status_lbl.pack(side="left", padx=10)
        
        self.generate_ai_btn = tk.Button(ai_title_row, text=tm.tr("generate_feedback"), bg=BG_DARK, fg=ACCENT_CYAN, relief="flat", font=("Helvetica", 8, "bold"),
                                        padx=8, pady=2, command=self.run_local_ai_inference)
        self.generate_ai_btn.pack(side="right")
        self.generate_ai_btn.bind("<Enter>", lambda e: self.generate_ai_btn.config(bg=ACCENT_CYAN, fg=BG_DARK) if self.generate_ai_btn["state"] != "disabled" else None)
        self.generate_ai_btn.bind("<Leave>", lambda e: self.generate_ai_btn.config(bg=BG_DARK, fg=ACCENT_CYAN) if self.generate_ai_btn["state"] != "disabled" else None)
        
        copy_btn = tk.Button(ai_title_row, text=tm.tr("copy_prompt"), bg=BG_DARK, fg=TEXT_MUTED, relief="flat", font=("Helvetica", 8, "bold"),
                             padx=8, pady=2, command=self.copy_ai_prompt_silent)
        copy_btn.pack(side="right", padx=5)
        copy_btn.bind("<Enter>", lambda e: copy_btn.config(bg=BORDER_COLOR, fg=TEXT_WHITE))
        copy_btn.bind("<Leave>", lambda e: copy_btn.config(bg=BG_DARK, fg=TEXT_MUTED))
        
        # Text container holding text + scrollbar
        text_container = tk.Frame(ai_frame, bg=BG_DARK, highlightbackground=BORDER_COLOR, highlightthickness=1)
        text_container.pack(fill="both", expand=True)
        
        # AI Comment text area (editable by user)
        self.ai_text = tk.Text(text_container, height=5, bg=BG_DARK, fg=TEXT_WHITE, insertbackground=TEXT_WHITE,
                               relief="flat", font=("Amiri", 11) if _ar else ("Helvetica", 10),
                               wrap="word", borderwidth=0, highlightthickness=0)
        self.ai_text.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        ai_scroll = ttk.Scrollbar(text_container, orient="vertical", command=self.ai_text.yview)
        ai_scroll.pack(side="right", fill="y")
        self.ai_text.configure(yscrollcommand=ai_scroll.set)
        
        # Configure RTL tag for Arabic alignment
        if _ar:
            self.ai_text.tag_configure("rtl", justify="right")
        
        _stored = self.data.get("ai_comment", "")
        self._set_ai_text(_stored)
        if not _ar:
            self.ai_text.bind("<KeyRelease>", self.on_ai_comment_modified)
        
        # AI Coach Advice Buttons Row
        advice_row = tk.Frame(ai_frame, bg=BG_CARD)
        advice_row.pack(fill="x", pady=(8, 0))
        
        self.small_advice_btn = tk.Button(advice_row, text=tm.tr("small_advice_btn"), bg=BG_DARK, fg=ACCENT_CYAN, relief="flat", font=("Helvetica", 8, "bold"),
                                          padx=8, pady=3, command=lambda: self.get_ai_coach_advice("small"))
        self.small_advice_btn.pack(side="left", padx=(0, 6))
        self.small_advice_btn.bind("<Enter>", lambda e: self.small_advice_btn.config(bg=ACCENT_CYAN, fg=BG_DARK) if self.small_advice_btn["state"] != "disabled" else None)
        self.small_advice_btn.bind("<Leave>", lambda e: self.small_advice_btn.config(bg=BG_DARK, fg=ACCENT_CYAN) if self.small_advice_btn["state"] != "disabled" else None)
        
        self.deep_advice_btn = tk.Button(advice_row, text=tm.tr("deep_advice_btn"), bg=BG_DARK, fg=ACCENT_PURPLE, relief="flat", font=("Helvetica", 8, "bold"),
                                         padx=8, pady=3, command=lambda: self.get_ai_coach_advice("deep"))
        self.deep_advice_btn.pack(side="left")
        self.deep_advice_btn.bind("<Enter>", lambda e: self.deep_advice_btn.config(bg=ACCENT_PURPLE, fg=BG_DARK) if self.deep_advice_btn["state"] != "disabled" else None)
        self.deep_advice_btn.bind("<Leave>", lambda e: self.deep_advice_btn.config(bg=BG_DARK, fg=ACCENT_PURPLE) if self.deep_advice_btn["state"] != "disabled" else None)
        
        self.check_active_ai_jobs()

    def _set_ai_text(self, raw_text):
        """Replace ai_text content with properly shaped+aligned text.
        Handles state toggling and RTL tag application automatically."""
        _ar = tm._current_language == "Arabic"
        self.ai_text.config(state="normal")
        self.ai_text.delete("1.0", tk.END)
        if raw_text.strip():
            shaped = shape_for_display(raw_text)
            self.ai_text.insert("1.0", shaped)
            if _ar:
                self.ai_text.tag_add("rtl", "1.0", "end")
        if _ar:
            self.ai_text.config(state="disabled")

    def on_ai_comment_modified(self, event=None):
        content = self.ai_text.get("1.0", tk.END).strip()
        _ar = tm._current_language == "Arabic"
        if _ar:
            if hasattr(self, 'raw_ai_comment') and content == shape_for_display(self.raw_ai_comment).strip():
                self.data["ai_comment"] = self.raw_ai_comment
            else:
                self.data["ai_comment"] = content
                self.raw_ai_comment = content
        else:
            self.data["ai_comment"] = content
            self.raw_ai_comment = content
        self.save_day_data()

    def copy_ai_prompt_silent(self):
        prompt = self.get_ai_prompt()
        self.clipboard_clear()
        self.clipboard_append(prompt)
        
        self.ai_status_lbl.config(text=tm.tr("prompt_copied"), fg=SUCCESS_GREEN)
        self.after(2000, lambda: self.ai_status_lbl.config(text=""))

    def run_local_ai_inference(self):
        # Prevent AI generation and hallucinations on a blank day
        main_tasks = self.data.get("main_tasks", [])
        side_tasks = self.data.get("side_tasks", [])
        total_items = sum(len(g.get("items", [])) for g in main_tasks + side_tasks)
        
        if total_items == 0:
            _lang = tm._current_language
            if _lang == "French":
                msg = "Aucune tâche n'est enregistrée pour aujourd'hui. Ajoutez des éléments à vos groupes pour commencer le suivi et recevoir un retour IA !"
            elif _lang == "Arabic":
                msg = "لا توجد مهام مسجلة لهذا اليوم. أضف عناصر إلى مجموعاتك لبدء التتبع والحصول على تعليق الذكاء الاصطناعي!"
            else:
                msg = "No tasks are logged for today. Add task items to your groups to start tracking and receive AI feedback!"
            self._set_ai_text(msg)
            self.data["ai_comment"] = msg
            self.save_day_data()
            self.ai_status_lbl.config(text=tm.tr("comment_updated"), fg=SUCCESS_GREEN)
            self.after(2000, lambda: self.ai_status_lbl.config(text=""))
            return

        model_path = get_model_path()
        
        if not os.path.exists(model_path):
            self.ai_status_lbl.config(text=tm.tr("error_model_not_found"), fg="#ef4444")
            return
            
        try:
            import llama_cpp
        except ImportError:
            self.ai_status_lbl.config(text=tm.tr("error_llama_not_installed"), fg="#ef4444")
            return
            
        self.generate_ai_btn.config(state="disabled", text=tm.tr("generating"))
        self.ai_status_lbl.config(text=tm.tr("loading_model"), fg=ACCENT_CYAN)
        
        # Set loading text inside the comment box
        self._set_ai_text(tm.tr_raw("generating"))
        
        prompt = self.get_ai_prompt()
        self.parent.start_ai_job(self.date_str, "comment", model_path, "", prompt)

    def get_today_tasks_text(self):
        main_tasks = self.data.get("main_tasks", [])
        side_tasks = self.data.get("side_tasks", [])
        
        total_items = 0
        done_items = 0
        
        # Helper to compute counts, counting empty task groups as 1 task item
        def get_group_counts(groups):
            tot = 0
            done = 0
            for g in groups:
                items = g.get("items", [])
                if items:
                    tot += len(items)
                    done += sum(1 for i in items if i.get("done"))
                else:
                    tot += 1
                    done += 1 if g.get("done", False) else 0
            return tot, done
            
        m_tot, m_done = get_group_counts(main_tasks)
        s_tot, s_done = get_group_counts(side_tasks)
        total_items = m_tot + s_tot
        done_items = m_done + s_done
        
        has_tasks = (len(main_tasks) > 0 or len(side_tasks) > 0)
        has_items = (total_items > 0)
        
        if tm._current_language == "French":
            text = ""
            if not has_tasks:
                text += "FAIT : L'utilisateur n'a créé aucun groupe de tâches ou mission pour aujourd'hui. La page est vide.\n"
            elif not has_items:
                text += "FAIT : L'utilisateur a créé des groupes de tâches mais n'y a pas encore ajouté de tâches spécifiques.\n"
            elif done_items == 0:
                text += f"FAIT : L'utilisateur a enregistré {total_items} tâches aujourd'hui mais en a complété 0 (taux d'achèvement de 0.0%).\n"
            else:
                pct_overall = (done_items / total_items * 100.0)
                text += f"FAIT : L'utilisateur a complété {done_items} sur {total_items} tâches aujourd'hui (taux d'achèvement global : {pct_overall:.1f}%).\n"
                
            # Process Side Tasks first
            text += "\n--- MISSIONS SECONDAIRES ---\n"
            if not side_tasks:
                text += "(Aucune mission secondaire enregistrée)\n"
            else:
                for group in side_tasks:
                    items = group.get("items", [])
                    done_items_g = [i for i in items if i.get("done")]
                    pct_done = (len(done_items_g) / len(items) * 100.0) if items else (100.0 if group.get("done", False) else 0.0)
                    
                    text += f"Groupe de tâches secondaires '{group.get('title')}' (Achèvement : {pct_done:.1f}%)\n"
                    if items:
                        for item in items:
                            status = "[FAIT]" if item.get("done") else "[EN_ATTENTE]"
                            text += f"  - {status} {item.get('name')}\n"
                    else:
                        status = "[FAIT]" if group.get("done", False) else "[EN_ATTENTE]"
                        text += f"  - {status} {group.get('title')}\n"
                        
            # Process Main Tasks second
            text += "\n--- MISSIONS PRINCIPALES ---\n"
            if not main_tasks:
                text += "(Aucune mission principale enregistrée)\n"
            else:
                for group in main_tasks:
                    items = group.get("items", [])
                    done_items_g = [i for i in items if i.get("done")]
                    pct_done = (len(done_items_g) / len(items) * 100.0) if items else (100.0 if group.get("done", False) else 0.0)
                    
                    text += f"Groupe de tâches principales '{group.get('title')}' (Achèvement : {pct_done:.1f}%)\n"
                    if items:
                        for item in items:
                            status = "[FAIT]" if item.get("done") else "[EN_ATTENTE]"
                            text += f"  - {status} {item.get('name')}\n"
                    else:
                        status = "[FAIT]" if group.get("done", False) else "[EN_ATTENTE]"
                        text += f"  - {status} {group.get('title')}\n"
            return text

        elif tm._current_language == "Arabic":
            text = ""
            if not has_tasks:
                text += "حقيقة: لم يقم المستخدم بإنشاء أي مجموعات مهام أو مهمات لهذا اليوم بعد.\n"
            elif not has_items:
                text += "حقيقة: قام المستخدم بإنشاء مجموعات مهام ولكنه لم يضف أي عناصر مهام محددة إليها بعد.\n"
            elif done_items == 0:
                text += f"حقيقة: سجل المستخدم {total_items} مهمة اليوم ولكنه أكمل 0 منها (نسبة إنجاز 0.0%).\n"
            else:
                pct_overall = (done_items / total_items * 100.0)
                text += f"حقيقة: أكمل المستخدم {done_items} من أصل {total_items} مهمة اليوم (معدل الإنجاز العام: {pct_overall:.1f}%).\n"
                
            # Process Side Tasks first
            text += "\n--- المهمات الثانوية ---\n"
            if not side_tasks:
                text += "(لم يتم تسجيل مهمات ثانوية)\n"
            else:
                for group in side_tasks:
                    items = group.get("items", [])
                    done_items_g = [i for i in items if i.get("done")]
                    pct_done = (len(done_items_g) / len(items) * 100.0) if items else (100.0 if group.get("done", False) else 0.0)
                    
                    text += f"مجموعة المهام الثانوية '{group.get('title')}' (الإنجاز: {pct_done:.1f}%)\n"
                    if items:
                        for item in items:
                            status = "[مكتمل]" if item.get("done") else "[معلق]"
                            text += f"  - {status} {item.get('name')}\n"
                    else:
                        status = "[مكتمل]" if group.get("done", False) else "[معلق]"
                        text += f"  - {status} {group.get('title')}\n"

            # Process Main Tasks second
            text += "\n--- المهمات الرئيسية ---\n"
            if not main_tasks:
                text += "(لم يتم تسجيل مهمات رئيسية)\n"
            else:
                for group in main_tasks:
                    items = group.get("items", [])
                    done_items_g = [i for i in items if i.get("done")]
                    pct_done = (len(done_items_g) / len(items) * 100.0) if items else (100.0 if group.get("done", False) else 0.0)
                    
                    text += f"مجموعة المهام الرئيسية '{group.get('title')}' (الإنجاز: {pct_done:.1f}%)\n"
                    if items:
                        for item in items:
                            status = "[مكتمل]" if item.get("done") else "[معلق]"
                            text += f"  - {status} {item.get('name')}\n"
                    else:
                        status = "[مكتمل]" if group.get("done", False) else "[معلق]"
                        text += f"  - {status} {group.get('title')}\n"
            return text

        else:
            text = ""
            if not has_tasks:
                text += "FACT: The user has not created any task groups or missions for today yet. They have a completely blank page.\n"
            elif not has_items:
                text += "FACT: The user has created task groups but has not added any specific task items to them yet.\n"
            elif done_items == 0:
                text += f"FACT: The user logged {total_items} tasks today but completed 0 of them (0.0% completion).\n"
            else:
                pct_overall = (done_items / total_items * 100.0)
                text += f"FACT: The user completed {done_items} out of {total_items} task items today (overall completion rate: {pct_overall:.1f}%).\n"
                
            # Process Side Tasks first
            text += "\n--- SIDE TASKS ---\n"
            if not side_tasks:
                text += "(No side tasks logged)\n"
            else:
                for group in side_tasks:
                    items = group.get("items", [])
                    done_items_g = [i for i in items if i.get("done")]
                    pct_done = (len(done_items_g) / len(items) * 100.0) if items else (100.0 if group.get("done", False) else 0.0)
                    
                    text += f"Side Task Group '{group.get('title')}' (Completion: {pct_done:.1f}%)\n"
                    if items:
                        for item in items:
                            status = "[DONE]" if item.get("done") else "[PENDING]"
                            text += f"  - {status} {item.get('name')}\n"
                    else:
                        status = "[DONE]" if group.get("done", False) else "[PENDING]"
                        text += f"  - {status} {group.get('title')}\n"

            # Process Main Tasks second
            text += "\n--- MAIN TASKS ---\n"
            if not main_tasks:
                text += "(No main tasks logged)\n"
            else:
                for group in main_tasks:
                    items = group.get("items", [])
                    done_items_g = [i for i in items if i.get("done")]
                    pct_done = (len(done_items_g) / len(items) * 100.0) if items else (100.0 if group.get("done", False) else 0.0)
                    
                    text += f"Main Task Group '{group.get('title')}' (Completion: {pct_done:.1f}%)\n"
                    if items:
                        for item in items:
                            status = "[DONE]" if item.get("done") else "[PENDING]"
                            text += f"  - {status} {item.get('name')}\n"
                    else:
                        status = "[DONE]" if group.get("done", False) else "[PENDING]"
                        text += f"  - {status} {group.get('title')}\n"
            return text

    def get_ai_prompt(self):
        today_text = self.get_today_tasks_text()
        import datetime
        today_str = datetime.date.today().isoformat()
        
        if tm._current_language == "French":
            if self.date_str == today_str:
                time_context = "CONTEXTE TEMPOREL CRITIQUE : Cette date est AUJOURD'HUI (en cours/non terminée). Écris au présent."
            elif self.date_str < today_str:
                time_context = "CONTEXTE TEMPOREL CRITIQUE : Cette date est PASSÉE (déjà terminée). Écris au passé."
            else:
                time_context = "CONTEXTE TEMPOREL CRITIQUE : Cette date est dans le FUTUR. Écris au futur."

            user_msg = (
                "MANDATORY: YOU MUST WRITE YOUR RESPONSE ONLY IN FRENCH. VEUILLEZ RÉPONDRE UNIQUEMENT EN FRANÇAIS.\n\n"
                "Tu es un analyste factuel et strict des tâches quotidiennes pour l'application de bureau 'Mission Ui'.\n"
                f"{time_context}\n"
                "Examine les faits de progression ci-dessous et rédige un résumé strictement factuel, sec et en exactement 3 phrases de ces données.\n\n"
                "RÈGLES CRITIQUES :\n"
                "1. PAS DE BAVARDAGE OU D'ADJECTIFS QUALITATIFS : N'utilise AUCUN adjectif ou descripteur qualitatif (par exemple, n'utilise PAS de mots comme 'régulier', 'minimal', 'constant', 'effort', 'excellent', 'actif', 'bon', 'mauvais'). Stricte neutralité.\n"
                "2. PAS DE DUPES : N'utilise pas de faux noms comme 'Tâche A' ou 'Groupe 1'. Réfère-toi aux groupes et aux tâches UNIQUEMENT par leurs noms exacts tels qu'écrits dans la liste des faits.\n"
                "3. UNIQUEMENT DES FAITS MATHÉMATIQUES : Limite-toi strictement aux taux d'achèvement et aux pourcentages fournis dans les faits. Ne fais aucun calcul toi-même; copie les pourcentages directement depuis la liste.\n"
                "4. PAS D'ÉTOILES NI DE SCORES : Ne mentionne pas d'étoiles, de points, de poids ou de scores. Concentre-toi uniquement sur le statut de complétion (fait ou en attente).\n"
                "5. STRUCTURE DE CONTENU REQUIS : Mentionne UNIQUEMENT ce qui est fait (complété) et ce qui ne l'est pas (en attente). Tu dois OBLIGATOIREMENT parler des tâches secondaires (missions secondaires) en premier (ce qui a été fait et ce qui ne l'a pas été), puis parler des tâches principales (missions principales) ensuite (ce qui a été fait et ce qui ne l'a pas été).\n"
                "6. LANGUE : Tu dois obligatoirement rédiger ta réponse en français et ne jamais utiliser l'anglais.\n\n"
                "=== EXEMPLE D'ENTRÉE ET DE SORTIE REQUISES ===\n"
                "=== FAITS DE PROGRESSION ENREGISTRÉS ===\n"
                "FAIT : L'utilisateur a complété 2 sur 4 tâches aujourd'hui (taux d'achèvement global : 50.0%).\n\n"
                "--- MISSIONS SECONDAIRES ---\n"
                "Groupe de tâches secondaires 'Quran' (Achèvement : 100.0%)\n"
                "  - [FAIT] Read Quran\n"
                "Groupe de tâches secondaires 'Sleep' (Achèvement : 0.0%)\n"
                "  - [EN_ATTENTE] Sleep early\n\n"
                "--- MISSIONS PRINCIPALES ---\n"
                "Groupe de tâches principales 'Gym' (Achèvement : 0.0%)\n"
                "  - [EN_ATTENTE] Go gym (back and shoulders day)\n"
                "Groupe de tâches principales 'Pixel art' (Achèvement : 100.0%)\n"
                "  - [FAIT] Draw pixel art\n\n"
                "Sortie (exactement 3 phrases en français) :\n"
                "L'utilisateur a complété 2 sur 4 tâches aujourd'hui, atteignant un taux d'achèvement global de 50.0%. Le groupe de tâches secondaires 'Quran' et le groupe de tâches principales 'Pixel art' sont complétés. La tâche principale 'Go gym (back and shoulders day)' et la tâche secondaire 'Sleep early' restent en attente.\n"
                "=============================================\n\n"
                f"=== FAITS DE PROGRESSION ENREGISTRÉS ===\n{today_text}\n\n"
                "Réponds uniquement avec le résumé de 3 phrases en français. Ne produis aucun code, JSON ou mise en forme."
            )
        elif tm._current_language == "Arabic":
            if self.date_str == today_str:
                time_context = "سياق زمني حرج: هذا التاريخ هو اليوم (لا يزال قيد التنفيذ). اكتب بصيغة المضارع."
            elif self.date_str < today_str:
                time_context = "سياق زمني حرج: هذا التاريخ قد مضى (اكتمل بالفعل). اكتب بصيغة الماضي."
            else:
                time_context = "سياق زمني حرج: هذا التاريخ في المستقبل. اكتب بصيغة المستقبل."

            user_msg = (
                "MANDATORY: YOU MUST WRITE YOUR RESPONSE ONLY IN ARABIC. يجب عليك كتابة الرد باللغة العربية فقط. لا تستخدم الإنجليزية أبداً.\n\n"
                "أنت محلل بيانات مهام جاف وصارم لتطبيق المكتب 'Mission Ui'.\n"
                f"{time_context}\n"
                "راجع حقائق التقدم المسجلة أدناه واكتب ملخصًا جافًا وصارمًا ومكونًا من 3 جمل بالضبط للبيانات.\n\n"
                "قيود صارمة:\n"
                "1. لا تعبيرات إنشائية أو وصفية: لا تستخدم أي صفات أو عبارات نوعية (مثال: لا تستخدم كلمات مثل 'ثابت'، 'أدنى'، 'مستمر'، 'جهد'، 'رائع'، 'نشط'، 'جيد'، 'سيء').\n"
                "2. لا تسميات وهمية: لا تستخدم أسماء وهمية مثل 'المهمة أ' أو 'المجموعة 1'. أشر إلى مجموعات وعناصر المهام فقط بأسمائها الدقيقة كما هي مكتوبة في قائمة الحقائق.\n"
                "3. حقائق رياضية فقط: التزم تمامًا بأرقام ونسب الإكمال الواردة في الحقائق. لا تقم بأي عمليات حسابية بنفسك؛ انقل النسب مباشرة من قائمة الحقائق.\n"
                "4. لا نجوم أو نقاط: لا تذكر النجوم أو النقاط أو الأوزان أو الدرجات في ردك. ركز فقط على حالة الإكمال (مكتمل أو معلق).\n"
                "5. اللغة: يجب أن تكتب ردك باللغة العربية فقط وبشكل صحيح وتام.\n\n"
                "=== مثال على المدخلات والمخرجات المطلوبة ===\n"
                "=== حقائق التقدم المسجلة ===\n"
                "حقيقة: أكمل المستخدم 2 من أصل 4 مهمة اليوم (معدل الإنجاز العام: 50.0%).\n\n"
                "--- المهمات الثانوية ---\n"
                "مجموعة المهام الثانوية 'Quran' (الإنجاز: 100.0%)\n"
                "  - [مكتمل] Read Quran\n"
                "مجموعة المهام الثانوية 'Sleep' (الإنجاز: 0.0%)\n"
                "  - [معلق] Sleep early\n\n"
                "--- المهمات الرئيسية ---\n"
                "مجموعة المهام الرئيسية 'Gym' (الإنجاز: 0.0%)\n"
                "  - [معلق] Go gym (back and shoulders day)\n"
                "مجموعة المهام الرئيسية 'Pixel art' (الإنجاز: 100.0%)\n"
                "  - [مكتمل] Draw pixel art\n\n"
                "المخرجات (3 جمل بالضبط باللغة العربية):\n"
                "أكمل المستخدم 2 من أصل 4 مهمة اليوم بمعدل إنجاز إجمالي 50.0%. اكتملت مجموعة المهام Pixel art ومجموعة المهام Quran بالكامل. وظلت المهام Go gym (back and shoulders day) وSleep early معلقة.\n"
                "========================================\n\n"
                f"=== حقائق التقدم المسجلة ===\n{today_text}\n\n"
                "أجب بالملخص المكون من 3 جمل فقط باللغة العربية. لا تخرج أي كود أو تنسيقات إضافية."
            )
        else:
            if self.date_str == today_str:
                time_context = "CRITICAL TIME CONTEXT: This date is TODAY (still in progress/ongoing). Write in the present tense."
            elif self.date_str < today_str:
                time_context = "CRITICAL TIME CONTEXT: This date has PASSED (already completed). Write in the past tense."
            else:
                time_context = "CRITICAL TIME CONTEXT: This date is in the FUTURE. Write in the future tense."
                
            user_msg = (
                "You are a strict, factual Daily Task Analyst for the desktop app 'Mission Ui'.\n"
                f"{time_context}\n"
                "Review the logged progress facts below and write a strictly factual, dry, 3-sentence summary of the data.\n\n"
                "CRITICAL CONSTRAINTS:\n"
                "1. NO SUBJECTIVE FLUFF: Do NOT use qualitative adjectives or descriptors (e.g., do NOT use words like 'steady', 'minimal', 'consistent', 'effort', 'great', 'active', 'good', 'bad').\n"
                "2. NO PLACEHOLDERS: Do NOT use dummy names like 'Task A' or 'Group 1'. Refer to task groups and task items ONLY by their exact names as written in the facts list.\n"
                "3. MATHEMATICAL FACTS ONLY: Stick strictly to the completion numbers, percentages, and names provided in the facts. Do NOT perform any math calculations yourself; copy the percentages directly from the facts list.\n"
                "4. NO STARS OR SCORES: Do NOT mention stars, points, weights, or scores in your response. Focus strictly on completion status and which tasks are completed or pending.\n"
                "5. STRUCTURE OF CONTENT REQUIRED: Mention ONLY what is completed (done) and what is not (pending). You MUST talk about the side tasks first (what is completed and what is pending), and then talk about the main tasks afterwards (what is completed and what is pending).\n"
                f"6. LANGUAGE: {tm.tr('ai_language_prompt')}\n\n"
                "=== EXAMPLE OF REQUIRED INPUT AND OUTPUT ===\n"
                "=== LOGGED PROGRESS FACTS ===\n"
                "FACT: The user completed 2 out of 4 task items today (overall completion rate: 50.0%).\n\n"
                "--- SIDE TASKS ---\n"
                "Side Task Group 'Quran' (Completion: 100.0%)\n"
                "  - [DONE] Read Quran\n"
                "Side Task Group 'Sleep' (Completion: 0.0%)\n"
                "  - [PENDING] Sleep early\n\n"
                "--- MAIN TASKS ---\n"
                "Main Task Group 'Gym' (Completion: 0.0%)\n"
                "  - [PENDING] Go gym (back and shoulders day)\n"
                "Main Task Group 'Pixel art' (Completion: 100.0%)\n"
                "  - [DONE] Draw pixel art\n\n"
                "Output (exactly 3 sentences):\n"
                "The user completed 2 out of 4 task items today, achieving an overall completion rate of 50.0%. Side task group 'Quran' and main task group 'Pixel art' are completed. Main task 'Go gym (back and shoulders day)' and side task 'Sleep early' remain pending.\n"
                "============================================\n\n"
                f"=== LOGGED PROGRESS FACTS ===\n{today_text}\n\n"
                "Respond with only the 3-sentence summary. Do not output any code, JSON, or formatting."
            )
        prompt = f"<start_of_turn>user\n{user_msg}<end_of_turn>\n<start_of_turn>model\n"
        return prompt

    def get_ai_coach_advice(self, advice_type):
        # Prevent AI generation and hallucinations on a blank day
        main_tasks = self.data.get("main_tasks", [])
        side_tasks = self.data.get("side_tasks", [])
        total_items = sum(len(g.get("items", [])) for g in main_tasks + side_tasks)
        
        if total_items == 0:
            _lang = tm._current_language
            if _lang == "French":
                msg = f"Aucune tâche n'est enregistrée pour aujourd'hui. Ajoutez des éléments à vos groupes pour commencer le suivi et recevoir des conseils de productivité ({advice_type}) !"
            elif _lang == "Arabic":
                msg = f"لا توجد مهام مسجلة لهذا اليوم. أضف عناصر إلى مجموعاتك لبدء التتبع والحصول على نصائح إنتاجية ({advice_type})!"
            else:
                msg = f"No tasks are logged for today. Add task items to your groups to start tracking and receive productivity {advice_type} advice!"
            self.data[advice_type + "_advice"] = msg
            self.save_day_data()
            self.ai_status_lbl.config(text=tm.tr("advice_updated"), fg=SUCCESS_GREEN)
            self.after(2000, lambda: self.ai_status_lbl.config(text=""))
            AdviceDisplayDialog(self, self.date_str, advice_type, msg)
            return

        model_path = get_model_path()
        
        if not os.path.exists(model_path):
            self.ai_status_lbl.config(text=tm.tr("error_model_not_found"), fg="#ef4444")
            return
            
        import llama_cpp
        if llama_cpp is None:
            self.ai_status_lbl.config(text=tm.tr("error_llama_not_installed"), fg="#ef4444")
            return
            
        existing = self.data.get(advice_type + "_advice")
        if existing:
            from tkinter import messagebox
            advice_type_tr = tm.tr("small_tag") if advice_type == "small" else tm.tr("deep_tag")
            choice = messagebox.askyesnocancel(
                tm.tr("advice_exists"), 
                tm.tr("advice_exists_body").format(advice_type=advice_type_tr)
            )
            if choice is True:
                AdviceDisplayDialog(self, self.date_str, advice_type, existing)
                return
            elif choice is False:
                pass
            else:
                return

        self.small_advice_btn.config(state="disabled")
        self.deep_advice_btn.config(state="disabled")
        self.generate_ai_btn.config(state="disabled")
        
        self.ai_status_lbl.config(text=tm.tr("generating_advice"), fg=ACCENT_CYAN)
        
        today_tasks_text = self.get_today_tasks_text()
        self.parent.start_ai_job(self.date_str, advice_type + "_advice", model_path, today_tasks_text, "")

    def handle_ai_job_success(self, job_type, result_text):
        if not self.winfo_exists():
            return
        if job_type == "comment":
            self.raw_ai_comment = result_text
            self._set_ai_text(result_text)
            self.data["ai_comment"] = result_text
            self.generate_ai_btn.config(state="normal", text=tm.tr("generate_feedback"), bg=BG_DARK, fg=ACCENT_CYAN)
            self.ai_status_lbl.config(text=tm.tr("comment_updated"), fg=SUCCESS_GREEN)
            self.after(3000, lambda: self.ai_status_lbl.config(text="") if self.winfo_exists() else None)
        elif job_type in ("small_advice", "deep_advice"):
            self.small_advice_btn.config(state="normal")
            self.deep_advice_btn.config(state="normal")
            self.generate_ai_btn.config(state="normal")
            self.ai_status_lbl.config(text=tm.tr("advice_loaded"), fg=SUCCESS_GREEN)
            self.after(3000, lambda: self.ai_status_lbl.config(text="") if self.winfo_exists() else None)
            
            advice_type = "small" if job_type == "small_advice" else "deep"
            self.data[advice_type + "_advice"] = result_text
            
            AdviceDisplayDialog(self, self.date_str, advice_type, result_text)

    def handle_ai_job_error(self, job_type, error_msg):
        if not self.winfo_exists():
            return
        if job_type == "comment":
            self.generate_ai_btn.config(state="normal", text=tm.tr("generate_feedback"), bg=BG_DARK, fg=ACCENT_CYAN)
            self.ai_status_lbl.config(text=f"Error: {error_msg}", fg="#ef4444")
        elif job_type in ("small_advice", "deep_advice"):
            self.small_advice_btn.config(state="normal")
            self.deep_advice_btn.config(state="normal")
            self.generate_ai_btn.config(state="normal")
            self.ai_status_lbl.config(text=f"Error: {error_msg}", fg="#ef4444")

    def check_active_ai_jobs(self):
        jobs = getattr(self.parent, "running_ai_jobs", {})
        
        comment_key = (self.date_str, "comment")
        if comment_key in jobs and jobs[comment_key]["status"] == "running":
            self.generate_ai_btn.config(state="disabled", text=tm.tr("generating"))
            self.ai_status_lbl.config(text=tm.tr("running_local_ai"), fg=ACCENT_CYAN)
            
        small_key = (self.date_str, "small_advice")
        if small_key in jobs and jobs[small_key]["status"] == "running":
            self.small_advice_btn.config(state="disabled")
            self.deep_advice_btn.config(state="disabled")
            self.generate_ai_btn.config(state="disabled")
            self.ai_status_lbl.config(text=tm.tr("generating_advice"), fg=ACCENT_CYAN)
            
        deep_key = (self.date_str, "deep_advice")
        if deep_key in jobs and jobs[deep_key]["status"] == "running":
            self.small_advice_btn.config(state="disabled")
            self.deep_advice_btn.config(state="disabled")
            self.generate_ai_btn.config(state="disabled")
            self.ai_status_lbl.config(text=tm.tr("generating_advice"), fg=ACCENT_CYAN)

    def add_task_group_prompt(self, is_main):
        g_type_raw = tm.tr_raw("main_tag") if is_main else tm.tr_raw("side_tag")
        win_title = f"{tm.tr_raw('create_group')} ({g_type_raw})"
        title_diag = CustomDialog(self, win_title, tm.tr("enter_group_title"))
        self.wait_window(title_diag)
        if title_diag.result is None:
            return
        title = title_diag.result
        
        star_diag = CustomDialog(self, win_title, tm.tr("enter_group_stars"), is_numeric=True)
        self.wait_window(star_diag)
        if star_diag.result is None:
            return
        stars = int(star_diag.result)
        
        groups = self.data["main_tasks"] if is_main else self.data["side_tasks"]
        new_id = 1
        if groups:
            new_id = max(g["id"] for g in groups) + 1
            
        groups.append({
            "id": new_id,
            "title": title,
            "stars": stars,
            "items": []
        })
        
        self.save_day_data()
        self.render_all_tasks()
        self.update_calculations()

    def bind_empty_area_menu(self, scrollable_widget, is_main):
        def show_menu(event):
            self.show_empty_area_menu(event, is_main)
            
        scrollable_widget.bind("<Button-3>", show_menu)
        scrollable_widget.canvas.bind("<Button-3>", show_menu)
        scrollable_widget.scrollable_frame.bind("<Button-3>", show_menu)

    def show_empty_area_menu(self, event, is_main):
        menu = tk.Menu(self.winfo_toplevel(), tearoff=0, bg=BG_CARD, fg=TEXT_WHITE, 
                       activebackground=ACCENT_PURPLE if is_main else ACCENT_CYAN, activeforeground=BG_DARK, font=("Helvetica", 10))
        g_type_tr = tm.tr("main_tag") if is_main else tm.tr("side_tag")
        menu.add_command(label=f"➕ {tm.tr('create_new_blank_group')} ({g_type_tr})", command=lambda: self.add_task_group_prompt(is_main))
        menu.add_command(label=f"⭐ {tm.tr('load_starred_pack')} ({g_type_tr})...", command=lambda: self.show_starred_packs_popup(is_main))
        menu.tk_popup(event.x_root, event.y_root)

    def show_starred_packs_popup(self, is_main):
        StarredPacksSelectionDialog(self, is_main)

    def add_starred_pack(self, selected, is_main):
        groups = self.data["main_tasks"] if is_main else self.data["side_tasks"]
        new_id = max([g["id"] for g in groups] + [0]) + 1
        
        # Clone items and ensure all of them are unchecked/undone (done = False)
        clean_items = []
        for it in selected.get("items", []):
            item_copy = it.copy()
            item_copy["done"] = False
            clean_items.append(item_copy)
            
        groups.append({
            "id": new_id,
            "title": selected["title"],
            "stars": selected["stars"],
            "items": clean_items,
            "done": False
        })
        self.save_day_data()
        self.render_all_tasks()
        self.update_calculations()

    def star_tasks_pack(self, group):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        try:
            c.execute("""
                INSERT OR REPLACE INTO starred_packs (title, stars, items)
                VALUES (?, ?, ?)
            """, (group["title"], group["stars"], json.dumps(group.get("items", []))))
            conn.commit()
            self.ai_status_lbl.config(text=tm.tr("pack_saved_starred").format(title=group['title']), fg=SUCCESS_GREEN)
            self.after(3000, lambda: self.ai_status_lbl.config(text=""))
        except Exception as e:
            messagebox.showerror(tm.tr("error"), f"{tm.tr('failed_save_starred_pack')}{e}")
        finally:
            conn.close()

    def render_all_tasks(self):
        # Clear containers
        for w in self.left_scroll.scrollable_frame.winfo_children():
            w.destroy()
        for w in self.right_scroll.scrollable_frame.winfo_children():
            w.destroy()
            
        # Keep list of UI references to update values dynamically without full rebuilds
        self.group_ui_widgets = {} # Maps (is_main, group_id) -> dict of widgets
        
        # Render Main tasks on the left
        main_groups = self.data.get("main_tasks", [])
        if not main_groups:
            lbl = tk.Label(self.left_scroll.scrollable_frame, text=tm.tr("no_main_tasks"), bg=BG_DARK, fg=TEXT_MUTED, font=("Helvetica", 10, "italic"), justify="center")
            lbl.pack(pady=40, fill="both", expand=True)
            lbl.bind("<Button-3>", lambda e: self.show_empty_area_menu(e, is_main=True))
        else:
            for index, group in enumerate(main_groups):
                self.create_task_group_card(group, is_main=True, container=self.left_scroll.scrollable_frame, index=index)
                
        # Render Side tasks on the right
        side_groups = self.data.get("side_tasks", [])
        if not side_groups:
            lbl = tk.Label(self.right_scroll.scrollable_frame, text=tm.tr("no_side_tasks"), bg=BG_DARK, fg=TEXT_MUTED, font=("Helvetica", 10, "italic"), justify="center")
            lbl.pack(pady=40, fill="both", expand=True)
            lbl.bind("<Button-3>", lambda e: self.show_empty_area_menu(e, is_main=False))
        else:
            for index, group in enumerate(side_groups):
                self.create_task_group_card(group, is_main=False, container=self.right_scroll.scrollable_frame, index=index)

    def create_task_group_card(self, group, is_main, container, index):
        group_id = group["id"]
        group_key = (is_main, group_id)
        
        card = tk.Frame(container, bg=BG_CARD, bd=1, highlightbackground=BORDER_COLOR, highlightthickness=1)
        card.pack(fill="x", pady=10, padx=10)
        
        color = ACCENT_PURPLE if is_main else ACCENT_CYAN
        
        # Card Header
        header = tk.Frame(card, bg=BG_CARD_HEADER)
        header.pack(fill="x")
        
        tag_text = tm.tr("main_tag") if is_main else tm.tr("side_tag")
        title_tag = f"{tag_text} {index+1}"
        tag_lbl = tk.Label(header, text=f" {title_tag} ", bg=BG_DARK, fg=color, font=("Helvetica", 8, "bold"))
        tag_lbl.pack(side="left", padx=8, pady=6)
        
        disp_title = shape_for_display(group["title"]) if tm._current_language == "Arabic" else group["title"]
        title_lbl = tk.Label(header, text=disp_title, bg=BG_CARD_HEADER, fg=TEXT_WHITE, font=("Helvetica", 11, "bold"), anchor="w")
        title_lbl.pack(side="left", padx=5)
        
        stars_lbl = tk.Label(header, text=f"⭐ {group['stars']} {tm.tr('stars_label')}", bg=BG_CARD_HEADER, fg=ACCENT_CYAN, font=("Helvetica", 10, "bold"))
        stars_lbl.pack(side="right", padx=10)
        
        # Outer list body
        body = tk.Frame(card, bg=BG_CARD)
        body.pack(fill="x", padx=15, pady=(10, 15))
        
        # Summary row inside card
        info_row = tk.Frame(body, bg=BG_CARD)
        info_row.pack(fill="x", pady=(0, 6))
        
        stats_lbl = tk.Label(info_row, text="", bg=BG_CARD, fg=TEXT_MUTED, font=("Helvetica", 9, "bold"))
        stats_lbl.pack(side="left")
        
        blank_area = tk.Frame(body, bg=BG_CARD, height=20)
        blank_area.pack(fill="both", expand=True)
        
        # Save references for dynamic updating
        self.group_ui_widgets[group_key] = {
            "card": card,
            "body": body,
            "blank_area": blank_area,
            "title_lbl": title_lbl,
            "stars_lbl": stars_lbl,
            "stats_lbl": stats_lbl,
            "item_widgets": []
        }
        
        self.render_group_items(group_key)
        
        # Context menus for card interaction (pointing in actual task group)
        def show_context_menu(event):
            menu = tk.Menu(self.winfo_toplevel(), tearoff=0, bg=BG_CARD, fg=TEXT_WHITE, activebackground=color, activeforeground=BG_DARK, font=("Helvetica", 10))
            menu.add_command(label=tm.tr("add_task_item"), command=lambda: self.add_task_item(is_main, group_id))
            if group["items"]:
                menu.add_command(label=tm.tr("set_percentage_weights"), command=lambda: self.set_group_percentages(is_main, group_id))
            menu.add_separator()
            menu.add_command(label=tm.tr("rename_group"), command=lambda: self.rename_group_title(is_main, group_id))
            menu.add_command(label=tm.tr("change_group_stars"), command=lambda: self.change_group_stars(is_main, group_id))
            menu.add_command(label=tm.tr("save_starred_pack"), command=lambda: self.star_tasks_pack(group))
            menu.add_separator()
            menu.add_command(label=f"❌ {tm.tr('delete_group')}", command=lambda: self.delete_task_group(is_main, group_id))
            menu.tk_popup(event.x_root, event.y_root)
            
        # Bind right click to card, headers, and backgrounds
        card.bind("<Button-3>", show_context_menu)
        header.bind("<Button-3>", show_context_menu)
        body.bind("<Button-3>", show_context_menu)
        blank_area.bind("<Button-3>", show_context_menu)
        title_lbl.bind("<Button-3>", show_context_menu)
        stars_lbl.bind("<Button-3>", show_context_menu)
        tag_lbl.bind("<Button-3>", show_context_menu)
        stats_lbl.bind("<Button-3>", show_context_menu)
        
        def on_blank_click(e):
            if not group["items"]:
                show_context_menu(e)
                
        blank_area.bind("<Button-1>", on_blank_click)

    def render_group_items(self, group_key):
        is_main, group_id = group_key
        ui = self.group_ui_widgets[group_key]
        body = ui["body"]
        
        # Clear existing item widgets
        for row_tuple in ui["item_widgets"]:
            for widget in row_tuple[1:]:
                if widget and widget.winfo_exists():
                    widget.destroy()
        ui["item_widgets"].clear()
        
        group = self.find_group(is_main, group_id)
        if not group:
            return
            
        color = ACCENT_PURPLE if is_main else ACCENT_CYAN
        
        # Draw items
        for item in group.get("items", []):
            item_row = tk.Frame(body, bg=BG_CARD)
            item_row.pack(fill="x", pady=3)
            
            var = tk.BooleanVar(value=item["done"])
            
            def on_check(v=var, itm=item):
                itm["done"] = v.get()
                self.save_day_data()
                self.update_calculations()
                
            cb = tk.Checkbutton(item_row, variable=var, bg=BG_CARD, activebackground=BG_CARD, selectcolor=BG_DARK,
                                highlightthickness=0, bd=0, relief="flat", command=on_check)
            cb.pack(side="left")
            
            def show_item_menu(event, itm=item):
                menu = tk.Menu(self.winfo_toplevel(), tearoff=0, bg=BG_CARD, fg=TEXT_WHITE, activebackground=color, activeforeground=BG_DARK, font=("Helvetica", 9))
                menu.add_command(label=tm.tr("rename_item"), command=lambda: self.rename_task_item(is_main, group_id, itm))
                menu.add_command(label=tm.tr("delete_item"), command=lambda: self.delete_task_item(is_main, group_id, itm))
                menu.tk_popup(event.x_root, event.y_root)
                
            cb.bind("<Button-3>", show_item_menu)
            
            disp_name = shape_for_display(item["name"]) if tm._current_language == "Arabic" else item["name"]
            text_lbl = tk.Label(item_row, text=disp_name, bg=BG_CARD, fg=TEXT_WHITE, font=("Helvetica", 10), anchor="w", wraplength=200, justify="left")
            text_lbl.pack(side="left", fill="x", expand=True, padx=5)
            text_lbl.bind("<Button-3>", show_item_menu)
            
            pct_lbl = tk.Label(item_row, text=f"{item['percent']:.1f}%", bg=BG_CARD, fg=TEXT_MUTED, font=("Helvetica", 9, "bold"))
            pct_lbl.pack(side="right", padx=10)
            pct_lbl.bind("<Button-3>", show_item_menu)
            
            stars_calc_lbl = tk.Label(item_row, text="", bg=BG_CARD, fg=ACCENT_CYAN, font=("Helvetica", 9, "bold"))
            stars_calc_lbl.pack(side="right", padx=5)
            stars_calc_lbl.bind("<Button-3>", show_item_menu)
            
            del_x = tk.Button(item_row, text="✕", bg=BG_CARD, fg=TEXT_MUTED, relief="flat", activebackground=BG_CARD, font=("Helvetica", 8),
                              command=lambda itm=item: self.delete_task_item(is_main, group_id, itm))
            del_x.pack(side="right", padx=5)
            del_x.bind("<Enter>", lambda e, btn=del_x: btn.config(fg="#ef4444"))
            del_x.bind("<Leave>", lambda e, btn=del_x: btn.config(fg=TEXT_MUTED))
            
            ui["item_widgets"].append((item, cb, text_lbl, pct_lbl, stars_calc_lbl, item_row))

    def find_group(self, is_main, group_id):
        groups = self.data["main_tasks"] if is_main else self.data["side_tasks"]
        for g in groups:
            if g["id"] == group_id:
                return g
        return None

    def add_task_item(self, is_main, group_id):
        group = self.find_group(is_main, group_id)
        if not group:
            return
            
        diag = CustomDialog(self, tm.tr_raw("add_task_item"), tm.tr("enter_item_desc"))
        self.wait_window(diag)
        if diag.result is None:
            return
            
        item_name = diag.result
        items = group.setdefault("items", [])
        num_items = len(items) + 1
        
        new_item = {
            "name": item_name,
            "done": False,
            "percent": 0.0
        }
        items.append(new_item)
        
        # Auto redistribute percentages equally
        base = round(100.0 / num_items, 1)
        for i, item in enumerate(items):
            item["percent"] = base
        diff = round(100.0 - (base * num_items), 1)
        items[-1]["percent"] = round(base + diff, 1)
        
        self.save_day_data()
        self.render_group_items((is_main, group_id))
        self.update_calculations()

    def rename_task_item(self, is_main, group_id, item):
        diag = CustomDialog(self, tm.tr_raw("rename_item"), tm.tr("enter_new_name"), value=item["name"])
        self.wait_window(diag)
        if diag.result is not None:
            item["name"] = diag.result
            self.save_day_data()
            self.render_group_items((is_main, group_id))

    def delete_task_item(self, is_main, group_id, item):
        group = self.find_group(is_main, group_id)
        if not group:
            return
        
        items = group.get("items", [])
        if item in items:
            # Enforce confirmation before deletion
            if messagebox.askyesno(tm.tr("delete_item_title"), tm.tr("delete_item_prompt").format(name=item['name'])):
                items.remove(item)
                
                # Redistribute percentages equally
                if items:
                    n = len(items)
                    base = round(100.0 / n, 1)
                    for remaining_item in items:
                        remaining_item["percent"] = base
                    diff = round(100.0 - (base * n), 1)
                    items[-1]["percent"] = round(base + diff, 1)
                    
                self.save_day_data()
                self.render_group_items((is_main, group_id))
                self.update_calculations()

    def set_group_percentages(self, is_main, group_id):
        group = self.find_group(is_main, group_id)
        if not group or not group.get("items"):
            return
            
        diag = PercentageDialog(self, f"Weights - {group['title']}", group["items"])
        self.wait_window(diag)
        if diag.result is not None:
            group["items"] = diag.result
            self.save_day_data()
            self.render_group_items((is_main, group_id))
            self.update_calculations()

    def rename_group_title(self, is_main, group_id):
        group = self.find_group(is_main, group_id)
        if not group:
            return
            
        diag = CustomDialog(self, tm.tr_raw("rename_group"), tm.tr("enter_new_group_title"), value=group["title"])
        self.wait_window(diag)
        if diag.result is not None and diag.result.strip():
            group["title"] = diag.result.strip()
            self.save_day_data()
            
            ui = self.group_ui_widgets.get((is_main, group_id))
            if ui:
                disp_t = shape_for_display(group["title"]) if tm._current_language == "Arabic" else group["title"]
                ui["title_lbl"].config(text=disp_t)
                
            self.update_calculations()

    def change_group_stars(self, is_main, group_id):
        group = self.find_group(is_main, group_id)
        if not group:
            return
            
        diag = CustomDialog(self, tm.tr_raw("change_group_stars"), tm.tr("enter_new_star_count"), value=str(group["stars"]), is_numeric=True)
        self.wait_window(diag)
        if diag.result is not None:
            group["stars"] = int(diag.result)
            self.save_day_data()
            
            ui = self.group_ui_widgets.get((is_main, group_id))
            if ui:
                ui["stars_lbl"].config(text=f"⭐ {group['stars']} {tm.tr('stars_label')}")
                
            self.update_calculations()

    def delete_task_group(self, is_main, group_id):
        groups = self.data["main_tasks"] if is_main else self.data["side_tasks"]
        group = self.find_group(is_main, group_id)
        if group and messagebox.askyesno(tm.tr("delete_group_title"), tm.tr("delete_group_prompt").format(title=group['title'])):
            groups.remove(group)
            self.save_day_data()
            self.render_all_tasks()
            self.update_calculations()

    def update_calculations(self):
        if not self.data:
            return
            
        main_done_items = 0
        main_tot_items = 0
        main_earned_stars = 0.0
        main_tot_stars = 0.0
        
        side_done_items = 0
        side_tot_items = 0
        side_earned_stars = 0.0
        side_tot_stars = 0.0
        
        # Calculate Main
        for g in self.data.get("main_tasks", []):
            group_key = (True, g["id"])
            ui = self.group_ui_widgets.get(group_key)
            
            g_total_stars = float(g.get("stars", 0))
            g_earned_stars = 0.0
            g_total_items = len(g.get("items", []))
            g_done_items = sum(1 for it in g.get("items", []) if it["done"])
            
            main_tot_items += g_total_items
            main_done_items += g_done_items
            main_tot_stars += g_total_stars
            
            items_ref = ui["item_widgets"] if ui else []
            for row_tuple in items_ref:
                item_dict, cb, text_lbl, pct_lbl, stars_calc_lbl, _ = row_tuple
                
                item_percent = float(item_dict.get("percent", 0.0))
                item_stars = g_total_stars * (item_percent / 100.0)
                
                if item_dict["done"]:
                    g_earned_stars += item_stars
                    text_lbl.config(fg=SUCCESS_GREEN, font=("Helvetica", 10, "overstrike"))
                else:
                    text_lbl.config(fg=TEXT_WHITE, font=("Helvetica", 10))
                    
                stars_calc_lbl.config(text=f"{item_stars:.1f}⭐")
                
            main_earned_stars += g_earned_stars
            
            if ui:
                done_ratio = (g_done_items / g_total_items) if g_total_items > 0 else 0.0
                card_lbl_text = f"{tm.tr('report')} \u200E{g_done_items}/{g_total_items} ({done_ratio:.2f})\u200E | {tm.tr('earned')} \u200E{g_earned_stars:.1f}/{g_total_stars:.1f} ({(g_earned_stars/g_total_stars if g_total_stars > 0 else 0.0):.2f})\u200E"
                ui["stats_lbl"].config(text=card_lbl_text)
                
        # Calculate Side
        for g in self.data.get("side_tasks", []):
            group_key = (False, g["id"])
            ui = self.group_ui_widgets.get(group_key)
            
            g_total_stars = float(g.get("stars", 0))
            g_earned_stars = 0.0
            g_total_items = len(g.get("items", []))
            g_done_items = sum(1 for it in g.get("items", []) if it["done"])
            
            side_tot_items += g_total_items
            side_done_items += g_done_items
            side_tot_stars += g_total_stars
            
            items_ref = ui["item_widgets"] if ui else []
            for row_tuple in items_ref:
                item_dict, cb, text_lbl, pct_lbl, stars_calc_lbl, _ = row_tuple
                
                item_percent = float(item_dict.get("percent", 0.0))
                item_stars = g_total_stars * (item_percent / 100.0)
                
                if item_dict["done"]:
                    g_earned_stars += item_stars
                    text_lbl.config(fg=SUCCESS_GREEN, font=("Helvetica", 10, "overstrike"))
                else:
                    text_lbl.config(fg=TEXT_WHITE, font=("Helvetica", 10))
                    
                stars_calc_lbl.config(text=f"{item_stars:.1f}⭐")
                
            side_earned_stars += g_earned_stars
            
            if ui:
                done_ratio = (g_done_items / g_total_items) if g_total_items > 0 else 0.0
                card_lbl_text = f"{tm.tr('report')} \u200E{g_done_items}/{g_total_items} ({done_ratio:.2f})\u200E | {tm.tr('earned')} \u200E{g_earned_stars:.1f}/{g_total_stars:.1f} ({(g_earned_stars/g_total_stars if g_total_stars > 0 else 0.0):.2f})\u200E"
                ui["stats_lbl"].config(text=card_lbl_text)
                
        # Calculate packs done
        main_done_packs = 0
        main_tot_packs = len(self.data.get("main_tasks", []))
        for g in self.data.get("main_tasks", []):
            items = g.get("items", [])
            if items:
                if all(item.get("done") for item in items):
                    main_done_packs += 1
            else:
                if g.get("done", False):
                    main_done_packs += 1

        side_done_packs = 0
        side_tot_packs = len(self.data.get("side_tasks", []))
        for g in self.data.get("side_tasks", []):
            items = g.get("items", [])
            if items:
                if all(item.get("done") for item in items):
                    side_done_packs += 1
            else:
                if g.get("done", False):
                    side_done_packs += 1

        # Update Static Summaries
        left_ratio_items = (main_done_items / main_tot_items) if main_tot_items > 0 else 0.0
        left_ratio_stars = (main_earned_stars / main_tot_stars) if main_tot_stars > 0 else 0.0
        left_ratio_packs = (main_done_packs / main_tot_packs) if main_tot_packs > 0 else 0.0
        l1 = fmt_stat("tasks_done", f"\u200E{main_done_items}/{main_tot_items} ({left_ratio_items:.2f})\u200E")
        l2 = fmt_stat("stars_earned", f"\u200E{main_earned_stars:.1f}/{main_tot_stars:.1f} ({left_ratio_stars:.2f})\u200E")
        l3 = fmt_stat("packs_done", f"\u200E{main_done_packs}/{main_tot_packs} ({left_ratio_packs:.2f})\u200E")
        self.left_summary_lbl.config(text=f"{l1}\n{l2}\n{l3}")
        
        right_ratio_items = (side_done_items / side_tot_items) if side_tot_items > 0 else 0.0
        right_ratio_stars = (side_earned_stars / side_tot_stars) if side_tot_stars > 0 else 0.0
        right_ratio_packs = (side_done_packs / side_tot_packs) if side_tot_packs > 0 else 0.0
        r1 = fmt_stat("tasks_done", f"\u200E{side_done_items}/{side_tot_items} ({right_ratio_items:.2f})\u200E")
        r2 = fmt_stat("stars_earned", f"\u200E{side_earned_stars:.1f}/{side_tot_stars:.1f} ({right_ratio_stars:.2f})\u200E")
        r3 = fmt_stat("packs_done", f"\u200E{side_done_packs}/{side_tot_packs} ({right_ratio_packs:.2f})\u200E")
        self.right_summary_lbl.config(text=f"{r1}\n{r2}\n{r3}")
        
        # Update Grand bottom totals
        grand_total_items = main_tot_items + side_tot_items
        grand_done_items = main_done_items + side_done_items
        grand_item_ratio = (grand_done_items / grand_total_items) if grand_total_items > 0 else 0.0
        
        grand_total_stars = main_tot_stars + side_tot_stars
        grand_earned_stars = main_earned_stars + side_earned_stars
        grand_star_ratio = (grand_earned_stars / grand_total_stars) if grand_total_stars > 0 else 0.0

        grand_done_packs = main_done_packs + side_done_packs
        grand_total_packs = main_tot_packs + side_tot_packs
        grand_pack_ratio = (grand_done_packs / grand_total_packs) if grand_total_packs > 0 else 0.0
        
        self.grand_tasks_lbl.config(text=fmt_stat("total_tasks", f"\u200E{grand_done_items}/{grand_total_items} ({grand_item_ratio:.2f})\u200E"))
        self.grand_stars_lbl.config(text=fmt_stat("total_stars", f"\u200E{grand_earned_stars:.1f}/{grand_total_stars:.1f} ({grand_star_ratio:.2f})\u200E"))
        self.grand_packs_lbl.config(text=fmt_stat("total_packs", f"\u200E{grand_done_packs}/{grand_total_packs} ({grand_pack_ratio:.2f})\u200E"))
        
        self.draw_progress_bar(self.pb_canvas, grand_star_ratio, ACCENT_PURPLE)
        self.draw_progress_bar(self.pb_tasks_canvas, grand_item_ratio, SUCCESS_GREEN)

    def draw_progress_bar(self, canvas, ratio, color):
        canvas.delete("all")
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width <= 1:
            width = 300
        if height <= 1:
            height = 18
            
        canvas.create_rectangle(0, 0, width, height, fill=BG_DARK, outline="")
        
        fill_w = int(width * min(1.0, max(0.0, ratio)))
        if fill_w > 0:
            canvas.create_rectangle(0, 0, fill_w, height, fill=color, outline="")
            canvas.create_line(0, 1, fill_w, 1, fill=GLOW_COLOR)
            
        text_pct = f"{int(ratio * 100)}%"
        canvas.create_text(width/2, height/2, text=text_pct, fill=TEXT_WHITE, font=("Helvetica", 9, "bold"))
        
        canvas.bind("<Configure>", lambda e: self.draw_progress_bar(canvas, ratio, color))

    def confirm_and_exit(self):
        self.on_ai_comment_modified()
        self.save_day_data()
        if self.return_screen == "calendar":
            self.parent.show_calendar_screen()
        else:
            self.parent.show_start_screen()


if __name__ == "__main__":
    app = MissionApp()
    style = ttk.Style()
    style.theme_use('default')
    style.configure("TScrollbar", gripcount=0, background=BG_CARD, darkcolor=BG_DARK, lightcolor=BORDER_COLOR, troughcolor=BG_DARK, bordercolor=BORDER_COLOR, arrowcolor=TEXT_MUTED)
    style.map("TScrollbar", background=[('active', ACCENT_PURPLE), ('pressed', GLOW_COLOR)])
    app.mainloop()
