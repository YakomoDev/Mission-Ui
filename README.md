# 🚀 Mission UI

Prepared with ❤️ by **[YakomoDev](https://ko-fi.com/yakomodev)**

**Mission UI** is a feature-rich, 100% offline desktop productivity and mission tracking application built with **Python**, **Tkinter**, **SQLite**, and integrated local AI capabilities (**Gemma 3 1B** via `llama-cpp-python`).

---

## ✨ Features

- 🛡️ **100% Offline & Private**: Runs completely locally without sending data to external APIs.
- 🤖 **Integrated Local AI**: Powered by Gemma 3 1B LLM for intelligent commentary and productivity insights.
- 📄 **Real Paper Sheet Exports**: Export memos, task sheets, and user data formatted in realistic, printable paper sheet layouts.
- 📊 **Analytics & Graph Exporting**: Track visual progress backed by SQLite and export charts, graphs, and task statistics.
- 🎨 **Custom Theme Engine**: Built-in dynamic theme manager supporting dark, light, and custom color modes.
- ⚡ **Standalone Executable Ready**: Includes optimized Nuitka compilation scripts (`compile_nuitka.sh`).

---

## 📦 Download Data & AI Agent Assets

To keep the source code repository lightweight and fast to clone, the external data files and AI model weights are hosted externally:

- **📥 MediaFire Data & Agent Assets Download**: [Download Data & Agent Assets](https://www.mediafire.com/folder/bq23c5xg65wcg/Mission+Ui+data+and+agent+repo)

> **Instructions**: Extract the downloaded assets package so that the `data/` and `agent/` directories are placed directly in the root folder of this project as shown in the project structure below.

---

## 📁 Project Structure

```text
Mission-Ui/
├── app.py               # Main application entry point & UI controller
├── ai_helper.py         # Offline LLM inference module (Gemma 3 1B)
├── setup_agent.py       # Automated virtual environment & dependency setup script
├── theme_manager.py     # Centralized theme & localization manager (EN, FR, AR)
├── graphs_screen.py     # Canvas-based analytics and graphing module
├── export_helper.py     # Paper sheet & graph export generator
├── settings_screen.py   # App settings & preferences interface
├── about_screen.py      # App documentation & about interface
├── compile_nuitka.sh    # Nuitka build script for standalone binary compilation for linux
├── LICENSE              # YakomoDev Non-Commercial License
├── README.md            # Project documentation
│
├── data/                # [From MediaFire] UI assets, icons, fonts & SQLite database
│   ├── azkar.json
│   ├── fonts/
│   ├── icone/
│   ├── quran_pages/
│   └── missions.db
│
└── agent/               # [From MediaFire] Local AI model weights
    └── Gemma 3 1B.gguf
```

---

## 🚀 Quick Start

### 1. Requirements
- Python 3.10+
- Virtual environment (`.venv`)

### 2. Setup & Run

```bash
# Clone the repository
git clone https://github.com/YakomoDev/Mission-Ui.git
cd Mission-Ui

# Setup environment & dependencies
python3 setup_agent.py

# Launch the application
python3 app.py
```

## 📜 License & Commercial Terms

This project is licensed under the **YakomoDev Non-Commercial License**:
- ✅ **Free for Personal Use**: Anyone can inspect, run, and use this app for personal, educational, or research purposes.
- ⛔ **Commercial Use Restricted**: Any commercial use, business integration, or re-selling is strictly prohibited without prior written permission and a licensing/royalty agreement from **YakomoDev**.

See the full [LICENSE](LICENSE) file for complete details.

---

## ☕ Support the Developer

If you find this project helpful, feel free to support my work:
👉 **[Support YakomoDev on Ko-fi](https://ko-fi.com/yakomodev)**
