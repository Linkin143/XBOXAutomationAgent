# 🎮 Xbox Automation V4 Agent

> **Automated Xbox game testing powered by AI** — press buttons, read the screen, write reports, all by itself.

---

## 🤔 What Is This?

This tool automatically tests Xbox games on a real console. You plug in some hardware, add your API key, and run one command. The AI then:

1. **Navigates** the Xbox dashboard and launches each game
2. **Verifies** the screen looks correct using computer vision
3. **Interacts** with game menus using a virtual controller
4. **Logs** every step as PASS or FAIL
5. **Generates** a Word document report when done

No manual clicking. No PowerShell scripts. Just Python + AI.

---

## ✅ Prerequisites — What You Need

Before starting, make sure you have:

### Software
| Tool | Version | Download |
|---|---|---|
| **Python** | 3.11 or newer | [python.org/downloads](https://www.python.org/downloads/) |
| **GIMX** | Latest | [gimx.fr/wiki](https://gimx.fr/wiki/index.php/Download) |
| **Tesseract OCR** | 5.x | [github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki) |
| **Git** (optional) | Any | [git-scm.com](https://git-scm.com/) |

### API Key (pick one — you only need ONE)
| Provider | Model | Get Key |
|---|---|---|
| **OpenAI** | GPT-4o | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| **Anthropic** | Claude 3.5 Sonnet | [console.anthropic.com](https://console.anthropic.com/) |

> 💡 **Tip:** OpenAI GPT-4o is the default. If you already have an OpenAI account, start there.

### Hardware Devices
| Device | Purpose |
|---|---|
| USB-to-Serial adapter | Connects PC to Arduino via UART |
| Arduino UNO | Sends keyboard/mouse inputs to Xbox |
| AVerMedia U3 Capture Card | Captures Xbox screen video on PC |
| Relay board (optional) | Hardware power button control |
| USB-UIRT (optional) | IR remote blaster |
| 3× Jumper wires | TX/RX/GND connections between adapter and Arduino |

---

## 🔧 Hardware Setup (Physical Connections)

Follow these steps in order. Take your time — getting the wiring right is the most important part.

### Step 1 — Connect Arduino to PC via UART

```
PC USB port
    ↓
USB-to-Serial Adapter (shows as COM3 in Device Manager)
    ↓  Jumper wires (3 wires!)
    ├── TX (adapter) ──────→ RX (Arduino pin 0)
    ├── RX (adapter) ←────── TX (Arduino pin 1)
    └── GND (adapter) ──────→ GND (Arduino)
    ↓
Arduino UNO
    ↓  USB cable
Xbox Console USB port (acts as keyboard/mouse)
```

> ⚠️ **Important:** TX and RX must be **crossed** (TX→RX, RX→TX). If you connect TX→TX it won't work.

### Step 2 — Connect Relay Board (if you have one)

```
PC USB port → USB-to-Serial Adapter (shows as COM8 in Device Manager)
    ↓
Relay Board → Xbox Console power button circuit
```

### Step 3 — Connect Capture Card

```
Xbox Console HDMI OUT
    ↓  HDMI cable
AVerMedia U3 Capture Card (USB 3.0 to PC)
    ↓
PC (appears as a camera device — usually index 0 or 1)
```

### Step 4 — Connect GIMX (Virtual Controller)

GIMX is software that runs on your PC and acts as a fake Xbox controller:

```
Python script
    ↓  UDP packets (127.0.0.1:51914)
GIMX.exe (running on PC)
    ↓  USB cable (shows as COM6 in Device Manager)
Xbox Console (sees it as a wired Xbox controller)
```

### Full Wiring Diagram

```
┌─────────────────────────────────────────────────────────┐
│                        TEST PC                          │
│                                                         │
│  Python main.py                                         │
│      │                                                  │
│      ├─── UDP 127.0.0.1:51914 ──→ GIMX.exe             │
│      │                                  │ COM6/USB      │
│      ├─── COM3 (Arduino KBM) ──→ UART ─┤               │
│      ├─── COM8 (Relay board) ──────────┤               │
│      └─── OpenCV / DirectShow ←── AVerMedia U3         │
│                                         │ USB 3.0       │
└─────────────────────────────────────────┼───────────────┘
                                          │
                              ┌───────────▼───────────┐
                              │     XBOX CONSOLE       │
                              │  ← GIMX (controller)  │
                              │  ← Arduino (KBM)      │
                              │  → HDMI → AVerMedia   │
                              └───────────────────────┘
```

---

## 💻 Software Installation

### Step 1 — Install Python 3.11+

1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Download **Python 3.11** or newer
3. ✅ During install, check **"Add Python to PATH"**
4. Verify it works:
   ```cmd
   python --version
   ```
   You should see something like `Python 3.11.9`

### Step 2 — Download This Project

If you have Git:
```cmd
git clone https://github.com/your-repo/XBOXAutomationAgent.git
cd XBOXAutomationAgent\Automation_V4_Agent
```

Or just download and unzip the folder, then open a command prompt inside `Automation_V4_Agent`.

### Step 3 — Install Python Packages

Open Command Prompt **inside** the `Automation_V4_Agent` folder and run:

```cmd
pip install -r requirements.txt
```

This will install everything automatically (LangChain, LiteLLM, OpenCV, pyserial, etc.). It may take 2–5 minutes.

> 💡 **If you get a permission error**, try:
> ```cmd
> pip install -r requirements.txt --user
> ```

### Step 4 — Install Tesseract OCR

Tesseract reads text from screenshots. You must install it separately:

1. Go to [github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki)
2. Download the **Windows installer** (e.g., `tesseract-ocr-w64-setup-5.x.x.exe`)
3. Run the installer — use the **default install path**: `C:\Program Files\Tesseract-OCR\`
4. Verify:
   ```cmd
   "C:\Program Files\Tesseract-OCR\tesseract.exe" --version
   ```

### Step 5 — Install and Configure GIMX

1. Download GIMX from [gimx.fr/wiki](https://gimx.fr/wiki/index.php/Download)
2. Install it (default location is fine)
3. Make sure the GIMX adapter (USB dongle) is plugged in — it appears as a COM port (e.g., COM6)
4. GIMX will be launched **automatically** by the Python script — you don't need to start it manually

---

## ⚙️ Configuration

### Step 1 — Create Your `.env` File

The `.env` file stores your secret API keys. **Never share this file.**

1. Find the file `.env.example` in the **root** `XBOXAutomationAgent` folder
2. Copy it and rename the copy to `.env`:
   ```cmd
   copy .env.example .env
   ```
3. Open `.env` in Notepad and fill in your API key:

   **If using OpenAI (GPT-4o):**
   ```
   OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxx
   ```

   **If using Anthropic (Claude):**
   ```
   ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxx
   LITELLM_MODEL=claude-3-5-sonnet-20241022
   ```

### Step 2 — Find Your COM Port Numbers

You need to know which COM port each device uses.

1. Press `Windows + X` → click **Device Manager**
2. Expand **"Ports (COM & LPT)"**
3. Look for your devices — they'll say something like:
   - `USB Serial Port (COM3)` → Arduino KBM
   - `USB Serial Port (COM6)` → GIMX adapter
   - `USB Serial Port (COM8)` → Relay board
4. Write down those numbers — you'll need them in the next step

> 💡 **Tip:** Plug in each device one at a time to see which COM port appears.

### Step 3 — Update Hardware Config

Open `config/hardware_config.yaml` in any text editor (Notepad is fine):

```yaml
gimx:
  host: "127.0.0.1"
  port_c1: 51914        # Leave these as-is
  port_c2: 51915
  com_port: "COM6"      # ← Change to YOUR GIMX COM port

serial_ports:
  relay:
    port: "COM8"        # ← Change to YOUR relay board COM port
    baud_rate: 9600
  arduino_kbm:
    port: "COM3"        # ← Change to YOUR Arduino COM port
    baud_rate: 115200

camera:
  device_index: 0       # ← Try 0 first. If screen is blank, try 1 or 2
```

> 💡 **Not sure about the camera index?** Run this quick test:
> ```python
> import cv2
> for i in range(5):
>     cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
>     if cap.isOpened():
>         print(f"Camera found at index {i}")
>         cap.release()
> ```

---

## 🚀 Running the Tests

Open Command Prompt **inside** the `Automation_V4_Agent` folder.

### Check Everything Is Configured

```cmd
python main.py --model-info
```

You should see something like:
```
🧠 LLM Configuration:
  Primary model  : gpt-4o
  Fallback model : claude-3-5-sonnet-20241022
  Provider       : openai
  Temperature    : 0.1
  Max tokens     : 2048
```

If you see an error about missing API keys, go back to Step 1 of Configuration.

### Run a Single Game (Recommended for First Try)

```cmd
python main.py --games Celeste
```

This will:
1. Launch the AI agent
2. Navigate to Celeste on the Xbox
3. Verify the game loads
4. Run basic menu tests
5. Quit back to home
6. Save a report in the `reports/` folder

### Run Multiple Specific Games

```cmd
python main.py --games Celeste "Hollow Knight" "Sea of Stars"
```

> ⚠️ **Use quotes around game names that have spaces.**

### Run All 19 Games

```cmd
python main.py
```

This is the full test suite. Allow **several hours** to complete.

### Test on Console 2

```cmd
python main.py --console 2
```

---

## 📋 All Commands (Quick Reference)

```cmd
# List all available games
python main.py --list

# Show AI model configuration
python main.py --model-info

# Run all games (default: GPT-4o, console 1)
python main.py

# Run specific games
python main.py --games "Game Name 1" "Game Name 2"

# Use Claude Sonnet instead of GPT-4o
python main.py --model claude-3-5-sonnet-20241022

# Use a cheaper/faster model
python main.py --model gpt-4o-mini

# Target console 2
python main.py --console 2

# Change max retries per game (default: 2)
python main.py --max-retries 3

# Combine options
python main.py --games Celeste --model claude-3-5-sonnet-20241022 --console 1
```

---

## 📂 Where Are My Reports?

After a test run, reports are saved in:

```
Automation_V4_Agent/
└── reports/
    └── TestReport_20260807_182500.docx   ← Word document with results
```

Open it with Microsoft Word. It contains:
- A table with every game tested
- PASS (green) / FAIL (red) for each step
- Pass rate percentage at the bottom

---

## 📁 Project Structure (What Each Folder Does)

```
Automation_V4_Agent/
│
├── main.py                   ← START HERE: run this to start testing
├── requirements.txt          ← Python packages list
├── .env.example              ← Copy this to .env and add your API key
│
├── config/                   ← All settings files (edit these for your hardware)
│   ├── hardware_config.yaml  ← COM ports, camera, GIMX settings
│   ├── llm_config.yaml       ← AI model settings (GPT-4o / Claude)
│   ├── game_config.yaml      ← Game names, timeouts
│   └── ocr_regions.yaml      ← Where to read text on screen
│
├── hardware/                 ← Code that talks to physical devices
│   ├── gimx_controller.py    ← Sends button presses to Xbox via GIMX
│   ├── uart_serial.py        ← Talks to Arduino and relay board
│   └── video_capture.py      ← Captures video from AVerMedia card
│
├── vision/                   ← Code that "sees" the screen
│   ├── pattern_match.py      ← Checks if correct screen is showing
│   ├── ocr_engine.py         ← Reads text from screenshots
│   └── image_utils.py        ← Image helper functions
│
├── agents/                   ← AI agent code (the "brain")
│   ├── llm_factory.py        ← Creates the LiteLLM AI model
│   ├── agent_executor.py     ← ReAct agent that decides what to do
│   ├── controller_agent.py   ← AI tool: press Xbox buttons
│   ├── vision_agent.py       ← AI tool: verify screen content
│   ├── serial_agent.py       ← AI tool: trigger relay/Arduino
│   └── report_agent.py       ← AI tool: log test results
│
├── graphs/                   ← LangGraph workflow (the "plan")
│   ├── test_execution_graph.py  ← Main workflow: launch→test→quit→report
│   ├── game_launch_graph.py     ← Sub-flow: how to launch a game
│   └── verification_graph.py   ← Sub-flow: how to verify a screen
│
├── game_scripts/             ← One file per game with test steps
│   ├── base_game.py          ← Template all games inherit from
│   ├── celeste.py
│   ├── gears5.py
│   ├── hollow_knight.py
│   └── sea_of_stars.py
│
├── reporting/
│   └── report_generator.py   ← Creates the Word document report
│
├── utils/
│   ├── logger.py             ← Saves logs to the logs/ folder
│   └── helpers.py            ← Shared helper functions
│
└── logs/                     ← Log files created during test runs
```

---

## ❓ Troubleshooting

### ❌ `ModuleNotFoundError: No module named 'langchain'`
You haven't installed the packages yet. Run:
```cmd
pip install -r requirements.txt
```

### ❌ `ModuleNotFoundError: No module named 'cv2'`
OpenCV isn't installed. Run:
```cmd
pip install opencv-python
```

### ❌ `TesseractNotFoundError`
Tesseract OCR isn't installed or isn't in the right place. Make sure it's installed at:
`C:\Program Files\Tesseract-OCR\tesseract.exe`

### ❌ `AuthenticationError: Invalid API key`
Your API key in `.env` is wrong or missing. Double-check:
1. The file is named `.env` (not `.env.example` or `.env.txt`)
2. The key starts with `sk-` (OpenAI) or `sk-ant-` (Anthropic)
3. There are no spaces around the `=` sign

### ❌ `Serial port COM3 not found`
The Arduino COM port is wrong. Check Device Manager and update `config/hardware_config.yaml`.

### ❌ `GIMX not responding` or controller not working
1. Make sure GIMX adapter is plugged in
2. Check the COM port in `hardware_config.yaml` matches what Device Manager shows
3. The Python script auto-starts GIMX — make sure `gimx.exe` path is correct in the config

### ❌ `Camera / AVerMedia capture card not found`
Try different `device_index` values (0, 1, 2) in `hardware_config.yaml` until you see video.

### ❌ Test runs but FAIL on every game
The icon images for pattern matching may be missing. Check the `vision/icons/` folder has `.png` reference images for each game screen.

---

## 🔬 Technology Stack

| What | V3 (Old — PowerShell + DLLs) | V4 (New — Python + AI) |
|---|---|---|
| **Language** | PowerShell + C# | Python 3.11+ |
| **Controller** | `System.Net.Sockets` UDP | `socket` module |
| **Serial/UART** | `Hcl.eDAT.SerialCommunication.dll` | `pyserial` |
| **Screen Capture** | `AForge.Video.DirectShow.dll` | `opencv-python` (DirectShow) |
| **Pattern Match** | `Emgu.CV` (OpenCV .NET) | `cv2.matchTemplate()` |
| **OCR** | `Hcl.eDAT.OCR.dll` + `libtesseract400.dll` | `pytesseract` |
| **Report** | `Hcl.eDAT.WordReport.dll` | `python-docx` |
| **Orchestration** | PowerShell scripting | `langgraph` state machine |
| **AI Brain** | ❌ None | `litellm` → GPT-4o / Claude Sonnet |
| **Test Logic** | Hardcoded if/else | LangChain ReAct agent |

---

## 💡 Tips for Beginners

1. **Start with one game** before running all 19. Use `--games Celeste` first.
2. **Watch the logs** in real time — they appear in the terminal window while tests run.
3. **Check `logs/` folder** after a run for detailed debug information.
4. **GPT-4o-mini** is cheaper than GPT-4o if you're testing — use `--model gpt-4o-mini`.
5. **COM port numbers change** when you unplug/replug devices. If something stops working, check Device Manager again.
6. **The AI is adaptive** — if it can't find a button, it retries up to 2 times automatically.

---

## 🆘 Still Stuck?

Look at the log file in `logs/automation_v4_YYYY-MM-DD.log` — it has detailed step-by-step information about what went wrong, including the exact error message and which line of code caused it.
