import socket
import threading
import json
import time
from utils import receive_message, send_message

# Sunucu Ayarları
HOST = '0.0.0.0'  # Tüm arayüzlerden dinle
PORT = 12345

class ChatServer:
    def __init__(self, host, port):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((host, port))
        self.server_socket.listen(5)
        
        # Bağlı istemcileri tutan sözlük: {username: socket}
        self.clients = {}
        # DEADLOCK ÇÖZÜMÜ: RLock kullanıyoruz.
        self.clients_lock = threading.RLock()
        
        print(f"Sunucu başlatıldı: {host}:{port}")
        
    def broadcast_user_list(self):
        """Tüm bağlı kullanıcılara güncel kullanıcı listesini gönderir."""
        with self.clients_lock:
            user_list = list(self.clients.keys())
            
        message = {
            "type": "USER_LIST",
            "users": user_list
        }
        
        with self.clients_lock:
            for user, sock in self.clients.items():
                try:
                    send_message(sock, message)
                except:
                    pass 

    def handle_client(self, client_socket, address):
        """Her istemci için çalışan iş parçacığı."""
        print(f"Yeni bağlantı: {address}")
        username = None
        
        try:
            while True:
                msg, binary_data = receive_message(client_socket)
                if not msg:
                    break
                
                msg_type = msg.get("type")
                
                # --- LOGIN ---
                if msg_type == "LOGIN":
                    new_user = msg.get("username")
                    with self.clients_lock:
                        if new_user in self.clients:
                            err_msg = {"type": "ERROR", "message": "Kullanıcı adı kullanımda."}
                            send_message(client_socket, err_msg)
                            return
                        else:
                            self.clients[new_user] = client_socket
                            username = new_user
                            print(f"Kullanıcı giriş yaptı: {username}")
                            
                            self.broadcast_user_list()
                            
                            join_msg = {"type": "USER_JOIN", "username": username}
                            for u, s in self.clients.items():
                                if u != username:
                                    send_message(s, join_msg)

                # --- MESSAGE & FILE ROUTING ---
                # HATA BURADAYDI: FILE_OFFER artık bu listeye dahil ve aşağıda işleniyor.
                elif msg_type in ["CHAT_MSG", "FILE_OFFER", "FILE_RESPONSE", "FILE_START", "FILE_CHUNK", "FILE_DONE", "FILE_PROGRESS"]:
                    target_user = msg.get("to")
                    
                    # Dosya teklifini REQUEST'e çevirip hedefe yolla
                    if msg_type == "FILE_OFFER":
                        forward_msg = msg.copy()
                        forward_msg["type"] = "FILE_REQUEST" 
                    else:
                        forward_msg = msg
                    
                    target_sock = None
                    with self.clients_lock:
                        target_sock = self.clients.get(target_user)
                        
                    if target_sock:
                        try:
                            send_message(target_sock, forward_msg, binary_data)
                        except:
                            pass
                    else:
                        # Kullanıcı çevrimdışı
                        err = {"type": "ERROR", "message": f"Kullanıcı {target_user} çevrimdışı."}
                        send_message(client_socket, err)

        except Exception as e:
            print(f"Hata ({address}): {e}")
        finally:
            if username:
                print(f"Kullanıcı ayrıldı: {username}")
                with self.clients_lock:
                    if username in self.clients:
                        del self.clients[username]
                
                leave_msg = {"type": "USER_LEAVE", "username": username}
                self.broadcast_user_list()
                
                with self.clients_lock:
                    for s in self.clients.values():
                        try:
                            send_message(s, leave_msg)
                        except:
                            pass
            
            client_socket.close()

    def start(self):
        print("Sunucu bağlantı bekliyor...")
        try:
            while True:
                client_sock, addr = self.server_socket.accept()
                thread = threading.Thread(target=self.handle_client, args=(client_sock, addr))
                thread.daemon = True
                thread.start()
        except KeyboardInterrupt:
            print("Sunucu kapatılıyor.")
        finally:
            self.server_socket.close()

if __name__ == "__main__":
    server = ChatServer(HOST, PORT)
    server.start()