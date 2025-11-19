from typing import Optional

SOZLER = {
    "motivation": {
        "label": "💪 Motivasyon",
        "tr": [
            ("Başarı sabır ister.", "Anonim"),
            ("Vazgeçmeyen kazanır.", "Anonim"),
            ("Hayallerine sahip çık.", "Anonim"),
            ("Bugün attığın küçük adımlar, yarının büyük başarılarıdır.", "Anonim"),
            ("Her yeni gün, yeniden başlamak için bir fırsattır.", "Anonim"),
            ("Düşmekten korkma, kalkmamayı alışkanlık haline getirmekten kork.", "Anonim"),
            ("Başaramayacağını söyleyenlere bakma, denemeyen zaten kaybeder.", "Anonim"),
            ("Yorulduğunda dinlen, vazgeçme.", "Anonim"),
            ("Zor zamanlar, güçlü insanları ortaya çıkarır.", "Anonim"),
            ("Bugün pes edersen, yarın nasıl hayal kuracaksın?", "Anonim"),
        ],
        "en": [
            ("Success requires patience.", "Başarı sabır ister.", "Anonim"),
            ("Winners never quit.", "Kazananlar asla vazgeçmez.", "Anonim"),
            ("Follow your dreams.", "Hayallerinin peşinden git.", "Anonim"),
            (
                "Small steps every day lead to big changes.",
                "Her gün atılan küçük adımlar büyük değişimlere yol açar.",
                "Anonim",
            ),
            (
                "Every new day is a chance to start again.",
                "Her yeni gün, yeniden başlamak için bir fırsattır.",
                "Anonim",
            ),
            (
                "Don’t be afraid to fall, be afraid of never trying to stand up again.",
                "Düşmekten korkma, bir daha ayağa kalkmamaktan kork.",
                "Anonim",
            ),
            (
                "It always seems impossible until it’s done.",
                "Her şey yapılana kadar imkansız görünür.",
                "Nelson Mandela’ya atfedilir",
            ),
            (
                "Your only limit is you.",
                "Tek sınırın sensin.",
                "Anonim",
            ),
        ],
    },
    "love": {
        "label": "❤️ Aşk",
        "tr": [
            ("Aşk kalpten gelen bir melodidir.", "Anonim"),
            ("Seven insan sabreder.", "Anonim"),
            ("Gerçek aşk hissedilir, anlatılmaz.", "Anonim"),
            ("Kalbinin attığını hissettiren insandan vazgeçme.", "Anonim"),
            ("Aşk, iki kalbin aynı dili konuşmasıdır.", "Anonim"),
            ("Sevgi, paylaştıkça çoğalan tek servettir.", "Anonim"),
            ("En güzel aşk, seni sen yapanı sevmektir.", "Anonim"),
        ],
        "en": [
            ("Love is a melody from the heart.", "Aşk kalpten gelen bir melodidir.", "Anonim"),
            ("True love is patient.", "Gerçek aşk sabırlıdır.", "Anonim"),
            ("Love is felt, not explained.", "Aşk hissedilir, anlatılmaz.", "Anonim"),
            (
                "Never let go of the one who makes your heart beat differently.",
                "Kalbini farklı attıran kişiden vazgeçme.",
                "Anonim",
            ),
            (
                "Love is when two hearts speak the same language.",
                "Aşk, iki kalbin aynı dili konuşmasıdır.",
                "Anonim",
            ),
            (
                "The best thing to hold onto in life is each other.",
                "Hayatta tutunulacak en güzel şey birbirinizsiniz.",
                "Audrey Hepburn’e atfedilir",
            ),
        ],
    },
    "life": {
        "label": "🌿 Yaşam",
        "tr": [
            ("Hayat bir yolculuktur, varış değil.", "Anonim"),
            ("Zaman en değerli hazinemizdir.", "Anonim"),
            ("Hayat cesurları ödüllendirir.", "Anonim"),
            ("Bugün, geri kalan hayatının ilk günü.", "Anonim"),
            ("Hayat, nefes aldığın anlarla değil, nefesini kesen anlarla ölçülür.", "Anonim"),
            ("Yaşadığın her şey, olman gereken kişiye doğru bir adımdır.", "Anonim"),
        ],
        "en": [
            (
                "Life is a journey, not a destination.",
                "Hayat bir yolculuktur, varış noktası değil.",
                "Anonim",
            ),
            (
                "Time is our most valuable treasure.",
                "Zaman en değerli hazinemizdir.",
                "Anonim",
            ),
            ("Life rewards the brave.", "Hayat cesurları ödüllendirir.", "Anonim"),
            (
                "Today is the first day of the rest of your life.",
                "Bugün, geri kalan hayatının ilk günü.",
                "Anonim",
            ),
            (
                "Life is measured not by the breaths we take, but by the moments that take our breath away.",
                "Hayat, nefes aldığın anlarla değil, nefesini kesen anlarla ölçülür.",
                "Anonim",
            ),
            (
                "In the middle of difficulty lies opportunity.",
                "Zorluğun ortasında fırsat yatar.",
                "Albert Einstein’a atfedilir",
            ),
        ],
    },
    "success": {
        "label": "🏆 Başarı",
        "tr": [
            ("Başarı, hazırlanma ile fırsatın buluştuğu yerdir.", "Anonim"),
            ("Bugün yaptıkların, yarın olmak istediğin kişi içindir.", "Anonim"),
            ("Başarının sırrı, bir kez daha denemektir.", "Anonim"),
            ("Başarı, konfor alanının dışındadır.", "Anonim"),
            ("En büyük başarı, pes etmediğin anda gelir.", "Anonim"),
            ("Başarı, her gün tekrar edilen küçük çabaların toplamıdır.", "Anonim"),
        ],
        "en": [
            (
                "Success is where preparation and opportunity meet.",
                "Başarı, hazırlanma ile fırsatın buluştuğu yerdir.",
                "Anonim",
            ),
            (
                "What you do today shapes who you become tomorrow.",
                "Bugün yaptıkların, yarın olmak istediğin kişiyi şekillendirir.",
                "Anonim",
            ),
            (
                "The secret of success is to try one more time.",
                "Başarının sırrı, bir kez daha denemektir.",
                "Anonim",
            ),
            (
                "Success lives outside your comfort zone.",
                "Başarı, konfor alanının dışındadır.",
                "Anonim",
            ),
            (
                "Your greatest success comes right after you decide not to give up.",
                "En büyük başarın, pes etmemeye karar verdiğin anda gelir.",
                "Anonim",
            ),
            (
                "Success is the sum of small efforts repeated day in and day out.",
                "Başarı, her gün tekrarlanan küçük çabaların toplamıdır.",
                "Anonim",
            ),
        ],
    },
    "wisdom": {
        "label": "🧠 Bilgelik",
        "tr": [
            ("Kendini bilen, dünyayı bilir.", "Anonim"),
            ("En büyük bilgelik, ne bilmediğini bilmektir.", "Sokrates’e atfedilir"),
            ("Sessizlik de bir cevaptır.", "Anonim"),
            ("Az konuş, çok dinle; az yargıla, çok anla.", "Anonim"),
            ("Doğru sorular, doğru cevaplardan daha değerlidir.", "Anonim"),
        ],
        "en": [
            ("Knowing yourself, you know the world.", "Kendini bilen, dünyayı bilir.", "Anonim"),
            (
                "The only true wisdom is in knowing you know nothing.",
                "Gerçek bilgelik, hiçbir şey bilmediğini bilmektir.",
                "Sokrates’e atfedilir",
            ),
            ("Silence is also an answer.", "Sessizlik de bir cevaptır.", "Anonim"),
            (
                "Speak less, listen more; judge less, understand more.",
                "Az konuş, çok dinle; az yargıla, çok anla.",
                "Anonim",
            ),
            (
                "Knowing yourself is the beginning of all wisdom.",
                "Kendini bilmek, tüm bilgeliğin başlangıcıdır.",
                "Aristoteles’e atfedilir",
            ),
        ],
    },
    "friendship": {
        "label": "🤝 Dostluk",
        "tr": [
            ("Gerçek dostluk, mesafelerle zayıflamaz.", "Anonim"),
            ("Zor zamanda yanında olan, gerçek dostundur.", "Anonim"),
            ("Dost, aynadaki yansıman değil; seni sen yapan kişidir.", "Anonim"),
            ("Gerçek dost, kalabalıkta değil; yalnız kaldığında yanındadır.", "Anonim"),
            ("Birlikte gülebilmek güzel, ama birlikte susabilmek daha değerlidir.", "Anonim"),
        ],
        "en": [
            (
                "True friendship is not weakened by distance.",
                "Gerçek dostluk, mesafelerle zayıflamaz.",
                "Anonim",
            ),
            (
                "A real friend stays when others leave.",
                "Gerçek dost, herkes giderken kalan kişidir.",
                "Anonim",
            ),
            (
                "A friend is not your reflection, but the one who helps you see yourself.",
                "Dost, aynadaki yansıman değil; seni sen yapan kişidir.",
                "Anonim",
            ),
            (
                "A true friend is beside you not in crowds, but in your loneliness.",
                "Gerçek dost, kalabalıkta değil; yalnız kaldığında yanındadır.",
                "Anonim",
            ),
            (
                "Friendship doubles joy and halves sorrow.",
                "Dostluk, sevinci ikiye, üzüntüyü yarıya böler.",
                "Anonim",
            ),
        ],
    },
    "happiness": {
        "label": "😊 Mutluluk",
        "tr": [
            ("Mutluluk, şükretmeyi bilen kalptedir.", "Anonim"),
            ("Küçük şeylerden mutlu olabilen, gerçek zengindir.", "Anonim"),
            ("Mutluluk bir varış değil, yolculuktur.", "Anonim"),
            ("Mutlu olmak için büyük sebeplere değil, sakin bir kalbe ihtiyacın var.", "Anonim"),
            ("Mutluluk bazen sadece derin bir nefes alabilmektir.", "Anonim"),
        ],
        "en": [
            (
                "Happiness lives in a grateful heart.",
                "Mutluluk, şükretmeyi bilen kalptedir.",
                "Anonim",
            ),
            (
                "Those who enjoy small things are truly rich.",
                "Küçük şeylerden mutlu olabilen, gerçek zengindir.",
                "Anonim",
            ),
            (
                "Happiness is not a destination, it's a journey.",
                "Mutluluk bir varış değil, yolculuktur.",
                "Anonim",
            ),
            (
                "You don’t need big reasons to be happy, just a peaceful heart.",
                "Mutlu olmak için büyük sebeplere değil, huzurlu bir kalbe ihtiyacın var.",
                "Anonim",
            ),
            (
                "Happiness is not having all you want, but enjoying all you have.",
                "Mutluluk, istediğin her şeye sahip olmak değil; sahip olduklarının kıymetini bilmektir.",
                "Anonim",
            ),
        ],
    },
    "self": {
        "label": "🪞 Öz Farkındalık",
        "tr": [
            ("Kendini tanımak, değişimin ilk adımıdır.", "Anonim"),
            ("Olduğun kişiyi kabul etmeden, olmak istediğin kişiye dönüşemezsin.", "Anonim"),
            ("Kendine dürüst olmak, özgürlüğün başlangıcıdır.", "Anonim"),
            ("Kendini sevmek, başkalarından beklediğin sevginin provasıdır.", "Anonim"),
        ],
        "en": [
            (
                "Knowing yourself is the first step to change.",
                "Kendini tanımak, değişimin ilk adımıdır.",
                "Anonim",
            ),
            (
                "You cannot become who you want to be without accepting who you are now.",
                "Şu anki halini kabul etmeden, olmak istediğin kişiye dönüşemezsin.",
                "Anonim",
            ),
            (
                "Being honest with yourself is the beginning of freedom.",
                "Kendine dürüst olmak, özgürlüğün başlangıcıdır.",
                "Anonim",
            ),
            (
                "Loving yourself is the beginning of a lifelong romance.",
                "Kendini sevmek, ömür boyu sürecek bir aşkın başlangıcıdır.",
                "Oscar Wilde’a atfedilir",
            ),
        ],
    },
    "mindset": {
        "label": "🧩 Zihniyet",
        "tr": [
            ("Düşüncelerin, gördüğün dünyayı şekillendirir.", "Anonim"),
            ("Zihnini değiştirdiğinde, hayatın da değişir.", "Anonim"),
            ("Sınırlayan şey çoğu zaman imkanların değil, bakış açındır.", "Anonim"),
            ("Olumsuz düşünceler, geleceğini değil sadece modunu bozmaya değerdir.", "Anonim"),
        ],
        "en": [
            (
                "Your thoughts shape the world you see.",
                "Düşüncelerin, gördüğün dünyayı şekillendirir.",
                "Anonim",
            ),
            (
                "When you change your mindset, you change your life.",
                "Zihnini değiştirdiğinde, hayatın da değişir.",
                "Anonim",
            ),
            (
                "What limits you is not your possibilities, but your perspective.",
                "Seni sınırlayan çoğu zaman imkanların değil, bakış açındır.",
                "Anonim",
            ),
            (
                "Whether you think you can, or you think you can’t – you’re right.",
                "Yapabileceğini de düşünsen, yapamayacağını da düşünsen haklısın.",
                "Henry Ford’a atfedilir",
            ),
        ],
    },
    "animals": {
        "label": "🐾 Hayvanlar",
        "tr": [
            ("Bir milletin büyüklüğü, hayvanlara olan yaklaşımıyla ölçülür.", "Mahatma Gandhi’ye atfedilir"),
            ("Hayvanlar konuşamaz ama kalpleriyle anlatırlar.", "Anonim"),
            ("Bir hayvanın gözlerine bak, koşulsuz sevgiyi görürsün.", "Anonim"),
        ],
        "en": [
            (
                "The greatness of a nation can be judged by the way its animals are treated.",
                "Bir milletin büyüklüğü, hayvanlara olan yaklaşımıyla ölçülür.",
                "Mahatma Gandhi’ye atfedilir",
            ),
            (
                "Animals cannot speak, but they speak to us with their hearts.",
                "Hayvanlar konuşamaz ama kalpleriyle anlatırlar.",
                "Anonim",
            ),
            (
                "Until one has loved an animal, a part of one's soul remains unawakened.",
                "Bir hayvanı sevmedikçe, ruhunun bir parçası uyanmaz.",
                "Anatole France’a atfedilir",
            ),
        ],
    },
    "sports": {
        "label": "🏃 Spor",
        "tr": [
            ("Vücudun yapabildiklerine değil, zihnin sınırlarına takılırsın.", "Anonim"),
            ("Her antrenman, dünkü halinden daha iyi olmak içindir.", "Anonim"),
            ("Pes etmek, acıyı bitirir ama gururu da bitirir.", "Anonim"),
            ("Disiplin, motivasyonun geride bıraktığı yeri doldurur.", "Anonim"),
        ],
        "en": [
            (
                "You are limited not by your body, but by your mind.",
                "Seni sınırlayan bedenin değil, zihnindir.",
                "Anonim",
            ),
            (
                "Every training is to become better than you were yesterday.",
                "Her antrenman, dünkü halinden daha iyi olmak içindir.",
                "Anonim",
            ),
            (
                "Pain is temporary, pride is forever.",
                "Acı geçicidir, gurur kalıcıdır.",
                "Anonim",
            ),
            (
                "Discipline is choosing between what you want now and what you want most.",
                "Disiplin, şu an istediğinle en çok istediğin şey arasında seçim yapmaktır.",
                "Anonim",
            ),
        ],
    },
}


def normalize_author(yazar: Optional[str]) -> str:
    """
    \"Nelson Mandela’ya atfedilir\" -> \"Nelson Mandela\"
    """
    if not yazar:
        return "Anonim"
    yazar = yazar.strip()
    if "atfedilir" in yazar and "’" in yazar:
        return yazar.split("’")[0].strip()
    return yazar
