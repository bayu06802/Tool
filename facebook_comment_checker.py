import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import requests
import threading
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import os
from datetime import datetime
import webbrowser
from concurrent.futures import ThreadPoolExecutor, as_completed

class FacebookCommentChecker:
    def __init__(self, root):
        self.root = root
        self.root.title("Facebook Comment Checker")
        self.root.geometry("1000x750")
        self.root.resizable(True, True)
        
        # Variables
        self.urls_var = tk.StringVar()
        self.tab_count_var = tk.StringVar(value="5")
        self.cookies = []
        self.is_running = False
        self.results = []
        self.processed_count = 0
        self.total_count = 0
        self.current_cookie = None
        self.failed_urls = []
        self.lock = threading.Lock()
        self.error_whatsapp_sent = False
        
        self.setup_ui()
        self.load_cookies()
        
    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(main_frame, text="FACEBOOK COMMENT CHECKER", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=10)
        
        # URL Input (Multiple URLs)
        ttk.Label(main_frame, text="URL Postingan (pisahkan dengan enter):", font=('Arial', 11)).grid(row=1, column=0, sticky=tk.W, pady=5)
        
        url_frame = ttk.Frame(main_frame)
        url_frame.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        self.url_text = scrolledtext.ScrolledText(url_frame, width=70, height=5)
        self.url_text.pack(fill=tk.BOTH, expand=True)
        self.url_text.insert('1.0', 'https://www.facebook.com/...\nhttps://www.facebook.com/...')
        
        # Tab/Browser count (Parallel)
        ttk.Label(main_frame, text="Cek Paralel (browser):", font=('Arial', 11)).grid(row=2, column=0, sticky=tk.W, pady=5)
        tab_spinbox = ttk.Spinbox(main_frame, from_=1, to=10, textvariable=self.tab_count_var, width=10)
        tab_spinbox.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Label(main_frame, text="(5-10 aman)", font=('Arial', 9)).grid(row=2, column=2, sticky=tk.W, pady=5)
        
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
        
        # Progress info
        self.progress_label = ttk.Label(main_frame, text="Progress: 0/0", font=('Arial', 10))
        self.progress_label.grid(row=5, column=0, columnspan=3, pady=5, sticky=tk.W)
        
        # Result display
        result_frame = ttk.LabelFrame(main_frame, text="Hasil Pengecekan", padding="10")
        result_frame.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)
        
        self.result_text = scrolledtext.ScrolledText(result_frame, wrap=tk.WORD, width=80, height=18)
        self.result_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='determinate')
        self.progress.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        # Kosong - tidak ada info cookie
        self.cookie_status = ttk.Label(main_frame, text="", font=('Arial', 9))
        self.cookie_status.grid(row=8, column=0, columnspan=3, pady=5, sticky=tk.W)
        
    def load_cookies(self):
        """Load cookies dari GitHub - ambil 1 cookie saja"""
        try:
            response = requests.get('https://raw.githubusercontent.com/bayu06802/Lisensi/main/acc.txt', timeout=10)
            if response.status_code == 200:
                lines = response.text.strip().split('\n')
                self.cookies = []
                for line in lines:
                    if '|' in line:
                        parts = line.split('|')
                        if len(parts) >= 3:
                            cookie_data = {
                                'email': parts[0].strip(),
                                'password': parts[1].strip(),
                                'cookie': parts[2].strip()
                            }
                            self.cookies.append(cookie_data)
                
                # Ambil 1 cookie pertama untuk semua URL
                if self.cookies:
                    self.current_cookie = self.cookies[0].get('cookie', '')
                    self.status_label.config(text="Status: Siap")
                else:
                    self.status_label.config(text="Status: Gagal memuat data")
            else:
                self.status_label.config(text="Status: Gagal memuat data")
        except Exception as e:
            self.status_label.config(text="Status: Error koneksi")
    
    def send_whatsapp_error(self):
        """Kirim notifikasi WhatsApp saat error - hanya 1x"""
        if not self.error_whatsapp_sent:
            self.error_whatsapp_sent = True
            wa_url = "https://wa.me/6283136183583?text=Skrip%20Eror"
            webbrowser.open(wa_url)
    
    def get_comment_count(self, url, cookie):
        """Get comment count - pakai 1 cookie, browser ditutup setiap selesai"""
        driver = None
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            driver = webdriver.Chrome(options=chrome_options)
            driver.get('https://www.facebook.com/')
            time.sleep(1)
            
            # Set cookie
            if cookie:
                cookie_parts = cookie.split(';')
                for part in cookie_parts:
                    if '=' in part:
                        key, value = part.strip().split('=', 1)
                        if key.lower() in ['c_user', 'xs', 'datr', 'fr']:
                            try:
                                driver.add_cookie({'name': key, 'value': value, 'domain': '.facebook.com'})
                            except:
                                pass
            
            # Buka URL
            driver.get(url)
            time.sleep(2)
            
            comment_count = 0
            try:
                selectors = [
                    "//span[contains(text(),'Komentar') or contains(text(),'Comments')]",
                    "//a[contains(@href, 'comment')]//span",
                    "//div[@role='button']//span[contains(text(),'Komentar')]",
                    "//span[contains(@class, 'comments')]"
                ]
                
                for selector in selectors:
                    try:
                        elements = driver.find_elements(By.XPATH, selector)
                        for element in elements:
                            text = element.text
                            if text:
                                numbers = re.findall(r'[\d,]+', text)
                                if numbers:
                                    num_str = numbers[0].replace(',', '')
                                    comment_count = int(num_str)
                                    break
                        if comment_count > 0:
                            break
                    except:
                        continue
                        
            except Exception as e:
                print(f"Error: {e}")
            
            # TUTUP BROWSER
            if driver:
                driver.quit()
                driver = None
            
            return comment_count
            
        except Exception as e:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            
            # Jika error, kirim WA (hanya 1x)
            self.send_whatsapp_error()
            return -1  # -1 menandakan error
    
    def process_url_parallel(self, url, url_index, total_urls):
        """Process single URL - dipanggil paralel"""
        try:
            # Pake 1 cookie yang sama untuk semua URL
            comment_count = self.get_comment_count(url, self.current_cookie)
            
            with self.lock:
                self.processed_count += 1
                progress_pct = (self.processed_count / total_urls) * 100
                self.root.after(0, self.update_progress, progress_pct)
                
                if comment_count == -1:
                    # Error cookie
                    result = {
                        'url': url,
                        'comment_count': 0,
                        'status': 'ERROR - Cookie Invalid'
                    }
                    self.failed_urls.append(url)
                else:
                    result = {
                        'url': url,
                        'comment_count': comment_count,
                        'status': 'Success' if comment_count > 0 else 'No comments'
                    }
                
                self.results.append(result)
                self.root.after(0, self.update_result_display)
                
            return result
            
        except Exception as e:
            with self.lock:
                self.processed_count += 1
                result = {
                    'url': url,
                    'comment_count': 0,
                    'status': 'Error'
                }
                self.results.append(result)
                self.root.after(0, self.update_result_display)
                self.send_whatsapp_error()
            return result
    
    def start_check(self):
        """Start checking dengan paralel"""
        urls_text = self.url_text.get('1.0', tk.END).strip()
        if not urls_text:
            messagebox.showerror("Error", "Masukkan URL postingan")
            return
        
        # Parse URLs
        urls = [u.strip() for u in urls_text.split('\n') if u.strip()]
        if not urls:
            messagebox.showerror("Error", "Masukkan minimal 1 URL")
            return
        
        if not self.current_cookie:
            messagebox.showerror("Error", "Gagal memuat data. Cek koneksi.")
            return
        
        try:
            tab_count = int(self.tab_count_var.get())
            if tab_count < 1 or tab_count > 10:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Jumlah browser 1-10")
            return
        
        # Clear previous
        self.results = []
        self.failed_urls = []
        self.processed_count = 0
        self.error_whatsapp_sent = False
        self.result_text.delete(1.0, tk.END)
        self.progress['value'] = 0
        
        self.is_running = True
        self.check_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.total_count = len(urls)
        
        # Start thread dengan paralel
        thread = threading.Thread(target=self.run_check_parallel, args=(urls, tab_count))
        thread.daemon = True
        thread.start()
    
    def run_check_parallel(self, urls, tab_count):
        """Run check dengan ThreadPoolExecutor - paralel"""
        try:
            total_urls = len(urls)
            
            # Gunakan ThreadPoolExecutor untuk paralel
            with ThreadPoolExecutor(max_workers=tab_count) as executor:
                # Submit semua task
                future_to_url = {
                    executor.submit(self.process_url_parallel, url, idx, total_urls): (url, idx)
                    for idx, url in enumerate(urls)
                }
                
                # Tunggu semua selesai
                for future in as_completed(future_to_url):
                    if not self.is_running:
                        executor.shutdown(wait=False, cancel_futures=True)
                        break
                    try:
                        future.result()
                    except Exception as e:
                        print(f"Error in parallel: {e}")
            
            # Simpan hasil
            if self.results:
                self.save_results()
            
            self.root.after(0, self.finish_check)
            
        except Exception as e:
            self.root.after(0, self.show_error, f"Error: {str(e)}")
            self.send_whatsapp_error()
    
    def update_status(self, message):
        self.status_label.config(text=f"Status: {message}")
    
    def update_progress(self, value):
        self.progress['value'] = value
        self.progress_label.config(text=f"Progress: {self.processed_count}/{self.total_count}")
    
    def update_result_display(self):
        self.result_text.delete(1.0, tk.END)
        
        for i, result in enumerate(self.results, 1):
            comment_str = f"{result['comment_count']:,}" if result['comment_count'] > 0 else "0"
            
            if 'ERROR' in result['status']:
                status_icon = "⚠"
            elif result['comment_count'] > 0:
                status_icon = "✓"
            else:
                status_icon = "✗"
            
            self.result_text.insert(tk.END, f"{'='*50}\n")
            self.result_text.insert(tk.END, f"URL #{i}\n")
            self.result_text.insert(tk.END, f"URL: {result['url']}\n")
            self.result_text.insert(tk.END, f"Jumlah Komentar: {comment_str}\n")
            self.result_text.insert(tk.END, f"Status: {status_icon} {result['status']}\n")
            self.result_text.insert(tk.END, f"{'='*50}\n\n")
        
        self.result_text.see(tk.END)
    
    def save_results(self):
        """Save results - TANPA COOKIE"""
        try:
            folder_name = f"hasil_cek_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            os.makedirs(folder_name, exist_ok=True)
            
            # Separate results
            above_2k = [r for r in self.results if r['comment_count'] > 2000]
            below_2k = [r for r in self.results if r['comment_count'] <= 2000 and r['comment_count'] > 0]
            failed = [r for r in self.results if r['comment_count'] == 0 or 'ERROR' in r['status']]
            
            # Save above 2K
            with open(os.path.join(folder_name, 'komentar_diatas_2k.txt'), 'w', encoding='utf-8') as f:
                f.write("="*60 + "\n")
                f.write("HASIL PENGECEKAN KOMENTAR > 2000\n")
                f.write("="*60 + "\n\n")
                f.write(f"Total URL: {len(above_2k)}\n")
                f.write(f"Total komentar: {sum(r['comment_count'] for r in above_2k):,}\n\n")
                f.write("-"*60 + "\n\n")
                
                for r in above_2k:
                    f.write(f"URL: {r['url']}\n")
                    f.write(f"Jumlah Komentar: {r['comment_count']:,}\n")
                    f.write("-"*40 + "\n\n")
            
            # Save below 2K
            with open(os.path.join(folder_name, 'komentar_dibawah_2k.txt'), 'w', encoding='utf-8') as f:
                f.write("="*60 + "\n")
                f.write("HASIL PENGECEKAN KOMENTAR <= 2000\n")
                f.write("="*60 + "\n\n")
                f.write(f"Total URL: {len(below_2k)}\n")
                f.write(f"Total komentar: {sum(r['comment_count'] for r in below_2k):,}\n\n")
                f.write("-"*60 + "\n\n")
                
                for r in below_2k:
                    f.write(f"URL: {r['url']}\n")
                    f.write(f"Jumlah Komentar: {r['comment_count']:,}\n")
                    f.write("-"*40 + "\n\n")
            
            # Save failed/error
            if failed:
                with open(os.path.join(folder_name, 'gagal_dicek.txt'), 'w', encoding='utf-8') as f:
                    f.write("="*60 + "\n")
                    f.write("URL GAGAL DICEK / ERROR\n")
                    f.write("="*60 + "\n\n")
                    for r in failed:
                        f.write(f"URL: {r['url']}\n")
                        f.write(f"Status: {r['status']}\n")
                        f.write("-"*40 + "\n\n")
            
            # Save all
            with open(os.path.join(folder_name, 'semua_hasil.txt'), 'w', encoding='utf-8') as f:
                f.write("="*60 + "\n")
                f.write("SEMUA HASIL PENGECEKAN\n")
                f.write("="*60 + "\n\n")
                f.write(f"Total dicek: {len(self.results)}\n")
                f.write(f"Berhasil: {len([r for r in self.results if r['comment_count'] > 0])}\n")
                f.write(f"Gagal/Error: {len([r for r in self.results if r['comment_count'] == 0])}\n")
                f.write(f"Total komentar: {sum(r['comment_count'] for r in self.results):,}\n\n")
                f.write("-"*60 + "\n\n")
                
                for i, r in enumerate(self.results, 1):
                    f.write(f"URL #{i}: {r['url']}\n")
                    f.write(f"Jumlah Komentar: {r['comment_count']:,}\n")
                    f.write(f"Status: {r['status']}\n")
                    f.write("-"*40 + "\n\n")
            
            self.root.after(0, self.show_save_message, folder_name)
            
        except Exception as e:
            print(f"Error: {e}")
    
    def show_save_message(self, folder_name):
        msg = f"Hasil disimpan di folder:\n{folder_name}\n\n"
        msg += f"Total dicek: {len(self.results)} URL\n"
        if self.failed_urls:
            msg += f"\n⚠ Ada {len(self.failed_urls)} URL error/gagal"
        messagebox.showinfo("✓ Berhasil", msg)
    
    def finish_check(self):
        self.is_running = False
        self.progress['value'] = 100
        self.check_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        
        if self.failed_urls:
            self.status_label.config(text=f"Status: Selesai ✓ ({len(self.failed_urls)} URL error)")
        else:
            self.status_label.config(text="Status: Selesai ✓")
    
    def stop_check(self):
        self.is_running = False
        self.status_label.config(text="Status: Dihentikan")
        self.check_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
    
    def show_error(self, message):
        self.is_running = False
        self.progress['value'] = 0
        self.check_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        messagebox.showerror("Error", message)
        self.status_label.config(text="Status: Error")

if __name__ == "__main__":
    root = tk.Tk()
    app = FacebookCommentChecker(root)
    root.mainloop()