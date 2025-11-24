# Telegram Günün Sözü Mini-App

Bu proje, Telegram Mini-App + AdsGram kullanarak
motivasyon sözleri gösteren ve reklam gelirini optimize eden bir örnek uygulamadır.

## Özellikler

- Interstitial reklam (her X aksiyonda 1 kez)
- Ödüllü reklam (izle → bonus söz aç)
- Konu seçimi (Motivasyon, Aşk, Spor)
- Favoriler
- Günlük görevler (3 söz oku, paylaş, ödüllü reklam izle)
- Basit motivasyon testi
- TR/EN dil desteği (Telegram kullanıcı diline göre başlangıç)
- Viral paylaşım iskeleti (ref parametresi)

## Çalıştırma

### Backend

```bash
cd backend
uvicorn backend.main:app --reload
