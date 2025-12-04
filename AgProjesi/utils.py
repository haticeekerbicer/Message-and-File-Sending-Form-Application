import socket
import struct
import json

# Sabitler
HEADER_SIZE = 4  # 4 Baytlık uzunluk bilgisi
CHUNK_SIZE = 65536  # 64 KB dosya parça boyutu
ENCODING = 'utf-8'

def send_message(sock, message_dict, binary_data=None):
    """
    Mesajı TCP üzerinden çerçeveleyerek (framing) gönderir.
    Format: [JSON_LEN (4 byte)] + [JSON_BYTES] + [BINARY_DATA (Opsiyonel)]
    """
    try:
        # Mesajı JSON formatına çevir ve byte'a kodla
        json_str = json.dumps(message_dict)
        json_bytes = json_str.encode(ENCODING)
        
        # JSON uzunluğunu 4 byte (big-endian) olarak hazırla
        json_len = len(json_bytes)
        header = struct.pack('!I', json_len)
        
        # Önce başlığı, sonra JSON verisini gönder
        sock.sendall(header + json_bytes)
        
        # Eğer dosya parçası (binary) varsa, hemen arkasından gönder
        if binary_data:
            sock.sendall(binary_data)
            
    except Exception as e:
        print(f"Mesaj gönderme hatası: {e}")
        raise e

def receive_message(sock):
    """
    TCP soketinden çerçevelenmiş mesajı okur.
    Önce 4 byte uzunluk okur, sonra o kadar JSON okur.
    Eğer mesaj tipi FILE_CHUNK ise, ayrıca binary veriyi de okur.
    
    Dönüş: (json_dict, binary_data)
    """
    try:
        # 1. Adım: 4 Byte başlığı (uzunluk bilgisini) oku
        header = recv_exactly(sock, HEADER_SIZE)
        if not header:
            return None, None
            
        json_len = struct.unpack('!I', header)[0]
        
        # 2. Adım: JSON verisini oku
        json_bytes = recv_exactly(sock, json_len)
        if not json_bytes:
            return None, None
            
        message_dict = json.loads(json_bytes.decode(ENCODING))
        
        # 3. Adım: Eğer dosya parçası ise binary veriyi oku
        binary_data = None
        if message_dict.get("type") == "FILE_CHUNK":
            chunk_len = message_dict.get("chunk_len", 0)
            if chunk_len > 0:
                binary_data = recv_exactly(sock, chunk_len)
                
        return message_dict, binary_data
        
    except Exception as e:
        print(f"Mesaj alma hatası: {e}")
        return None, None

def recv_exactly(sock, n):
    """
    Soketten tam olarak n byte veri okumaya çalışır.
    """
    data = b''
    while len(data) < n:
        try:
            packet = sock.recv(n - len(data))
            if not packet:
                return None
            data += packet
        except socket.error:
            return None
    return data