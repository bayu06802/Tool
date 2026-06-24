import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import requests
import threading
import time
import json
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import os
import sys
from datetime import datetime

class FacebookCommentChecker:
    def __init__(self, root):
        self.root = root
        self.root.title("Facebook Comment Checker Tools")
        self.root.geometry("900x700")
        self.root.resizable(True, True)
        
        # Variables
        self.url_var = tk.StringVar()
        self.tab_count_var = tk.StringVar(value="1")
        self.cookies = []
        self.is_running = False
        self.results = []
        
        self.setup_ui()
        self.load_cookies()
        
    def setup_ui(self):
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(main_frame, text="FACEBOOK COMMENT CHECKER", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=10)
        
        # URL Input
        ttk.Label(main_frame, text="URL Postingan:", font=('Arial', 11)).grid(row=1, column=0, sticky=tk.W, pady=5)
        url_entry = ttk.Entry(main_frame, textvariable=self.url_var, width=60)
        url_entry.grid(row=1, column=1, padx=5, pady=5)
        
        # Tab/Browser count
        ttk.Label(main_frame, text="Jumlah Tab:", font=('Arial', 11)).grid(row=2, column=0, sticky=tk.W, pady=5)
        tab_spinbox = ttk.Spinbox(main_frame, from_=1, to=10, textvariable=self.tab_count_var, width=10)
        tab_spinbox.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=3, pady=20)
        
        self.check_button = ttk.Button(button_frame, text="CEK KOMPENTAR", 
                                      command=self.start_check, width=20)
        self.check_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="STOP", 
                                     command=self.stop_check, width=20, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # Status
        self.status_label = ttk.Label(main_frame, text="Status: Siap", font=('Arial', 10))
        self.status_label.grid(row=4, column=0, columnspan=3, pady=5, sticky=tk.W)
        
        # Result display
        result_frame = ttk.LabelFrame(main_frame, text="Hasil Pengecekan", padding="10")
        result_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)
        
        self.result_text = scrolledtext.ScrolledText(result_frame, wrap=tk.WORD, width=80, height=20)
        self.result_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        # Status cookies
        cookie_status = ttk.Label(main_frame, text="Status Cookie: Memuat...", font=('Arial', 9))
        cookie_status.grid(row=7, column=0, columnspan=3, pady=5, sticky=tk.W)
        self.cookie_status = cookie_status
        
    def load_cookies(self):
        """Load cookies from GitHub"""
        try:
            self.status_label.config(text="Status: Memuat cookie dari GitHub...")
            response = requests.get('https://raw.githubusercontent.com/bayu06802/Lisensi/main/acc.txt', timeout=10)
            if response.status_code == 200:
                lines = response.text.strip().split('\n')
                self.cookies = []
                for line in lines:
                    if '|' in line:
                        parts = line.split('|')
                        if len(parts) >= 3:
                            # Format: email|password|cookie
                            cookie_data = {
                                'email': parts[0].strip(),
                                'password': parts[1].strip(),
                                'cookie': parts[2].strip()
                            }
                            self.cookies.append(cookie_data)
                
                self.cookie_status.config(text=f"Status Cookie: {len(self.cookies)} cookie berhasil dimuat")
                self.status_label.config(text="Status: Siap")
            else:
                self.cookie_status.config(text="Status Cookie: Gagal memuat cookie")
                self.status_label.config(text="Status: Error - Gagal memuat cookie")
        except Exception as e:
            self.cookie_status.config(text=f"Status Cookie: Error - {str(e)[:50]}")
            self.status_label.config(text="Status: Error")
    
    def get_comment_count(self, url, cookie):
        """Get comment count from Facebook post"""
        try:
            # Setup Chrome options
            chrome_options = Options()
            chrome_options.add_argument('--headless')  # Run in background
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument(f'--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            
            # Set cookie
            driver = webdriver.Chrome(options=chrome_options)
            driver.get('https://www.facebook.com/')
            
            # Add cookie
            cookie_parts = cookie.split(';')
            for part in cookie_parts:
                if '=' in part:
                    key, value = part.strip().split('=', 1)
                    if key.lower() in ['c_user', 'xs', 'datr', 'fr']:
                        driver.add_cookie({'name': key, 'value': value, 'domain': '.facebook.com'})
            
            # Navigate to post
            driver.get(url)
            time.sleep(3)
            
            # Try to find comment count
            comment_count = 0
            try:
                # Try multiple selectors for comment count
                selectors = [
                    "//span[contains(text(),'Komentar') or contains(text(),'Comments')]",
                    "//a[contains(@href, 'comment')]//span",
                    "//div[@role='button']//span[contains(text(),'Komentar') or contains(text(),'Comments')]",
                    "//span[contains(@class, 'comments')]"
                ]
                
                for selector in selectors:
                    try:
                        elements = driver.find_elements(By.XPATH, selector)
                        for element in elements:
                            text = element.text
                            if text:
                                # Extract number from text
                                numbers = re.findall(r'[\d,]+', text)
                                if numbers:
                                    num_str = numbers[0].replace(',', '')
                                    comment_count = int(num_str)
                                    break
                        if comment_count > 0:
                            break
                    except:
                        continue
                
                # If still 0, try to find comment section
                if comment_count == 0:
                    try:
                        comment_elements = driver.find_elements(By.XPATH, "//div[@data-testid='UFI2CommentsList']//div[@role='article']")
                        comment_count = len(comment_elements)
                    except:
                        pass
                        
            except Exception as e:
                print(f"Error finding comments: {e}")
            
            driver.quit()
            return comment_count
            
        except Exception as e:
            print(f"Error processing URL: {e}")
            return 0
    
    def process_single_url(self, url, cookie, index, total):
        """Process a single URL with given cookie"""
        try:
            self.root.after(0, self.update_status, f"Memproses {index+1}/{total}...")
            
            comment_count = self.get_comment_count(url, cookie)
            
            result = {
                'url': url,
                'comment_count': comment_count,
                'cookie_used': cookie[:20] + '...' if len(cookie) > 20 else cookie,
                'status': 'Success' if comment_count > 0 else 'Failed/No comments'
            }
            
            self.results.append(result)
            self.root.after(0, self.update_result_display)
            
            return result
            
        except Exception as e:
            result = {
                'url': url,
                'comment_count': 0,
                'cookie_used': 'Error',
                'status': f'Error: {str(e)[:50]}'
            }
            self.results.append(result)
            self.root.after(0, self.update_result_display)
            return result
    
    def start_check(self):
        """Start the checking process"""
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Error", "Silakan masukkan URL postingan Facebook")
            return
        
        if not self.cookies:
            messagebox.showerror("Error", "Tidak ada cookie yang dimuat. Periksa koneksi internet.")
            return
        
        try:
            tab_count = int(self.tab_count_var.get())
        except ValueError:
            messagebox.showerror("Error", "Jumlah tab harus berupa angka")
            return
        
        # Clear previous results
        self.results = []
        self.result_text.delete(1.0, tk.END)
        
        # Update UI
        self.is_running = True
        self.check_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.progress.start()
        
        # Start checking in thread
        thread = threading.Thread(target=self.run_check, args=(url, tab_count))
        thread.daemon = True
        thread.start()
    
    def run_check(self, url, tab_count):
        """Run the checking process in thread"""
        try:
            # Use cookies based on tab count
            cookies_to_use = self.cookies[:tab_count]
            if len(cookies_to_use) < tab_count:
                # Reuse cookies if not enough
                cookies_to_use = self.cookies * (tab_count // len(self.cookies) + 1)
                cookies_to_use = cookies_to_use[:tab_count]
            
            total = len(cookies_to_use)
            
            for i, cookie_data in enumerate(cookies_to_use):
                if not self.is_running:
                    break
                
                cookie = cookie_data.get('cookie', '')
                if cookie:
                    self.process_single_url(url, cookie, i, total)
                    time.sleep(2)  # Delay to avoid rate limiting
            
            # Save results
            if self.results:
                self.save_results()
            
            self.root.after(0, self.finish_check)
            
        except Exception as e:
            self.root.after(0, self.show_error, f"Error: {str(e)}")
    
    def update_status(self, message):
        """Update status label"""
        self.status_label.config(text=f"Status: {message}")
    
    def update_result_display(self):
        """Update result display in text area"""
        self.result_text.delete(1.0, tk.END)
        for result in self.results:
            self.result_text.insert(tk.END, f"URL: {result['url']}\n")
            self.result_text.insert(tk.END, f"Jumlah Komentar: {result['comment_count']}\n")
            self.result_text.insert(tk.END, f"Cookie: {result['cookie_used']}\n")
            self.result_text.insert(tk.END, f"Status: {result['status']}\n")
            self.result_text.insert(tk.END, "-" * 50 + "\n\n")
        
        self.result_text.see(tk.END)
    
    def save_results(self):
        """Save results to text files"""
        try:
            # Create folder for results
            folder_name = f"hasil_cek_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            os.makedirs(folder_name, exist_ok=True)
            
            # Separate results
            above_2k = [r for r in self.results if r['comment_count'] > 2000]
            below_2k = [r for r in self.results if r['comment_count'] <= 2000 and r['comment_count'] > 0]
            
            # Save above 2K
            with open(os.path.join(folder_name, 'komentar_diatas_2k.txt'), 'w', encoding='utf-8') as f:
                f.write("Hasil Pengecekan Komentar > 2000\n")
                f.write("=" * 60 + "\n\n")
                for r in above_2k:
                    f.write(f"URL: {r['url']}\n")
                    f.write(f"Jumlah Komentar: {r['comment_count']}\n")
                    f.write(f"Cookie: {r['cookie_used']}\n")
                    f.write("-" * 40 + "\n\n")
            
            # Save below 2K
            with open(os.path.join(folder_name, 'komentar_dibawah_2k.txt'), 'w', encoding='utf-8') as f:
                f.write("Hasil Pengecekan Komentar <= 2000\n")
                f.write("=" * 60 + "\n\n")
                for r in below_2k:
                    f.write(f"URL: {r['url']}\n")
                    f.write(f"Jumlah Komentar: {r['comment_count']}\n")
                    f.write(f"Cookie: {r['cookie_used']}\n")
                    f.write("-" * 40 + "\n\n")
            
            # Also save all results
            with open(os.path.join(folder_name, 'semua_hasil.txt'), 'w', encoding='utf-8') as f:
                f.write("Semua Hasil Pengecekan\n")
                f.write("=" * 60 + "\n\n")
                for r in self.results:
                    f.write(f"URL: {r['url']}\n")
                    f.write(f"Jumlah Komentar: {r['comment_count']}\n")
                    f.write(f"Cookie: {r['cookie_used']}\n")
                    f.write(f"Status: {r['status']}\n")
                    f.write("-" * 40 + "\n\n")
            
            self.root.after(0, self.show_save_message, folder_name)
            
        except Exception as e:
            print(f"Error saving results: {e}")
    
    def show_save_message(self, folder_name):
        """Show save confirmation"""
        messagebox.showinfo("Berhasil", f"Hasil disimpan di folder: {folder_name}")
    
    def finish_check(self):
        """Finish the checking process"""
        self.is_running = False
        self.progress.stop()
        self.check_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_label.config(text="Status: Selesai")
    
    def stop_check(self):
        """Stop the checking process"""
        self.is_running = False
        self.status_label.config(text="Status: Dihentikan oleh user")
    
    def show_error(self, message):
        """Show error message"""
        self.is_running = False
        self.progress.stop()
        self.check_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        messagebox.showerror("Error", message)
        self.status_label.config(text=f"Status: Error - {message[:50]}")

if __name__ == "__main__":
    root = tk.Tk()
    app = FacebookCommentChecker(root)
    root.mainloop()