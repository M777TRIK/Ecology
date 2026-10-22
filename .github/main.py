import threading, time, json, os, requests, numpy as np, pandas as pd
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from plyer import notification

BASE = "https://api.bybit.com"
STATE_FILE = "seen_signals.json"

# ================= ЛОГИКА СТРАТЕГИИ =================
def get_symbols():
    try:
        r = requests.get(f"{BASE}/v5/market/instruments-info", params={"category": "linear"}, timeout=10).json()
        return [s["symbol"] for s in r["result"]["list"] if s["quoteCoin"] == "USDT" and s["status"] == "Trading"]
    except: 
        return ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

def get_klines(symbol, interval="15", limit=200):
    r = requests.get(f"{BASE}/v5/market/kline", params={"category": "linear", "symbol": symbol, "interval": interval, "limit": limit}, timeout=10).json()
    df = pd.DataFrame(r["result"]["list"], columns=["ts","open","high","low","close","volume","turnover"])
    df = df.astype({"open":float,"high":float,"low":float,"close":float})
    return df.iloc[::-1].reset_index(drop=True)

def pivots(high, low, left=5, right=5):
    ph = np.zeros(len(high), dtype=bool)
    pl = np.zeros(len(low), dtype=bool)
    for i in range(left, len(high) - right):
        if high[i] == max(high[i-left:i+right+1]): ph[i] = True
        if low[i] == min(low[i-left:i+right+1]): pl[i] = True
    return ph, pl

def build_setup(symbol, df):
    high, low, close = df["high"].to_numpy(), df["low"].to_numpy(), df["close"].to_numpy()
    ph, pl = pivots(high, low)
    swings = []
    for i in range(len(high)):
        if ph[i]: swings.append((i, high[i], 'H'))
        elif pl[i]: swings.append((i, low[i], 'L'))
    
    if len(swings) < 2: return None
    
    last = swings[-1]
    if last[2] == 'L':
        prev_high = next((s for s in reversed(swings[:-1]) if s[2]=='H'), None)
        if prev_high and close[-1] > prev_high[1]:
            p0, p1 = last[1], prev_high[1]
            return {"symbol": symbol, "side": "bull", "entry": p0+(p1-p0)*0.618, "sl": p0, "tp1": p0+(p1-p0)*2.0}
    else:
        prev_low = next((s for s in reversed(swings[:-1]) if s[2]=='L'), None)
        if prev_low and close[-1] < prev_low[1]:
            p0, p1 = last[1], prev_low[1]
            return {"symbol": symbol, "side": "bear", "entry": p0+(p1-p0)*0.618, "sl": p0, "tp1": p0+(p1-p0)*2.0}
    return None

def notify(title, message):
    try: 
        notification.notify(title=title, message=message, timeout=10)
    except: 
        pass

# ================= ИНТЕРФЕЙС ПРИЛОЖЕНИЯ =================
def load_seen():
    if os.path.exists(STATE_FILE): return set(json.load(open(STATE_FILE)))
    return set()

def save_seen(s): 
    json.dump(list(s), open(STATE_FILE, "w"))

class ScannerApp(App):
    def build(self):
        self.seen = load_seen()
        root = BoxLayout(orientation="vertical", padding=10, spacing=10)
        
        self.status = Label(text="Готов к сканированию", size_hint=(1, 0.1))
        root.add_widget(self.status)
        
        self.btn = Button(text="▶ Запустить сканер", size_hint=(1, 0.15))
        self.btn.bind(on_press=self.toggle_scan)
        root.add_widget(self.btn)
        
        self.scroll = ScrollView()
        self.log = BoxLayout(orientation="vertical", size_hint_y=None, spacing=5)
        self.log.bind(minimum_height=self.log.setter("height"))
        self.scroll.add_widget(self.log)
        root.add_widget(self.scroll)
        
        return root

    def toggle_scan(self, *_):
        if getattr(self, "running", False):
            self.running = False
            self.btn.text = "▶ Запустить сканер"
            return
        self.running = True
        self.btn.text = "⏹ Остановить"
        threading.Thread(target=self.scan_loop, daemon=True).start()

    def scan_loop(self):
        Clock.schedule_once(lambda *_: setattr(self.status, "text", "Загружаю список пар..."))
        symbols = get_symbols()
        while self.running:
            Clock.schedule_once(lambda *_: setattr(self.status, "text", f"Сканирую {len(symbols)} пар..."))
            for sym in symbols:
                if not self.running: break
                try:
                    df = get_klines(sym, "15", 200)
                    setup = build_setup(sym, df)
                    if setup:
                        key = f"{sym}_{setup['side']}_{int(df['ts'].iloc[-1])}"
                        if key not in self.seen:
                            self.seen.add(key)
                            save_seen(self.seen)
                            Clock.schedule_once(lambda dt, s=setup: self.add_row(s))
                            notify(f"{setup['side'].upper()} {setup['symbol']}", f"Entry: {setup['entry']:.4f}")
                except Exception as e: 
                    print(sym, e)
            time.sleep(60)

    def add_row(self, s):
        txt = f"[{s['symbol']}] {s['side'].upper()}\nEntry: {s['entry']:.4f} | SL: {s['sl']:.4f} | TP1: {s['tp1']:.4f}"
        lbl = Label(text=txt, size_hint_y=None, height=60, halign="left", valign="middle", font_size="14sp")
        lbl.bind(size=lambda *_: setattr(lbl, "text_size", lbl.size))
        self.log.add_widget(lbl)

if __name__ == "__main__":
    ScannerApp().run()
