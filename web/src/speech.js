const lower = (text) => (text && /^[A-Z][a-z]/.test(text) ? text.charAt(0).toLowerCase() + text.slice(1) : text);
const sentence = (text) => (text ? text.replace(/[.।\s]+$/, "") : "");

const PHRASES = {
  en: {
    step: (number) => `Step ${number}`,
    recognised: (name) => `Recognised ${name}. Monitoring.`,
    selected: (name) => `Selected ${name}. Monitoring.`,
    started: (name) => `Monitoring ${name}.`,
    unavailable: (name) => `Recognised ${name}, but it cannot be monitored yet.`,
    notRecognised: "Experiment not recognised.",
    first: (text) => `First: ${lower(sentence(text))}.`,
    done: (label) => `${label} done.`,
    next: (text) => `Next: ${lower(sentence(text))}.`,
    complete: "Procedure complete.",
    skipped: (label) => `Alert. ${label} skipped.`,
    outOfOrder: (label) => `Alert. ${label} done out of order.`,
    noProgress: (label) => `Alert. No progress on ${lower(label)}.`,
    overdue: (label) => `Alert. ${label} is taking longer than planned.`,
    alert: (label) => `Alert on ${lower(label)}.`,
    summary: ({ done, total, skipped, late, missed }) =>
      `Analysis finished. ${done} of ${total} steps done.` +
      (skipped ? ` Skipped: step ${skipped}.` : "") +
      (late ? ` Out of order: step ${late}.` : "") +
      (missed ? ` Not reached: step ${missed}.` : "") +
      (!skipped && !late && !missed ? " All in order." : ""),
  },
  hi: {
    step: (number) => `चरण ${number}`,
    recognised: (name) => `${name} पहचाना गया। निगरानी शुरू।`,
    selected: (name) => `${name} चुना गया। निगरानी शुरू।`,
    started: (name) => `${name} की निगरानी शुरू।`,
    unavailable: (name) => `${name} पहचाना गया, पर इसकी निगरानी अभी संभव नहीं है।`,
    notRecognised: "प्रयोग पहचाना नहीं गया।",
    first: (text) => `पहला चरण: ${sentence(text)}।`,
    done: (label) => `${label} पूरा।`,
    next: (text) => `अगला: ${sentence(text)}।`,
    complete: "प्रक्रिया पूरी हुई।",
    skipped: (label) => `चेतावनी। ${label} छूट गया।`,
    outOfOrder: (label) => `चेतावनी। ${label} क्रम से बाहर किया गया।`,
    noProgress: (label) => `चेतावनी। ${label} में कोई प्रगति नहीं।`,
    overdue: (label) => `चेतावनी। ${label} में योजना से अधिक समय लग रहा है।`,
    alert: (label) => `चेतावनी: ${label}।`,
    summary: ({ done, total, skipped, late, missed }) =>
      `विश्लेषण पूरा। ${total} में से ${done} चरण पूरे।` +
      (skipped ? ` छूटे: चरण ${skipped}।` : "") +
      (late ? ` क्रम से बाहर: चरण ${late}।` : "") +
      (missed ? ` नहीं पहुँचे: चरण ${missed}।` : "") +
      (!skipped && !late && !missed ? " सभी सही क्रम में।" : ""),
  },
};

export const SPEECH_LANGUAGES = [
  ["en", "EN", "English"],
  ["hi", "हिं", "हिन्दी"],
];

export function phrases(lang) {
  return PHRASES[lang] || PHRASES.en;
}

export function spokenName(plan, lang) {
  return plan?.spoken_name?.[lang] || plan?.spoken_name?.en || plan?.name || "";
}

export function instructionFor(step, lang, fallback) {
  return step?.instruction?.[lang] || (lang === "en" ? fallback : "") || "";
}

export function nextStepAfter(steps, stepId, completedIds) {
  const index = steps.findIndex((step) => step.id === stepId);
  if (index < 0) return null;
  return steps.slice(index + 1).find((step) => !completedIds.has(step.id)) || null;
}

export function stepCompletedText(lang, { label, next, nextNumber, nextFallback }) {
  const say = phrases(lang);
  if (!next) return `${say.done(label)} ${say.complete}`;
  const instruction = instructionFor(next, lang, nextFallback);
  return `${say.done(label)} ${say.next(instruction || say.step(nextNumber))}`;
}

export function startText(lang, { verb, plan, fallbackFirst }) {
  const say = phrases(lang);
  const name = spokenName(plan, lang);
  const first = plan?.steps?.[0];
  const instruction = instructionFor(first, lang, fallbackFirst);
  const opening = say[verb](name);
  return instruction ? `${opening} ${say.first(instruction)}` : opening;
}

export function alertText(lang, event, label) {
  const say = phrases(lang);
  if (event.step_status === "skipped") return say.skipped(label);
  if (event.alert_code === "OUT_OF_ORDER") return say.outOfOrder(label);
  if (event.alert_code === "PAUSE_EXCEEDED") return say.noProgress(label);
  if (event.alert_code === "STEP_OVERDUE") return say.overdue(label);
  return say.alert(label);
}

export function summaryText(lang, counts) {
  return phrases(lang).summary(counts);
}
