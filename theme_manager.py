# Prepared with love by YakomoDev - https://ko-fi.com/yakomodev
"""
theme_manager.py — Centralized Theme and Language Manager for Mission Ui.
Prevents circular imports and manages settings persistence.
"""

import os
import json
import re

APP_DIR = os.path.dirname(os.path.abspath(__file__))
PREFS_PATH = os.path.join(APP_DIR, "data", "prefs.json")

# ── Themes Configuration ──────────────────────────────────────────────────────
THEMES = {
    "Neon Dark": {
        "BG_DARK": "#0a0a0c",
        "BG_CARD": "#141417",
        "BG_CARD_HEADER": "#1c1c21",
        "BORDER_COLOR": "#27272a",
        "TEXT_WHITE": "#f4f4f5",
        "TEXT_MUTED": "#a1a1aa",
        "ACCENT_PURPLE": "#a855f7",
        "ACCENT_CYAN": "#06b6d4",
        "SUCCESS_GREEN": "#10b981",
        "GLOW_COLOR": "#d8b4fe",
        "WARN_ORANGE": "#f97316",
        "ERR_RED": "#ef4444"
    },
    "Cyberpunk": {
        "BG_DARK": "#0f0f13",
        "BG_CARD": "#181822",
        "BG_CARD_HEADER": "#1f2130",
        "BORDER_COLOR": "#333752",
        "TEXT_WHITE": "#ffffff",
        "TEXT_MUTED": "#8b8fa8",
        "ACCENT_PURPLE": "#ff007f",
        "ACCENT_CYAN": "#00f0ff",
        "SUCCESS_GREEN": "#00ff66",
        "GLOW_COLOR": "#ff007f",
        "WARN_ORANGE": "#ffaa00",
        "ERR_RED": "#ff3333"
    },
    "Forest Emerald": {
        "BG_DARK": "#0b120f",
        "BG_CARD": "#122018",
        "BG_CARD_HEADER": "#182c20",
        "BORDER_COLOR": "#1f3a2b",
        "TEXT_WHITE": "#f0fdf4",
        "TEXT_MUTED": "#6ee7b7",
        "ACCENT_PURPLE": "#10b981",
        "ACCENT_CYAN": "#f59e0b",
        "SUCCESS_GREEN": "#10b981",
        "GLOW_COLOR": "#34d399",
        "WARN_ORANGE": "#d97706",
        "ERR_RED": "#dc2626"
    },
    "Rose Gold": {
        "BG_DARK": "#120d14",
        "BG_CARD": "#211625",
        "BG_CARD_HEADER": "#2c1c32",
        "BORDER_COLOR": "#3c2844",
        "TEXT_WHITE": "#fff1f2",
        "TEXT_MUTED": "#fda4af",
        "ACCENT_PURPLE": "#f43f5e",
        "ACCENT_CYAN": "#fb7185",
        "SUCCESS_GREEN": "#10b981",
        "GLOW_COLOR": "#ffe4e6",
        "WARN_ORANGE": "#f43f5e",
        "ERR_RED": "#e11d48"
    },
    "Midnight Blue": {
        "BG_DARK": "#0b0f19",
        "BG_CARD": "#111827",
        "BG_CARD_HEADER": "#1f2937",
        "BORDER_COLOR": "#374151",
        "TEXT_WHITE": "#f9fafb",
        "TEXT_MUTED": "#9ca3af",
        "ACCENT_PURPLE": "#3b82f6",
        "ACCENT_CYAN": "#60a5fa",
        "SUCCESS_GREEN": "#10b981",
        "GLOW_COLOR": "#93c5fd",
        "WARN_ORANGE": "#f59e0b",
        "ERR_RED": "#ef4444"
    },
    "Nord Ice": {
        "BG_DARK": "#0f172a",
        "BG_CARD": "#1e293b",
        "BG_CARD_HEADER": "#334155",
        "BORDER_COLOR": "#475569",
        "TEXT_WHITE": "#f8fafc",
        "TEXT_MUTED": "#94a3b8",
        "ACCENT_PURPLE": "#38bdf8",
        "ACCENT_CYAN": "#a5f3fc",
        "SUCCESS_GREEN": "#10b981",
        "GLOW_COLOR": "#bae6fd",
        "WARN_ORANGE": "#f97316",
        "ERR_RED": "#ef4444"
    }
}

# ── Dynamic Colors State ──────────────────────────────────────────────────────
_current_theme = "Neon Dark"
_current_language = "English"

# Load theme values into module globals and try updating app.py variables
def apply_theme_colors(theme_name):
    global _current_theme
    if theme_name in THEMES:
        _current_theme = theme_name
        colors = THEMES[theme_name]
        globals().update(colors)
        
        # Propagate to app if imported
        try:
            import app
            for k, v in colors.items():
                setattr(app, k, v)
        except Exception:
            pass
            
        # Propagate to graphs_screen if imported
        try:
            import graphs_screen
            for k, v in colors.items():
                setattr(graphs_screen, k, v)
        except Exception:
            pass

        # Propagate to __main__ (the running entry point, i.e., app.py)
        try:
            import sys
            if "__main__" in sys.modules:
                main_mod = sys.modules["__main__"]
                for k, v in colors.items():
                    if hasattr(main_mod, k):
                        setattr(main_mod, k, v)
        except Exception:
            pass

# Default initialization
apply_theme_colors(_current_theme)


# ── Translation System ────────────────────────────────────────────────────────
# English -> key, French -> value, Arabic -> value
# We shape Arabic using arabic_reshaper & python_bidi to ensure proper connections and RTL.
LOCALIZATION = {
    "English": {
        "title": "MISSION UI",
        "subtitle": "Elite Mission Tracker",
        "create_list": "Create Today's Task List",
        "edit_list": "Edit & Continue Today's List",
        "calendar_dashboard": "Calendar Dashboard",
        "graphs_dashboard": "Graphs Dashboard",
        "tools": "🔧 Tools",
        "settings": "⚙️ Settings",
        "made_by": "Made with love by YakomoDev",
        "support_project": "☕ Support the Project",
        "tools_title": "Tools & Utilities:",
        "inspect_starred": "⭐ Inspect Starred Packs",
        "read_quran": "📖 Read Quran",
        "listen_quran": "🎧 Listen to Quran",
        "addkar": "📿 Addkar",
        "back": "← Back",
        "menu_back": "← Menu",
        "today_lbl": "Today: ",
        "save_exit": "Save & Exit",
        "cancel": "Cancel",
        "about_btn": "📖  About",
        "choose_blueprint": "Choose a day template or start blank:",
        "close": "Close",
        "add_group": "Add Task Group",
        "add_starred": "Add Starred Pack",
        "delete_group": "Delete Group",
        "edit_pack": "Edit Pack",
        "star_pack": "Star Pack",
        "blueprint": "Blueprint:",
        "main_missions": "MAIN MISSIONS",
        "side_missions": "SIDE MISSIONS",
        "done": "Done",
        "weight": "Weight:",
        "stars": "Stars:",
        "page": "Page",
        "days_lbl": "Days: ",
        "remove_day": "- Day",
        "add_day": "+ Day",
        "tasks_completed": "Tasks Completed:",
        "total_stars": "Total Stars:",
        "small_advice": "Small Advice",
        "deep_advice": "Deep Advice",
        "generating": "Generating...",
        "ai_updating": "Comment updated!",
        "save_graph_png": "💾 Download as PNG",
        "save_graph_pdf": "📄 Download as PDF",
        "avg_t_done": "Avg Total Done ⭐",
        "avg_m_done": "Avg Main Done ⭐",
        "avg_s_done": "Avg Side Done ⭐",
        "avg_t_missed": "Avg Total Missed 💔",
        "avg_m_missed": "Avg Main Missed 💔",
        "avg_s_missed": "Avg Side Missed 💔",
        "avg_t_done_tasks": "Avg Total Done Tasks",
        "avg_m_done_tasks": "Avg Main Done Tasks",
        "avg_s_done_tasks": "Avg Side Done Tasks",
        "avg_t_undone_tasks": "Avg Total Undone Tasks",
        "avg_m_undone_tasks": "Avg Main Undone Tasks",
        "avg_s_undone_tasks": "Avg Side Undone Tasks",
        "avg_t_ratio": "Avg Total Ratio %",
        "avg_m_ratio": "Avg Main Ratio %",
        "avg_s_ratio": "Avg Side Ratio %",
        "avg_t_ratio_packs": "Avg Total Packs Ratio %",
        "avg_m_ratio_packs": "Avg Main Packs Ratio %",
        "avg_s_ratio_packs": "Avg Side Packs Ratio %",
        "avg_t_done_packs": "Avg Total Done Packs",
        "avg_m_done_packs": "Avg Main Done Packs",
        "avg_s_done_packs": "Avg Side Done Packs",
        "avg_t_undone_packs": "Avg Total Undone Packs",
        "avg_m_undone_packs": "Avg Main Undone Packs",
        "avg_s_undone_packs": "Avg Side Undone Packs",
        "monthly_averages": "MONTHLY AVERAGES (logged days only)",
        "month_total": "Month Total",
        "monthly_ai_summary": "🤖 MONTHLY AI SUMMARY",
        "generate": "Generate",
        "generating": "⏳ Generating...",
        "done_status": "✓ Done!",
        "comment_updated": "Comment updated!",
        "advice_updated": "Advice updated!",
        "advice_loaded": "Advice loaded!",
        "running_local_ai": "Running local AI...",
        "generating_advice": "Generating advice...",
        "chart_type": "CHART TYPE",
        "scope": "SCOPE",
        "mode": "MODE",
        "chart_line": "📈 Line",
        "chart_bar": "📊 Bar / Histogram",
        "chart_pie": "🥧 Pie Chart",
        "scope_total": "Total (Main + Side)",
        "scope_main": "Main tasks only",
        "scope_side": "Side tasks only",
        "mode_done": "⭐ Stars Earned",
        "mode_missed": "💔 Stars Missed",
        "mode_done_tasks": "✅ Done Tasks",
        "mode_undone_tasks": "❌ Undone Tasks",
        "mode_ratio": "📐 Ratio %",
        "mode_done_packs": "🎒 Packs Completed",
        "mode_undone_packs": "🎒 Packs Undone",
        "mode_packs_ratio": "📐 Packs Ratio %",
        "axis_days": "Day of Month",
        "axis_ratio": "Completion Ratio (%)",
        "axis_tasks": "Number of Tasks",
        "axis_stars": "Stars count",
        "axis_packs": "Packs count",
        "no_logged_days": "No logged days for this month",
        "no_data_month": "No data for this month",
        "pie_done": "Done ⭐",
        "pie_missed": "Missed",
        "pie_done_tasks": "Done Tasks",
        "pie_undone_tasks": "Undone Tasks",
        "pie_done_packs": "Completed Packs",
        "pie_undone_packs": "Undone Packs",
        "play_mode": "Play Mode",
        "mode_single": "Play Once",
        "mode_loop": "Repeat",
        "mode_next": "Auto Next",
        "mode_shuffle": "Shuffle",
        "loading_model": "Loading model...",
        "error_model_not_found": "Error: Gemma 3 1B.gguf not found",
        "error_llama_not_installed": "Error: llama-cpp-python not installed",
        "add_offset": "Add Day Offset",
        "remove_offset": "Remove Day Offset",
        "reset_offset": "Reset Offset",
        "clear_day_logs": "Clear day logs",
        "delete_day": "Delete day",
        "no_task_logs": "No task logs for this day.",
        "download_paper": "📄 Download Paper",
        "view_memo": "📓 View Memo",
        "daily_diary": "Daily Diary",
        "no_memo_warning": "No memo recorded for this day. Start typing to create one.",
        "diary_loaded": "Diary loaded successfully",
        "diary_saved": "Diary saved successfully",
        "language": "Language",
        "themes": "Themes",
        "select_lang": "Select Language:",
        "select_theme": "Select Theme:",
        "settings_title": "Settings Screen",
        "ai_language_prompt": "You must write your response strictly in English.",
        "day_details_preview": " Day Details Preview ",
        "hover_day_preview": "Hover over any calendar day to preview logged daily task sheets.\n\nClick a day to load it or start tracking.",
        "empty": "Empty",
        "today_badge": "TODAY",
        "no_task_logs_click": "No task logs for this day.\n\nClick to start tracking!",
        "stars_earned": "Stars Earned:",
        "report": "Report:",
        "earned": "Earned:",
        "ai_daily_insight": "🤖 AI DAILY INSIGHT",
        "coach_small_advice": "💡 COACH SMALL ADVICE",
        "coach_deep_advice": "🧠 COACH DEEP ADVICE",
        "save_daily_paper": "Save Daily Paper as",
        "export_success": "Export Success",
        "export_success_msg": "Successfully exported daily paper to:\n",
        "export_error": "Export Error",
        "export_error_msg": "Failed to export daily paper:\n",
        "error": "Error",
        "initialize": "Initialize",
        "start_tracking_for": "Start tracking missions for:",
        "start_blank": "Start Blank (New)",
        "choose_format": "Choose Format",
        "export_sheet_for": "Export sheet for:",
        "png_image": "PNG Image",
        "pdf_document": "PDF Document",
        "main_tag": "Main",
        "side_tag": "Side",
        "stars_label": "stars",
        "add_task_item": "➕ Add Task Item",
        "set_percentage_weights": "📊 Set Percentage Weights",
        "rename_group": "✏️ Rename Group Title",
        "change_group_stars": "⭐ Change Stars for Group",
        "save_starred_pack": "⭐ Save as Starred Pack",
        "rename_item": "✏️ Rename Item",
        "delete_item": "❌ Delete Item",
        "add_task_item_title": "Add Task Item",
        "enter_item_desc": "Enter Item Description:",
        "create_new_blank_group": "Create New Blank Group",
        "load_starred_pack": "Load Starred Pack",
        "pack_saved_starred": "saved as Starred!",
        "quran_recitations": "🎧 Quran Recitations - Reciter Yasser Al-Dossary",
        "search_surah": "Search Surah:",
        "search_helper_text": "Search by name in Arabic, English or Surah number (e.g. 18, Al-Kahf, Kahf)",
        "select_surah_to_listen": "Select a Surah to start listening",
        "play": "▶ Play",
        "stop": "⏹ Stop",
        "volume": "Volume: 🔊",
        "last_pos": "Last",
        "file_missing": "File Missing",
        "daily_azkar_title": "Daily Azkar",
        "select_azkar_category": "Select Azkar Category",
        "morning_tag": "Morning",
        "evening_tag": "Evening",
        "sleep_tag": "Sleep",
        "completed": "Completed",
        "mashaallah": "Masha'Allah! 🎉",
        "azkar_completed_title": "You have completed your Azkar!",
        "azkar_completed_subtitle": "May Allah reward you bountifully.",
        "ameen": "Ameen / آمين",
        "personal_ai_advice": "Personal AI Advice",
        "load_starred_pack_title": "Load Starred Tasks Pack",
        "starred_packs_title": "⭐ Starred Tasks Packs",
        "no_starred_packs": "No starred packs saved yet.\n\nRight-click any task group and select 'Save as Starred Pack' to save.",
        "manage_starred_packs": "Manage Starred Packs",
        "starred_packs_manager": "⭐ Starred Packs Manager",
        "close_manager": "Close Manager",
        "tracker_target_date": "TRACKER TARGET DATE",
        "tasks_done": "Tasks Done:",
        "packs_done": "Packs Completed:",
        "grand_total_overview": "GRAND TOTAL OVERVIEW",
        "total_tasks": "Total Tasks:",
        "total_packs": "Total Packs:",
        "total": "Total",
        "note": "Note",
        "memo": "memo",
        "earned_stars_ratio": "Earned Stars Ratio:",
        "tasks_completion_ratio": "Tasks Completion Ratio:",
        "legend_base_progress": "Base Progress",
        "legend_peak_level": "Peak Level",
        "local_ai_commentary": "🤖 LOCAL AI COMMENTARY",
        "generate_feedback": "🤖 Generate Feedback",
        "copy_prompt": "📋 Copy Prompt",
        "prompt_copied": "✅ Prompt Copied!",
        "enter_group_title": "Enter Group Title",
        "enter_new_name": "Enter new name:",
        "enter_new_group_title": "Enter new group title:",
        "enter_new_star_count": "Enter new star count:",
        "summary": "SUMMARY",
        "advice_exists": "Advice Exists",
        "advice_exists_body": "Productivity {advice_type} advice already exists for this day.\n\nClick 'Yes' to view the existing advice.\nClick 'No' to generate new advice (this will overwrite the old one).",
        "small_tag": "small",
        "deep_tag": "deep",
        "small_advice_btn": "💡 Small Advice",
        "deep_advice_btn": "🧠 Deep Advice",
        "edit_starred_pack": "Edit Starred Tasks Pack",
        "pack_title_label": "Pack Title:",
        "total_stars_alloc_label": "Total Stars Allocation:",
        "task_items_in_pack_label": "Task Items in Pack",
        "weight_label": "Weight:",
        "save_changes": "Save Changes",
        "new_task_placeholder": "New Task",
        "pack_title_empty": "Pack Title cannot be empty!",
        "stars_alloc_numeric": "Stars Allocation must be a numeric value!",
        "failed_save_changes": "Failed to save changes: ",
        "no_starred_packs_desc": "No starred packs saved yet.\n\nYou can star a task group inside a day tracker\nto save it as a template.",
        "edit_label": "Edit",
        "empty_pack_label": "Empty pack",
        "delete_starred_pack_title": "Delete Starred Pack?",
        "delete_starred_pack_confirm": "Are you sure you want to permanently delete '{title}'?",
        "quran_reader_title": "Quran Reader",
        "no_quran_pages_error": "No page images found in Quran pages directory.",
        "quran_page_of": "Page {current} of {total}",
        "quran_pages_left": "{left} pages left",
        "quran_completions": "🏆 Quran Fully Read completions: {count} times",
        "quran_completion_success": "Masha'Allah! You have completed reading the entire Quran! Your total completions count has been incremented.",
        "now_playing_prefix": "Now Playing: ",
        "pause": "⏸ Pause",
        "resume": "▶ Resume",
        "audio_error": "Audio Error",
        "could_not_play_audio": "Could not play audio file: ",
        "audio_file_not_found": "Audio file not found: ",
        "back_to_home": "Back to Home",
        "no_main_tasks": "No main tasks created yet.\n\nClick '+' above to add your first main task!",
        "no_side_tasks": "No side tasks created yet.\n\nClick '+' above to add your first side task!",
        "confirm": "Confirm",
        "input_cannot_be_empty": "Input cannot be empty.",
        "enter_valid_integer": "Please enter a valid non-negative integer.",
        "acknowledge_close": "Acknowledge & Close",
        "ai_coach_advice_title": "AI Coach - {type} Advice",
        "save": "Save",
        "equal_split": "Equal Split",
        "sum_label": "Sum: ",
        "set_pct_weights": "Set Percentage Weights (Total: 100%)",
        "invalid_pct_val": "Invalid percentage value for '{name}'.",
        "normalize_title": "Normalize?",
        "normalize_body": "Percentages sum to {total:.1f}%. Would you like to normalize them to sum to 100.0%?",
        "no_azkar_found": "No Azkar found for category: {category}",
        "reset_zikr_title": "Reset Zikr",
        "reset_zikr_confirm": "Do you want to reset this Zikr count?",
        "limit_reached": "Limit Reached",
        "cannot_remove_days": "Cannot remove any more days — month must have at least 1 day.",
        "cannot_add_days": "Cannot add more than 7 extra days to a month.",
        "confirm_cal_adjustment": "Confirm Calendar Adjustment",
        "remove_day_prompt": "Remove day {day} from {month} {year}?\n\nExisting task data on that day will be hidden but not deleted.",
        "add_day_prompt": "Add an extra day ({day}) to {month} {year}?",
        "failed_save_starred_pack": "Failed to save tasks pack: ",
        "pack_saved_starred": "Pack '{title}' saved as Starred!",
        "delete_item_title": "Delete Item",
        "delete_item_prompt": "Are you sure you want to delete the item '{name}'?",
        "delete_group_title": "Delete Group",
        "delete_group_prompt": "Are you sure you want to delete the group '{title}' and all its tasks?",
        "graph_exported_to": "Graph exported to:\n{filename}",
        "failed_export_graph": "Failed to export graph:\n{e}",
        "no_data": "No Data",
        "no_logged_days": "No logged days found for this month. Log some days first!"
    },
    "French": {
        "title": "MISSION UI",
        "subtitle": "Suivi de mission d'élite",
        "create_list": "Créer la liste des tâches",
        "edit_list": "Modifier la liste du jour",
        "calendar_dashboard": "Calendrier de bord",
        "graphs_dashboard": "Graphiques de bord",
        "tools": "🔧 Outils",
        "settings": "⚙️ Paramètres",
        "made_by": "Fait avec amour par YakomoDev",
        "support_project": "☕ Soutenir le projet",
        "tools_title": "Outils & Utilitaires:",
        "inspect_starred": "⭐ Inspecter les Packs Favoris",
        "read_quran": "📖 Lire le Coran",
        "listen_quran": "🎧 Écouter le Coran",
        "addkar": "📿 Adhkar",
        "back": "← Retour",
        "menu_back": "← Menu",
        "today_lbl": "Aujourd'hui: ",
        "save_exit": "Enregistrer & Quitter",
        "cancel": "Annuler",
        "about_btn": "📖  À propos",
        "choose_blueprint": "Choisissez un modèle ou démarrez vide :",
        "close": "Fermer",
        "add_group": "Ajouter Groupe",
        "add_starred": "Ajouter Pack Favori",
        "delete_group": "Supprimer Groupe",
        "edit_pack": "Modifier Pack",
        "star_pack": "Ajouter aux Favoris",
        "blueprint": "Modèle:",
        "main_missions": "MISSIONS PRINCIPALES",
        "side_missions": "MISSIONS SECONDAIRES",
        "done": "Fait",
        "weight": "Poids:",
        "stars": "Étoiles:",
        "days_lbl": "Jours : ",
        "remove_day": "- Jour",
        "add_day": "+ Jour",
        "tasks_completed": "Tâches Complétées:",
        "total_stars": "Total Étoiles:",
        "small_advice": "Conseil Rapide",
        "deep_advice": "Conseil Profond",
        "generating": "Génération...",
        "ai_updating": "Commentaire mis à jour!",
        "save_graph_png": "💾 Télécharger en PNG",
        "save_graph_pdf": "📄 Télécharger en PDF",
        "avg_t_done": "Moy. Total Fait ⭐",
        "avg_m_done": "Moy. Principal Fait ⭐",
        "avg_s_done": "Moy. Secondaire Fait ⭐",
        "avg_t_missed": "Moy. Total Manqué 💔",
        "avg_m_missed": "Moy. Principal Manqué 💔",
        "avg_s_missed": "Moy. Secondaire Manqué 💔",
        "avg_t_done_tasks": "Moy. Tâches Faites (Total)",
        "avg_m_done_tasks": "Moy. Tâches Faites (Principal)",
        "avg_s_done_tasks": "Moy. Tâches Faites (Secondaire)",
        "avg_t_undone_tasks": "Moy. Tâches Non Faites (Total)",
        "avg_m_undone_tasks": "Moy. Tâches Non Faites (Principal)",
        "avg_s_undone_tasks": "Moy. Tâches Non Faites (Secondaire)",
        "avg_t_ratio": "Moy. Ratio Total %",
        "avg_m_ratio": "Moy. Ratio Principal %",
        "avg_s_ratio": "Moy. Ratio Secondaire %",
        "avg_t_ratio_packs": "Moy. Ratio Total Packs %",
        "avg_m_ratio_packs": "Moy. Ratio Packs Principaux %",
        "avg_s_ratio_packs": "Moy. Ratio Packs Secondaires %",
        "avg_t_done_packs": "Moy. Total Packs Complétés",
        "avg_m_done_packs": "Moy. Packs Principaux Complétés",
        "avg_s_done_packs": "Moy. Packs Secondaires Complétés",
        "avg_t_undone_packs": "Moy. Total Packs Non Complétés",
        "avg_m_undone_packs": "Moy. Packs Principaux Non Complétés",
        "avg_s_undone_packs": "Moy. Packs Secondaires Non Complétés",
        "monthly_averages": "MOYENNES MENSUELLES (jours actifs)",
        "month_total": "Total du Mois",
        "monthly_ai_summary": "🤖 SYNTÈSE AI MENSUELLE",
        "generate": "Générer",
        "generating": "⏳ Génération...",
        "done_status": "✓ Fait!",
        "comment_updated": "Commentaire mis à jour!",
        "advice_updated": "Conseil mis à jour!",
        "advice_loaded": "Conseil chargé!",
        "running_local_ai": "IA locale en cours...",
        "generating_advice": "Génération du conseil...",
        "chart_type": "TYPE DE GRAPHIQUE",
        "scope": "PORTÉE",
        "mode": "MODE",
        "chart_line": "📈 Courbe",
        "chart_bar": "📊 Histogramme",
        "chart_pie": "🥧 Diagramme Circulaire",
        "scope_total": "Total (Principal + Secondaire)",
        "scope_main": "Missions principales",
        "scope_side": "Missions secondaires",
        "mode_done": "⭐ Étoiles Gagnées",
        "mode_missed": "💔 Étoiles Perdues",
        "mode_done_tasks": "✅ Tâches Faites",
        "mode_undone_tasks": "❌ Tâches Non Faites",
        "mode_ratio": "📐 Ratio %",
        "mode_done_packs": "🎒 Packs Complétés",
        "mode_undone_packs": "🎒 Packs Non Complétés",
        "mode_packs_ratio": "📐 Ratio Packs %",
        "axis_days": "Jour du Mois",
        "axis_ratio": "Ratio de Complétion (%)",
        "axis_tasks": "Nombre de Tâches",
        "axis_stars": "Étoiles",
        "axis_packs": "Nombre de Packs",
        "no_logged_days": "Aucune donnée ce mois-ci",
        "no_data_month": "Pas de données pour ce mois",
        "pie_done": "Réussies ⭐",
        "pie_missed": "Ratées",
        "pie_done_tasks": "Tâches Faites",
        "pie_undone_tasks": "Tâches Non Faites",
        "pie_done_packs": "Packs Complétés",
        "pie_undone_packs": "Packs Non Complétés",
        "play_mode": "Mode de Lecture",
        "mode_single": "Lecture Unique",
        "mode_loop": "Répéter",
        "mode_next": "Suivant Auto",
        "mode_shuffle": "Aléatoire",
        "loading_model": "Chargement du modèle...",
        "error_model_not_found": "Erreur : Gemma 3 1B.gguf introuvable",
        "error_llama_not_installed": "Erreur : llama-cpp-python non installé",
        "add_offset": "Ajouter décalage de jour",
        "remove_offset": "Retirer décalage de jour",
        "reset_offset": "Réinitialiser décalage",
        "clear_day_logs": "Effacer l'historique",
        "delete_day": "Supprimer le jour",
        "no_task_logs": "Pas de tâches pour ce jour.",
        "download_paper": "📄 Exporter la fiche",
        "view_memo": "📓 Voir le Mémo",
        "daily_diary": "Journal Quotidien",
        "no_memo_warning": "Aucun mémo enregistré pour ce jour. Écrivez ci-dessous pour le créer.",
        "diary_loaded": "Journal chargé avec succès",
        "diary_saved": "Journal enregistré avec succès",
        "language": "Langue",
        "themes": "Thèmes",
        "select_lang": "Choisir la Langue:",
        "select_theme": "Choisir le Thème:",
        "settings_title": "Écran des Paramètres",
        "ai_language_prompt": "Tu dois obligatoirement rédiger ta réponse en français.",
        "day_details_preview": " Aperçu des détails du jour ",
        "hover_day_preview": "Survolez un jour pour prévisualiser les fiches.\n\nCliquez pour charger ou commencer le suivi.",
        "empty": "Vide",
        "today_badge": "AUJOURD'HUI",
        "no_task_logs_click": "Pas d'historique pour ce jour.\n\nCliquez pour commencer le suivi !",
        "stars_earned": "Étoiles Gagnées:",
        "report": "Rapport :",
        "earned": "Gagné :",
        "ai_daily_insight": "🤖 ANALYSE QUOTIDIENNE IA",
        "coach_small_advice": "💡 CONSEIL RAPIDE DU COACH",
        "coach_deep_advice": "🧠 ANALYSE DE FOND DU COACH",
        "save_daily_paper": "Enregistrer la fiche quotidienne en",
        "export_success": "Export Réussi",
        "export_success_msg": "Fiche quotidienne exportée avec succès vers :\n",
        "export_error": "Erreur d'Export",
        "export_error_msg": "Échec de l'exportation de la fiche quotidienne :\n",
        "error": "Erreur",
        "initialize": "Initialiser",
        "start_tracking_for": "Commencer le suivi des missions pour :",
        "start_blank": "Commencer à vide (Nouveau)",
        "choose_format": "Choisir le Format",
        "export_sheet_for": "Exporter la fiche pour :",
        "png_image": "Image PNG",
        "pdf_document": "Document PDF",
        "main_tag": "Principal",
        "side_tag": "Secondaire",
        "stars_label": "étoiles",
        "add_task_item": "➕ Ajouter une Tâche",
        "set_percentage_weights": "📊 Ajuster les Poids %",
        "rename_group": "✏️ Renommer le Groupe",
        "change_group_stars": "⭐ Modifier les Étoiles",
        "save_starred_pack": "⭐ Enregistrer en favori",
        "rename_item": "✏️ Renommer la Tâche",
        "delete_item": "❌ Supprimer la Tâche",
        "add_task_item_title": "Ajouter une Tâche",
        "enter_item_desc": "Entrez la description de la tâche :",
        "create_new_blank_group": "Créer un Nouveau Groupe Vide",
        "load_starred_pack": "Charger un Pack Favori",
        "pack_saved_starred": "enregistré en favori !",
        "quran_recitations": "🎧 Récitations du Coran - Yasser Al-Dossary",
        "search_surah": "Rechercher une Sourate :",
        "search_helper_text": "Rechercher par nom en arabe, anglais ou numéro (ex: 18)",
        "select_surah_to_listen": "Sélectionnez une sourate pour commencer l'écoute",
        "play": "▶ Lire",
        "stop": "⏹ Arrêter",
        "volume": "Volume : 🔊",
        "last_pos": "Dernier",
        "file_missing": "Fichier Manquant",
        "daily_azkar_title": "Adhkar Quotidiens",
        "select_azkar_category": "Sélectionnez une Catégorie d'Adhkar",
        "morning_tag": "Matin",
        "evening_tag": "Soir",
        "sleep_tag": "Sommeil",
        "completed": "Complété",
        "mashaallah": "Masha'Allah! 🎉",
        "azkar_completed_title": "Vous avez terminé vos Adhkar !",
        "azkar_completed_subtitle": "Qu'Allah accepte vos bonnes actions.",
        "ameen": "Ameen / آمين",
        "personal_ai_advice": "Conseil Personnel de l'IA",
        "load_starred_pack_title": "Charger un Pack de Tâches Favori",
        "starred_packs_title": "⭐ Packs de Tâches Favoris",
        "no_starred_packs": "Aucun pack favori enregistré.\n\nFaites un clic droit sur un groupe et choisissez 'Enregistrer en favori'.",
        "manage_starred_packs": "Gérer les Packs Favoris",
        "starred_packs_manager": "⭐ Gestionnaire des Packs Favoris",
        "close_manager": "Fermer",
        "tracker_target_date": "DATE CIBLE DU SUIVI",
        "tasks_done": "Tâches Faites :",
        "packs_done": "Packs Complétés :",
        "grand_total_overview": "APERCU GENERAL TOTAL",
        "total_tasks": "Tâches Totales :",
        "total_packs": "Packs Totaux :",
        "total": "Total",
        "note": "Note",
        "memo": "mémo",
        "earned_stars_ratio": "Ratio des Étoiles Gagnées :",
        "tasks_completion_ratio": "Ratio de Complétion des Tâches :",
        "legend_base_progress": "Progrès de base",
        "legend_peak_level": "Niveau pic",
        "local_ai_commentary": "🤖 ANALYSE IA LOCALE",
        "generate_feedback": "🤖 Générer l'Analyse",
        "copy_prompt": "📋 Copier l'Instruction",
        "prompt_copied": "✅ Instruction copiée !",
        "enter_group_title": "Entrez le titre du groupe",
        "enter_new_name": "Entrez le nouveau nom :",
        "enter_new_group_title": "Entrez le nouveau titre du groupe :",
        "enter_new_star_count": "Entrez le nouveau nombre d'étoiles :",
        "summary": "RÉSUMÉ",
        "advice_exists": "L'avis existe déjà",
        "advice_exists_body": "Un avis de productivité ({advice_type}) existe déjà pour cette journée.\n\nCliquez sur 'Oui' pour afficher l'avis existant.\nCliquez sur 'Non' pour générer un nouvel avis (cela écrasera l'ancien).",
        "small_tag": "court",
        "deep_tag": "profond",
        "small_advice_btn": "💡 Conseil Rapide",
        "deep_advice_btn": "🧠 Conseil Profond",
        "edit_starred_pack": "Modifier le Pack Favori",
        "pack_title_label": "Titre du Pack :",
        "total_stars_alloc_label": "Allocation Totale des Étoiles :",
        "task_items_in_pack_label": "Tâches dans le Pack",
        "weight_label": "Poids :",
        "save_changes": "Enregistrer les Modifications",
        "new_task_placeholder": "Nouvelle Tâche",
        "pack_title_empty": "Le titre du pack ne peut pas être vide !",
        "stars_alloc_numeric": "L'allocation d'étoiles doit être une valeur numérique !",
        "failed_save_changes": "Échec de l'enregistrement des modifications : ",
        "no_starred_packs_desc": "Aucun pack favori enregistré pour le moment.\n\nVous pouvez marquer d'une étoile un groupe de tâches dans le suivi quotidien pour le sauvegarder comme modèle.",
        "edit_label": "Modifier",
        "empty_pack_label": "Pack vide",
        "delete_starred_pack_title": "Supprimer le Pack Favori ?",
        "delete_starred_pack_confirm": "Êtes-vous sûr de vouloir supprimer définitivement '{title}' ?",
        "quran_reader_title": "Lecteur du Coran",
        "no_quran_pages_error": "Aucune image de page trouvée dans le répertoire du Coran.",
        "quran_page_of": "Page {current} sur {total}",
        "quran_pages_left": "{left} pages restantes",
        "quran_completions": "🏆 Lectures complètes du Coran : {count} fois",
        "quran_completion_success": "Masha'Allah ! Vous avez terminé la lecture complète du Coran ! Votre compteur de lectures complètes a été incrémenté.",
        "now_playing_prefix": "En Cours de Lecture : ",
        "pause": "⏸ Pause",
        "resume": "▶ Reprendre",
        "audio_error": "Erreur Audio",
        "could_not_play_audio": "Impossible de lire le fichier audio : ",
        "audio_file_not_found": "Fichier audio introuvable : ",
        "back_to_home": "Retour à l'accueil",
        "no_main_tasks": "Aucune tâche principale créée pour le moment.\n\nCliquez sur '+' ci-dessus pour ajouter votre première tâche principale !",
        "no_side_tasks": "Aucune tâche secondaire créée pour le moment.\n\nCliquez sur '+' ci-dessus pour ajouter votre première tâche secondaire !",
        "confirm": "Confirmer",
        "input_cannot_be_empty": "La saisie ne peut pas être vide.",
        "enter_valid_integer": "Veuillez saisir un entier non négatif valide.",
        "acknowledge_close": "Prendre note & Fermer",
        "ai_coach_advice_title": "Coach IA - Conseil {type}",
        "save": "Enregistrer",
        "equal_split": "Répartition Égale",
        "sum_label": "Somme : ",
        "set_pct_weights": "Définir les Poids en Pourcentage (Total : 100%)",
        "invalid_pct_val": "Valeur de pourcentage invalide pour '{name}'.",
        "normalize_title": "Normaliser ?",
        "normalize_body": "La somme des pourcentages est de {total:.1f}%. Souhaitez-vous les normaliser pour atteindre 100,0 % ?",
        "no_azkar_found": "Aucun Azkar trouvé pour la catégorie : {category}",
        "reset_zikr_title": "Réinitialiser le Zikr",
        "reset_zikr_confirm": "Voulez-vous réinitialiser le compteur de ce Zikr ?",
        "limit_reached": "Limite Atteinte",
        "cannot_remove_days": "Impossible de supprimer plus de jours - le mois doit avoir au moins 1 jour.",
        "cannot_add_days": "Impossible d'ajouter plus de 7 jours supplémentaires à un mois.",
        "confirm_cal_adjustment": "Confirmer l'Ajustement du Calendrier",
        "remove_day_prompt": "Supprimer le jour {day} de {month} {year} ?\n\nLes données de tâches existantes de ce jour seront masquées mais pas supprimées.",
        "add_day_prompt": "Ajouter un jour supplémentaire ({day}) à {month} {year} ?",
        "failed_save_starred_pack": "Échec de l'enregistrement du pack de tâches : ",
        "pack_saved_starred": "Pack '{title}' enregistré dans les favoris !",
        "delete_item_title": "Supprimer l'Élément",
        "delete_item_prompt": "Êtes-vous sûr de vouloir supprimer l'élément '{name}' ?",
        "delete_group_title": "Supprimer le Groupe",
        "delete_group_prompt": "Êtes-vous sûr de vouloir supprimer le groupe '{title}' et toutes ses tâches ?",
        "graph_exported_to": "Graphique exporté vers :\n{filename}",
        "failed_export_graph": "Échec de l'exportation du graphique :\n{e}",
        "no_data": "Aucune Donnée",
        "no_logged_days": "Aucun jour enregistré trouvé pour ce mois. Enregistrez des jours d'abord !"
    },
    "Arabic": {
        "title": "قائمة المهام",
        "subtitle": "تتبع المهام النخبوية",
        "create_list": "إنشاء قائمة اليوم",
        "edit_list": "تعديل ومتابعة قائمة اليوم",
        "calendar_dashboard": "لوحة التقويم",
        "graphs_dashboard": "لوحة الإحصائيات",
        "tools": "🔧 الأدوات",
        "settings": "⚙️ الإعدادات",
        "made_by": "صنع بكل حب بواسطة YakomoDev",
        "support_project": "☕ ادعم المشروع",
        "tools_title": "الأدوات والمرافق:",
        "inspect_starred": "⭐ فحص المجموعات المفضلة",
        "read_quran": "📖 قراءة القرآن",
        "listen_quran": "🎧 الاستماع للقرآن",
        "addkar": "📿 الأذكار",
        "back": "← رجوع",
        "menu_back": "← القائمة",
        "today_lbl": "اليوم: ",
        "save_exit": "حفظ وخروج",
        "cancel": "إلغاء",
        "about_btn": "📖  حول التطبيق",
        "choose_blueprint": "اختر قالباً لليوم أو ابدأ فارغاً:",
        "close": "إغلاق",
        "add_group": "إضافة مجموعة",
        "add_starred": "إضافة مجموعة مفضلة",
        "delete_group": "حذف المجموعة",
        "edit_pack": "تعديل المجموعة",
        "star_pack": "حفظ كمفضلة",
        "blueprint": "النموذج:",
        "main_missions": "المهام الرئيسية",
        "side_missions": "المهام الثانوية",
        "done": "تم",
        "weight": "الوزن:",
        "stars": "النجوم:",
        "days_lbl": "الأيام: ",
        "remove_day": "- يوم",
        "add_day": "+ يوم",
        "tasks_completed": "المهام المكتملة:",
        "total_stars": "مجموع النجوم:",
        "small_advice": "نصيحة سريعة",
        "deep_advice": "تحليل عميق",
        "generating": "جاري التحليل...",
        "ai_updating": "تم تحديث التعليق!",
        "save_graph_png": "💾 تحميل كصورة PNG",
        "save_graph_pdf": "📄 تحميل كملف PDF",
        "avg_t_done": "معدل النجوم المكتملة ⭐",
        "avg_m_done": "معدل النجوم الرئيسية ⭐",
        "avg_s_done": "معدل النجوم الثانوية ⭐",
        "avg_t_missed": "معدل النجوم الفائتة الإجمالية 💔",
        "avg_m_missed": "معدل النجوم الرئيسية الفائتة 💔",
        "avg_s_missed": "معدل النجوم الثانوية الفائتة 💔",
        "avg_t_done_tasks": "معدل المهام المنجزة الإجمالية",
        "avg_m_done_tasks": "معدل المهام المنجزة الرئيسية",
        "avg_s_done_tasks": "معدل المهام المنجزة الثانوية",
        "avg_t_undone_tasks": "معدل المهام غير المنجزة الإجمالية",
        "avg_m_undone_tasks": "معدل المهام غير المنجزة الرئيسية",
        "avg_s_undone_tasks": "معدل المهام غير المنجزة الثانوية",
        "avg_t_ratio": "معدل الإنجاز الإجمالي %",
        "avg_m_ratio": "معدل إنجاز الرئيسية %",
        "avg_s_ratio": "معدل إنجاز الثانوية %",
        "avg_t_ratio_packs": "معدل نسبة إجمالي المجموعات %",
        "avg_m_ratio_packs": "معدل نسبة المجموعات الرئيسية %",
        "avg_s_ratio_packs": "معدل نسبة المجموعات الثانوية %",
        "avg_t_done_packs": "معدل إجمالي المجموعات المكتملة",
        "avg_m_done_packs": "معدل المجموعات الرئيسية المكتملة",
        "avg_s_done_packs": "معدل المجموعات الثانوية المكتملة",
        "avg_t_undone_packs": "معدل إجمالي المجموعات غير المكتملة",
        "avg_m_undone_packs": "معدل المجموعات الرئيسية غير المكتملة",
        "avg_s_undone_packs": "معدل المجموعات الثانوية غير المكتملة",
        "monthly_averages": "المعدلات الشهرية (للأيام النشطة فقط)",
        "month_total": "إجمالي الشهر",
        "monthly_ai_summary": "🤖 ملخص الذكاء الاصطناعي الشهري",
        "generate": "تحليل",
        "generating": "⏳ جاري التوليد...",
        "done_status": "✓ تم!",
        "comment_updated": "تم تحديث التعليق!",
        "advice_updated": "تم تحديث النصيحة!",
        "advice_loaded": "تم تحميل النصيحة!",
        "running_local_ai": "جارٍ تشغيل الذكاء المحلي...",
        "generating_advice": "جارٍ توليد النصيحة...",
        "chart_type": "نوع الرسم البياني",
        "scope": "المجال",
        "mode": "الوضعية",
        "chart_line": "📈 خطي",
        "chart_bar": "📊 أعمدة / بياني",
        "chart_pie": "🥧 دائري",
        "scope_total": "الرئيسي والثانوي",
        "scope_main": "المهام الرئيسية فقط",
        "scope_side": "المهام الثانوية فقط",
        "mode_done": "⭐ النجوم المكتسبة",
        "mode_missed": "💔 النجوم المفقودة",
        "mode_done_tasks": "✅ المهام المنجزة",
        "mode_undone_tasks": "❌ المهام غير المنجزة",
        "mode_ratio": "📐 نسبة الإنجاز %",
        "mode_done_packs": "المجموعات المكتملة",
        "mode_undone_packs": "المجموعات غير المكتملة",
        "mode_packs_ratio": "نسبة إكمال المجموعات %",
        "axis_days": "يوم الشهر",
        "axis_ratio": "نسبة الإنجاز",
        "axis_tasks": "عدد المهام",
        "axis_stars": "النجوم",
        "axis_packs": "عدد المجموعات",
        "no_logged_days": "لا توجد أيام مسجلة لهذا الشهر",
        "no_data_month": "لا توجد بيانات لهذا الشهر",
        "pie_done": "منجزة ⭐",
        "pie_missed": "مفقودة",
        "pie_done_tasks": "المهام المنجزة",
        "pie_undone_tasks": "المهام غير المنجزة",
        "pie_done_packs": "المجموعات المنجزة",
        "pie_undone_packs": "المجموعات غير المنجزة",
        "play_mode": "وضعية التشغيل",
        "mode_single": "مرة واحدة",
        "mode_loop": "تكرار",
        "mode_next": "التالي",
        "mode_shuffle": "عشوائي",
        "loading_model": "جارٍ تحميل النموذج...",
        "error_model_not_found": "خطأ: ملف Gemma 3 1B.gguf غير موجود",
        "error_llama_not_installed": "خطأ: llama-cpp-python غير مثبت",
        "add_offset": "إضافة إزاحة لليوم",
        "remove_offset": "إزالة إزاحة لليوم",
        "reset_offset": "إعادة ضبط الإزاحة",
        "clear_day_logs": "مسح السجلات اليومية",
        "delete_day": "حذف اليوم",
        "no_task_logs": "لا توجد مهام مسجلة لهذا اليوم.",
        "download_paper": "📄 تحميل الورقة اليومية",
        "view_memo": "📓 عرض المذكرة",
        "daily_diary": "اليوميات اليومية",
        "no_memo_warning": "لا توجد مذكرة مسجلة لهذا اليوم. اكتب أدناه لإنشاء واحدة.",
        "diary_loaded": "تم تحميل اليومية بنجاح",
        "diary_saved": "تم حفظ اليومية بنجاح",
        "language": "اللغة",
        "themes": "المظاهر",
        "select_lang": "اختر اللغة:",
        "select_theme": "اختر المظهر:",
        "settings_title": "شاشة الإعدادات",
        "ai_language_prompt": "يجب أن تكتب ردك باللغة العربية فقط وبشكل صحيح.",
        "day_details_preview": "معاينة تفاصيل اليوم",
        "hover_day_preview": "مرر فوق أي يوم لمعاينة الأوراق.\n\nانقر لتحميل اليوم أو بدء التتبع.",
        "empty": "فارغ",
        "today_badge": "اليوم",
        "no_task_logs_click": "لا توجد سجلات مهام لهذا اليوم.\n\nانقر لبدء التتبع!",
        "stars_earned": "النجوم المكتسبة:",
        "report": "التقرير:",
        "earned": "المكتسب:",
        "ai_daily_insight": "🤖 تحليل الذكاء الاصطناعي اليومي",
        "coach_small_advice": "💡 نصيحة المدرب السريعة",
        "coach_deep_advice": "🧠 تحليل المدرب العميق",
        "save_daily_paper": "حفظ الورقة اليومية بصيغة",
        "export_success": "تم التصدير بنجاح",
        "export_success_msg": "تم تصدير الورقة اليومية بنجاح إلى:\n",
        "export_error": "خطأ في التصدير",
        "export_error_msg": "فشل تصدير الورقة اليومية:\n",
        "error": "خطأ",
        "initialize": "تهيئة",
        "start_tracking_for": "بدء تتبع المهام لـ:",
        "start_blank": "بدء بصفحة فارغة (جديد)",
        "choose_format": "اختر الصيغة",
        "export_sheet_for": "تصدير الورقة لـ:",
        "png_image": "صورة PNG",
        "pdf_document": "ملف PDF",
        "main_tag": "رئيسية",
        "side_tag": "ثانوية",
        "stars_label": "نجوم",
        "add_task_item": "➕ إضافة مهمة",
        "set_percentage_weights": "📊 ضبط الأوزان النسبية",
        "rename_group": "✏️ إعادة تسمية المجموعة",
        "change_group_stars": "⭐ تغيير نجوم المجموعة",
        "save_starred_pack": "⭐ حفظ كمجموعة مفضلة",
        "rename_item": "✏️ إعادة تسمية المهمة",
        "delete_item": "❌ حذف المهمة",
        "add_task_item_title": "إضافة مهمة",
        "enter_item_desc": "أدخل وصف المهمة:",
        "create_new_blank_group": "إنشاء مجموعة فارغة جديدة",
        "load_starred_pack": "تحميل مجموعة مفضلة",
        "pack_saved_starred": "تم الحفظ كمفضلة!",
        "quran_recitations": "🎧 تلاوات القرآن الكريم - القارئ ياسر الدوسري",
        "search_surah": "البحث عن سورة:",
        "search_helper_text": "البحث بالاسم بالعربية، الإنجليزية أو برقم السورة (مثال: 18)",
        "select_surah_to_listen": "اختر سورة للبدء في الاستماع",
        "play": "▶ تشغيل",
        "stop": "⏹ إيقاف",
        "volume": "مستوى الصوت: 🔊",
        "last_pos": "الأخير",
        "file_missing": "الملف غير موجود",
        "daily_azkar_title": "الأذكار اليومية",
        "select_azkar_category": "اختر تصنيف الأذكار",
        "morning_tag": "الصباح",
        "evening_tag": "المساء",
        "sleep_tag": "النوم",
        "completed": "تم إكمال",
        "mashaallah": "ما شاء الله! 🎉",
        "azkar_completed_title": "أتممت أذكارك اليومية",
        "azkar_completed_subtitle": "جعلها الله في ميزان حسناتك",
        "ameen": "آمين",
        "personal_ai_advice": "نصيحة الذكاء الاصطناعي الشخصية",
        "load_starred_pack_title": "تحميل مجموعة مهام مفضلة",
        "starred_packs_title": "⭐ مجموعات المهام المفضلة",
        "no_starred_packs": "لم يتم حفظ أي مجموعات مفضلة بعد.\n\nانقر بزر الماوس الأيمن على أي مجموعة مهام واختيار 'حفظ كمجموعة مفضلة'.",
        "manage_starred_packs": "إدارة المجموعات المفضلة",
        "starred_packs_manager": "⭐ مدير المجموعات المفضلة",
        "close_manager": "إغلاق المدير",
        "tracker_target_date": "تاريخ التتبع المستهدف",
        "tasks_done": "المهام المنجزة:",
        "packs_done": "المجموعات المنجزة:",
        "grand_total_overview": "نظرة عامة على المجموع الكلي",
        "total_tasks": "إجمالي المهام:",
        "total_packs": "إجمالي المجموعات:",
        "total": "المجموع الكلي",
        "note": "ملاحظة",
        "memo": "مذكرة",
        "earned_stars_ratio": "نسبة النجوم المكتسبة:",
        "tasks_completion_ratio": "نسبة إكمال المهام:",
        "legend_base_progress": "التقدم الأساسي",
        "legend_peak_level": "مستوى الذروة",
        "local_ai_commentary": "🤖 تعليق الذكاء الاصطناعي المحلي",
        "generate_feedback": "🤖 توليد التعليق",
        "copy_prompt": "📋 نسخ التوجيه",
        "prompt_copied": "✅ تم نسخ التوجيه",
        "enter_group_title": "أدخل عنوان المجموعة",
        "enter_new_name": "أدخل الاسم الجديد:",
        "enter_new_group_title": "أدخل عنوان المجموعة الجديد:",
        "enter_new_star_count": "أدخل عدد النجوم الجديد:",
        "summary": "ملخص",
        "advice_exists": "النصيحة موجودة بالفعل",
        "advice_exists_body": "توجد نصيحة إنتاجية بالفعل ({advice_type}) لهذا اليوم.\n\nانقر فوق 'نعم' لعرض النصيحة الحالية.\nانقر فوق 'لا' لإنشاء نصيحة جديدة (سيؤدي ذلك إلى استبدال النصيحة القديمة).",
        "small_tag": "سريعة",
        "deep_tag": "عميقة",
        "small_advice_btn": "💡 نصيحة سريعة",
        "deep_advice_btn": "🧠 نصيحة عميقة",
        "edit_starred_pack": "تعديل حزمة المهام المميزة بالنجوم",
        "pack_title_label": "عنوان الحزمة:",
        "total_stars_alloc_label": "إجمالي تخصيص النجوم:",
        "task_items_in_pack_label": "عناصر المهام في الحزمة",
        "weight_label": "الوزن:",
        "save_changes": "حفظ التغييرات",
        "new_task_placeholder": "مهمة جديدة",
        "pack_title_empty": "لا يمكن أن يكون عنوان الحزمة فارغًا!",
        "stars_alloc_numeric": "يجب أن يكون تخصيص النجوم قيمة رقمية!",
        "failed_save_changes": "فشل في حفظ التغييرات: ",
        "no_starred_packs_desc": "لم يتم حفظ أي حزم مميزة بعد.\n\nيمكنك تمييز مجموعة مهام بنجمة داخل متتبع اليوم لحفظها كقالب.",
        "edit_label": "تعديل",
        "empty_pack_label": "حزمة فارغة",
        "delete_starred_pack_title": "حذف الحزمة المميزة بالنجوم؟",
        "delete_starred_pack_confirm": "هل أنت متأكد أنك تريد حذف '{title}' نهائيًا؟",
        "quran_reader_title": "قارئ القرآن",
        "no_quran_pages_error": "لم يتم العثور على صور لصفحات المصحف في المجلد المحدد.",
        "quran_page_of": "الصفحة {current} من {total}",
        "quran_pages_left": "متبقي {left} صفحة",
        "quran_completions": "🏆 عدد ختمات القرآن الكريم: {count} مرات",
        "quran_completion_success": "ما شاء الله! لقد أكملت قراءة القرآن الكريم بالكامل! تم زيادة عدد ختماتك.",
        "now_playing_prefix": "جاري التشغيل: ",
        "pause": "⏸ مؤقت",
        "resume": "▶ استئناف",
        "audio_error": "خطأ صوتي",
        "could_not_play_audio": "تعذر تشغيل الملف الصوتي: ",
        "audio_file_not_found": "الملف الصوتي غير موجود: ",
        "back_to_home": "العودة للرئيسية",
        "no_main_tasks": "لم يتم إنشاء مهام رئيسية بعد.\n\nانقر فوق '+' أعلاه لإضافة أول مهمة رئيسية!",
        "no_side_tasks": "لم يتم إنشاء مهام ثانوية بعد.\n\nانقر فوق '+' أعلاه لإضافة أول مهمة ثانوية!",
        "confirm": "تأكيد",
        "input_cannot_be_empty": "لا يمكن أن يكون الإدخال فارغًا.",
        "enter_valid_integer": "يرجى إدخال عدد صحيح غير سالب صالح.",
        "acknowledge_close": "تأكيد وإغلاق",
        "ai_coach_advice_title": "مدرب الذكاء الاصطناعي - نصيحة {type}",
        "save": "حفظ",
        "equal_split": "تقسيم بالتساوي",
        "sum_label": "المجموع: ",
        "set_pct_weights": "تحديد نسب الأوزان (المجموع: 100%)",
        "invalid_pct_val": "قيمة نسبة مئوية غير صالحة لـ '{name}'.",
        "normalize_title": "تسوية؟",
        "normalize_body": "مجموع النسب المئوية هو {total:.1f}%. هل ترغب في تسويتها لتصبح 100.0%؟",
        "no_azkar_found": "لم يتم العثور على أذكار للفئة: {category}",
        "reset_zikr_title": "إعادة تعيين الذكر",
        "reset_zikr_confirm": "هل تريد إعادة تعيين هذا الذكر؟",
        "limit_reached": "تم الوصول للحد الأقصى",
        "cannot_remove_days": "لا يمكن إزالة المزيد من الأيام - يجب أن يحتوي الشهر على يوم واحد على الأقل.",
        "cannot_add_days": "لا يمكن إضافة أكثر من 7 أيام إضافية إلى الشهر.",
        "confirm_cal_adjustment": "تأكيد تعديل التقويم",
        "remove_day_prompt": "هل تريد إزالة اليوم {day} من {month} {year}؟\n\nسيتم إخفاء بيانات المهام الحالية في هذا اليوم ولكن لن يتم حذفها.",
        "add_day_prompt": "هل تريد إضافة يوم إضافي ({day}) إلى {month} {year}؟",
        "failed_save_starred_pack": "فشل حفظ حزمة المهام: ",
        "pack_saved_starred": "تم حفظ الحزمة '{title}' في المفضلة!",
        "delete_item_title": "حذف العنصر",
        "delete_item_prompt": "هل أنت متأكد أنك تريد حذف العنصر '{name}'؟",
        "delete_group_title": "حذف المجموعة",
        "delete_group_prompt": "هل أنت متأكد أنك تريد حذف المجموعة '{title}' وجميع مهامها؟",
        "graph_exported_to": "تم تصدير الرسم البياني إلى:\n{filename}",
        "failed_export_graph": "فشل تصدير الرسم البياني:\n{e}",
        "no_data": "لا يوجد بيانات",
        "no_logged_days": "لم يتم العثور على أيام مسجلة لهذا الشهر. يرجى تسجيل بعض الأيام أولاً!"
    }
}

def run_diagnostics():
    try:
        diag_path = os.path.join(APP_DIR, "data", "shaping_diagnostics.txt")
        with open(diag_path, "w", encoding="utf-8") as f:
            f.write("=== Mission UI Diagnostic Log ===\n")
            f.write(f"Current language: {_current_language}\n")
            
            # Check arabic_reshaper import
            try:
                import arabic_reshaper
                f.write(f"arabic_reshaper import: SUCCESS (version: {getattr(arabic_reshaper, '__version__', 'unknown')})\n")
                try:
                    config = {'delete_harakat': False}
                    reshaper = arabic_reshaper.ArabicReshaper(configuration=config)
                    f.write("ArabicReshaper init: SUCCESS\n")
                    test_str = "السبت"
                    shaped = reshaper.reshape(test_str)
                    f.write(f"Reshaped 'السبت' (repr): {repr(shaped)}\n")
                except Exception as e:
                    f.write(f"ArabicReshaper init/reshape FAILED: {e}\n")
            except Exception as e:
                f.write(f"arabic_reshaper import FAILED: {e}\n")
                
            # Check python-bidi import
            try:
                from bidi.algorithm import get_display
                f.write("bidi.algorithm.get_display import: SUCCESS\n")
                try:
                    test_str = "السبت"
                    import arabic_reshaper
                    config = {'delete_harakat': False}
                    reshaper = arabic_reshaper.ArabicReshaper(configuration=config)
                    shaped = reshaper.reshape(test_str)
                    bidi_res = get_display(shaped)
                    f.write(f"bidi of reshaped 'السبت' (repr): {repr(bidi_res)}\n")
                except Exception as e:
                    f.write(f"bidi process FAILED: {e}\n")
            except Exception as e:
                f.write(f"bidi.algorithm import FAILED: {e}\n")
                
            # Check shape_line directly
            try:
                res = shape_line("السبت")
                f.write(f"shape_line('السبت') (repr): {repr(res)}\n")
            except Exception as e:
                f.write(f"shape_line FAILED: {e}\n")
                
            # Check font paths
            try:
                reg, bold = get_best_font_paths(APP_DIR)
                f.write(f"Font path regular: {reg} (exists: {os.path.exists(reg)})\n")
                f.write(f"Font path bold: {bold} (exists: {os.path.exists(bold)})\n")
            except Exception as e:
                f.write(f"get_best_font_paths FAILED: {e}\n")
                
            # Check PIL imports and font loading
            try:
                from PIL import ImageFont
                f.write("PIL ImageFont import: SUCCESS\n")
                reg, bold = get_best_font_paths(APP_DIR)
                if os.path.exists(reg):
                    try:
                        font = ImageFont.truetype(reg, 18)
                        f.write(f"PIL loading regular font: SUCCESS\n")
                    except Exception as e:
                        f.write(f"PIL loading regular font FAILED: {e}\n")
            except Exception as e:
                f.write(f"PIL import FAILED: {e}\n")
    except Exception as e:
        print(f"Diagnostics runner encountered error: {e}")

def load_settings():
    global _current_theme, _current_language
    os.makedirs(os.path.join(APP_DIR, "data"), exist_ok=True)
    if os.path.exists(PREFS_PATH):
        try:
            with open(PREFS_PATH, "r", encoding="utf-8") as f:
                prefs = json.load(f)
            _current_theme = prefs.get("theme", "Neon Dark")
            _current_language = prefs.get("language", "English")
            if _current_language == "Arabic":
                _current_language = "English"
            apply_theme_colors(_current_theme)
        except Exception as e:
            print(f"[prefs] load error: {e}")
    run_diagnostics()


def save_settings(theme_name, language_name):
    global _current_theme, _current_language
    _current_theme = theme_name
    _current_language = language_name
    apply_theme_colors(_current_theme)
    
    prefs = {}
    if os.path.exists(PREFS_PATH):
        try:
            with open(PREFS_PATH, "r", encoding="utf-8") as f:
                prefs = json.load(f)
        except Exception:
            pass
            
    prefs["theme"] = theme_name
    prefs["language"] = language_name
    try:
        with open(PREFS_PATH, "w", encoding="utf-8") as f:
            json.dump(prefs, f)
    except Exception as e:
        print(f"[prefs] save error: {e}")

_shared_reshaper = None

def _get_reshaper():
    global _shared_reshaper
    if _shared_reshaper is None:
        try:
            import arabic_reshaper
            config = {'delete_harakat': False}
            _shared_reshaper = arabic_reshaper.ArabicReshaper(configuration=config)
        except Exception as e:
            print(f"[arabic_reshaper] init error: {e}")
    return _shared_reshaper


_arabic_shaped_cache = {}

def tr(key):
    """Translate key using current language. Shape Arabic correctly if needed (cached)."""
    lang_dict = LOCALIZATION.get(_current_language, LOCALIZATION["English"])
    text = lang_dict.get(key, LOCALIZATION["English"].get(key, key))
    if _current_language == "Arabic":
        if text not in _arabic_shaped_cache:
            try:
                from bidi.algorithm import get_display
                reshaper = _get_reshaper()
                if reshaper is not None:
                    _arabic_shaped_cache[text] = get_display(reshaper.reshape(text))
                else:
                    _arabic_shaped_cache[text] = text
            except Exception:
                _arabic_shaped_cache[text] = text
        return _arabic_shaped_cache[text]
    return text

def tr_raw(key):
    """Translate key using current language, returning the raw un-shaped string."""
    lang_dict = LOCALIZATION.get(_current_language, LOCALIZATION["English"])
    return lang_dict.get(key, LOCALIZATION["English"].get(key, key))

def clean_emojis(text):
    """Replace emojis with standard unicode characters or strip them for PIL compatibility."""
    if not text:
        return ""
    replacements = {
        "⭐": "★",
        "✩": "★",
        "💔": "✗",
        "✅": "✔",
        "❌": "✘",
        "🥧": "",
        "📊": "",
        "📈": "",
        "📐": "",
        "🤖": "",
    }
    cleaned = text
    for emoji, substitute in replacements.items():
        cleaned = cleaned.replace(emoji, substitute)
    return cleaned.strip()

def _fix_arabic_colons(text):
    """Insert an RLM (U+200F) before colons that follow Arabic characters.
    This prevents the bidi algorithm from doubling or misplacing colons in
    Arabic RTL text (the 'two-dots problem')."""
    import re
    _RLM = "\u200F"  # Right-to-Left Mark
    # Insert RLM before ':' when preceded by an Arabic letter
    return re.sub(r'([\u0600-\u06FF\u0750-\u077F\uFB50-\uFEFF])\s*:', r'\1' + _RLM + ':', text)



def shape_line(text):
    """Clean emojis and shape/bidi-reverse Arabic text if needed."""
    return clean_emojis(text)

def shape_for_display(text):
    """Apply Arabic reshaping+bidi only when current language is Arabic.
    Use this before inserting text into tk.Text widgets."""
    if not text:
        return ""
    if _current_language == "Arabic":
        try:
            from bidi.algorithm import get_display
            reshaper = _get_reshaper()
            if reshaper is not None:
                lines = text.split("\n")
                shaped_lines = []
                for line in lines:
                    shaped_lines.append(get_display(reshaper.reshape(line)))
                return "\n".join(shaped_lines)
        except Exception:
            pass
    return text

# ── Localized date helpers ─────────────────────────────────────────────────

_DAYS_EN = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
_DAYS_FR = ["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"]
_DAYS_AR = ["الاثنين","الثلاثاء","الأربعاء","الخميس","الجمعة","السبت","الأحد"]

_MONTHS_EN = ["January","February","March","April","May","June",
              "July","August","September","October","November","December"]
_MONTHS_FR = ["Janvier","Février","Mars","Avril","Mai","Juin",
              "Juillet","Août","Septembre","Octobre","Novembre","Décembre"]
_MONTHS_AR = ["يناير","فبراير","مارس","أبريل","مايو","يونيو",
              "يوليو","أغسطس","سبتمبر","أكتوبر","نوفمبر","ديسمبر"]


def _day_name(weekday_idx):
    """weekday_idx: 0=Monday … 6=Sunday (Python datetime.weekday())"""
    if _current_language == "French":
        return _DAYS_FR[weekday_idx]
    elif _current_language == "Arabic":
        return _DAYS_AR[weekday_idx]
    return _DAYS_EN[weekday_idx]


def _month_name(month_1indexed):
    idx = month_1indexed - 1
    if _current_language == "French":
        return _MONTHS_FR[idx]
    elif _current_language == "Arabic":
        return _MONTHS_AR[idx]
    return _MONTHS_EN[idx]


def _shape_arabic(raw):
    """Apply reshaper + bidi to a raw Arabic string. Internal helper."""
    try:
        from bidi.algorithm import get_display
        reshaper = _get_reshaper()
        if reshaper is None:
            return raw
        return get_display(reshaper.reshape(raw))
    except Exception:
        return raw


def _format_date_raw(dt):
    """Return the logical (un-shaped) date string for the current language."""
    day = _day_name(dt.weekday())
    month = _month_name(dt.month)
    if _current_language == "Arabic":
        return f"{day}، {dt.day} {month} {dt.year}"
    elif _current_language == "French":
        return f"{day}, {dt.day} {month} {dt.year}"
    return f"{day}, {month} {dt.day}, {dt.year}"


def _format_month_raw(year, month):
    """Return the logical (un-shaped) month+year string."""
    return f"{_month_name(month)} {year}"


def format_date(dt):
    """Return a fully localized full date string.
    dt must be a datetime.date object.
    """
    raw = _format_date_raw(dt)
    if _current_language == "Arabic":
        return _shape_arabic(raw)
    return raw


def format_date_labeled(prefix_key, dt):
    """Return prefix label + date as ONE correctly shaped Arabic string.
    Use this instead of tr(key) + format_date() to avoid bidi split.
    prefix_key: a theme_manager translation key (e.g. 'today_lbl').
    """
    lang_dict = LOCALIZATION.get(_current_language, LOCALIZATION["English"])
    raw_prefix = lang_dict.get(prefix_key, LOCALIZATION["English"].get(prefix_key, ""))
    raw_date = _format_date_raw(dt)
    raw = f"{raw_prefix}{raw_date}"
    if _current_language == "Arabic":
        return _shape_arabic(raw)
    return raw


def format_date_multiline(dt):
    """Like format_date but returns day name on first line, rest on second.
    Used for calendar sidebar header.
    """
    day = _day_name(dt.weekday())
    month = _month_name(dt.month)
    if _current_language == "Arabic":
        raw = f"{day}\n{dt.day} {month} {dt.year}"
    elif _current_language == "French":
        raw = f"{day}\n{dt.day} {month} {dt.year}"
    else:
        raw = f"{day}\n{month} {dt.day}, {dt.year}"
    if _current_language == "Arabic":
        try:
            from bidi.algorithm import get_display
            reshaper = _get_reshaper()
            if reshaper is None:
                return raw
            lines = raw.split("\n")
            return "\n".join(get_display(reshaper.reshape(line)) for line in lines)
        except Exception:
            return raw
    return raw


def format_month(year, month):
    """Return localized month + year, e.g. 'August 2026' / 'Août 2026' / 'أغسطس 2026'."""
    raw = _format_month_raw(year, month)
    if _current_language == "Arabic":
        return _shape_arabic(raw)
    return raw


def get_best_font_paths(app_dir):
    """Return (regular, bold) font paths suitable for the current language.
    For Arabic, prefers NotoNaskhArabic which has correct pre-composed Arabic
    glyph shaping compatible with PIL's TrueType renderer.
    Checks absolute known paths first for speed and reliability.
    """
    import os
    import glob

    fonts_dir = os.path.join(app_dir, "data", "fonts")
    default_reg  = os.path.join(fonts_dir, "DejaVuSansMono.ttf")
    default_bold = os.path.join(fonts_dir, "DejaVuSansMono-Bold.ttf")

    if _current_language == "Arabic":
        # 1. Check absolute known paths first (fast and reliable)
        _known = [
            ("/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
             "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf"),
            ("/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
             "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf"),
            ("/usr/share/fonts/truetype/amiri/amiri-regular.ttf",
             "/usr/share/fonts/truetype/amiri/amiri-bold.ttf"),
            ("/usr/share/fonts/truetype/freefont/FreeSans.ttf",
             "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"),
            (os.path.join(fonts_dir, "NotoNaskhArabic-Regular.ttf"),
             os.path.join(fonts_dir, "NotoNaskhArabic-Bold.ttf")),
        ]
        for reg, bold in _known:
            if os.path.exists(reg):
                return reg, bold if os.path.exists(bold) else reg

        # 2. Recursive glob scan as broader fallback
        _candidates = ["NotoNaskhArabic", "NotoSansArabic", "Amiri",
                       "DejaVuSans", "FreeSans", "LiberationSans"]
        _scan_dirs = ["/usr/share/fonts", "/usr/share/fonts/truetype",
                      "/usr/share/fonts/opentype",
                      os.path.expanduser("~/.local/share/fonts")]
        for dir_path in _scan_dirs:
            if not os.path.isdir(dir_path):
                continue
            for name in _candidates:
                files = []
                for ext in ("*.ttf", "*.otf"):
                    files.extend(glob.glob(
                        os.path.join(dir_path, "**", f"*{name}*{ext}"),
                        recursive=True))
                if files:
                    reg = None
                    bold = None
                    for f in files:
                        f_name = os.path.basename(f).lower()
                        if "bold" in f_name:
                            bold = f
                        elif "regular" in f_name or "normal" in f_name or name.lower() in f_name:
                            if reg is None or "regular" in f_name:
                                reg = f
                    if not reg:
                        reg = files[0]
                    if not bold:
                        bold = reg
                    return reg, bold

    return default_reg, default_bold


import unicodedata

def unshape_arabic_text(text):
    if not text:
        return text
    if not any('\ufb50' <= c <= '\ufeff' for c in text):
        return text
    words = text.split(" ")
    unshaped_words = []
    for word in words:
        if any('\ufb50' <= c <= '\ufeff' for c in word):
            decomp = unicodedata.normalize('NFKC', word)
            unshaped_words.append(decomp[::-1])
        else:
            unshaped_words.append(word)
    return " ".join(unshaped_words)


# Load settings immediately on import
load_settings()
