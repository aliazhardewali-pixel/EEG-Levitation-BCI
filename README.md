# EEG-Based Aerodynamic Levitation BCI

Control a levitating ping-pong ball using your brain focus levels.
Built with NeuroSky MindWave Mobile 2 + ESP32 + Python.

---

## How It Works

The EEG headset reads your brainwaves via Bluetooth.
Python calculates your focus score and sends it to the ESP32 via USB.
The ESP32 controls the fan speed using PWM.
Higher focus = faster fan = ball levitates higher.

---

## Hardware Required

- NeuroSky MindWave Mobile 2 headset
- ESP32-WROOM-32
- IRLZ44N MOSFET
- 1N5408 flyback diode
- 220Ω resistor
- 80mm DC fan
- 20–25V DC power supply
- 3D-printed nozzle
- 2.7g ping-pong ball

---

## Setup Instructions

### Step 1 — Flash the ESP32

1. Install [PlatformIO](https://platformio.org/) in VS Code
2. Open the project folder
3. Place `design day.cpp` inside the `src/` folder
4. Connect your ESP32 via USB
5. Click the **Upload** button (arrow icon) in VS Code
6. Wait for it to say **SUCCESS**

### Step 2 — Run the Python Script

1. Install Python 3 from [python.org](https://python.org)
2. Install required libraries by running this in your terminal:
```

pip install pyserial numpy matplotlib

```
3. Open `design day.py` in VS Code
4. Change these two lines to match your setup:
```

com_port = 'COM8'    # Your MindWave Bluetooth port
esp32_port = 'COM5'  # Your ESP32 USB port

```
5. Run the script — the dashboard window will open

### Step 3 — Use It

1. Wear the MindWave headset
2. Wait for **SIGNAL: PERFECT** to appear on the dashboard
3. Concentrate — the ball will rise as your focus increases
4. Relax — the ball will lower

---

## Finding Your COM Ports (Windows)

1. Open **Device Manager**
2. Expand **Ports (COM & LPT)**
3. MindWave will appear as a Bluetooth device
4. ESP32 will appear as a USB Serial device

---

## Built By

Ali Azhar, Mansour Azad
Department of Biomedical Engineering
University of Duhok
Supervisor: Dr. Soleen Jaladet Al-Sofi
```
