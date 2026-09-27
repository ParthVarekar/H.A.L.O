const OWNER_KEY = "halo-voice-owner";
const OWNER_STALE_MS = 3000;
const HEARTBEAT_MS = 1000;
const WATCHDOG_BASE_MS = 2500;
const WATCHDOG_PER_WORD_MS = 450;

const tabId = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;

function readOwner() {
  try {
    return JSON.parse(window.localStorage.getItem(OWNER_KEY) || "null");
  } catch {
    return { id: tabId, at: Date.now() };
  }
}

function writeOwner() {
  try {
    window.localStorage.setItem(OWNER_KEY, JSON.stringify({ id: tabId, at: Date.now() }));
  } catch {
    return;
  }
}

function ownerIsStale(owner) {
  return !owner || Date.now() - owner.at > OWNER_STALE_MS;
}

export function ownsVoice() {
  return readOwner()?.id === tabId;
}

export function startVoiceOwnership() {
  const claim = () => writeOwner();
  const heartbeat = () => {
    const owner = readOwner();
    if (owner?.id === tabId) writeOwner();
    else if (ownerIsStale(owner) && document.visibilityState === "visible") writeOwner();
  };
  const release = () => {
    if (ownsVoice()) {
      try {
        window.localStorage.removeItem(OWNER_KEY);
      } catch {
        return;
      }
    }
  };
  if (ownerIsStale(readOwner()) || document.hasFocus()) claim();
  const timer = window.setInterval(heartbeat, HEARTBEAT_MS);
  window.addEventListener("focus", claim);
  window.addEventListener("pointerdown", claim);
  window.addEventListener("keydown", claim);
  window.addEventListener("pagehide", release);
  return () => {
    window.clearInterval(timer);
    window.removeEventListener("focus", claim);
    window.removeEventListener("pointerdown", claim);
    window.removeEventListener("keydown", claim);
    window.removeEventListener("pagehide", release);
    release();
  };
}

const LANGUAGE_TAGS = { en: ["en-in", "en-gb", "en-us", "en"], hi: ["hi-in", "hi"] };

function localVoices() {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) return [];
  return window.speechSynthesis.getVoices().filter((voice) => voice.localService);
}

export function pickVoice(lang) {
  const voices = localVoices();
  for (const tag of LANGUAGE_TAGS[lang] || [lang]) {
    const match = voices.find((voice) => voice.lang.toLowerCase().replace("_", "-").startsWith(tag));
    if (match) return match;
  }
  return null;
}

export function hasLocalVoice(lang) {
  return pickVoice(lang) !== null;
}

export function watchVoices(onChange) {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) return () => undefined;
  const notify = () => onChange(localVoices().map((voice) => voice.lang));
  notify();
  window.speechSynthesis.addEventListener("voiceschanged", notify);
  return () => window.speechSynthesis.removeEventListener("voiceschanged", notify);
}

export class Announcer {
  constructor(rate) {
    this.rate = rate;
    this.lang = "en";
    this.queue = [];
    this.current = null;
    this.watchdog = null;
  }

  get available() {
    return typeof window !== "undefined" && "speechSynthesis" in window;
  }

  setLanguage(lang) {
    this.lang = lang;
  }

  enqueue(text, kind = "info") {
    if (!this.available || !text) return;
    const item = { text, kind };
    if (kind === "alert") {
      let insertAt = 0;
      while (insertAt < this.queue.length && this.queue[insertAt].kind === "alert") insertAt += 1;
      this.queue.splice(insertAt, 0, item);
    } else {
      this.queue.push(item);
    }
    this.flush();
  }

  clear() {
    this.queue = [];
    this.current = null;
    window.clearTimeout(this.watchdog);
    if (this.available) window.speechSynthesis.cancel();
  }

  flush() {
    if (this.current || this.queue.length === 0) return;
    const item = this.queue.shift();
    const utterance = new SpeechSynthesisUtterance(item.text);
    utterance.rate = this.rate;
    const voice = pickVoice(this.lang);
    if (voice) {
      utterance.voice = voice;
      utterance.lang = voice.lang;
    }
    const token = { item };
    this.current = token;
    const finish = () => {
      if (this.current !== token) return;
      window.clearTimeout(this.watchdog);
      this.current = null;
      this.flush();
    };
    utterance.onend = finish;
    utterance.onerror = finish;
    const words = item.text.split(/\s+/).length;
    this.watchdog = window.setTimeout(() => {
      if (this.current !== token) return;
      window.speechSynthesis.cancel();
      finish();
    }, WATCHDOG_BASE_MS + words * WATCHDOG_PER_WORD_MS);
    window.speechSynthesis.speak(utterance);
  }
}
