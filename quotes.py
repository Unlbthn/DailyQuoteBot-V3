# quotes.py

from typing import Dict, List, Tuple

# SOZLER yapısı:
# {
#   "category_key": {
#       "label_tr": "Türkçe İsim",
#       "label_en": "English Name",
#       "tr": [("Metin", "Yazar (veya '')"), ...],
#       "en": [("Text EN", "Metin TR", "Author (veya '')"), ...],
#   },
#   ...
# }

SOZLER: Dict[str, Dict[str, object]] = {
    "motivation": {
        "label_tr": "Motivasyon",
        "label_en": "Motivation",
        "tr": [
            ("Başladığın işi bitirene kadar pes etme.", ""),
            ("Bugün attığın küçük adımlar, yarının büyük değişimini hazırlar.", ""),
            ("Her yeni gün, yeniden başlamak için bir fırsattır.", ""),
            ("Zorlanıyorsan, güçleniyorsun demektir.", ""),
            ("Hayallerin, konfor alanından daha değerlidir.", ""),
        ],
        "en": [
            ("Keep going until you finish what you started.", "Başladığın işi bitirene kadar pes etme.", ""),
            ("Small steps today prepare big changes tomorrow.", "Bugün attığın küçük adımlar, yarının büyük değişimini hazırlar.", ""),
            ("Every new day is a chance to start again.", "Her yeni gün, yeniden başlamak için bir fırsattır.", ""),
            ("If it’s challenging, it’s changing you.", "Zorlanıyorsan, güçleniyorsun demektir.", ""),
            ("Your dreams are worth more than your comfort zone.", "Hayallerin, konfor alanından daha değerlidir.", ""),
        ],
    },
    "life": {
        "label_tr": "Yaşam",
        "label_en": "Life",
        "tr": [
            ("Hayat, cevaplardan çok sorularla anlam kazanır.", ""),
            ("Zaman, geri alamadığın tek sermayendir.", ""),
            ("Bugün, geri kalan hayatının ilk günü.", ""),
            ("Hayat, planladıkların değil; başına gelenlere verdiğin tepkidir.", ""),
        ],
        "en": [
            ("Life finds meaning more in questions than in answers.", "Hayat, cevaplardan çok sorularla anlam kazanır.", ""),
            ("Time is the only capital you can never get back.", "Zaman, geri alamadığın tek sermayendir.", ""),
            ("Today is the first day of the rest of your life.", "Bugün, geri kalan hayatının ilk günü.", ""),
            ("Life is not what happens in your plans, but how you respond when plans change.", "Hayat, planladıkların değil; başına gelenlere verdiğin tepkidir.", ""),
        ],
    },
    "success": {
        "label_tr": "Başarı",
        "label_en": "Success",
        "tr": [
            ("Başarı, her gün tekrarlanan küçük çabaların toplamıdır.", ""),
            ("Hazırlık yoksa şans da işe yaramaz.", ""),
            ("En büyük başarı, vazgeçmediğin o son denemede saklıdır.", ""),
        ],
        "en": [
            ("Success is the sum of small efforts repeated every day.", "Başarı, her gün tekrarlanan küçük çabaların toplamıdır.", ""),
            ("Without preparation, even luck can’t help you.", "Hazırlık yoksa şans da işe yaramaz.", ""),
            ("Your greatest success is hidden in the attempt where you decided not to give up.", "En büyük başarı, vazgeçmediğin o son denemede saklıdır.", ""),
        ],
    },
    "wisdom": {
        "label_tr": "Bilgelik",
        "label_en": "Wisdom",
        "tr": [
            ("Kendini tanımak, değişimin ilk adımıdır.", ""),
            ("Ne düşündüğün değil, neyi fark ettiğin hayatını değiştirir.", ""),
            ("Sessizlik bazen en güçlü cevaptır.", ""),
        ],
        "en": [
            ("Knowing yourself is the first step to change.", "Kendini tanımak, değişimin ilk adımıdır.", ""),
            ("It’s not what you think, but what you realize that changes your life.", "Ne düşündüğün değil, neyi fark ettiğin hayatını değiştirir.", ""),
            ("Sometimes silence is the strongest answer.", "Sessizlik bazen en güçlü cevaptır.", ""),
        ],
    },
    "friendship": {
        "label_tr": "Dostluk",
        "label_en": "Friendship",
        "tr": [
            ("Zor günlerinde yanında kalanlar, gerçek dostlarındır.", ""),
            ("Bir dost, aynaya değil kalbine bakandır.", ""),
        ],
        "en": [
            ("Those who stay in your hardest days are your true friends.", "Zor günlerinde yanında kalanlar, gerçek dostlarındır.", ""),
            ("A real friend looks not at your mirror, but at your heart.", "Bir dost, aynaya değil kalbine bakandır.", ""),
        ],
    },
    "happiness": {
        "label_tr": "Mutluluk",
        "label_en": "Happiness",
        "tr": [
            ("Mutluluk, çoğu zaman yavaşlayınca fark ettiğin şeydir.", ""),
            ("Şükrettiğin şeyler, hayatının en parlak tarafları olur.", ""),
        ],
        "en": [
            ("Happiness is often what you notice only when you slow down.", "Mutluluk, çoğu zaman yavaşlayınca fark ettiğin şeydir.", ""),
            ("What you are grateful for becomes the brightest part of your life.", "Şükrettiğin şeyler, hayatının en parlak tarafları olur.", ""),
        ],
    },
    "self": {
        "label_tr": "Öz Farkındalık",
        "label_en": "Self-awareness",
        "tr": [
            ("Kendine karşı dürüst olmadığın sürece özgür değilsin.", ""),
            ("Kendini sevmek, başkalarından beklediğin sevginin provasıdır.", ""),
        ],
        "en": [
            ("As long as you are not honest with yourself, you are not free.", "Kendine karşı dürüst olmadığın sürece özgür değilsin.", ""),
            ("Loving yourself is the rehearsal for the love you expect from others.", "Kendini sevmek, başkalarından beklediğin sevginin provasıdır.", ""),
        ],
    },
    "mindset": {
        "label_tr": "Zihniyet",
        "label_en": "Mindset",
        "tr": [
            ("Bakış açını değiştirdiğinde hikâyen de değişir.", ""),
            ("Seni sınırlayan, çoğu zaman imkanların değil düşüncelerindir.", ""),
        ],
        "en": [
            ("When you change your perspective, your story changes.", "Bakış açını değiştirdiğinde hikâyen de değişir.", ""),
            ("What limits you is usually not your possibilities, but your thoughts.", "Seni sınırlayan, çoğu zaman imkanların değil düşüncelerindir.", ""),
        ],
    },
    "animals": {
        "label_tr": "Hayvanlar",
        "label_en": "Animals",
        "tr": [
            ("Bir hayvanın gözlerine baktığında, koşulsuz sevgiyi görebilirsin.", ""),
            ("Hayvanlar konuşmaz ama kalbinle dinlersen çok şey anlatırlar.", ""),
        ],
        "en": [
            ("When you look into an animal’s eyes, you can see unconditional love.", "Bir hayvanın gözlerine baktığında, koşulsuz sevgiyi görebilirsin.", ""),
            ("Animals can’t speak, but if you listen with your heart, they tell you a lot.", "Hayvanlar konuşmaz ama kalbinle dinlersen çok şey anlatırlar.", ""),
        ],
    },
    "sports": {
        "label_tr": "Spor",
        "label_en": "Sports",
        "tr": [
            ("Vücudun değil, zihnin yorulduğunda pes edersin.", ""),
            ("Her antrenman, dünkü halinden daha güçlü bir seni inşa eder.", ""),
        ],
        "en": [
            ("You don’t quit when your body is tired, you quit when your mind is.", "Vücudun değil, zihnin yorulduğunda pes edersin.", ""),
            ("Every training builds a stronger version of you than yesterday.", "Her antrenman, dünkü halinden daha güçlü bir seni inşa eder.", ""),
        ],
    },
}


def normalize_author(author: str) -> str:
    """Yazar bilgisini sadeleştir. Boşsa '' döndür."""
    if not author:
        return ""
    a = author.strip()
    return a
