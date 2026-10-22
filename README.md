# ♻️ NEONCYCLE — Real-Time Circular Economy & AI Scrap Exchange Platform

**NEONCYCLE** is a full-stack circular economy web application built with **Python (Django)**, **SQLite**, **Bootstrap 5.3**, and **Chart.js** featuring a **Neon Gen-Z Dark UI**. It transforms unorganized doorstep scrap collection into a transparent, real-time commodity exchange connecting **Households**, **Collector Riders**, **Recycling Hubs**, and **Admin ("God-Mode")**.

---

## 🚀 Key Features

1. **📈 Live Scrap Stock Exchange Ticker**
   - Continuously scrolling top marquee polling `/api/live-ticker/` every 3 seconds.
   - Displays live `₹/kg` prices and `▲/▼ %` market momentum across 5 core waste categories (`Plastic (PET)`, `E-Waste`, `Metal & Copper`, `Paper & Cardboard`, `Glass Bottles`).

2. **🧠 AI Engine #1: 7-Day Scrap Price Forecaster ("Hold or Sell" Advisor)**
   - Analyzes real-time SQLite market supply (`CollectionOrder`), active factory demand & bonus bids (`RecyclerDemand`), and ticker momentum (`GarbagePrice.change_pct`).
   - Plots a 7-day price curve (`Today` → `Day +7`) on an interactive **Chart.js** line graph and tells households whether to **`HOLD FOR X DAYS`** or **`SELL TODAY`** with exact extra profit calculations in `₹`.

3. **⚖️ AI Engine #2: Smart-Scale Fraud & Anomaly Detector**
   - Guards against weight tampering when Collector Riders weigh waste on their digital scale.
   - Automatically calculates $\text{Variance \%} = \frac{\text{Actual Weight} - \text{Estimated Weight}}{\text{Estimated Weight}} \times 100$.
   - Flags any deviation beyond **$\pm 40\%$** in real time on the Rider's terminal and logs a red fraud alert in the **Admin God-Mode Audit Monitor** (detecting *Payout Inflation* $>+40\%$ or *Rider Skimming* $<-40\%$).

4. **🔄 4 Connected Role Portals & Swiggy/Zomato-Style Live Order Tracker**
   - **Household (`/household/`)**: Check AI 7-Day price forecasts, book doorstep pickups, track orders across 4 live stages (`1. Requested` → `2. Rider Assigned` → `3. Weighed & Paid` → `4. Recycled`), and track wallet earnings + $\text{CO}_2$ & Trees Saved.
   - **Collector Rider (`/collector/`)**: Toggle Online/Offline status, accept nearby pending orders, verify weight on the AI Smart-Scale, trigger instant household payouts, and earn a **20% commission**.
   - **Recycler Hub (`/recycler/`)**: Post raw material demands with bonus rates, recycle incoming collector batches, and sell recycled pellets/products to B2B manufacturers.
   - **Admin God-Mode (`/admin-panel/`)**: Update live scrap prices, add new waste categories, view system KPIs & Chart.js price graphs, inspect all users, and audit flagged transactions in the **AI Scale Fraud Monitor**.

---

## 🛠️ Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Frontend** | HTML5, CSS3, JavaScript (ES6 `fetch` API), Bootstrap 5.3, Bootstrap Icons |
| **Data Visualization** | Chart.js 4.4 (7-Day AI Forecast Line Graph & Admin Live Price Bar Graph) |
| **Backend** | Python 3, Django (MVT Architecture) |
| **AI & Analytics** | Python Supply–Demand Regression Forecaster (`core/ai_scanner.py`) & Smart-Scale Anomaly Guardrail (`core/models.py`) |
| **Database** | SQLite 3 (`db.sqlite3`) |

---

## 📂 Project Folder Structure

```text
neoncycle_project/
├── manage.py                      # Django CLI utility
├── db.sqlite3                     # SQLite relational database
├── requirements.txt               # Python dependencies
├── README.md                      # Project documentation
├── neoncycle/                     # Project configuration package
│   ├── settings.py                # App config, SQLite setup, Templates path
│   ├── urls.py                    # Root URL routing
│   └── wsgi.py / asgi.py
└── core/                          # Main application package
    ├── models.py                  # 5 SQLite tables + AI Scale Fraud properties
    ├── ai_scanner.py              # AI 7-Day Scrap Price Forecaster engine
    ├── views.py                   # Role controllers, Auth logic, & JSON APIs
    ├── urls.py                    # App URL endpoints
    ├── admin.py                   # Django Admin registration
    └── templates/core/
        ├── base.html              # Master Neon UI layout + Live Stock Ticker
        ├── login.html             # Login & Register toggle card with Role selector
        ├── household.html         # Household Portal + AI 7-Day Forecaster Chart
        ├── collector.html         # Collector Rider Portal + AI Smart-Scale Guardrail
        ├── recycler.html          # Recycler Hub Portal + B2B Marketplace
        └── admin_panel.html       # Admin God-Mode + AI Scale Fraud Audit Monitor
```

---

## ⚡ How to Clone & Run on Your Computer (Step-by-Step for Teammates)

### 1. Clone the Repository
Open **Terminal** (Mac/Linux) or **Command Prompt / PowerShell / Git Bash** (Windows) and run:
```bash
git clone https://github.com/nafees2007/NeonCycle.git
cd NeonCycle
```

### 2. Create & Activate a Virtual Environment
**On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```
### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run Database Migrations & Start the Live Server
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

### 5. Open in Browser
Open **`http://127.0.0.1:8000/`** in your browser!

---

## 🧪 How to Test All 4 Roles End-to-End

1. **Recycler (`RECYCLER`)**: Register/Login as **Recycler Hub** → Post a demand for `500 kg` of `Plastic (PET)` at `₹55/kg`.
2. **Household (`HOUSEHOLD`)**: Logout & Login as **Household** → Select `Plastic (PET)` and `5.0 kg` to see the **AI 7-Day Price Forecaster** recommend holding/selling → Click **Lock Today's Rate & Request Pickup**.
3. **Collector (`COLLECTOR`)**: Logout & Login as **Collector Rider** → Click **Accept** on the order → Enter `9.0 kg` in the scale box to test the live **AI Scale Fraud Alert (`+80%`)** → Click **Verify & Pay**.
4. **Admin (`ADMIN`)**: Logout & Login as **Admin God-Mode** → Update any scrap price live and scroll down to **4. AI Scale Fraud & Anomaly Audit Monitor** to see the flagged order highlighted in red.
