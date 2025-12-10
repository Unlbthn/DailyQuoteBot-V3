# quotes.py
# -*- coding: utf-8 -*-

# QUOTES[(lang, topic)] => list of {"text": "...", "author": "..."}

QUOTES = {
    # MOTIVATION
    ("tr", "motivation"): [
        {"text": "Başarı, hazırlık ile fırsatın buluştuğu yerdir.", "author": "Seneca"},
        {"text": "Hedefi olmayan rüzgarla savrulur.", "author": ""},
        {"text": "Yapabileceğine inan; başarmanın yarısı budur.", "author": "Theodore Roosevelt"},
    ],
    ("en", "motivation"): [
        {"text": "You can do anything you set your mind to.", "author": ""},
        {"text": "Great things never come from comfort zones.", "author": ""},
        {"text": "Dream big. Start small. Act now.", "author": ""},
    ],

    # SUCCESS
    ("tr", "success"): [
        {"text": "Zafer, hazırlanmış olanlarındır.", "author": "Herodot"},
        {"text": "Başarıya giden yol, küçük adımlarla başlar.", "author": ""},
    ],
    ("en", "success"): [
        {"text": "Success usually comes to those who are too busy to be looking for it.", "author": "Henry David Thoreau"},
        {"text": "Success is the sum of small efforts repeated day in and day out.", "author": ""},
    ],

    # SELF-CARE
    ("tr", "selfcare"): [
        {"text": "Kendine iyi bakmak bir lüks değil, zorunluluktur.", "author": ""},
        {"text": "Kendin için zaman ayır; yeniden doğarsın.", "author": ""},
    ],
    ("en", "selfcare"): [
        {"text": "You can’t pour from an empty cup.", "author": ""},
        {"text": "Self-care is how you take your power back.", "author": ""},
    ],

    # DISCIPLINE
    ("tr", "discipline"): [
        {"text": "Disiplin, özgürlüğün kapısıdır.", "author": ""},
        {"text": "Her gün küçük adımlar, büyük sonuçlar doğurur.", "author": ""},
    ],
    ("en", "discipline"): [
        {"text": "We are what we repeatedly do. Excellence, then, is not an act but a habit.", "author": "Aristotle"},
        {"text": "Discipline is choosing between what you want now and what you want most.", "author": ""},
    ],

    # RESILIENCE
    ("tr", "resilience"): [
        {"text": "Güçlü olmak, asla düşmemek değil; her düştüğünde kalkabilmektir.", "author": ""},
        {"text": "Düşmek kaderindir ama kalkmak tercihindir.", "author": ""},
    ],
    ("en", "resilience"): [
        {"text": "Fall seven times, stand up eight.", "author": "Japanese Proverb"},
        {"text": "Tough times don’t last; tough people do.", "author": "Robert H. Schuller"},
    ],

    # CAREER
    ("tr", "career"): [
        {"text": "Zaman, geri alamadığın tek sermayedir; nereye harcadığına dikkat et.", "author": ""},
        {"text": "Kariyer, tesadüf değil, tercihlerinin toplamıdır.", "author": ""},
    ],
    ("en", "career"): [
        {"text": "Choose a job you love, and you will never have to work a day in your life.", "author": "Confucius"},
        {"text": "Opportunities don't happen. You create them.", "author": ""},
    ],

    # LOVE
    ("tr", "love"): [
        {"text": "Gerçek aşk, kusurları kabul edebilme cesaretidir.", "author": ""},
        {"text": "Sevgi paylaştıkça çoğalır.", "author": ""},
    ],
    ("en", "love"): [
        {"text": "Where there is love, there is life.", "author": "Mahatma Gandhi"},
        {"text": "Love is composed of a single soul inhabiting two bodies.", "author": "Aristotle"},
    ],

    # LIFE
    ("tr", "life"): [
        {"text": "Hayat kısa; gülümsemediğin her an kayıptır.", "author": ""},
        {"text": "Bugün, hayatının geri kalanının ilk günü.", "author": ""},
    ],
    ("en", "life"): [
        {"text": "Life is what happens while you are busy making other plans.", "author": "John Lennon"},
        {"text": "In the end, we only regret the chances we didn’t take.", "author": ""},
    ],

    # SPORT – Türkçe (senin gönderdiğin setten örnekler)
    ("tr", "sport"): [
        {"text": "Kelebek gibi uçar, arı gibi sokarım.", "author": "Muhammed Ali"},
        {"text": "Zorluklar, şampiyonları belirler.", "author": ""},
        {"text": "Ter, başarıya açılan kapının anahtarıdır.", "author": ""},
        {"text": "Kaybetmekten korkma; denememekten kork.", "author": ""},
        {"text": "Disiplin, yeteneği yener.", "author": ""},
        {"text": "İmkânsız sadece daha uzun süren bir şeydir.", "author": "Muhammed Ali"},
        {"text": "Bugün acı çek, yarın şampiyon ol.", "author": ""},
        {"text": "Başarı tesadüf değildir; emek ister.", "author": "Michael Jordan"},
        {"text": "En büyük rakibin dünkü halindir.", "author": ""},
        {"text": "Zafer, inananlarındır.", "author": "Mustafa Kemal Atatürk"},
    ],

    # SPORT – English
    ("en", "sport"): [
        {"text": "I float like a butterfly, I sting like a bee.", "author": "Muhammad Ali"},
        {"text": "Success is no accident.", "author": "Pelé"},
        {"text": "Champions keep playing until they get it right.", "author": "Billie Jean King"},
        {"text": "You miss 100% of the shots you don’t take.", "author": "Wayne Gretzky"},
        {"text": "Don’t stop when you’re tired. Stop when you’re done.", "author": ""},
        {"text": "Every champion was once a beginner.", "author": "Muhammad Ali"},
    ],

    # FRIENDSHIP
    ("tr", "friendship"): [
        {"text": "Gerçek dost, iki beden arasında yaşayan tek ruhtur.", "author": ""},
        {"text": "Yanında yürüyen bir dost, yolu kısaltır.", "author": ""},
    ],
    ("en", "friendship"): [
        {"text": "A real friend is one who walks in when the rest of the world walks out.", "author": ""},
        {"text": "Friendship doubles joys and halves griefs.", "author": ""},
    ],

    # CREATIVITY
    ("tr", "creativity"): [
        {"text": "Yaratıcılık, zekânın eğlenmesidir.", "author": "Albert Einstein"},
        {"text": "Farklı düşünmek, yeni kapılar açar.", "author": ""},
    ],
    ("en", "creativity"): [
        {"text": "Creativity takes courage.", "author": "Henri Matisse"},
        {"text": "You can’t use up creativity. The more you use, the more you have.", "author": "Maya Angelou"},
    ],

    # GRATITUDE
    ("tr", "gratitude"): [
        {"text": "Şükreden kalp huzur bulur.", "author": ""},
        {"text": "Sahip olduklarının farkına varmak, mutluluğun anahtarıdır.", "author": ""},
    ],
    ("en", "gratitude"): [
        {"text": "Gratitude turns what we have into enough.", "author": ""},
        {"text": "Start each day with a grateful heart.", "author": ""},
    ],
}
