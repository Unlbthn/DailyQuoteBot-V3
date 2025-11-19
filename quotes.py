SOZLER = {
    "motivation": {
        "label_tr": "💪 Motivasyon",
        "label_en": "💪 Motivation",
        "tr": [
            ("Başarı sabır ister.", "Anonim"),
            ("Vazgeçmeyen kazanır.", "Anonim"),
            ("Hayallerine sahip çık.", "Anonim"),
            ("Bugün attığın küçük adımlar, yarının büyük başarılarıdır.", "Anonim"),
        ],
        "en": [
            ("Success requires patience.", "", "Anonim"),
            ("Winners never quit.", "", "Anonim"),
            ("Follow your dreams.", "", "Anonim"),
            ("Small steps every day lead to big changes.", "", "Anonim"),
        ],
    },

    "love": {
        "label_tr": "❤️ Aşk",
        "label_en": "❤️ Love",
        "tr": [
            ("Aşk kalpten gelen bir melodidir.", "Anonim"),
            ("Seven insan sabreder.", "Anonim"),
        ],
        "en": [
            ("Love is a melody from the heart.", "", "Anonim"),
            ("True love is patient.", "", "Anonim"),
        ],
    },

    "life": {
        "label_tr": "🌿 Yaşam",
        "label_en": "🌿 Life",
        "tr": [
            ("Hayat bir yolculuktur, varış değil.", "Anonim"),
            ("Zaman en değerli hazinemizdir.", "Anonim"),
        ],
        "en": [
            ("Life is a journey, not a destination.", "", "Anonim"),
            ("Time is our most valuable treasure.", "", "Anonim"),
        ],
    },

    "success": {
        "label_tr": "🏆 Başarı",
        "label_en": "🏆 Success",
        "tr": [
            ("Başarı, hazırlanma ile fırsatın buluştuğu yerdir.", "Anonim"),
            ("Başarının sırrı, bir kez daha denemektir.", "Anonim"),
        ],
        "en": [
            ("Success is where preparation and opportunity meet.", "", "Anonim"),
            ("The secret of success is to try one more time.", "", "Anonim"),
        ],
    },
}


def normalize_author(author: str) -> str:
    """
    İsimlerin sonundaki '…’ya atfedilir' vb. ekleri temizler.
    Örn:
      "Nelson Mandela’ya atfedilir" -> "Nelson Mandela"
      "Anonim" -> "Anonim"
    """
    if not author:
        return ""

    a = author.strip()

    # Türkçe tırnak ve atfedilir eklerini temizle
    for suffix in ["’a atfedilir", "’e atfedilir", "’ya atfedilir", "’ye atfedilir", "ya atfedilir", "ye atfedilir"]:
        if a.endswith(suffix):
            a = a[: -len(suffix)].strip()

    return a
