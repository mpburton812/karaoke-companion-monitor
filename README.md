# Karaoke Companion Monitor

A modern Python GUI application to monitor the health, system resources, and user activity of the [Karaoke Companion](https://github.com/mpburton812/karaoke) React application.

## Features

- **Real-time Database Health:** Monitor connection status and latency to your LibSQL/Turso database.
- **System Resource Tracking:** Live dashboard for CPU and RAM usage.
- **User Statistics:** Comprehensive table showing user activity, song counts, and venue counts.
- **Log Tailing:** View local application logs in real-time.
- **Recent Activity:** Track the latest performances and upcoming songs from setlists.

## Tech Stack

- **Python 3.10+**
- **GUI:** [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)
- **Database:** `libsql-client`
- **System Metrics:** `psutil`
- **Environment:** `python-dotenv`

## Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/mpburton812/karaoke-companion-monitor.git
   cd karaoke-companion-monitor
   ```

2. **Install dependencies:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure Environment:**
   Create a `.env` file based on `.env.template`:
   ```env
   LIBSQL_URL=libsql://your-database.turso.io
   LIBSQL_AUTH_TOKEN=your-token
   LOG_FILE_PATH=C:/path/to/your/app.log
   POLLING_INTERVAL_SECONDS=5
   ```

4. **Run the application:**
   ```bash
   python main.py
   ```

## Development

The application is structured into three main modules:
- `db.py`: Handles all asynchronous database interactions.
- `monitor_engine.py`: Manages system metrics and log file reading.
- `main.py`: The CustomTkinter GUI implementation and event loop.
