#include <Arduino.h>

// --- SETTINGS ---
const int fanPin      = 4;
const int pwmChannel  = 0;
const int freq        = 25000;  // 25kHz = silent operation
const int resolution  = 8;     // 0-255 steps

// Tune PWM_START for your specific fan (run calibration sketch first)
const int PWM_START   = 90;    // Minimum PWM that actually spins the fan
const int PWM_MAX     = 255;   // Full throttle
const int FOCUS_FLOOR = 20;    // Below this % = fan off

void setup() {
  Serial.begin(115200);
  ledcSetup(pwmChannel, freq, resolution);
  ledcAttachPin(fanPin, pwmChannel);
  ledcWrite(pwmChannel, 0);   // Fan OFF on boot
  Serial.println("ESP32 Ready. Waiting for Focus Score...");
}

void loop() {
  if (Serial.available() > 0) {
    int focusPercent = Serial.read();  // Single raw byte: 0–100 from Python

    int dutyCycle;

    if (focusPercent < FOCUS_FLOOR) {
      // Below threshold: hard off
      dutyCycle = 0;
    } else {
      // Map FOCUS_FLOOR–100 → PWM_START–PWM_MAX
      // Guarantees fan always spins when focus is detected
      dutyCycle = map(focusPercent, FOCUS_FLOOR, 100, PWM_START, PWM_MAX);
    }

    ledcWrite(pwmChannel, dutyCycle);

    // Debug output
    Serial.print("Received Focus: ");
    Serial.print(focusPercent);
    Serial.print("% -> PWM: ");
    Serial.println(dutyCycle);
  }
}