import socket
import threading
import json
import tkinter as tk
from tkinter import simpledialog, messagebox, filedialog, scrolledtext, ttk
import os
import time
from datetime import datetime
from utils import send_message, receive_message, CHUNK_SIZE

HOST = '127.0.0.1' # Sunucu IP'si (Localhost)
PORT = 12345

class ClientApp:
   
    def __init__(self, root):
        
        self.root = root
        self.root.title("TCP Mesajlaşma ve Dosya Transferi")
        self.root.geometry("400x550")
        
        self.sock = None
        self.username = None
        self.is_connected = False
        
        self.pending_offers = {}
        self.user_colors = {} 
        self.transfer_progress = {} 
        
        self.setup_gui()
        self.chat_windows = {}
        
        self.root.after(100, self.connect_to_server)
        root.config(bg="#005c4b")

    def get_user_color(self, user):
        """Kullanıcı adına göre sabit bir renk döndürür."""
        if user not in self.user_colors:
            colors = ["#4a90e2", "#7ed321", "#bd10e0", "#f5a623", "#50e3c2", "#009688"]
            color_index = sum(ord(c) for c in user) % len(colors)
            self.user_colors[user] = colors[color_index]
        return self.user_colors[user]

    def setup_gui(self):
        self.top_frame = tk.Frame(self.root)
        self.top_frame.pack(pady=5)
        self.lbl_status = tk.Label(self.top_frame, text="Bağlantı Bekleniyor...", fg="red")
        self.lbl_status.pack()

        self.list_frame = tk.LabelFrame(self.root, text="Çevrimiçi Kullanıcılar")
        self.list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.user_listbox = tk.Listbox(self.list_frame)
        self.user_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        self.user_listbox.bind("<Double-Button-1>", self.open_chat_from_list)

        self.btn_chat = tk.Button(self.root, text="Seçili Kişiyle Sohbet Et", command=self.open_chat_from_list)
        self.btn_chat.pack(pady=5)

    def connect_to_server(self):
        self.username = simpledialog.askstring("Giriş", "Kullanıcı Adı:")
        if not self.username:
            self.root.destroy()
            return

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((HOST, PORT))
            
            login_msg = {"type": "LOGIN", "username": self.username}
            send_message(self.sock, login_msg)
            
            self.is_connected = True
            self.lbl_status.config(text=f"Bağlı: {self.username}", fg="green")
            
            threading.Thread(target=self.receive_loop, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Hata", f"Sunucuya bağlanılamadı: {e}")
            self.root.destroy()

    def receive_loop(self):
        while self.is_connected:
            try:
                msg, binary_data = receive_message(self.sock)
                if not msg:
                    break
                self.root.after(0, self.handle_incoming_message, msg, binary_data)
                
            except Exception as e:
                print(f"Bağlantı hatası: {e}")
                break
        
        self.is_connected = False
        try:
            self.root.after(0, lambda: self.lbl_status.config(text="Bağlantı Koptu", fg="red"))
        except:
            pass
        if self.sock:
            self.sock.close()

    def handle_incoming_message(self, msg, binary_data):
        msg_type = msg.get("type")
        
        if msg_type == "USER_LIST":
            self.update_user_list(msg.get("users", []))
            
        elif msg_type == "CHAT_MSG":
            sender = msg.get("from")
            text = msg.get("text")
            timestamp = msg.get("timestamp")
            self.show_chat_message(sender, text, timestamp)
            
        elif msg_type == "FILE_REQUEST":
            sender = msg.get("from")
            filename = msg.get("name")
            size = msg.get("size")
            self.handle_file_offer(sender, filename, size)
            
        elif msg_type == "FILE_RESPONSE":
            receiver_user = msg.get("from")
            is_accepted = msg.get("accept")
            
            if is_accepted:
                path = self.pending_offers.get(receiver_user)
                if path and os.path.exists(path):
                    self.show_progress_bar(receiver_user, os.path.getsize(path))
                    threading.Thread(target=self.start_file_transfer, args=(receiver_user, path)).start()
                else:
                    messagebox.showerror("Hata", "Gönderilecek dosya bulunamadı veya yol hatalı.")
            else:
                messagebox.showinfo("Reddedildi", f"{receiver_user} dosya teklifini reddetti.")

        elif msg_type == "FILE_PROGRESS":
            sender = msg.get("from")
            progress = msg.get("progress", 0)
            self.update_progress_bar(sender, progress)
            
        elif msg_type == "FILE_CHUNK":
            self.save_file_chunk(msg, binary_data)
            
        elif msg_type == "FILE_DONE":
            sender = msg.get("from")
            fname = msg.get("filename")
            
            # Sohbet penceresine sistem mesajı olarak ekle
            if sender not in self.chat_windows:
                self.open_chat_window(sender)
            self.chat_windows[sender].display_message("Sistem", f"Dosya başarıyla alındı: {fname}", time.time())

            messagebox.showinfo("Tamamlandı", f"{sender} tarafından {fname} gönderimi tamamlandı.")
            self.hide_progress_bar(sender)
            if hasattr(self, 'incoming_file') and self.incoming_file:
                self.incoming_file.close()
                self.incoming_file = None

        elif msg_type == "ERROR":
            messagebox.showerror("Hata", msg.get("message"))

    def update_user_list(self, users):
        self.user_listbox.delete(0, tk.END)
        for u in users:
            if u != self.username:
                self.user_listbox.insert(tk.END, u)

    def open_chat_from_list(self, event=None):
        selection = self.user_listbox.curselection()
        if not selection:
            return
        target_user = self.user_listbox.get(selection[0])
        self.open_chat_window(target_user)

    def open_chat_window(self, target_user):
        if target_user in self.chat_windows:
            try:
                self.chat_windows[target_user].win.lift()
            except tk.TclError:
                cw = ChatWindow(self, target_user)
                self.chat_windows[target_user] = cw
            return
        
        cw = ChatWindow(self, target_user)
        self.chat_windows[target_user] = cw

    def show_chat_message(self, sender, text, timestamp):
        window_key = sender
        if window_key not in self.chat_windows:
            self.open_chat_window(sender)
        self.chat_windows[window_key].display_message(sender, text, timestamp)

    # --- DOSYA TRANSFER YARDIMCILARI ---
    def show_progress_bar(self, target_user, total_size):
        if target_user not in self.transfer_progress:
            frame = tk.LabelFrame(self.root, text=f"Aktarım: {target_user}")
            frame.pack(fill="x", padx=10, pady=2)
            
            progress_bar = ttk.Progressbar(frame, orient="horizontal", length=300, mode="determinate")
            progress_bar.pack(fill="x", padx=5, pady=5)
            progress_bar["maximum"] = total_size
            
            label = tk.Label(frame, text="0%")
            label.pack(side="right", padx=5)
            
            self.transfer_progress[target_user] = {"frame": frame, "bar": progress_bar, "label": label, "total": total_size, "current": 0}

    def update_progress_bar(self, target_user, current_size):
        if target_user in self.transfer_progress:
            data = self.transfer_progress[target_user]
            data["current"] = current_size
            progress_percent = int((current_size / data["total"]) * 100) if data["total"] > 0 else 0
            
            data["bar"]["value"] = current_size
            data["label"].config(text=f"{progress_percent}%")
            
    def hide_progress_bar(self, target_user):
        if target_user in self.transfer_progress:
            data = self.transfer_progress[target_user]
            data["frame"].destroy()
            del self.transfer_progress[target_user]

    # --- DOSYA ALMA ---
    def handle_file_offer(self, sender, filename, size):
        # Boyutu MB cinsinden hesapla
        size_mb = size / (1024 * 1024)
        msg_text = f"{sender} size bir dosya göndermek istiyor.\nDosya: {filename}\nBoyut: {size_mb:.2f} MB"
        accept = messagebox.askyesno("Dosya Teklifi", msg_text)
        
        resp = {
            "type": "FILE_RESPONSE",
            "to": sender,
            "from": self.username,
            "accept": accept
        }
        
        if accept:
            save_path = filedialog.asksaveasfilename(initialfile=filename)
            if save_path:
                try:
                    self.incoming_file = open(save_path, "wb")
                    self.incoming_file_name = filename
                    self.show_progress_bar(sender, size)
                except Exception as e:
                    messagebox.showerror("Hata", f"Dosya oluşturulamadı: {e}")
                    resp["accept"] = False
            else:
                resp["accept"] = False
        
        send_message(self.sock, resp)

    def save_file_chunk(self, msg, data):
        sender = msg.get("from")
        chunk_len = len(data)
        
        if hasattr(self, 'incoming_file') and self.incoming_file:
            self.incoming_file.write(data)
            if sender in self.transfer_progress:
                current_size = self.transfer_progress[sender]["current"] + chunk_len
                self.update_progress_bar(sender, current_size)

    # --- DOSYA GÖNDERME ---
    def start_file_transfer(self, target_user, filepath):
        filename = os.path.basename(filepath)
        sent_size = 0
        
        try:
            send_message(self.sock, {
                "type": "FILE_START",
                "to": target_user,
                "from": self.username,
                "filename": filename
            })
            
            with open(filepath, "rb") as f:
                seq = 0
                while True:
                    chunk = f.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    
                    chunk_msg = {
                        "type": "FILE_CHUNK",
                        "to": target_user,
                        "from": self.username,
                        "seq": seq,
                        "chunk_len": len(chunk)
                    }
                    send_message(self.sock, chunk_msg, chunk)
                    seq += 1
                    sent_size += len(chunk)
                    
                    progress_msg = {
                        "type": "FILE_PROGRESS",
                        "to": target_user,
                        "from": self.username,
                        "progress": sent_size
                    }
                    send_message(self.sock, progress_msg)
                    self.update_progress_bar(target_user, sent_size)
                    time.sleep(0.005) 
            
            send_message(self.sock, {
                "type": "FILE_DONE",
                "to": target_user,
                "from": self.username,
                "filename": filename
            })
            print(f"{filename} gönderimi tamamlandı.")
            
            # --- DÜZELTME: Gönderen tarafında barı kapat ---
            self.root.after(0, self.hide_progress_bar, target_user)
            
        except Exception as e:
            print(f"Dosya gönderme hatası: {e}")

class ChatWindow: 
    
    def __init__(self, main_app, target_user):
        self.main_app = main_app
        self.target_user = target_user
        
        title = f"Sohbet: {target_user}"
        self.win = tk.Toplevel()
        self.win.title(title)
        self.win.geometry("500x400")
        self.win.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.input_frame = tk.Frame(self.win)
        self.input_frame.pack(side="bottom", fill="x", padx=5, pady=5)
        
        self.entry_msg = tk.Entry(self.input_frame)
        self.entry_msg.pack(side="left", fill="x", expand=True)
        self.entry_msg.bind("<Return>", self.send_chat)
        
        self.btn_send = tk.Button(self.input_frame, text="Gönder", command=self.send_chat)
        self.btn_send.pack(side="right", padx=5)
        
        self.btn_file = tk.Button(self.input_frame, text="Dosya", command=self.offer_file)
        self.btn_file.pack(side="right")

        # Örnek: Arka planı açık mavi yapmak için 'bg' ekliyoruz
        self.chat_area = scrolledtext.ScrolledText(self.win, state='disabled')
        self.chat_area.pack(side="top", fill="both", expand=True, padx=5, pady=5)
        
        self.chat_area.tag_config('sender', foreground=self.main_app.get_user_color(target_user), font=('Arial', 9, 'bold'))
        self.chat_area.tag_config('self', foreground='blue', font=('Arial', 9, 'bold'))
        self.chat_area.tag_config('timestamp', foreground='gray', font=('Arial', 8))
        self.chat_area.tag_config('system', foreground='red', font=('Arial', 9, 'italic'))

    def display_message(self, sender, text, timestamp_value):
        if timestamp_value is None:
            timestamp_value = time.time()
            
        time_str = datetime.fromtimestamp(timestamp_value).strftime('%H:%M:%S')
        
        self.chat_area.config(state='normal')
        self.chat_area.insert(tk.END, f"[{time_str}] ", 'timestamp')
        
        if sender == "Ben":
            self.chat_area.insert(tk.END, "[Ben]: ", 'self')
            self.chat_area.insert(tk.END, f"{text}\n")
        elif sender == "Sistem":
            self.chat_area.insert(tk.END, "[Sistem]: ", 'system')
            self.chat_area.insert(tk.END, f"{text}\n")
        else:
            self.chat_area.tag_config(sender, foreground=self.main_app.get_user_color(sender))
            self.chat_area.insert(tk.END, f"[{sender}]: ", sender)
            self.chat_area.insert(tk.END, f"{text}\n")
        
        self.chat_area.config(state='disabled')
        self.chat_area.yview(tk.END)

    def send_chat(self, event=None):
        text = self.entry_msg.get()
        if not text: return
        
        msg = {
            "type": "CHAT_MSG",
            "to": self.target_user,
            "from": self.main_app.username,
            "text": text,
            "timestamp": time.time()
        }
        send_message(self.main_app.sock, msg)
        self.display_message("Ben", text, time.time()) 
        self.entry_msg.delete(0, tk.END)

    def offer_file(self):
        filepath = filedialog.askopenfilename()
        if not filepath: return
        
        filename = os.path.basename(filepath)
        filesize = os.path.getsize(filepath)
        
        # Boyutu MB cinsinden hesapla
        size_mb = filesize / (1024 * 1024)
        
        offer_msg = {
            "type": "FILE_OFFER",
            "to": self.target_user,
            "from": self.main_app.username,
            "name": filename,
            "size": filesize
        }
        send_message(self.main_app.sock, offer_msg)
        # Mesajda MB bilgisini göster
        self.display_message("Sistem", f"Dosya teklifi gönderildi: {filename} ({size_mb:.2f} MB)", time.time())
        self.main_app.pending_offers[self.target_user] = filepath

    def on_close(self):
        if self.target_user in self.main_app.chat_windows:
            del self.main_app.chat_windows[self.target_user]
        self.win.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ClientApp(root)
    root.mainloop()