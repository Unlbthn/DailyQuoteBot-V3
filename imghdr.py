# imghdr.py
# Python 3.13'te kaldırılan imghdr modülü için basit bir uyumluluk dosyası.
# python-telegram-bot 13.x sadece imghdr.what(...) fonksiyonunu kullanıyor.
# Burada basit bir stub tanımlamak yeterli.

def what(file, h=None):
    """
    Eski imghdr.what(...) fonksiyonunun basit stub versiyonu.
    Her zaman None döndürüyoruz; bu durumda telegram kütüphanesi
    sadece dosyayı 'binary' olarak yollar, bu bizim için sorun değil.
    """
    return None
