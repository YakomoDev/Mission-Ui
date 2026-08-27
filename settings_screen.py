# YakomoDev - https://ko-fi.com/yakomodev
import tkinter as tk
from tkinter import ttk, messagebox
import theme_manager as tm

class SettingsScreen(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=tm.BG_DARK)
        self.parent = parent
        self._build_ui()

    def _build_ui(self):
        # Container frame
        container = tk.Frame(self, bg=tm.BG_CARD, highlightbackground=tm.BORDER_COLOR, highlightthickness=1)
        container.place(relx=0.5, rely=0.5, anchor="center", width=550, height=450)

        # Title
        title_lbl = tk.Label(container, text=tm.tr("settings"), bg=tm.BG_CARD, fg=tm.TEXT_WHITE,
                             font=("Helvetica", 18, "bold"))
        title_lbl.pack(pady=(30, 20))

        # Dropdowns container
        form = tk.Frame(container, bg=tm.BG_CARD)
        form.pack(pady=10, padx=40, fill="x")

        # Configure style of Combobox to match theme
        style = ttk.Style()
        style.theme_use('default')
        style.configure("TCombobox", 
                        fieldbackground=tm.BG_DARK, 
                        background=tm.BG_DARK, 
                        foreground=tm.TEXT_WHITE, 
                        bordercolor=tm.BORDER_COLOR,
                        darkcolor=tm.BG_DARK,
                        lightcolor=tm.BG_DARK,
                        arrowcolor=tm.ACCENT_CYAN,
                        arrowsize=12)
        
        style.map('TCombobox',
                  fieldbackground=[('readonly', tm.BG_DARK), ('focus', tm.BG_DARK)],
                  foreground=[('readonly', tm.TEXT_WHITE)],
                  arrowcolor=[('readonly', tm.ACCENT_CYAN), ('hover', tm.ACCENT_PURPLE)],
                  bordercolor=[('readonly', tm.BORDER_COLOR)])
        
        # Configure listbox popup of Combobox
        self.option_add('*TCombobox*Listbox.background', tm.BG_DARK)
        self.option_add('*TCombobox*Listbox.foreground', tm.TEXT_WHITE)
        self.option_add('*TCombobox*Listbox.selectBackground', tm.ACCENT_PURPLE)
        self.option_add('*TCombobox*Listbox.selectForeground', tm.TEXT_WHITE)
        self.option_add('*TCombobox*Listbox.borderWidth', 0)
        self.option_add('*TCombobox*Listbox.highlightThickness', 0)
        self.option_add('*TCombobox*Listbox.font', ("Helvetica", 11))

        # ── Language Option ──
        lang_lbl = tk.Label(form, text=tm.tr("select_lang"), bg=tm.BG_CARD, fg=tm.TEXT_WHITE,
                            font=("Helvetica", 11, "bold"))
        lang_lbl.grid(row=0, column=0, pady=15, sticky="w")

        self.lang_var = tk.StringVar(value=tm._current_language)
        lang_combo = ttk.Combobox(form, textvariable=self.lang_var, values=["English", "French"],
                                  state="readonly", font=("Helvetica", 11), width=18)
        lang_combo.grid(row=0, column=1, pady=15, padx=15, sticky="e")
        
        # ── Theme Option ──
        theme_lbl = tk.Label(form, text=tm.tr("select_theme"), bg=tm.BG_CARD, fg=tm.TEXT_WHITE,
                             font=("Helvetica", 11, "bold"))
        theme_lbl.grid(row=1, column=0, pady=15, sticky="w")

        self.theme_var = tk.StringVar(value=tm._current_theme)
        theme_combo = ttk.Combobox(form, textvariable=self.theme_var, values=list(tm.THEMES.keys()),
                                   state="readonly", font=("Helvetica", 11), width=18)
        theme_combo.grid(row=1, column=1, pady=15, padx=15, sticky="e")

        # ── Buttons ──
        btns = tk.Frame(container, bg=tm.BG_CARD)
        btns.pack(pady=(40, 20))

        save_btn = tk.Button(btns, text=tm.tr("save_exit"), bg=tm.SUCCESS_GREEN, fg=tm.BG_DARK,
                             relief="flat", bd=0, activebackground=tm.GLOW_COLOR, activeforeground=tm.BG_DARK,
                             font=("Helvetica", 11, "bold"), padx=25, pady=10,
                             command=self._save_settings)
        save_btn.pack(side="left", padx=10)
        save_btn.bind("<Enter>", lambda e: save_btn.config(bg=tm.GLOW_COLOR))
        save_btn.bind("<Leave>", lambda e: save_btn.config(bg=tm.SUCCESS_GREEN))

        about_btn = tk.Button(btns, text=tm.tr("about_btn"), bg=tm.ACCENT_PURPLE, fg=tm.BG_DARK,
                              relief="flat", bd=0, activebackground=tm.ACCENT_CYAN, activeforeground=tm.BG_DARK,
                              font=("Helvetica", 11, "bold"), padx=20, pady=10,
                              command=self.parent.show_about_screen)
        about_btn.pack(side="left", padx=10)
        about_btn.bind("<Enter>", lambda e: about_btn.config(bg=tm.ACCENT_CYAN))
        about_btn.bind("<Leave>", lambda e: about_btn.config(bg=tm.ACCENT_PURPLE))

        cancel_btn = tk.Button(btns, text=tm.tr("cancel"), bg=tm.BG_DARK, fg=tm.TEXT_MUTED,
                               relief="flat", bd=0, activebackground=tm.BORDER_COLOR, activeforeground=tm.TEXT_WHITE,
                               font=("Helvetica", 11, "bold"), padx=25, pady=10,
                               command=self.parent.show_start_screen)
        cancel_btn.pack(side="left", padx=10)
        cancel_btn.bind("<Enter>", lambda e: cancel_btn.config(bg=tm.BORDER_COLOR, fg=tm.TEXT_WHITE))
        cancel_btn.bind("<Leave>", lambda e: cancel_btn.config(bg=tm.BG_DARK, fg=tm.TEXT_MUTED))

    def _save_settings(self):
        new_lang = self.lang_var.get()
        new_theme = self.theme_var.get()
        
        # Save to pref.json and update global config
        tm.save_settings(new_theme, new_lang)
        
        # Return to Start Screen immediately so changes are visible
        self.parent.show_start_screen()
