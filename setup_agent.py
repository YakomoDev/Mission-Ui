#!/usr/bin/env python3
# Prepared with love by YakomoDev - https://ko-fi.com/yakomodev
import os
import sys
import shutil
import subprocess

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
AGENT_DIR = os.path.join(ROOT_DIR, "agent")
MODEL_FILENAME = "Gemma 3 1B.gguf"
SRC_MODEL_PATH = os.path.join(ROOT_DIR, MODEL_FILENAME)
DEST_MODEL_PATH = os.path.join(AGENT_DIR, MODEL_FILENAME)
VENV_DIR = os.path.join(ROOT_DIR, ".venv")

# Determine OS and executable paths
is_windows = os.name == "nt"
if is_windows:
    venv_python = os.path.join(VENV_DIR, "Scripts", "python.exe")
    venv_activate_command = r".venv\Scripts\activate"
else:
    venv_python = os.path.join(VENV_DIR, "bin", "python")
    venv_activate_command = "source .venv/bin/activate"

def setup_folders_and_model():
    print("=== Step 1: Setting up agent directory and relocating model ===")
    
    # Create agent folder if not exists
    if not os.path.exists(AGENT_DIR):
        print(f"[*] Creating agent directory: {AGENT_DIR}")
        os.makedirs(AGENT_DIR, exist_ok=True)
    else:
        print("[+] Agent directory already exists.")
        
    # Check if model is in root and needs moving
    if os.path.exists(SRC_MODEL_PATH):
        print(f"[*] Moving {MODEL_FILENAME} from root into agent folder...")
        try:
            shutil.move(SRC_MODEL_PATH, DEST_MODEL_PATH)
            print(f"[+] Successfully moved model to: {DEST_MODEL_PATH}")
        except Exception as e:
            print(f"[-] Failed to move model file: {e}")
            sys.exit(1)
    elif os.path.exists(DEST_MODEL_PATH):
        print(f"[+] Model is already located in: {DEST_MODEL_PATH}")
    else:
        print(f"[-] Error: Could not find '{MODEL_FILENAME}' at root ({SRC_MODEL_PATH}) or in the agent folder ({DEST_MODEL_PATH}).")
        print("[-] Please place the Gemma 3 1B.gguf file in the project root folder and try again.")
        sys.exit(1)

def setup_virtual_environment():
    print("\n=== Step 2: Setting up virtual environment ===")
    if not os.path.exists(VENV_DIR):
        print(f"[*] Creating Python virtual environment in: {VENV_DIR}...")
        try:
            subprocess.run([sys.executable, "-m", "venv", VENV_DIR], check=True)
            print("[+] Virtual environment created successfully!")
        except subprocess.CalledProcessError as e:
            print(f"[-] Failed to create virtual environment: {e}")
            sys.exit(1)
    else:
        print("[+] Virtual environment already exists.")

def install_dependencies():
    print("\n=== Step 3: Upgrading Pip and installing llama-cpp-python in venv ===")
    
    # Check if we can find venv python
    if not os.path.exists(venv_python):
        print(f"[-] Error: Virtual environment python executable not found at {venv_python}")
        sys.exit(1)
        
    # Upgrade pip inside venv
    print("[*] Upgrading pip inside venv...")
    subprocess.run([venv_python, "-m", "pip", "install", "--upgrade", "pip"], check=False)
    
    # Check if llama-cpp-python is already installed in venv
    check_cmd = [venv_python, "-c", "import llama_cpp"]
    res = subprocess.run(check_cmd, capture_output=True)
    if res.returncode == 0:
        print("[+] llama-cpp-python is already installed in the virtual environment.")
        return
        
    print("[*] Installing llama-cpp-python inside virtual environment...")
    print("[*] Note: Standard CPU installation will be executed by default.")
    print("[*] If compiling with hardware acceleration, please run manually inside active virtual environment:")
    print("    - CUDA (NVIDIA): CMAKE_ARGS=\"-DLLAMA_CUDA=on\" pip install llama-cpp-python --force-reinstall --no-cache-dir")
    print("    - Metal (Apple): CMAKE_ARGS=\"-DLLAMA_METAL=on\" pip install llama-cpp-python --force-reinstall --no-cache-dir")
    
    try:
        # Install llama-cpp-python inside virtual environment
        subprocess.run([venv_python, "-m", "pip", "install", "llama-cpp-python"], check=True)
        print("[+] llama-cpp-python installed successfully inside venv!")
    except subprocess.CalledProcessError as e:
        print(f"[-] Failed to install llama-cpp-python: {e}")
        print("[-] Try activating the virtual environment and running pip install manually.")
        sys.exit(1)

def test_inference():
    print("\n=== Step 4: Testing Local Inference using venv python ===")
    
    # Inline test code to run inside venv Python
    test_code = f"""
import sys
try:
    from llama_cpp import Llama
    print("[*] Model loading (using venv Python)...")
    llm = Llama(model_path={repr(DEST_MODEL_PATH)}, n_ctx=512, verbose=False)
    print("[*] Running test completion...")
    prompt = "Write a one-sentence encouraging quote for productivity:"
    response = llm(prompt, max_tokens=60, temperature=0.7)
    text = response["choices"][0]["text"].strip()
    print("\\n[+] Test completion succeeded!")
    print(f"Response: \\"{{text}}\\"")
    print("\\n=== Setup Completed Successfully! ===")
except Exception as e:
    print(f"[-] Local test failed: {{e}}")
"""
    
    try:
        subprocess.run([venv_python, "-c", test_code], check=True)
    except subprocess.CalledProcessError as e:
        print(f"[-] Inference test execution failed: {e}")

def show_activation_info():
    print("\n" + "="*50)
    print("To run the application or AI assistant inside the environment:")
    print(f"1. Activate the environment:")
    print(f"   Linux/macOS:  {venv_activate_command}")
    print(f"   Windows:      .venv\\Scripts\\activate")
    print(f"\n2. Start the tracking app:")
    print(f"   python3 app.py")
    print(f"\n3. Generate AI commentary:")
    print(f"   python3 ai_helper.py")
    print("="*50 + "\n")

if __name__ == "__main__":
    setup_folders_and_model()
    setup_virtual_environment()
    install_dependencies()
    test_inference()
    show_activation_info()
