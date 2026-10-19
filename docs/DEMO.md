# VitaSense AI — Demonstration & Mobile Access Guide (`docs/DEMO.md`)

This guide provides instructions for launching the VitaSense AI application on a workstation or laptop and streaming live telemetry and benchmarks to a mobile smartphone over the local area network (LAN).

---

## 1. System Overview & Core Modules
1. **Signal Lab (Replay Simulator):**
   - Mode: `"REPLAY: public dataset, not live"`.
   - Streams synchronized wrist-PPG HR, gold-standard ECG reference HR, rule-based trust scores ($S_{\text{trust}}$), and dynamic ENMO kinematics for subjects $S_1$ to $S_{15}$.
   - Interactive fault injection module toggles faults $F_1$ to $F_7$ (strictly labelled `"SYNTHETIC"`) and demonstrates real-time trust degradation and alert suppression.
   - Reads strictly from `data/processed` caches; zero model training at runtime.
2. **Benchmark Dashboard:**
   - Visualizes empirical findings transcribed directly from `docs/RESULTS_SUMMARY.md`:
     - Executive summary cards (including `"H1 not supported"` prominently displayed).
     - Combined metric tables across all 4 experimental conditions.
     - Pre-specified paired comparisons between Arm 3b and Arm 3a (with 95% bootstrap CIs and Hodges-Lehmann median diffs).
     - Per-fault disaggregated false alert rates ($F_1\text{--}F_6$) with sample count validation.
3. **Safety-Aligned AI Companion (`POST /api/assistant`):**
   - Conversational telemetry explainer.
   - Strictly enforces intent routing: greetings return plain conversational text (no cards); medical diagnosis requests are refused; telemetry cards render **ONLY** upon explicit user request.
4. **Progressive Web App (PWA):**
   - Fully responsive mobile layout with touch-friendly navigation, standalone display mode, and manifest integration.

---

## 2. Prerequisites
- **Same Local Network:** Ensure your laptop and mobile phone are connected to the same Wi-Fi network (or mobile hotspot).
- **Python 3.10+:** Dependencies installed (`fastapi`, `uvicorn`, `numpy`, `python-dotenv`).
- **Node.js 18+:** Vite and React dependencies installed (`npm install`).

---

## 3. Step-by-Step Launch Instructions

### Step 1: Start the Backend FastAPI Server
Open a terminal in the project root directory and start the API server binding to all network interfaces (`0.0.0.0`):

```bash
# Windows PowerShell / CMD
python -m uvicorn vitasense.api.app:app --host 0.0.0.0 --port 8000 --reload
```

- Verify locally in your desktop browser: [http://localhost:8000/api/health](http://localhost:8000/api/health)
- Output should return `{"status": "healthy", "service": "VitaSense AI Backend", "notice": "REPLAY: public dataset, not live"}`.

### Step 2: Start the Vite Development Server
Open a second terminal window in the project root directory and run the frontend with network host binding:

```bash
# Windows PowerShell / CMD
npm run dev -- --host 0.0.0.0
```

- The terminal will display your Network URL, for example:
  ```
  VITE v5.4.21  ready in 240 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: http://192.168.1.145:5173/
  ```

### Step 3: Find Your Laptop's Local IP Address
If Vite does not print the Network address, look it up manually:

- **Windows:**
  ```powershell
  ipconfig
  ```
  Look for your active Wi-Fi adapter under **IPv4 Address** (typically `192.168.1.X` or `10.0.0.X`).
- **macOS / Linux:**
  ```bash
  ifconfig | grep "inet "
  ```

---

## 4. Opening on Your Mobile Phone

1. Connect your phone's Wi-Fi to the same local router or laptop hotspot.
2. Open your preferred mobile browser:
   - **iOS:** Safari
   - **Android:** Google Chrome
3. In the address bar, type your laptop's network URL:
   ```
   http://<YOUR_LAPTOP_IP>:5173
   ```
   *(Example: `http://192.168.1.145:5173`)*
4. The VitaSense AI dashboard will load with responsive mobile navigation pinned to the bottom.

---

## 5. Installing as a Standalone PWA App

VitaSense includes a full web app manifest (`public/manifest.json`) and high-resolution vector icons:

- **iOS (Safari):**
  1. Tap the **Share** icon at the bottom of the Safari toolbar.
  2. Scroll down and tap **Add to Home Screen**.
  3. Confirm the name *"VitaSense"*. An icon will appear on your iOS home screen, launching full-screen without browser URL bars.
- **Android (Chrome):**
  1. Tap the **Three Dots (⋮)** menu in Chrome.
  2. Tap **Install app** or **Add to Home screen**.
  3. Confirm installation. The standalone PWA will be added to your app drawer.

---

## 6. Troubleshooting Local Network Access

1. **Connection Timed Out on Mobile:**
   - Windows Defender Firewall may block inbound connections on port 5173 or 8000.
   - Quick fix in PowerShell (Admin):
     ```powershell
     New-NetFirewallRule -DisplayName "VitaSense Dev" -Direction Inbound -LocalPort 5173,8000 -Protocol TCP -Action Allow
     ```
2. **API Calls Fail on Mobile:**
   - The Vite configuration (`vite.config.ts`) includes a proxy for `/api` pointing to `http://127.0.0.1:8000`. Ensure the backend server is running in Terminal 1.
3. **Public Wi-Fi / AP Isolation:**
   - Some university or corporate Wi-Fi networks block device-to-device communication (AP Isolation). In that case, enable a personal hotspot on your mobile phone and connect your laptop to the hotspot.
