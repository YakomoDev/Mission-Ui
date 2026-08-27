#!/usr/bin/env python3
# YakomoDev - https://ko-fi.com/yakomodev
import os
import json
import datetime
import sys
import subprocess
import socket
import sqlite3

# Offline environment guard
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

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

def get_model_path():
    agent_dir = os.path.join(ROOT_DIR, "agent")
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

MODEL_PATH = get_model_path()

# Virtual environment python path
is_windows = os.name == "nt"
if is_windows:
    VENV_PYTHON = os.path.join(ROOT_DIR, ".venv", "Scripts", "python.exe")
else:
    VENV_PYTHON = os.path.join(ROOT_DIR, ".venv", "bin", "python")

# Auto-relaunch inside the virtual environment if it exists and we aren't using it yet
if os.path.exists(VENV_PYTHON) and os.path.abspath(sys.executable) != os.path.abspath(VENV_PYTHON):
    print(f"[*] Detecting project virtual environment. Relaunching inside venv...")
    try:
        # Run ourselves using the venv python interpreter
        result = subprocess.run([VENV_PYTHON] + sys.argv)
        sys.exit(result.returncode)
    except Exception as e:
        print(f"[-] Failed to relaunch inside venv: {e}")
        # Continue executing with current python and hope llama-cpp-python is installed globally

def load_language_pref():
    prefs_path = os.path.join(ROOT_DIR, "data", "prefs.json")
    if os.path.exists(prefs_path):
        try:
            with open(prefs_path, "r", encoding="utf-8") as f:
                prefs = json.load(f)
                return prefs.get("language", "English")
        except Exception:
            pass
    return "English"

def load_day_data(today_str):
    db_path = os.path.join(ROOT_DIR, "data", "missions.db")
    if not os.path.exists(db_path):
        print(f"[-] Database file not found at: {db_path}")
        print("[-] Please run the Mission Ui app first to initialize the database.")
        return None
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT main_tasks, side_tasks, ai_comment FROM days WHERE date = ?", (today_str,))
        row = c.fetchone()
        conn.close()
        if row:
            return {
                "date": today_str,
                "main_tasks": json.loads(row[0]),
                "side_tasks": json.loads(row[1]),
                "ai_comment": row[2]
            }
        else:
            print(f"[-] Today's tracker date {today_str} not initialized in database.")
            print("[-] Please open the app first to initialize today's tracker.")
            return None
    except Exception as e:
        print(f"[-] Error reading daily database records: {e}")
        return None

def save_day_data(today_str, comment):
    db_path = os.path.join(ROOT_DIR, "data", "missions.db")
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("UPDATE days SET ai_comment = ? WHERE date = ?", (comment, today_str))
        conn.commit()
        conn.close()
        print(f"[+] Successfully saved commentary to local database!")
        return True
    except Exception as e:
        print(f"[-] Error writing comment to database: {e}")
        return False

def generate_prompt(data, lang):
    date_str = data.get("date", datetime.date.today().isoformat())
    main_tasks = data.get("main_tasks", [])
    side_tasks = data.get("side_tasks", [])
    
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
    
    if lang == "French":
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
            
        # Process Main Tasks
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
                    
        # Process Side Tasks
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
                    
        time_context = "CONTEXTE TEMPOREL CRITIQUE : Cette date est AUJOURD'HUI (en cours/non terminée). Écris au présent."
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
            "5. LANGUE : Tu dois obligatoirement rédiger ta réponse en français et ne jamais utiliser l'anglais.\n\n"
            f"=== FAITS DE PROGRESSION ENREGISTRÉS ===\n{text}\n\n"
            "Réponds uniquement avec le résumé de 3 phrases en français. Ne produis aucun code, JSON ou mise en forme."
        )
    elif lang == "Arabic":
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
            
        # Process Main Tasks
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
                    
        # Process Side Tasks
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
                    
        time_context = "سياق زمني حرج: هذا التاريخ هو اليوم (لا يزال قيد التنفيذ). اكتب بصيغة المضارع."
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
            "--- المهمات الرئيسية ---\n"
            "مجموعة المهام الرئيسية 'Gym' (الإنجاز: 0.0%)\n"
            "  - [معلق] Go gym (back and shoulders day)\n"
            "مجموعة المهام الرئيسية 'Pixel art' (الإنجاز: 100.0%)\n"
            "  - [مكتمل] Draw pixel art\n\n"
            "--- المهمات الثانوية ---\n"
            "مجموعة المهام الثانوية 'Quran' (الإنجاز: 100.0%)\n"
            "  - [مكتمل] Read Quran\n"
            "مجموعة المهام الثانوية 'Sleep' (الإنجاز: 0.0%)\n"
            "  - [معلق] Sleep early\n\n"
            "المخرجات (3 جمل بالضبط باللغة العربية):\n"
            "أكمل المستخدم 2 من أصل 4 مهمة اليوم بمعدل إنجاز إجمالي 50.0%. اكتملت مجموعة المهام Pixel art ومجموعة المهام Quran بالكامل. وظلت المهام Go gym (back and shoulders day) وSleep early معلقة.\n"
            "========================================\n\n"
            f"=== حقائق التقدم المسجلة ===\n{text}\n\n"
            "أجب بالملخص المكون من 3 جمل فقط باللغة العربية. لا تخرج أي كود أو تنسيقات إضافية."
        )
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
            
        # Process Main Tasks
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
                    
        # Process Side Tasks
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
                    
        time_context = "CRITICAL TIME CONTEXT: This date is TODAY (still in progress/ongoing). Write in the present tense."
        user_msg = (
            "You are a strict, factual Daily Task Analyst for the desktop app 'Mission Ui'.\n"
            f"{time_context}\n"
            "Review the logged progress facts below and write a strictly factual, dry, 3-sentence summary of the data.\n\n"
            "CRITICAL CONSTRAINTS:\n"
            "1. NO SUBJECTIVE FLUFF: Do NOT use qualitative adjectives or descriptors (e.g., do NOT use words like 'steady', 'minimal', 'consistent', 'effort', 'great', 'active', 'good', 'bad').\n"
            "2. NO PLACEHOLDERS: Do NOT use dummy names like 'Task A' or 'Group 1'. Refer to task groups and task items ONLY by their exact names as written in the facts list.\n"
            "3. MATHEMATICAL FACTS ONLY: Stick strictly to the completion numbers, percentages, and names provided in the facts. Do NOT perform any math calculations yourself; copy the percentages directly from the facts list.\n"
            "4. NO STARS OR SCORES: Do NOT mention stars, points, weights, or scores in your response. Focus strictly on completion status and which tasks are completed or pending.\n"
            "5. LANGUAGE: Write the commentary strictly in English.\n\n"
            f"=== LOGGED PROGRESS FACTS ===\n{text}\n\n"
            "Respond with only the 3-sentence summary. Do not output any code, JSON, or formatting."
        )
        
    prompt = f"<start_of_turn>user\n{user_msg}<end_of_turn>\n<start_of_turn>model\n"
    return prompt

def query_local_model(prompt):
    # Verify model file exists
    if not os.path.exists(MODEL_PATH):
        print(f"[-] Model file not found at: {MODEL_PATH}")
        print("[-] Please run setup_agent.py to download/move the model.")
        return None
        
    if llama_cpp is None:
        print("[-] llama-cpp-python is not installed.")
        print("[-] Please run setup_agent.py to install it.")
        return None
        
    print(f"[*] Loading model: {MODEL_PATH}...")
    print("[*] Performing offline local inference...")
    
    try:
        # Load the model
        llm = llama_cpp.Llama(
            model_path=MODEL_PATH,
            n_ctx=4096,
            verbose=False,
            seed=-1
        )
        
        # Run completion
        response = llm(
            prompt,
            max_tokens=256,
            temperature=0.3,
            repeat_penalty=1.1,
            top_p=0.9,
            stop=["<end_of_turn>", "<|im_end|>"]
        )
        
        ai_text = response["choices"][0]["text"].strip()
        return ai_text
    except Exception as e:
        print(f"[-] Error during local model execution: {e}")
        return None

def run_validation_and_fallback(comment, data, lang):
    text_lower = comment.lower()
    has_placeholders = any(x in text_lower for x in ["task a", "task b", "task c", "group 1", "group 2", "group 3"])
    
    main_tasks = data.get("main_tasks", [])
    side_tasks = data.get("side_tasks", [])
    date_str = data.get("date", datetime.date.today().isoformat())
    
    total_items = 0
    done_items = 0
    completed_groups = []
    pending_items = []
    
    for g in main_tasks + side_tasks:
        items = g.get("items", [])
        if items:
            total_items += len(items)
            done_g = sum(1 for i in items if i.get("done"))
            done_items += done_g
            if done_g == len(items):
                completed_groups.append(g.get("title"))
            else:
                for i in items:
                    if not i.get("done"):
                        pending_items.append(i.get("name"))
        else:
            total_items += 1
            is_done = g.get("done", False)
            done_items += 1 if is_done else 0
            if is_done:
                completed_groups.append(g.get("title"))
            else:
                pending_items.append(g.get("title"))
                                
    has_math_hallucination = False
    if done_items > 0 and ("0.0%" in comment or "0%" in comment):
        has_math_hallucination = True
        
    is_arabic = (lang == "Arabic")
    def contains_arabic(text):
        return any('\u0600' <= char <= '\u06FF' or '\u0750' <= char <= '\u077F' or '\u08A0' <= char <= '\u08FF' for char in text)
    
    has_language_hallucination = is_arabic and not contains_arabic(comment)
    
    if has_placeholders or has_math_hallucination or has_language_hallucination or len(comment.strip()) < 10:
        is_today = (date_str == datetime.date.today().isoformat())
        
        if lang == "French":
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
        elif lang == "Arabic":
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
        return f"{s1} {s2} {s3}"
    return comment

def main():
    print("=== Mission Ui Local AI Engine ===")
    today_str = datetime.date.today().isoformat()
    data = load_day_data(today_str)
    if not data:
        return
        
    lang = load_language_pref()
    print(f"[*] Loaded active language preference: {lang}")
    
    prompt = generate_prompt(data, lang)
    comment = query_local_model(prompt)
    
    if comment:
        validated_comment = run_validation_and_fallback(comment, data, lang)
        
        print("\n[+] Received commentary from local Gemma model:")
        print(f"\"\"\"\n{validated_comment}\n\"\"\"\n")
        
        save_day_data(today_str, validated_comment)
        print("[*] Open Mission Ui to view the updated response!")
    else:
        print("[-] Failed to generate AI commentary.")

if __name__ == "__main__":
    main()
