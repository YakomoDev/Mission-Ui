# Prepared with love by YakomoDev - https://ko-fi.com/yakomodev
"""
about_screen.py — About Page for Mission Ui
A rich, scrollable About screen accessible from Settings.
Covers: what the app is, who made it, every feature, every screen and button,
comparison with other apps, and future roadmap.
"""

import tkinter as tk
from tkinter import ttk
import webbrowser
import theme_manager as tm

# ──────────────────────────────────────────────────────────────────────────────
# Content helpers – builds per-language rich content
# ──────────────────────────────────────────────────────────────────────────────

def _build_sections():
    lang = tm._current_language

    if lang == "French":
        return [
            ("🌟 Mission Ui — Qu'est-ce que c'est ?", [
                "Mission Ui est un gestionnaire de missions et de tâches quotidiennes entièrement hors ligne, "
                "développé par YakomoDev. L'application est conçue pour aider les personnes ambitieuses à "
                "organiser leur journée avec précision, suivre leurs progrès, s'améliorer spirituellement et "
                "recevoir des retours intelligents générés localement par une IA légère.",
                "",
                "Contrairement aux applications cloud standards (Notion, Todoist, TickTick…), Mission Ui "
                "fonctionne entièrement sur votre machine — aucun compte, aucune connexion internet, "
                "aucune donnée envoyée. Votre vie reste privée.",
            ]),
            ("👨‍💻 Qui l'a fait et pourquoi ?", [
                "Mission Ui a été conçu et développé par YakomoDev, un développeur passionné qui voulait "
                "combiner productivité islamique, suivi de missions rigoureuses et intelligence artificielle "
                "locale dans une seule application élégante et sombre.",
                "",
                "L'idée : une 'paper de mission' numérique — comme une feuille physique de tâches mais "
                "enrichie d'étoiles, de statistiques, d'un journal personnel et d'une IA locale.",
            ]),
            ("📋 Fonctionnalités principales", [
                "• Suivi de tâches quotidiennes avec deux catégories : Missions Principales (avec étoiles) et Missions Secondaires.",
                "• Système d'étoiles pondéré : chaque tâche a un poids en étoiles et un pourcentage de contribution.",
                "• Blueprints (modèles de journée) : créez des modèles réutilisables ou démarrez une journée vide.",
                "• Journal quotidien (Memo) : éditeur de texte riche avec gras, italique, couleurs, tailles de police.",
                "• IA locale Gemma 1B : génère des commentaires sur votre journée sans aucune connexion.",
                "• Conseils IA : petit conseil rapide ou analyse approfondie de votre productivité.",
                "• Calendrier mensuel : visualisez chaque journée avec ses couleurs de progression.",
                "• Graphiques mensuels : courbes, barres et totaux pour suivre vos performances dans le temps.",
                "• Export PDF/PNG : exportez votre feuille de mission en papier numérique stylisé.",
                "• Adhkar (Azkars) : compteurs de dhikr du matin, du soir et du sommeil avec progression.",
                "• Coran : lecteur audio et visionneuse de Coran intégrés, avec recherche de sourate.",
                "• Thèmes multiples : 10+ thèmes visuels dont Nord Ice, Sombre Classique, Emeraude, etc.",
                "• Support multilingue : Anglais, Français, Arabe (RTL complet).",
            ]),
            ("🖥️ Toutes les pages et leurs boutons", [
                "── ÉCRAN PRINCIPAL ──",
                "• Créer la liste du jour : démarre un nouveau jour (vide ou depuis un modèle).",
                "• Modifier la liste du jour : ouvre le jour déjà créé pour continuer.",
                "• Tableau de bord Calendrier : vue mensuelle de toutes vos journées.",
                "• Tableau de bord Graphiques : visualisations de vos performances mensuelles.",
                "• 🔧 Outils : accès aux outils (Coran texte, Coran audio, Adhkar).",
                "• ⚙️ Paramètres : langue, thème, page À propos.",
                "• ☕ Soutenir le projet : lien Ko-fi vers la page de support.",
                "",
                "── SUIVI DE TÂCHES QUOTIDIENNES ──",
                "• ← Menu : quitter (avec sauvegarde automatique).",
                "• 📥 Télécharger : exporter la feuille de tâches en PDF/PNG.",
                "• Missions principales et secondaires avec cases à cocher.",
                "• Barres de progression : étoiles gagnées et tâches accomplies.",
                "• Générer un retour IA : inférence locale Gemma pour commenter votre journée.",
                "• Petit conseil / Analyse approfondie : deux niveaux d'analyse IA.",
                "",
                "── CALENDRIER ──",
                "• ◀ / ▶ : mois précédent/suivant.",
                "• Clic sur une case : affiche les détails du jour dans le panneau latéral.",
                "• Double-clic : ouvre la feuille de tâches du jour.",
                "• Clic droit : télécharger les deux pages (tâches + mémo).",
                "",
                "── JOURNAL / MÉMO ──",
                "• 𝐁 Gras, 𝑰 Italique, 🎨 Couleur, Taille de police.",
                "• 📥 Exporter uniquement les pages du mémo.",
                "• ◀ / ▶ : naviguer entre les jours.",
                "",
                "── GRAPHIQUES ──",
                "• Onglets : Étoiles, Tâches, Paquets.",
                "• Graphique en barres + courbe de tendance + résumé mensuel.",
                "",
                "── CORAN (AUDIO) ──",
                "• Recherche de sourate, lecture/arrêt, barre de progression, volume.",
                "",
                "── ADHKAR (DHIKR) ──",
                "• Trois sessions : Matin / Soir / Sommeil. Compteur tactile avec progression.",
            ]),
            ("🆚 Ce qui le rend spécial", [
                "• 100% hors ligne — aucune donnée n'est partagée.",
                "• IA embarquée (Gemma 1B GGUF) — retour intelligent sans abonnement.",
                "• Système d'étoiles pondéré, unique sur le marché.",
                "• Export papier numérique (PDF/PNG) stylisé avec logo et commentaires.",
                "• Intégration spirituelle : Coran + Adhkar dans la même application.",
                "• Support RTL complet pour l'arabe.",
                "• 10+ thèmes visuels premium.",
            ]),
            ("🔮 Fonctionnalités futures prévues", [
                "• Langues supplémentaires : Espagnol, Turc, Ourdou et plus.",
                "• Paramètres IA avancés : modèles plus grands pour usage professionnel.",
                "• Mode synchronisation optionnel (cloud chiffré).",
                "• Tableaux de bord avancés : tendances hebdomadaires, mensuelles et annuelles.",
                "• Rappels et notifications système.",
                "• Plus d'outils de bien-être et de productivité.",
                "• Application mobile compagnon.",
            ]),
            ("☕ Soutenir le projet", [
                "Si Mission Ui vous aide dans votre quotidien, soutenez le développement :",
                "→ https://ko-fi.com/yakomodev",
                "",
                "Merci d'utiliser Mission Ui. 🙏",
            ]),
        ]

    elif lang == "Arabic":
        return [
            ("🌟 Mission Ui — ما هو التطبيق؟", [
                "Mission Ui هو مدير مهام ومهمات يومية يعمل بالكامل دون اتصال، طوّره YakomoDev. "
                "صُمِّم لمساعدة الأشخاص الطموحين على تنظيم يومهم بدقة وتتبع تقدمهم وتلقي ملاحظات ذكية.",
                "",
                "بخلاف تطبيقات السحابة، يعمل Mission Ui على جهازك فقط — لا حساب، لا إنترنت، لا بيانات مُرسَلة.",
            ]),
            ("👨‍💻 من صنعه ولماذا؟", [
                "صمّمه وطوّره YakomoDev لدمج الإنتاجية الإسلامية، والذكاء الاصطناعي المحلي، "
                "وتتبع المهمات في تطبيق أنيق واحد.",
            ]),
            ("📋 الميزات الرئيسية", [
                "• تتبع المهام: مهام رئيسية بالنجوم + مهام جانبية.",
                "• نظام النجوم الموزون: لكل مهمة وزن ونسبة مئوية.",
                "• قوالب اليوم: ابدأ من قالب أو ابدأ بيوم فارغ.",
                "• مذكرة يومية: محرر نصوص غني بالألوان والأحجام.",
                "• ذكاء اصطناعي محلي Gemma 1B: تعليق على يومك بدون إنترنت.",
                "• التقويم الشهري: شاهد كل يوم بألوان التقدم.",
                "• الرسوم البيانية الشهرية.",
                "• تصدير PDF/PNG: ورقة مهمة رقمية منسقة.",
                "• الأذكار: عدادات بالضغط مع شريط تقدم.",
                "• القرآن: قارئ صوتي ونصي مدمج.",
                "• ثيمات متعددة: 10+ ثيمات بصرية.",
                "• دعم عربي كامل (RTL).",
            ]),
            ("🔮 ميزات مستقبلية", [
                "• لغات إضافية: إسبانية، تركية، أردية.",
                "• إعدادات ذكاء اصطناعي متقدمة ونماذج أكبر.",
                "• مزامنة اختيارية مشفرة.",
                "• لوحات تحكم متقدمة وتذكيرات.",
                "• مزيد من أدوات الإنتاجية والرفاهية.",
            ]),
            ("☕ دعم المشروع", [
                "إذا ساعدك التطبيق، يمكنك دعم التطوير:",
                "→ https://ko-fi.com/yakomodev",
                "",
                "شكراً لاستخدامك Mission Ui. 🙏",
            ]),
        ]

    else:  # English
        return [
            ("🌟 Mission Ui — What is it?", [
                "Mission Ui is a fully offline daily mission and task manager built by YakomoDev. "
                "It is designed for ambitious individuals who want to organize their day with precision, "
                "track their progress over time, grow spiritually, and receive intelligent AI feedback — "
                "all without sending a single byte of data to the cloud.",
                "",
                "Unlike mainstream cloud apps (Notion, Todoist, TickTick…), Mission Ui runs completely "
                "on your own machine. No account required, no internet connection needed, no data ever "
                "leaves your device. Your life stays private.",
            ]),
            ("👨‍💻 Who built it and why?", [
                "Mission Ui was designed and built by YakomoDev — a passionate developer who wanted to "
                "combine Islamic productivity principles, rigorous mission tracking, and local AI "
                "intelligence into a single elegant dark-themed application.",
                "",
                "The concept: a digital 'mission paper' — like the classic physical task sheet, but "
                "enriched with a weighted star system, statistics, a rich-text personal diary, and a "
                "locally running AI model that comments on your day with zero internet dependency.",
            ]),
            ("📋 Core Features", [
                "• Daily Task Tracking — Two categories: Main Missions (star-weighted) and Side Missions.",
                "• Weighted Star System — Each task group has a star value; sub-items carry a % weight.",
                "• Day Blueprints — Reusable day templates (e.g. 'Study Day', 'Ramadan Routine') or blank days.",
                "• Daily Diary / Memo — Rich text editor with bold, italic, custom colors, and font sizes.",
                "• Local AI Commentary — Gemma 1B GGUF model runs on your machine; generates day feedback.",
                "• AI Coach Advice — Two levels: quick small tip or a deep productivity analysis.",
                "• Monthly Calendar — Color-coded day grid showing completion ratios at a glance.",
                "• Monthly Graphs Dashboard — Canvas-drawn bar charts, trend lines and monthly totals.",
                "• PDF & PNG Export — Export your daily mission sheet as a styled printable document.",
                "• Adhkar (Dhikr Counters) — Morning, evening, and sleep sessions with tap-to-count progress tracking.",
                "• Quran Reader & Audio Player — Integrated text viewer and audio streamer with Surah search.",
                "• Starred Packs — Save and reuse favorite task group packs across days.",
                "• 10+ Visual Themes — Nord Ice, Classic Dark, Emerald, Sakura, Desert Gold, and more.",
                "• Multi-language Support — Full English, French, and Arabic (RTL) support.",
            ]),
            ("🖥️ Every Screen & Button Explained", [
                "── MAIN / START SCREEN ──",
                "• Create Today's Task List — Start a new day (blank or from blueprint).",
                "• Edit & Continue Today's List — Open today's already-created mission tracker.",
                "• Calendar Dashboard — Full monthly calendar view of all your logged days.",
                "• Graphs Dashboard — Visual performance analytics with bar charts and trend lines.",
                "• 🔧 Tools — Expands a sub-panel: Quran text, Quran audio, Adhkar buttons.",
                "• ⚙️ Settings — Opens the settings page (language, theme, about).",
                "• ☕ Support the Project — Opens the Ko-fi donation page in your browser.",
                "",
                "── DAILY TASK TRACKER (Mission Paper) ──",
                "• ← Menu — Exit the tracker (auto-saves before closing).",
                "• 📥 Download — Exports only the task paper as PDF or PNG.",
                "• Main Mission Groups — Each group has a title, star value, and sub-tasks with checkboxes.",
                "• Side Mission Groups — Similar but separate category for secondary objectives.",
                "• Task Checkboxes (✓/○) — Click to mark individual sub-tasks as done/undone.",
                "• Stars Progress Bar — Shows earned stars vs total possible stars.",
                "• Tasks Completion Bar — Shows how many individual tasks are completed.",
                "• Grand Total Overview — Combined star and task counts for main + side missions.",
                "• AI Commentary Box — Editable text box showing the generated AI day summary.",
                "• Generate Feedback — Runs local Gemma 1B to analyze your day.",
                "• Copy Prompt — Copies the AI prompt to clipboard for external use.",
                "• Small Advice — Requests a concise AI coaching tip.",
                "• Deep Analysis — Requests a thorough AI analysis of your productivity patterns.",
                "",
                "── CALENDAR SCREEN ──",
                "• ← Menu — Return to main screen.",
                "• Month ◀ / ▶ — Navigate between months.",
                "• Day Cells — Color-coded: green (high), yellow (partial), red (low), grey (no log).",
                "• Single Click on Day — Shows day details in the right panel (tasks, stars, items).",
                "• Double Click on Day — Opens the mission tracker for that day directly.",
                "• Right Click on Day — Context menu: Download both pages or View Memo.",
                "• Day Details Panel — Scrollable preview of that day's tasks and star stats.",
                "• Deep Advice Panel — Shows the saved deep AI analysis for that day.",
                "",
                "── DAILY DIARY / MEMO SCREEN ──",
                "• ← Menu — Exit and auto-save.",
                "• ◀ / ▶ Date Navigator — Move to previous or next day's memo.",
                "• 📥 Download — Exports only the memo pages as PDF or PNG.",
                "• 💾 Save — Manually saves memo content to the database.",
                "• 𝐁 Bold — Toggle bold on selected text or set for next typed characters.",
                "• 𝑰 Italic — Toggle italic on selected text.",
                "• 🎨 Color Picker — Opens a full color dialog; chosen color shows in the swatch.",
                "• Color Swatch Box — Small square showing the currently active text color.",
                "• ● Preset Color Dots — 5 quick-access colors (red, green, cyan, orange, white).",
                "• Font Size Dropdown — 10pt to 32pt; applies to selection or future typing.",
                "",
                "── GRAPHS DASHBOARD ──",
                "• ← Menu — Return to main screen.",
                "• Month ◀ / ▶ — Navigate between months.",
                "• Stars Tab — Bar chart of earned stars per day.",
                "• Tasks Tab — Bar chart of task completion counts.",
                "• Packs Tab — Bar chart of fully completed task groups.",
                "• Trend Line — Performance trend drawn over the bars.",
                "• Monthly Summary Footer — Cumulative totals and daily averages.",
                "",
                "── QURAN AUDIO SCREEN ──",
                "• Surah Search Bar — Search any Surah by name (diacritic-insensitive).",
                "• Surah List — Scrollable; click to select for playback.",
                "• ▶ Play / ⏹ Stop — Control playback.",
                "• Seek Bar — Click, drag, or scroll to seek position.",
                "• Volume Slider — Click, drag, or scroll to adjust volume.",
                "",
                "── ADHKAR (DHIKR) SCREEN ──",
                "• Adhkar — Three dhikr session categories (Morning / Evening / Sleep). Tap to count, progress bar.",
                "",
                "── SETTINGS SCREEN ──",
                "• Language Dropdown — Switch between English and French.",
                "• Theme Dropdown — Choose from 10+ visual themes.",
                "• 📖 About — Opens this About page.",
                "• Save & Exit — Apply settings and return to main screen.",
                "• Cancel — Discard changes and return.",
            ]),
            ("🆚 What Makes It Special vs Other Apps?", [
                "Most task managers are cloud-first: your data lives on their servers, "
                "you need a subscription for advanced features, and privacy is secondary.",
                "",
                "Mission Ui is different:",
                "• 100% Offline — Your data never leaves your machine, ever.",
                "• No subscription — One download, yours forever.",
                "• Weighted star system — No other free app offers nuanced task scoring like this.",
                "• Local AI Commentary — Gemma 1B generates genuine reflections with zero network.",
                "• Styled PDF/PNG export — Your mission paper becomes a beautiful printable document.",
                "• Spiritual integration — Quran audio + text + Adhkar built in, not bolted on.",
                "• Full RTL Arabic support with correct text shaping.",
                "• Premium dark themes rivaling paid productivity apps.",
            ]),
            ("🔮 Planned Future Features", [
                "Mission Ui is actively developed. Planned additions include:",
                "",
                "• More Languages — Spanish, Turkish, Urdu, and more coming soon.",
                "• Advanced AI Parameters — Larger GGUF models, adjustable temperature and context "
                "window for professional-grade deep analysis.",
                "• Optional Encrypted Sync — Secure, opt-in sync; your data stays private.",
                "• Advanced Dashboards — Weekly, monthly, and yearly performance heatmaps.",
                "• System Reminders & Notifications — Scheduled alerts for your missions.",
                "• Enhanced Blueprint Editor — Pre-built templates for common routines.",
                "• Complete Quran Audio Library — All 114 Surahs with multiple reciters.",
                "• More Wellness & Productivity Tools — Pomodoro timer, habit tracker, and more.",
                "• Mobile Companion App — A lightweight companion for on-the-go tracking.",
            ]),
            ("☕ Support the Project", [
                "Mission Ui is free and open to everyone. If it helps your daily life, "
                "consider supporting development:",
                "",
                "→ https://ko-fi.com/yakomodev",
                "",
                "Every contribution helps keep the project alive and funds new features.",
                "Thank you for using Mission Ui. 🙏",
            ]),
        ]


# ──────────────────────────────────────────────────────────────────────────────
# About Screen class
# ──────────────────────────────────────────────────────────────────────────────

class AboutScreen(tk.Frame):
    """
    Full-featured About / Documentation page for Mission Ui.
    Accessible from Settings via the About button.
    """

    def __init__(self, parent):
        super().__init__(parent, bg=tm.BG_DARK)
        self.parent = parent
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build()

    def _build(self):
        # ── Header ────────────────────────────────────────────────────────────
        header = tk.Frame(self, bg=tm.BG_DARK)
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 5))

        back_btn = tk.Button(
            header, text=tm.tr("menu_back"), bg=tm.BG_CARD, fg=tm.TEXT_WHITE,
            relief="flat", activebackground=tm.ACCENT_PURPLE, activeforeground=tm.BG_DARK,
            font=("Helvetica", 10, "bold"), padx=12, pady=6,
            command=self.parent.show_settings_screen
        )
        back_btn.pack(side="left")
        back_btn.bind("<Enter>", lambda e=None: back_btn.config(bg=tm.ACCENT_PURPLE, fg=tm.BG_DARK))
        back_btn.bind("<Leave>", lambda e=None: back_btn.config(bg=tm.BG_CARD, fg=tm.TEXT_WHITE))

        title_lbl = tk.Label(
            header,
            text="📖  Mission Ui",
            bg=tm.BG_DARK, fg=tm.ACCENT_CYAN,
            font=("Helvetica", 16, "bold")
        )
        title_lbl.pack(side="left", padx=20)

        kofi_btn = tk.Button(
            header, text="☕  Ko-fi", bg=tm.BG_CARD, fg="#e0aaff",
            relief="flat", activebackground="#2d0a52", activeforeground="#ffffff",
            font=("Helvetica", 10, "bold"), padx=12, pady=6,
            command=lambda: webbrowser.open("https://ko-fi.com/yakomodev")
        )
        kofi_btn.pack(side="right")
        kofi_btn.bind("<Enter>", lambda e=None: kofi_btn.config(bg="#2d0a52", fg="#ffffff"))
        kofi_btn.bind("<Leave>", lambda e=None: kofi_btn.config(bg=tm.BG_CARD, fg="#e0aaff"))

        version_lbl = tk.Label(
            header, text="v1.0  •  Made with love by YakomoDev",
            bg=tm.BG_DARK, fg=tm.TEXT_MUTED, font=("Helvetica", 9, "italic")
        )
        version_lbl.pack(side="right", padx=15)

        # Divider line
        tk.Frame(self, bg=tm.BORDER_COLOR, height=1).grid(
            row=0, column=0, sticky="sew", padx=0, pady=(64, 0)
        )

        # ── Scrollable Content ────────────────────────────────────────────────
        content_wrapper = tk.Frame(self, bg=tm.BG_DARK)
        content_wrapper.grid(row=1, column=0, sticky="nsew")
        content_wrapper.grid_rowconfigure(0, weight=1)
        content_wrapper.grid_columnconfigure(0, weight=1)

        canvas = tk.Canvas(content_wrapper, bg=tm.BG_DARK, highlightthickness=0)
        scrollbar = ttk.Scrollbar(content_wrapper, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        inner = tk.Frame(canvas, bg=tm.BG_DARK)
        window_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(window_id, width=e.width))

        def _scroll(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _scroll)
        canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))

        # ── Render Sections ───────────────────────────────────────────────────
        sections = _build_sections()
        is_rtl = tm._current_language == "Arabic"
        justify = "right" if is_rtl else "left"
        anchor_side = "e" if is_rtl else "w"

        for sec_title, paragraphs in sections:
            self._render_section(inner, sec_title, paragraphs, justify, anchor_side)

        tk.Frame(inner, bg=tm.BG_DARK, height=50).pack()

    def _render_section(self, parent, title, paragraphs, justify, anchor_side):
        # Section card header
        section_frame = tk.Frame(
            parent, bg=tm.BG_CARD,
            highlightbackground=tm.BORDER_COLOR, highlightthickness=1
        )
        section_frame.pack(fill="x", padx=30, pady=(18, 0))

        tk.Label(
            section_frame, text=title,
            bg=tm.BG_CARD, fg=tm.ACCENT_CYAN,
            font=("Helvetica", 12, "bold"),
            anchor=anchor_side, justify=justify,
            padx=15, pady=10
        ).pack(fill="x")

        # Body
        body = tk.Frame(parent, bg=tm.BG_DARK)
        body.pack(fill="x", padx=30, pady=(2, 0))

        for line in paragraphs:
            if not line:
                tk.Frame(body, bg=tm.BG_DARK, height=5).pack()
                continue

            is_separator = line.startswith("──")
            is_link = line.startswith("→ https://")

            fg = (tm.TEXT_MUTED if is_separator else
                  tm.ACCENT_CYAN if is_link else
                  tm.TEXT_WHITE)
            font = (("Helvetica", 10, "bold") if is_separator else
                    ("Helvetica", 10, "underline") if is_link else
                    ("Helvetica", 10))

            lbl = tk.Label(
                body, text=line,
                bg=tm.BG_DARK, fg=fg, font=font,
                anchor=anchor_side, justify=justify,
                padx=10, pady=2
            )
            lbl.pack(fill="x", padx=5)

            if is_link:
                url = line.replace("→ ", "").strip()
                lbl.config(cursor="hand2")
                lbl.bind("<Button-1>", lambda e, u=url: webbrowser.open(u))

        tk.Frame(parent, bg=tm.BORDER_COLOR, height=1).pack(fill="x", padx=30, pady=(4, 0))
