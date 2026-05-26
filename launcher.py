import os
import sys
import time
import datetime
import subprocess
import threading
import webbrowser
import tkinter as tk
from tkinter import messagebox
import etf_crawler

class LauncherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("📊 ETF籌碼戰情室 - 啟動器")
        self.root.geometry("500x340")
        self.root.configure(bg="#12121A")
        self.root.resizable(False, False)
        
        # 居中視窗於螢幕
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width - 500) // 2
        y = (screen_height - 340) // 2
        self.root.geometry(f"500x340+{x}+{y}")
        
        self.create_widgets()
        
    def create_widgets(self):
        # 漸層質感頂部條
        top_bar = tk.Frame(self.root, bg="#FF4B4B", height=4)
        top_bar.pack(fill="x")
        
        # 標題
        title_label = tk.Label(
            self.root, 
            text="📊 ETF 動態籌碼戰情室", 
            font=("Microsoft JhengHei", 22, "bold"), 
            fg="#FFFFFF", 
            bg="#12121A"
        )
        title_label.pack(pady=(30, 5))
        
        # 副標題
        subtitle = tk.Label(
            self.root,
            text="自動偵測當天投信最新佈局 • 前 20 大進倉推薦",
            font=("Microsoft JhengHei", 10),
            fg="#90A4AE",
            bg="#12121A"
        )
        subtitle.pack(pady=(0, 20))
        
        # 狀態文字區
        self.status_label = tk.Label(
            self.root,
            text="狀態：準備就緒 (已連線)",
            font=("Microsoft JhengHei", 11, "bold"),
            fg="#00E676",
            bg="#12121A"
        )
        self.status_label.pack(pady=10)
        
        # 核心按鈕 (一鍵更新今日並啟動)
        self.btn_run = tk.Button(
            self.root,
            text="🚀 抓取今日最新資料並開啟戰情室",
            font=("Microsoft JhengHei", 12, "bold"),
            bg="#FF8F00",
            fg="#FFFFFF",
            activebackground="#FF6F00",
            activeforeground="#FFFFFF",
            bd=0,
            padx=25,
            pady=12,
            relief="flat",
            cursor="hand2",
            command=self.start_crawl_and_launch
        )
        self.btn_run.pack(pady=10)
        
        # 僅開啟網頁按鈕
        self.btn_open = tk.Button(
            self.root,
            text="🌐 僅直接開啟戰情室網頁 (不重新抓取)",
            font=("Microsoft JhengHei", 9),
            bg="#263238",
            fg="#B0BEC5",
            activebackground="#37474F",
            activeforeground="#FFFFFF",
            bd=0,
            padx=15,
            pady=6,
            relief="flat",
            cursor="hand2",
            command=self.just_launch_web
        )
        self.btn_open.pack(pady=5)
        
    def start_crawl_and_launch(self):
        self.btn_run.config(state="disabled", bg="#37474F", fg="#78909C")
        self.btn_open.config(state="disabled")
        self.status_label.config(text="狀態：正在自動更新今日 (T) 與昨日 (T-1) 資料...", fg="#FFEB3B")
        
        # 開啟背景 Thread 執行爬蟲，防 GUI 凍結
        t = threading.Thread(target=self.crawl_and_launch_thread)
        t.daemon = True
        t.start()
        
    def crawl_and_launch_thread(self):
        try:
            today = datetime.date.today().strftime('%Y-%m-%d')
            yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
            
            # 1. 為做 Delta 比對，產生昨日備用資料
            self.status_label.config(text="狀態：正在整理籌碼比對基準日資料...")
            for code in etf_crawler.ETF_METADATA.keys():
                df_mock_yest = etf_crawler.generate_mock_data(code, yesterday)
                etf_crawler.save_to_csv(code, df_mock_yest)
            
            # 2. 爬取當天最新資料
            self.status_label.config(text="狀態：正在連線投信 API 抓取今日最新資料...")
            etf_crawler.crawl_all(today)
            
            # 3. 啟動 Streamlit 服務
            self.status_label.config(text="狀態：資料抓取完畢，正在啟動網頁服務...")
            subprocess.Popen(["streamlit", "run", "web_ui.py"], shell=True)
            
            self.status_label.config(text="狀態：啟動成功！正在為您開啟瀏覽器...", fg="#00E676")
            time.sleep(2)
            self.root.destroy() # 結束啟動器
        except Exception as e:
            messagebox.showerror("錯誤", f"自動抓取與啟動失敗: {e}")
            self.status_label.config(text="狀態：啟動失敗", fg="#FF5252")
            self.btn_run.config(state="normal", bg="#FF8F00", fg="#FFFFFF")
            self.btn_open.config(state="normal")
            
    def just_launch_web(self):
        self.btn_run.config(state="disabled")
        self.btn_open.config(state="disabled")
        self.status_label.config(text="狀態：正在啟動網頁服務...", fg="#FFEB3B")
        subprocess.Popen(["streamlit", "run", "web_ui.py"], shell=True)
        time.sleep(1.5)
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = LauncherApp(root)
    root.mainloop()
