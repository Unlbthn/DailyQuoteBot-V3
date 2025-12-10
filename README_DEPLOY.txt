QuoteMastersBot - Deploy Talimatı (Railway / Render / Sunucu)

1) Klasör yapısı:
   QuoteMastersBot/
     ├─ bot.py
     ├─ quotes.py
     ├─ requirements.txt

2) Gerekli Python sürümü:
   - Python 3.10+ önerilir
   - python-telegram-bot 20.7 ile uyumludur

3) Ortam değişkeni:
   BOT_TOKEN = <Telegram Bot Token>

4) Kurulum (lokalde):
   pip install -r requirements.txt
   python bot.py

5) Railway / Render:
   - Build komutu (genelde otomatik):  pip install -r requirements.txt
   - Start komutu:                     python bot.py
   - Environment sekmesinden:
       BOT_TOKEN değişkenini ekle.

6) Notlar:
   - Günlük bildirimler Türkiye saati ile 10:00'da gönderilir.
   - Kullanıcı ayarları RAM'de tutulur (sunucu restart olursa sıfırlanır).
   - AdsGram reklamları için platform ID requirements'a göre botta tanımlıdır.
