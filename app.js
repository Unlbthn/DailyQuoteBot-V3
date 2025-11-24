const BACKEND_URL = "http://localhost:8000"; // kendi domainine göre değiştir

const tg = window.Telegram?.WebApp;
let tgUserId = null;
let tgLangCode = null;
let appLang = "tr";
let currentTopic = "motivation";

if (tg && tg.initDataUnsafe && tg.initDataUnsafe.user) {
  tgUserId = tg.initDataUnsafe.user.id;
  tgLangCode = tg.initDataUnsafe.user.language_code;
} else {
  // test için
  tgUserId = 123456;
  tgLangCode = "tr";
}

// AdsGram controller'ları
let interstitialController = null;
let rewardController = null;

// --- Localization (sadece frontend label’ları için basit map) ---
const texts = {
  tr: {
    appTitle: "Günün Sözü",
    newQuote: "Yeni söz aç",
    rewardBtn: "🎁 Ek söz aç (Reklam izle)",
    shareWhatsApp: "WhatsApp'ta paylaş",
    shareTelegram: "Telegram'da paylaş",
    tasksLoading: "Görevler yükleniyor...",
    tasksLabel: "Günlük görevlerin:",
    topicMotivation: "Motivasyon",
    topicLove: "Aşk",
    topicSports: "Spor",
  },
  en: {
    appTitle: "Daily Quote",
    newQuote: "Open a new quote",
    rewardBtn: "🎁 Open bonus quote (watch ad)",
    shareWhatsApp: "Share on WhatsApp",
    shareTelegram: "Share on Telegram",
    tasksLoading: "Loading tasks...",
    tasksLabel: "Your daily tasks:",
    topicMotivation: "Motivation",
    topicLove: "Love",
    topicSports: "Sports",
  }
};

function applyTexts() {
  const t = texts[appLang];
  document.getElementById("app-title").innerText = t.appTitle;
  document.getElementById("btn-new-quote").innerText = t.newQuote;
  document.getElementById("btn-reward").innerText = t.rewardBtn;
  document.getElementById("btn-share-whatsapp").innerText = t.shareWhatsApp;
  document.getElementById("btn-share-telegram").innerText = t.shareTelegram;
  document.getElementById("tasks-info").innerText = t.tasksLoading;

  document.getElementById("topic-motivation").innerText = t.topicMotivation;
  document.getElementById("topic-love").innerText = t.topicLove;
  document.getElementById("topic-sports").innerText = t.topicSports;
}

function detectLangFromTelegram() {
  if (!tgLangCode) return "tr";
  if (tgLangCode.toLowerCase().startsWith("tr")) return "tr";
  return "en";
}

// --- AdsGram init ---
function initInterstitial() {
  interstitialController = window.Adsgram.init({
    blockId: "int-XXXXXX" // kendi interstitial blockId'in
  });
}

function initReward() {
  rewardController = window.Adsgram.init({
    blockId: "rw-YYYYYY" // kendi rewarded blockId'in
  });
}

async function maybeShowInterstitial(shouldShow) {
  if (!shouldShow || !interstitialController) return;
  try {
    await interstitialController.show();
  } catch (err) {
    console.warn("Interstitial ad error:", err);
  }
}

async function showRewardedAd() {
  if (!rewardController) return;
  try {
    await rewardController.show();
    // Reklam tamamlandı → backend'den ödül iste
    const res = await fetch(`${BACKEND_URL}/api/reward-quote`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: tgUserId })
    });
    const data = await res.json();
    if (data.quote) {
      document.getElementById("quote-text").innerText = data.quote;
    }
    alert(data.message || "Bonus!");
    // Rewarded izlenince görev güncellemesi backend'de zaten yapılıyor
    await loadTasks();
  } catch (err) {
    console.warn("Rewarded cancelled or error:", err);
  }
}

// --- API Calls ---
async function startApp() {
  const res = await fetch(`${BACKEND_URL}/api/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: tgUserId,
      language_code: tgLangCode
    })
  });
  const data = await res.json();
  appLang = data.lang;
  currentTopic = data.current_topic;
  applyTexts();
  document.getElementById("quote-text").innerText = data.initial_quote;
  await maybeShowInterstitial(data.show_ad);
  highlightCurrentTopic();
  await loadTasks();
}

async function getNewQuote() {
  const res = await fetch(`${BACKEND_URL}/api/new_quote`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: tgUserId,
      topic: currentTopic
    })
  });
  const data = await res.json();
  document.getElementById("quote-text").innerText = data.quote;
  await maybeShowInterstitial(data.show_ad);
  await loadTasks();
}

async function changeTopic(topic) {
  currentTopic = topic;
  highlightCurrentTopic();
  const res = await fetch(`${BACKEND_URL}/api/change_topic`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: tgUserId,
      topic: currentTopic
    })
  });
  const data = await res.json();
  document.getElementById("quote-text").innerText = data.quote;
  await maybeShowInterstitial(data.show_ad);
}

async function addFavorite() {
  const quote = document.getElementById("quote-text").innerText;
  await fetch(`${BACKEND_URL}/api/favorites/add`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: tgUserId,
      quote
    })
  });
  alert(appLang === "tr" ? "Favorilere eklendi." : "Added to favorites.");
}

async function showFavorites() {
  const res = await fetch(`${BACKEND_URL}/api/favorites/list`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: tgUserId })
  });
  const data = await res.json();
  if (!data.favorites || data.favorites.length === 0) {
    alert(appLang === "tr" ? "Henüz favorin yok." : "No favorites yet.");
    return;
  }
  alert(data.favorites.join("\n\n"));
}

async function loadTasks() {
  const res = await fetch(`${BACKEND_URL}/api/tasks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: tgUserId })
  });
  const data = await res.json();
  const t = texts[appLang];
  const lines = [t.tasksLabel];
  data.tasks.forEach(task => {
    const status = task.completed
      ? (appLang === "tr" ? "Tamamlandı" : "Done")
      : `${task.progress}/${task.target}`;
    lines.push(`• ${task.title} — ${status}`);
  });
  document.getElementById("tasks-info").innerText = lines.join("\n");
}

// --- Test flow (özet) ---
async function startTest() {
  const res = await fetch(`${BACKEND_URL}/api/test/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: tgUserId })
  });
  const data = await res.json();
  // Basit: sadece 2 soruyu konsola yazıyoruz.
  console.log("Test questions:", data.questions);
  alert(appLang === "tr"
    ? "Mini test örnek: Konsole bak (gerçekte burada ayrı ekran açarsın)."
    : "Mini test example: Check console (you would create a separate screen)."
  );

  // Örnek cevap: hep orta seçeneği işaretle
  const answers = [1, 1];
  const res2 = await fetch(`${BACKEND_URL}/api/test/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: tgUserId,
      answers
    })
  });
  const result = await res2.json();
  alert(result.message);
}

// --- Sharing ---
function shareWhatsApp() {
  const quote = document.getElementById("quote-text").innerText;
  const url = `https://wa.me/?text=${encodeURIComponent(quote)}`;
  window.open(url, "_blank");
  trackShare();
}

function shareTelegram() {
  const quote = document.getElementById("quote-text").innerText;
  const url = `https://t.me/share/url?url=&text=${encodeURIComponent(quote)}`;
  window.open(url, "_blank");
  trackShare();
}

async function trackShare() {
  await fetch(`${BACKEND_URL}/api/tasks/share`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: tgUserId })
  });
  await loadTasks();
}

// --- Dropdown menu ---
function toggleMenu() {
  const menu = document.getElementById("dropdown-menu");
  menu.classList.toggle("show");
}

function highlightCurrentTopic() {
  const ids = ["topic-motivation", "topic-love", "topic-sports"];
  ids.forEach(id => {
    const el = document.getElementById(id);
    el.classList.remove("active");
  });
  if (currentTopic === "motivation") {
    document.getElementById("topic-motivation").classList.add("active");
  } else if (currentTopic === "love") {
    document.getElementById("topic-love").classList.add("active");
  } else if (currentTopic === "sports") {
    document.getElementById("topic-sports").classList.add("active");
  }
}

// --- Language toggle ---
function toggleLanguage() {
  appLang = appLang === "tr" ? "en" : "tr";
  applyTexts();
  loadTasks();
}

// --- Init ---
document.addEventListener("DOMContentLoaded", () => {
  if (tg) tg.ready();

  appLang = detectLangFromTelegram();
  applyTexts();

  initInterstitial();
  initReward();
  startApp();

  document.getElementById("btn-new-quote").onclick = getNewQuote;
  document.getElementById("btn-reward").onclick = showRewardedAd;
  document.getElementById("btn-share-whatsapp").onclick = shareWhatsApp;
  document.getElementById("btn-share-telegram").onclick = shareTelegram;

  document.getElementById("menu-button").onclick = toggleMenu;

  document.getElementById("topic-motivation").onclick = () => changeTopic("motivation");
  document.getElementById("topic-love").onclick = () => changeTopic("love");
  document.getElementById("topic-sports").onclick = () => changeTopic("sports");

  const menu = document.getElementById("dropdown-menu");
  menu.addEventListener("click", (e) => {
    const action = e.target.getAttribute("data-action");
    if (!action) return;
    menu.classList.remove("show");

    if (action === "change-topic") {
      // zaten topic pill'ler var, burada belki ayrı modal açarsın
      alert(appLang === "tr" ? "Konu yukarıdan değiştirilebilir." : "You can change topic from the top.");
    } else if (action === "add-favorite") {
      addFavorite();
    } else if (action === "show-favorites") {
      showFavorites();
    } else if (action === "start-test") {
      startTest();
    } else if (action === "change-language") {
      toggleLanguage();
    }
  });
});
