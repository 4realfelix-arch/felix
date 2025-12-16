# Complete Module Standards - Single File Reference

Directory Structure:
module/
├── manifest.json          # Required metadata
├── main.py                # Entry point (module class)
├── ui/                    # Flyout applet assets
│   ├── index.html
│   ├── style.css
│   └── script.js
├── assets/                # Images, icons, etc.
└── requirements.txt       # Optional deps (if sandbox allows)

manifest.json:
{
  "name": "weather",
  "version": "1.0.0",
  "display_name": "Weather Flyout",
  "description": "Shows weather in a side panel",
  "author": "User",
  "icon": "assets/icon.png",
  "permissions": ["network", "storage"],
  "entry_point": "main.WeatherModule"
}

main.py (Module Class Standard):
class WeatherModule:
    metadata = {
        "name": "weather",
        "ui_panel": True
    }

    def __init__(self):
        self.ui = None

    def on_load(self, core):
        self.ui = core.create_flyout(
            title=self.metadata.get("display_name", "Panel"),
            html_path="ui/index.html"
        )

    def on_unload(self):
        if self.ui:
            self.ui.destroy()

    def can_handle(self, context) -> bool:
        return False  # Implement logic

    def handle(self, context) -> None:
        pass  # Modify response / use self.ui

    def on_ui_event(self, event):
        pass  # Optional JS bridge

Core API (via `core` in on_load):
- core.create_flyout(title, html_path, width?, height?) → UI object
- ui.update(data) → send JSON to flyout JS
- ui.close()
- core.request_permission(perm)
- core.storage.get/set(key, value)

UI Bridge:
Flyout JS uses window.postMessage() → core → module.on_ui_event()

Best Practices:
- Stateless preferred
- Graceful no-UI fallback
- Permission check before use
- Semantic versioning
- No direct core/DOM access



# weather-module.zip contents (save as text or recreate folder)

manifest.json
{
  "name": "weather",
  "version": "1.0.0",
  "display_name": "Weather Flyout",
  "description": "Displays current weather in a side panel",
  "author": "Dev",
  "icon": "assets/icon.png",
  "permissions": ["network"],
  "entry_point": "main.WeatherModule"
}

main.py
import json
import requests

class WeatherModule:
    metadata = {
        "name": "weather",
        "ui_panel": True
    }

    def __init__(self):
        self.ui = None
        self.api_key = "YOUR_OPENWEATHER_API_KEY"

    def on_load(self, core):
        self.core = core
        if "network" not in core.granted_permissions(self.metadata["name"]):
            return
        self.ui = core.create_flyout(
            title="Weather",
            html_path="ui/index.html",
            width=380,
            height=600
        )

    def on_unload(self):
        if self.ui:
            self.ui.destroy()

    def can_handle(self, context) -> bool:
        return any(word in context["input"].lower() for word in ["weather", "temperature", "forecast"])

    def handle(self, context) -> None:
        location = self.extract_location(context["input"]) or "London"
        weather = self.fetch_weather(location)
        if weather:
            text = f"{weather['desc']}, {weather['temp']}°C in {location}"
            context["response"] += text
            if self.ui:
                self.ui.update({
                    "location": location,
                    "temp": weather['temp'],
                    "desc": weather['desc'],
                    "icon": f"https://openweathermap.org/img/wn/{weather['icon']}@2x.png"
                })

    def extract_location(self, text):
        words = text.lower().split()
        if "in" in words:
            idx = words.index("in")
            return " ".join(words[idx+1:]) if idx+1 < len(words) else None
        return None

    def fetch_weather(self, location):
        url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={self.api_key}&units=metric"
        try:
            r = requests.get(url, timeout=5)
            data = r.json()
            if data["cod"] == 200:
                return {
                    "temp": round(data["main"]["temp"]),
                    "desc": data["weather"][0]["description"].capitalize(),
                    "icon": data["weather"][0]["icon"]
                }
        except:
            pass
        return None

    def on_ui_event(self, event):
        pass

ui/index.html
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Weather</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div id="content">
        <h2 id="location">Loading...</h2>
        <img id="icon" src="" alt="Weather icon">
        <p id="temp"></p>
        <p id="desc"></p>
    </div>
    <script>
        window.addEventListener('message', (e) => {
            const data = e.data;
            if (data.location) {
                document.getElementById('location').textContent = data.location;
                document.getElementById('temp').textContent = data.temp + '°C';
                document.getElementById('desc').textContent = data.desc;
                document.getElementById('icon').src = data.icon;
            }
        });
    </script>
</body>
</html>

ui/style.css
body { font-family: sans-serif; padding: 20px; background: #f0f0f0; }
#content { text-align: center; }
#icon { width: 100px; height: 100px; }
h2 { margin: 0; }
#temp { font-size: 48px; margin: 10px 0; }
#desc { font-size: 20px; color: #555; }