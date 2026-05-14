import serial
import threading
import math
import csv
import os
import time
import logging
import random
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque
from datetime import datetime

# --- 1. CONFIGURATION ---
DEMO_MODE = False
com_port = 'COM8'
esp32_port = 'COM5'

BLINK_THRESHOLD = 800000
FOCUS_GOAL = 0.5
history_length = 50
SMOOTH_FACTOR = 0.15

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Initialize ESP32 Link
try:
    esp32_ser = serial.Serial(esp32_port, 115200, timeout=0.1)
    logging.info(f"SUCCESS: ESP32 Link established on {esp32_port}")
except Exception as e:
    logging.warning(f"ESP32 NOT FOUND: {e}. Fan control disabled.")
    esp32_ser = None

WAVE_COLORS = {
    'Delta': '#1f77b4', 'Theta': '#9467bd', 'L-Alpha': '#2ca02c',
    'H-Alpha': '#98df8a', 'L-Beta': '#ff7f0e', 'H-Beta': '#ffbb78',
    'L-Gamma': '#d62728', 'M-Gamma': '#ff9896'
}

data_lock = threading.Lock()
stop_event = threading.Event()
blink_count = 0
signal_quality = 200
headset_connected = False
waves = {name: deque([0.0]*history_length, maxlen=history_length) for name in WAVE_COLORS.keys()}
focus_history = deque([0.0]*history_length, maxlen=history_length)
target_vals = {name: 0.0 for name in WAVE_COLORS.keys()}
display_vals = {name: 0.0 for name in WAVE_COLORS.keys()}

# --- 2. DATA INGESTOR ---
def verify_checksum(payload, check):
    calc = (~sum(payload)) & 0xFF
    return calc == check

def reset_vals():
    with data_lock:
        for name in WAVE_COLORS.keys():
            target_vals[name] = 0.0

def ingest_data():
    global blink_count, signal_quality, headset_connected

    if DEMO_MODE:
        logging.info("SIMULATION ACTIVE: Generating synthetic brain data...")
        while not stop_event.is_set():
            time.sleep(0.5)
            with data_lock:
                signal_quality = 0
                for name in WAVE_COLORS.keys():
                    target_vals[name] = random.uniform(2.5, 5.5)
                    waves[name].append(target_vals[name])
        return

    csv_fn = "research_session.csv"

    while not stop_event.is_set():
        headset = None
        try:
            logging.info(f"Attempting to connect to headset on {com_port}...")
            headset = serial.Serial(com_port, 57600, timeout=1)
            headset_connected = True
            logging.info(f"Headset Connected: {com_port}")

            with open(csv_fn, mode='a', newline='') as f:
                writer = csv.writer(f)
                if os.stat(csv_fn).st_size == 0:
                    writer.writerow(['Timestamp'] + list(WAVE_COLORS.keys()) + ['Signal'])

                while not stop_event.is_set():
                    try:
                        b1 = headset.read(1)
                        if not b1:
                            raise serial.SerialTimeoutException("No data")
                        if b1 != b'\xaa':
                            continue
                        if headset.read(1) != b'\xaa':
                            continue

                        p_len_raw = headset.read(1)
                        if not p_len_raw:
                            continue
                        p_len = ord(p_len_raw)
                        payload = headset.read(p_len)
                        check = ord(headset.read(1))

                        if not verify_checksum(payload, check):
                            continue

                        i = 0
                        while i < len(payload):
                            code = payload[i]; i += 1
                            if code == 0x83:
                                i += 1
                                if i + 24 <= len(payload):
                                    data = payload[i:i+24]; i += 24
                                    raw = [(data[j] << 16 | data[j+1] << 8 | data[j+2]) for j in range(0, 24, 3)]
                                    with data_lock:
                                        if raw[0] > BLINK_THRESHOLD:
                                            blink_count += 1
                                        for idx, n in enumerate(WAVE_COLORS.keys()):
                                            target_vals[n] = math.log10(raw[idx] + 1)
                                            waves[n].append(target_vals[n])
                                    writer.writerow([datetime.now()] + raw + [signal_quality])
                                    f.flush()
                            elif code == 0x02:
                                with data_lock:
                                    signal_quality = payload[i]; i += 1
                            elif code >= 0x80:
                                i += payload[i] + 1
                            else:
                                i += 1

                    except Exception as e:
                        logging.warning(f"Headset signal lost: {e}")
                        break

        except Exception as e:
            logging.warning(f"Could not connect to headset: {e}")

        finally:
            headset_connected = False
            reset_vals()
            if esp32_ser and esp32_ser.is_open:
                esp32_ser.write(bytes([0]))
            if headset and headset.is_open:
                headset.close()
            if not stop_event.is_set():
                logging.info("Retrying headset connection in 3 seconds...")
                time.sleep(3)

threading.Thread(target=ingest_data, daemon=True).start()

# --- 3. UI SETUP ---
fig = plt.figure(figsize=(15, 9), facecolor='#0a0a0a')
plt.style.use('dark_background')

blink_txt = fig.text(0.2, 0.93, "BLINKS: 0", color='white', ha='center', weight='bold',
                     bbox=dict(facecolor='#d62728', alpha=0.5, edgecolor='none'))
sig_txt   = fig.text(0.5, 0.93, "SIGNAL: WAIT", color='white', ha='center', weight='bold',
                     bbox=dict(facecolor='orange', alpha=0.5, edgecolor='none'))
mode_txt  = fig.text(0.8, 0.93, "MODE: LIVE" if not DEMO_MODE else "MODE: DEMO",
                     color='cyan' if not DEMO_MODE else 'yellow', ha='center', weight='bold')

# Radar
ax_radar   = plt.subplot(221, polar=True, facecolor='#111111')
categories = list(WAVE_COLORS.keys())
angles     = np.linspace(0, 2*np.pi, len(categories), endpoint=False).tolist() + [0]
ax_radar.set_ylim(0, 7)
ax_radar.set_xticks(angles[:-1])
ax_radar.set_xticklabels(categories, color='white', size=8)
radar_line, = ax_radar.plot(angles, [0]*9, color='#00ffcc', lw=2.5)
radar_fill  = ax_radar.fill(angles, [0]*9, color='#00ffcc', alpha=0.2)[0]

# Timeline
ax_line = plt.subplot(222, facecolor='#111111')
lines   = {n: ax_line.plot(range(history_length), [0]*history_length,
           color=c, label=n, lw=1.5)[0] for n, c in WAVE_COLORS.items()}
ax_line.set_ylim(0, 7)
ax_line.legend(loc='upper left', fontsize='xx-small', ncol=2)

# Focus Trend
ax_focus    = plt.subplot(212, facecolor='#111111')
focus_line, = ax_focus.plot(range(history_length), [0]*history_length, color='#00ffcc', lw=3)
ax_focus.axhline(y=FOCUS_GOAL, color='yellow', linestyle='--', lw=1, alpha=0.6)
ax_focus.set_ylim(0, 1.2)
ax_focus.set_title("Quantitative Focus Trend", color='white')
focus_pct_txt = ax_focus.text(0.02, 1.05, "Focus: 0%", transform=ax_focus.transAxes,
                               color='#00ffcc', fontsize=14, weight='bold')

# --- 4. ANIMATION LOOP ---
def update(frame):
    with data_lock:
        l_blinks    = blink_count
        l_sig       = signal_quality
        l_targets   = target_vals.copy()
        l_waves     = {n: list(waves[n]) for n in categories}
        l_connected = headset_connected

    # Smooth interpolation
    for n in categories:
        display_vals[n] += (l_targets[n] - display_vals[n]) * SMOOTH_FACTOR

    # Update Radar
    r_vals = [display_vals[n] for n in categories] + [display_vals[categories[0]]]
    radar_line.set_ydata(r_vals)
    radar_fill.set_xy(np.column_stack([angles, r_vals]))

    # Update Timeline
    for n in categories:
        lines[n].set_ydata(l_waves[n])

    # Focus Calculation
    beta      = l_targets['L-Beta'] + l_targets['H-Beta']
    relax     = l_targets['L-Alpha'] + l_targets['H-Alpha'] + l_targets['Theta'] + 0.1
    raw_focus = beta / relax

    FOCUS_MIN = 0.4
    FOCUS_MAX = 0.7
    current_focus = (raw_focus - FOCUS_MIN) / (FOCUS_MAX - FOCUS_MIN)
    current_focus = max(0.0, min(current_focus, 1.0))

    # Send to ESP32
    if esp32_ser and esp32_ser.is_open:
        focus_byte = int(current_focus * 100)
        esp32_ser.write(bytes([focus_byte]))

    # Update Focus Trend
    focus_history.append(current_focus)
    focus_line.set_ydata(list(focus_history))
    focus_line.set_color('#00ffcc' if current_focus > FOCUS_GOAL else '#d62728')

    # Update focus % text
    focus_pct_txt.set_text(f"Focus: {int(current_focus * 100)}%")
    focus_pct_txt.set_color('#00ffcc' if current_focus > FOCUS_GOAL else '#d62728')

    # Update signal/blink UI
    blink_txt.set_text(f"BLINKS: {l_blinks}")

    if not l_connected:
        sig_txt.set_text("HEADSET: DISCONNECTED")
        sig_txt.get_bbox_patch().set_facecolor('#555555')
    elif l_sig == 0:
        sig_txt.set_text("SIGNAL: PERFECT")
        sig_txt.get_bbox_patch().set_facecolor('green')
    else:
        sig_txt.set_text("SIGNAL: ADJUSTING")
        sig_txt.get_bbox_patch().set_facecolor('red')

ani = animation.FuncAnimation(fig, update, interval=30, cache_frame_data=False)
fig.canvas.mpl_connect('close_event', lambda e: stop_event.set())
plt.tight_layout(rect=[0, 0.03, 1, 0.9])
plt.show()