import csv
import os


SOZLER = {

    "motivation": {
        "label_tr": "Motivasyon",
        "label_en": "Motivation",
        "tr": [
            ("Başarı sabır ister.", "Anonim"),
            ("Vazgeçmeyen kazanır.", "Anonim"),
            ("Bugün attığın küçük adımlar, yarının büyük başarılarıdır.", "Anonim"),
            ("Her yeni gün yeniden başlamak için bir fırsattır.", "Anonim"),
            ("Düşmekten korkma, kalkmamayı alışkanlık haline getirmekten kork.", "Anonim"),
            ("Zorluklar seni durdurmak için değil, güçlendirmek için vardır.", "Anonim"),
            ("En karanlık an, şafaktan hemen önce gelir.", "Anonim"),
            ("Kendine inandığında her şey mümkün olur.", "Anonim"),
            ("Büyük hayaller büyük cesaret ister.", "Anonim"),
            ("Başlamanın yolu konuşmayı bırakıp yapmaya başlamaktır.", "Walt Disney"),
        ],
        "en": [
            ("Success requires patience.", "", "Anonim"),
            ("Winners never quit.", "", "Anonim"),
            ("Small steps every day lead to big changes.", "", "Anonim"),
            ("Every new day is a chance to begin again.", "", "Anonim"),
            ("Difficulties make you stronger.", "", "Anonim"),
            ("The darkest hour is just before dawn.", "", "Anonim"),
            ("Believe in yourself and everything is possible.", "", "Anonim"),
            ("Dream big. Act bigger.", "", "Anonim"),
            ("The way to get started is to stop talking and start doing.", "", "Walt Disney"),
        ],
    },

    "love": {
        "label_tr": "Aşk",
        "label_en": "Love",
        "tr": [
            ("Aşk kalpten gelen bir melodidir.", "Anonim"),
            ("Gerçek aşk anlatılmaz, hissedilir.", "Anonim"),
            ("Aşk iki insanın tek bir ruhta buluşmasıdır.", "Anonim"),
            ("Seven insan sabreder.", "Anonim"),
            ("Aşk paylaştıkça büyür.", "Anonim"),
            ("Kalbini hızlı attıran insanı kaybetme.", "Anonim"),
        ],
        "en": [
            ("Love is a melody from the heart.", "", "Anonim"),
            ("True love is felt, not explained.", "", "Anonim"),
            ("Love is two souls meeting as one.", "", "Anonim"),
            ("Love grows when shared.", "", "Anonim"),
            ("Hold onto the one who makes your heart beat differently.", "", "Anonim"),
        ],
    },

    "life": {
        "label_tr": "Yaşam",
        "label_en": "Life",
        "tr": [
            ("Hayat bir yolculuktur, varış noktası değil.", "Anonim"),
            ("Zaman en değerli hazinedir.", "Anonim"),
            ("Hayat cesurları ödüllendirir.", "Anonim"),
            ("Bugün geri kalan hayatının ilk günü.", "Anonim"),
            ("Yaşadığın her şey seni dönüştürür.", "Anonim"),
            ("Hayat nefes almakla değil, nefesini kesen anlarla ölçülür.", "Anonim"),
        ],
        "en": [
            ("Life is a journey, not a destination.", "", "Anonim"),
            ("Time is our most valuable treasure.", "", "Anonim"),
            ("Life rewards the brave.", "", "Anonim"),
            ("Today is the first day of the rest of your life.", "", "Anonim"),
            ("Life is measured in moments that take your breath away.", "", "Anonim"),
        ],
    },

    "success": {
        "label_tr": "Başarı",
        "label_en": "Success",
        "tr": [
            ("Başarı hazırlanma ve fırsatın buluştuğu yerdir.", "Anonim"),
            ("Başarı, tekrar eden küçük çabaların toplamıdır.", "Anonim"),
            ("Konfor alanının dışına çıkmadan başarı gelmez.", "Anonim"),
            ("Pes eden kaybeder, devam eden kazanır.", "Anonim"),
            ("Başarının sırrı bir kez daha denemektir.", "Anonim"),
        ],
        "en": [
            ("Success is where preparation meets opportunity.", "", "Seneca"),
            ("Success is the sum of small efforts repeated day in and day out.", "", "Anonim"),
            ("Success lives outside your comfort zone.", "", "Anonim"),
            ("Winners are simply those who never gave up.", "", "Anonim"),
            ("The secret of success is to try one more time.", "", "Thomas Edison"),
        ],
    },

    "wisdom": {
        "label_tr": "Bilgelik",
        "label_en": "Wisdom",
        "tr": [
            ("En büyük bilgelik ne bilmediğini bilmektir.", "Sokrates’e atfedilir"),
            ("Sessizlik de bir cevaptır.", "Anonim"),
            ("Kendini bilen dünyayı bilir.", "Anonim"),
            ("Doğru sorular doğru cevaplardan değerlidir.", "Anonim"),
            ("Bilgelik deneyimden gelir.", "Anonim"),
        ],
        "en": [
            ("The only true wisdom is in knowing you know nothing.", "", "Socrates’e atfedilir"),
            ("Silence is also an answer.", "", "Anonim"),
            ("Knowing yourself is the beginning of wisdom.", "", "Aristotle’a atfedilir"),
            ("Wisdom comes from experience.", "", "Anonim"),
            ("The wise speak because they have something to say.", "", "Plato’ya atfedilir"),
        ],
    },

    "friendship": {
        "label_tr": "Dostluk",
        "label_en": "Friendship",
        "tr": [
            ("Gerçek dostluk mesafelerle zayıflamaz.", "Anonim"),
            ("Zor zamanda yanında olan gerçek dosttur.", "Anonim"),
            ("Dost, aynadaki yansıman değil seni sen yapan kişidir.", "Anonim"),
        ],
        "en": [
            ("True friendship is not weakened by distance.", "", "Anonim"),
            ("A true friend stays when others leave.", "", "Anonim"),
            ("A friend is someone who helps you be yourself.", "", "Anonim"),
        ],
    },

    "happiness": {
        "label_tr": "Mutluluk",
        "label_en": "Happiness",
        "tr": [
            ("Mutluluk şükredebilmekten gelir.", "Anonim"),
            ("Küçük şeylerden mutlu olabilen gerçek zengindir.", "Anonim"),
            ("Mutluluk bir varış değil, yolculuktur.", "Anonim"),
        ],
        "en": [
            ("Happiness lives in a grateful heart.", "", "Anonim"),
            ("Those who enjoy small things are truly rich.", "", "Anonim"),
            ("Happiness is a journey, not a destination.", "", "Anonim"),
        ],
    },

    "self": {
        "label_tr": "Öz Farkındalık",
        "label_en": "Self-awareness",
        "tr": [
            ("Kendini tanımak değişimin ilk adımıdır.", "Anonim"),
            ("Kendine dürüst olmak özgürlüğün başlangıcıdır.", "Anonim"),
            ("Kendini sevmek bir ömür sürecek aşkın başlangıcıdır.", "Oscar Wilde’a atfedilir"),
        ],
        "en": [
            ("Knowing yourself is the first step to change.", "", "Anonim"),
            ("Being honest with yourself is the beginning of freedom.", "", "Anonim"),
            ("To love oneself is the beginning of a lifelong romance.", "", "Oscar Wilde’a atfedilir"),
        ],
    },

    "mindset": {
        "label_tr": "Zihniyet",
        "label_en": "Mindset",
        "tr": [
            ("Zihnini değiştirdiğinde hayatın da değişir.", "Anonim"),
            ("Düşüncelerin dünyanı şekillendirir.", "Anonim"),
            ("Engeller çoğu zaman bakış açısından kaynaklanır.", "Anonim"),
        ],
        "en": [
            ("Change your mindset, change your life.", "", "Anonim"),
            ("Your thoughts shape your world.", "", "Anonim"),
            ("Limitations are often in perspective, not reality.", "", "Anonim"),
        ],
    },

    "animals": {
        "label_tr": "Hayvanlar",
        "label_en": "Animals",
        "tr": [
            ("Hayvanlar konuşamaz ama kalpleriyle anlatırlar.", "Anonim"),
            ("Bir hayvanın gözlerinde koşulsuz sevgiyi görürsün.", "Anonim"),
        ],
        "en": [
            ("Animals cannot speak, but they speak with their hearts.", "", "Anonim"),
            ("In an animal's eyes you see pure love.", "", "Anonim"),
        ],
    },

    "sports": {
        "label_tr": "Spor",
        "label_en": "Sports",
        "tr": [
            ("Seni sınırlayan bedenin değil zihnindir.", "Anonim"),
            ("Her antrenman dünden daha iyi olmak içindir.", "Anonim"),
            ("Acı geçici, gurur kalıcıdır.", "Anonim"),
        ],
        "en": [
            ("You are limited not by your body but by your mind.", "", "Anonim"),
            ("Every training is to be better than yesterday.", "", "Anonim"),
            ("Pain is temporary, pride is forever.", "", "Anonim"),
        ],
    },

    "discipline": {
        "label_tr": "Disiplin",
        "label_en": "Discipline",
        "tr": [
            ("Disiplin, motivasyonun geride bıraktığı yeri doldurur.", "Anonim"),
            ("İstikrarlı olan kazanır.", "Anonim"),
            ("Her gün daha iyi olmak için çalış.", "Anonim"),
        ],
        "en": [
            ("Discipline fills the gap where motivation fades.", "", "Anonim"),
            ("Consistency wins.", "", "Anonim"),
            ("Work every day to become better.", "", "Anonim"),
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

    endings = [
        "’a atfedilir",
        "’e atfedilir",
        "’ya atfedilir",
        "’ye atfedilir",
        " ya atfedilir",
        " ye atfedilir",
    ]
    for e in endings:
        if a.endswith(e):
            a = a[: -len(e)].strip()

    return a



def extend_from_csv(csv_path: str = "quotes_extra.csv") -> None:
    """
    quotes_extra.csv dosyasından ek sözleri SOZLER yapısına ekler.
    Dosya yoksa sessizce geçer.

    CSV başlıkları:
      category_key, lang, text, tr_text, author

    - category_key: motivation, love, life, success, ... (veya yeni kategori)
    - lang: 'tr' veya 'en'
    - text: sözün metni (ilgili dilde)
    - tr_text: (opsiyonel) İngilizce sözler için Türkçe çeviri
    - author: (opsiyonel) boşsa 'Anonim' olarak kaydedilir
    """
    if not os.path.exists(csv_path):
        return

    try:
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                category_key = (row.get("category_key") or "").strip().lower()
                lang = (row.get("lang") or "").strip().lower()
                text = (row.get("text") or "").strip()
                tr_text = (row.get("tr_text") or "").strip()
                author = (row.get("author") or "").strip() or "Anonim"

                if not category_key or not lang or not text:
                    continue

                if category_key not in SOZLER:
                    # Yeni kategori ise basit bir label ile oluştur
                    base_label = category_key.title()
                    SOZLER[category_key] = {
                        "label_tr": base_label,
                        "label_en": base_label,
                        "tr": [],
                        "en": [],
                    }

                if lang == "tr":
                    # Türkçe söz: (metin, yazar)
                    SOZLER[category_key]["tr"].append((text, author))
                elif lang == "en":
                    # İngilizce söz: (metin_en, metin_tr_ceviri, yazar)
                    SOZLER[category_key]["en"].append((text, tr_text, author))
    except Exception as e:
        print("CSV'den söz yüklenirken hata:", e)


# Modül import edildiğinde CSV'den ek sözleri yükle
extend_from_csv()

