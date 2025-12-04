#  TCP Tabanlı Mesajlaşma ve Dosya Gönderim Uygulaması


###  Proje Bilgileri

Ders: BMB501 / BMB507 – Bilgisayar Ağlarına Giriş
Konu: İstemci–Sunucu (Client–Server) Mimarisi ile TCP Tabanlı Güvenli İletişim
Geliştirilen Teknolojiler: Python (Socket, Threading, Tkinter)

###  Proje Özellikleri
***Temel Gereksinimler***

Mesajlaşma: İki kullanıcı arasında anlık ve sürekli iletişim.
Dosya Gönderimi: Sunucu üzerinden büyük dosyaların parçalı şekilde aktarımı (streaming).
Veri Çerçeveleme (Framing): TCP akışında karışmayı engellemek için 4 byte'lık uzunluk ön ekli protokol.
Eşzamanlılık: Sunucu, threading. RLock ile çoklu bağlantıları güvenli şekilde yönetir.

---
###  Ekstra Uygulanan Özellikler

1. Gelişmiş Görünüm:
Mesajlarda zaman damgası ve kullanıcıya özel renkli etiketler.

2. Kullanıcı Dostu Etiketleme:
Gönderen kişi kendi mesajını [Ben]: etiketiyle görür.
Karşı taraf gönderenin ismiyle ([Ahmet]:) etiketlenir.

3. Aktarım İlerleme Çubuğu:
Dosya gönderimi sırasında yüzde (%) bazlı progress bar görünür.

4. MB Cinsinden Boyut Gösterimi:
Dosya boyutları byte yerine Megabayt (MB) cinsinden gösterilir.

---
###  Teknik Mimari
***Dosya Yapısı***

**server.py:** Merkezi sunucu uygulaması

**client.py:** Tkinter arayüzlü istemci

**utils.py:** Ortak fonksiyonlar (framing, gönderme/alma)

**İletişim Protokolü**

**Başlık (4 Bayt):** JSON verisinin toplam uzunluğunu içerir

**Veri (Değişken Boyutlu):** JSON formatında mesaj ve opsiyonel binary dosya parçası

---
###  Nasıl Kullanılır?
#### A) Gerekli Ön Hazırlık

*Tüm dosyaların aynı klasörde olduğuna emin ol*

Sunucunun yerel IP adresini öğren (ipconfig)

**client.py** içinde:

**HOST** = 'sunucu_ip_adresi' olarak güncelle

Windows Güvenlik Duvarı’nda 12345 TCP portu için inbound rule ekle

#### B) Uygulamayı Başlatma

Aynı dizinde üç terminal aç:

Sunucu:
- python server.py

İstemci 1:
- python client.py

İstemci 2:
- python client.py

---
###  Temel İşlevler
Sohbet Başlatma

Listeden kullanıcı seç → Seçili Kişiyle Sohbet Et butonu

Dosya Gönderimi

Sohbet ekranında → Dosya butonuna bas → karşı taraf onayladığında aktarım başlar

Dosya Alımı

Teklifi onayla → kayıt klasörünü seç → transfer tamamlanınca sistem mesajı görünür
