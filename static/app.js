const form = document.getElementById("renderForm");
const clipGallery = document.getElementById("clipGallery");
const progressBar = document.getElementById("progressBar");
const statusText = document.getElementById("statusText");
const jobText = document.getElementById("jobText");
const logBox = document.getElementById("logBox");
const downloadLink = document.getElementById("downloadLink");
const submitBtn = document.getElementById("submitBtn");
const buyOneCreditBtn = document.getElementById("buyOneCreditBtn");
const checkCreditsBtn = document.getElementById("checkCreditsBtn");
const tokenCreditStatus = document.getElementById("tokenCreditStatus");
const openBuyCreditsTabBtn = document.getElementById("openBuyCreditsTabBtn");
const freeTrialHint = document.getElementById("freeTrialHint");
const creditBalanceHint = document.getElementById("creditBalanceHint");
const renderCreditUsage = document.getElementById("renderCreditUsage");
const outputPreset = document.getElementById("outputPreset");
const outputWidthInput = document.getElementById("outputWidth");
const outputHeightInput = document.getElementById("outputHeight");
const clipPickerInput = document.getElementById("clipPicker");
const clipCountStatus = document.getElementById("clipCountStatus");
const openClipPickerBtn = document.getElementById("openClipPickerBtn");
const clipDropzone = document.getElementById("clipDropzone");
const clipGalleryViewport = document.getElementById("clipGalleryViewport");
const clipSliderPrev = document.getElementById("clipSliderPrev");
const clipSliderNext = document.getElementById("clipSliderNext");
const titleFontFamilyInput = document.getElementById("titleFontFamily");
const listFontFamilyInput = document.getElementById("listFontFamily");
const titleFontSizeInput = document.getElementById("titleFontSize");
const listFontSizeInput = document.getElementById("listFontSize");
const uploadLimitNote = document.getElementById("uploadLimitNote");
const selectedUploadSize = document.getElementById("selectedUploadSize");
const renderProtectionNote = document.getElementById("renderProtectionNote");
const finalRenderSummary = document.getElementById("finalRenderSummary");
const renderHistory = document.getElementById("renderHistory");
const narrationBillingPanel = document.getElementById("narrationBillingPanel");
const narrationModeStatus = document.getElementById("narrationModeStatus");
const estimatedCreditCost = document.getElementById("estimatedCreditCost");
const hostedCreditsSection = document.getElementById("hostedCreditsSection");
const enableNarrationInput = document.getElementById("enableNarration");
const voiceIdInput = document.getElementById("voiceId");
const previewVoiceBtn = document.getElementById("previewVoiceBtn");
const updateStatusBanner = document.getElementById("updateStatusBanner");
const updateStatusText = document.getElementById("updateStatusText");
const updateDownloadLink = document.getElementById("updateDownloadLink");

let currentSource = null;
const TOKEN_STORAGE_KEY = "videoforge_paid_access_token";
let billingConfig = null;
let accountBillingStatus = null;
let maxUploadMb = 1024;
let clipMin = 3;
let clipMax = 10;
const selectedClips = [];
const completedFinalRenders = [];
let lastCompletedRender = null;
let hasChangesSinceLastRender = false;
let activeRenderMeta = null;
const CAPTION_GUIDE_DISMISSED_KEY = "videoforge_caption_guide_dismissed";
let hostedTokenPromise = null;
const musicLevelInput = document.getElementById("musicLevel");
const musicLevelRow = document.getElementById("musicLevelRow");
const includeMusic = document.getElementById("includeMusic");
const intermissionPreviewRow = document.getElementById("intermissionPreviewRow");
const intermissionOpacityWrap = document.getElementById("intermissionOpacityWrap");
const CLIP_DROPZONE_EMPTY_MESSAGE = "Drop video files here or click Add Clips";

// ── Access code recovery elements ──────────────────────────────────────────
const accessCodeBanner      = document.getElementById("accessCodeBanner");
const accessCodeSub         = document.getElementById("accessCodeSub");
const accessCodeDisplay     = document.getElementById("accessCodeDisplay");
const copyAccessCodeBtn     = document.getElementById("copyAccessCodeBtn");
const accessEmailInput      = document.getElementById("accessEmailInput");
const linkEmailBtn          = document.getElementById("linkEmailBtn");
const linkEmailStatus       = document.getElementById("linkEmailStatus");
const recoveryModalOverlay  = document.getElementById("recoveryModalOverlay");
const recoveryEmailInput    = document.getElementById("recoveryEmailInput");
const sendRecoveryBtn       = document.getElementById("sendRecoveryBtn");
const closeRecoveryModalBtn = document.getElementById("closeRecoveryModalBtn");
const recoveryStatus        = document.getElementById("recoveryStatus");
const restoreCodeSection    = document.getElementById("restoreCodeSection");
const restoreCodeInput      = document.getElementById("restoreCodeInput");
const applyRestoreCodeBtn   = document.getElementById("applyRestoreCodeBtn");
const restoreCodeStatus     = document.getElementById("restoreCodeStatus");
const openRecoveryModalLink = document.getElementById("openRecoveryModalLink");
const openRecoveryModalBannerLink = document.getElementById("openRecoveryModalBannerLink");
const openRestoreCodeLink   = document.getElementById("openRestoreCodeLink");
const openRestoreCodeBannerLink = document.getElementById("openRestoreCodeBannerLink");
const openRestoreCodeModalLink = document.getElementById("openRestoreCodeModalLink");
const openRestoreCodeInlineLink = document.getElementById("openRestoreCodeInlineLink");
const accessCodeDismissNote = document.querySelector(".access-code-dismiss-note");
const accessEmailRow        = document.getElementById("accessEmailRow");
const secureCreditsModalOverlay = document.getElementById("secureCreditsModalOverlay");
const secureCreditsCodePreview = document.getElementById("secureCreditsCodePreview");
const secureCreditsEmailInput = document.getElementById("secureCreditsEmailInput");
const secureCreditsStatus = document.getElementById("secureCreditsStatus");
const secureCreditsConfirmBtn = document.getElementById("secureCreditsConfirmBtn");
const secureCreditsLaterBtn = document.getElementById("secureCreditsLaterBtn");
const buyCreditsModalOverlay = document.getElementById("buyCreditsModalOverlay");
const buyPackGrid            = document.getElementById("buyPackGrid");
const buyCreditsSummary      = document.getElementById("buyCreditsSummary");
const confirmBuyCreditsBtn   = document.getElementById("confirmBuyCreditsBtn");
const closeBuyCreditsModalBtn = document.getElementById("closeBuyCreditsModalBtn");

let selectedBuyCredits = 1;
let secureCreditsPromptDismissed = false;

function formatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) {
    return "0 MB";
  }
  const mb = bytes / (1024 * 1024);
  if (mb < 1024) {
    return `${mb.toFixed(1)} MB`;
  }
  return `${(mb / 1024).toFixed(2)} GB`;
}

function getSelectedUploadBytes() {
  const clipFiles = selectedClips.map((clip) => clip.file).filter(Boolean);
  const bgMusic = document.getElementById("backgroundMusic").files[0];
  const totalClipBytes = clipFiles.reduce((sum, file) => sum + (file.size || 0), 0);
  return totalClipBytes + (bgMusic?.size || 0);
}

function setUpdateBanner(message, options = {}) {
  if (!updateStatusBanner || !updateStatusText) {
    return;
  }

  const priorCheck = updateStatusBanner.querySelector(".update-status-check");
  if (priorCheck) {
    priorCheck.remove();
  }

  updateStatusText.textContent = message;
  updateStatusBanner.hidden = false;
  updateStatusBanner.classList.toggle("is-available", Boolean(options.available));
  updateStatusBanner.classList.toggle("is-up-to-date", Boolean(options.upToDate));

  if (options.upToDate) {
    const check = document.createElement("span");
    check.className = "update-status-check";
    check.textContent = "Up to date";
    updateStatusBanner.appendChild(check);
  }

  if (!updateDownloadLink) {
    return;
  }

  const href = (options.href || "").trim();
  if (href) {
    updateDownloadLink.href = href;
    updateDownloadLink.hidden = false;
    updateDownloadLink.textContent = options.linkText || "Download Update";
  } else {
    updateDownloadLink.hidden = true;
    updateDownloadLink.removeAttribute("href");
  }
}

if (updateDownloadLink) {
  updateDownloadLink.addEventListener("click", (event) => {
    const href = (updateDownloadLink.getAttribute("href") || "").trim();
    if (!href || href === "#") {
      event.preventDefault();
    }
  });
}

function formatVersionLabel(version) {
  const cleaned = String(version || "").trim();
  if (!cleaned) {
    return "unknown";
  }
  return cleaned.toLowerCase().startsWith("v") ? cleaned : `v${cleaned}`;
}

function updateClipDropzoneState(isDragOver = false) {
  if (!clipDropzone) {
    return;
  }

  if (isDragOver) {
    clipDropzone.hidden = false;
    clipDropzone.textContent = "Release to add clips";
    return;
  }

  const clipCount = selectedClips.length;
  if (clipCount <= 0) {
    clipDropzone.hidden = false;
    clipDropzone.textContent = CLIP_DROPZONE_EMPTY_MESSAGE;
    clipDropzone.classList.remove("has-files");
    return;
  }

  clipDropzone.hidden = true;
  clipDropzone.classList.add("has-files");
  clipDropzone.textContent = CLIP_DROPZONE_EMPTY_MESSAGE;
}

async function checkForAppUpdate() {
  if (!updateStatusBanner) {
    return;
  }

  try {
    const response = await fetch("/api/app-update");
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Update check failed");
    }

    if (!data.enabled) {
      updateStatusBanner.hidden = true;
      return;
    }

    const latest = formatVersionLabel(data.latest_version || data.current_version);
    const current = formatVersionLabel(data.current_version);

    if (data.update_available) {
      const target = "/api/app-update/download";
      setUpdateBanner(`Update available: ${latest} (current release ${current}).`, {
        available: true,
        href: target,
        linkText: "Download Update",
      });
      return;
    }

    if (data.error) {
      setUpdateBanner(`Current release ${current}. Update check unavailable right now.`);
      log(`Update check warning: ${data.error}`);
      return;
    }

    setUpdateBanner(`Release ${current}`, {
      upToDate: true,
    });
  } catch (error) {
    setUpdateBanner("Current release unknown. Could not check for updates right now.");
    log(`Update check failed: ${error.message}`);
  }
}

function refreshSelectedUploadSize() {
  const totalBytes = getSelectedUploadBytes();
  selectedUploadSize.textContent = `Selected upload size: ${formatBytes(totalBytes)} / limit ${maxUploadMb} MB`;
}

function log(message) {
  const line = `[${new Date().toLocaleTimeString()}] ${message}`;
  logBox.textContent += `${line}\n`;
  logBox.scrollTop = logBox.scrollHeight;
}

function mapApiErrorToUserMessage(errorText, statusCode) {
  const text = String(errorText || "").trim();
  const lowered = text.toLowerCase();

  if (!text) {
    if (statusCode === 413) return `Upload too large for server limit (${maxUploadMb} MB).`;
    if (statusCode === 402) return "Payment or credits are required to continue this action.";
    if (statusCode === 409) return "Request could not be completed in current state. Please retry.";
    if (statusCode >= 500) return "Server error while starting render. Please retry in a moment.";
    return "Request failed. Please review inputs and try again.";
  }

  if (lowered.includes("upload too large") || lowered.includes("max_upload_mb") || statusCode === 413) {
    return `Upload too large for server limit (${maxUploadMb} MB).`;
  }
  if (lowered.includes("token is required") || lowered.includes("invalid token format")) {
    return "Your access token is invalid or missing. Refresh credits and retry.";
  }
  if (lowered.includes("credits") && lowered.includes("required")) {
    return "You need credits to continue. Use Buy Credits, then retry.";
  }
  if (lowered.includes("stripe is not configured")) {
    return "Billing is temporarily unavailable on this server. Try again later.";
  }
  if (statusCode >= 500) {
    return "Server error while processing request. Please retry in a moment.";
  }
  return text;
}

function reportClientDiagnostic(eventName, component, details = {}) {
  fetch("/api/diagnostics/client-event", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      event: eventName,
      component,
      details,
    }),
  }).catch(() => {
    // Diagnostics must never break user flow.
  });
}

function attachVideoDiagnostics(videoElement, component, fileLabel = "") {
  if (!videoElement || videoElement.dataset.diagAttached === "true") {
    return;
  }

  videoElement.dataset.diagAttached = "true";

  const emit = (eventName, extra = {}) => {
    reportClientDiagnostic(eventName, component, {
      fileLabel,
      src: videoElement.currentSrc || videoElement.getAttribute("src") || "",
      readyState: videoElement.readyState,
      networkState: videoElement.networkState,
      duration: Number.isFinite(videoElement.duration) ? videoElement.duration : null,
      errorCode: videoElement.error ? videoElement.error.code : null,
      ...extra,
    });
  };

  ["loadedmetadata", "canplay", "playing", "stalled", "abort", "emptied", "error"].forEach((evt) => {
    videoElement.addEventListener(evt, () => emit(evt));
  });
}

function abbreviateForHistory(text, maxLen = 48) {
  if (!text || text.length <= maxLen) {
    return text || "Rendered video";
  }
  return `${text.slice(0, maxLen - 3)}...`;
}

function updateRenderProtectionNote() {
  if (!lastCompletedRender || !hasChangesSinceLastRender) {
    renderProtectionNote.hidden = true;
    renderProtectionNote.textContent = "";
    return;
  }

  renderProtectionNote.hidden = false;
  if (lastCompletedRender.usedNarration) {
    renderProtectionNote.textContent = "Clips or settings changed since the last narration render. Starting Render again creates a new final export and may use ElevenLabs again. Previous exports remain available on the right.";
    return;
  }

  renderProtectionNote.textContent = "Clips or settings changed since the last final render. Starting Render again creates a new export. Previous exports remain available on the right.";
}

function markFinalRenderDirty() {
  if (!lastCompletedRender) {
    return;
  }
  hasChangesSinceLastRender = true;
  updateRenderProtectionNote();
}

function updateFinalExportsUI() {
  if (!completedFinalRenders.length) {
    finalRenderSummary.textContent = "No final render yet.";
    downloadLink.hidden = true;
    renderHistory.hidden = true;
    renderHistory.innerHTML = "";
    return;
  }

  const latest = completedFinalRenders[0];
  finalRenderSummary.textContent = `Latest export: ${latest.usedNarration ? "with" : "without"} ElevenLabs narration at ${latest.completedAt}.`;
  downloadLink.href = latest.href;
  downloadLink.download = latest.filename || "VideoForge-Studio-render.mp4";
  downloadLink.hidden = false;

  if (completedFinalRenders.length === 1) {
    renderHistory.hidden = true;
    renderHistory.innerHTML = "";
    return;
  }

  renderHistory.hidden = false;
  renderHistory.innerHTML = completedFinalRenders
    .slice(1, 6)
    .map((entry) => `<a href="${entry.href}" target="_blank" rel="noopener noreferrer">${abbreviateForHistory(entry.label)}</a>`)
    .join("");
}

function sanitizeTitle(raw) {
  return raw
    .replace(/\.[^/.]+$/, "")
    .replace(/[._-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function abbreviateTitle(text, maxLen = 24) {
  const clean = text || "Untitled";
  if (clean.length <= maxLen) {
    return clean;
  }
  return `${clean.slice(0, maxLen - 1)}...`;
}

function renderClipGallery() {
  clipGallery.innerHTML = "";
  clipGallery.classList.toggle("single-clip", selectedClips.length === 1);
  selectedClips.forEach((clip, index) => {
    const card = document.createElement("div");
    card.className = "clip-card";
    card.dataset.index = String(index);
    card.innerHTML = `
      <span class="clip-index-badge">#${index + 1}</span>
      <video src="${clip.objectUrl}" controls preload="metadata" playsinline></video>
      <p class="clip-caption-label">Clip Card Title</p>
      <input class="clip-title-input" type="text" data-role="clipTitleInput" data-index="${index}" value="${clip.title.replace(/\"/g, "&quot;")}" placeholder="Edit displayed clip title">
      <p class="clip-title" title="${clip.title.replace(/\"/g, "&quot;")}">${clip.shortTitle}</p>
      <p class="clip-caption-label">Clip Caption / Narration Text</p>
      <textarea class="clip-caption-input" data-role="clipCaptionInput" data-index="${index}" rows="3" placeholder="What should appear on-screen during intermission and be spoken by narration?">${clip.caption.replace(/</g, "&lt;").replace(/>/g, "&gt;")}</textarea>
      <button class="clip-remove-btn" type="button" data-role="removeClip" data-index="${index}">Remove</button>
    `;

    const clipVideo = card.querySelector("video");
    if (clipVideo) {
      attachVideoDiagnostics(clipVideo, `clip-card-${index + 1}`, clip.file.name || clip.title || "clip");
    }

    clipGallery.appendChild(card);
  });

  clipCountStatus.textContent = `${selectedClips.length} clip${selectedClips.length === 1 ? "" : "s"} selected`;
  updateClipDropzoneState(false);
  refreshSelectedUploadSize();
  requestAnimationFrame(updateClipSliderState);
}

function updateClipSliderState() {
  if (!clipGalleryViewport || !clipSliderPrev || !clipSliderNext) {
    return;
  }

  const needsSlider = selectedClips.length > 2;
  clipSliderPrev.hidden = !needsSlider;
  clipSliderNext.hidden = !needsSlider;

  if (!needsSlider) {
    clipSliderPrev.disabled = true;
    clipSliderNext.disabled = true;
    clipGalleryViewport.scrollLeft = 0;
    return;
  }

  const maxScrollLeft = Math.max(0, clipGalleryViewport.scrollWidth - clipGalleryViewport.clientWidth - 1);
  clipSliderPrev.disabled = clipGalleryViewport.scrollLeft <= 1;
  clipSliderNext.disabled = clipGalleryViewport.scrollLeft >= maxScrollLeft;
}

function scrollClipGallery(direction) {
  if (!clipGalleryViewport) {
    return;
  }
  const step = clipGalleryViewport.clientWidth;
  clipGalleryViewport.scrollBy({ left: direction * step, behavior: "smooth" });
}

function addSelectedFiles(files) {
  const existingKeys = new Set(selectedClips.map((c) => `${c.file.name}|${c.file.size}|${c.file.lastModified}`));
  let added = 0;

  Array.from(files).forEach((file) => {
    if (selectedClips.length >= clipMax) {
      return;
    }
    const key = `${file.name}|${file.size}|${file.lastModified}`;
    if (existingKeys.has(key)) {
      return;
    }
    const title = sanitizeTitle(file.name);
    selectedClips.push({
      file,
      title,
      shortTitle: abbreviateTitle(title),
      caption: title,
      objectUrl: URL.createObjectURL(file),
    });
    existingKeys.add(key);
    added += 1;
  });

  if (added === 0 && files.length > 0) {
    log(`No clips added. You may have reached the ${clipMax}-clip limit or selected duplicates.`);
  }
  renderClipGallery();
  markFinalRenderDirty();
  schedulePreviewUpdate();
}

function closeStream() {
  if (currentSource) {
    currentSource.close();
    currentSource = null;
  }
}

function getTokenInput() {
  return document.getElementById("paidAccessToken");
}

async function ensureHostedToken() {
  const tokenInput = getTokenInput();
  if (!tokenInput) {
    throw new Error("Hosted token input is missing.");
  }

  const existing = tokenInput.value.trim() || localStorage.getItem(TOKEN_STORAGE_KEY) || "";
  if (existing) {
    tokenInput.value = existing;
    localStorage.setItem(TOKEN_STORAGE_KEY, existing);
    return existing;
  }

  if (!hostedTokenPromise) {
    hostedTokenPromise = requestServerToken()
      .then((result) => {
        const token = String(result.token || "").trim();
        if (!token) {
          throw new Error("Server returned an empty hosted token.");
        }
        tokenInput.value = token;
        localStorage.setItem(TOKEN_STORAGE_KEY, token);
        setAccountBillingStatus(result);
        return token;
      })
      .finally(() => {
        hostedTokenPromise = null;
      });
  }

  return hostedTokenPromise;
}

function getNarrationMode() {
  return "hosted";
}

function getNarrationWordCount() {
  return selectedClips.reduce((sum, clip) => {
    const text = String((clip.caption || "").trim());
    if (!text) return sum;
    const words = text.split(/\s+/).filter(Boolean).length;
    return sum + words;
  }, 0);
}

function formatFreeTrialUses(count) {
  return `${count} Free Trial Use${count === 1 ? "" : "s"}`;
}

function setAccountBillingStatus(status) {
  accountBillingStatus = status || null;
}

function getActiveAccessToken() {
  return (getTokenInput() && getTokenInput().value.trim()) || localStorage.getItem(TOKEN_STORAGE_KEY) || "";
}

function getMaskedToken(token) {
  if (!token) {
    return "";
  }
  return token.length > 20 ? token.slice(0, 10) + "..." + token.slice(-6) : token;
}

function updateCreditBalanceHint() {
  if (!creditBalanceHint) {
    return;
  }

  if (!billingConfig) {
    creditBalanceHint.textContent = "Credits in your account: loading...";
    return;
  }

  const paidCredits = Math.max(0, Number((accountBillingStatus && accountBillingStatus.paid_credits) || 0));
  creditBalanceHint.textContent = `Credits in your account: ${paidCredits}`;
}

function getNarrationCreditEstimate() {
  const wordsPerCredit = Math.max(1, Number((billingConfig && billingConfig.narration_words_per_credit) || 30));
  const wordCount = Math.max(0, getNarrationWordCount());
  const creditCost = Math.max(1, Math.ceil(Math.max(1, wordCount) / wordsPerCredit));
  const narrationEnabled = Boolean(enableNarrationInput && enableNarrationInput.checked);
  const mode = getNarrationMode();
  const hostedMode = narrationEnabled && mode === "hosted";

  return {
    creditCost,
    wordCount,
    wordsPerCredit,
    narrationEnabled,
    mode,
    hostedMode,
  };
}

function updateActionCreditUsage() {
  updateCreditBalanceHint();

  if (!renderCreditUsage) {
    return;
  }

  if (!billingConfig) {
    renderCreditUsage.textContent = "(Checking free trial...)";
    return;
  }

  const estimate = getNarrationCreditEstimate();
  const freeTrialRemaining = Math.max(0, Number((accountBillingStatus && accountBillingStatus.free_trial_remaining) ?? billingConfig.free_trial_credits ?? 0));
  const paidCredits = Math.max(0, Number((accountBillingStatus && accountBillingStatus.paid_credits) || 0));

  if (!estimate.narrationEnabled) {
    renderCreditUsage.textContent = freeTrialRemaining > 0
      ? `(${formatFreeTrialUses(freeTrialRemaining)})`
      : paidCredits > 0
        ? `(${paidCredits} Credit${paidCredits === 1 ? "" : "s"} Available)`
        : "(No Free Trial Uses Left)";
    return;
  }

  if (freeTrialRemaining > 0) {
    renderCreditUsage.textContent = `(${formatFreeTrialUses(freeTrialRemaining)}) ElevenLabs narration needs ${estimate.creditCost} credit${estimate.creditCost === 1 ? "" : "s"} for ${estimate.wordCount} words.`;
    return;
  }

  if (paidCredits >= estimate.creditCost) {
    renderCreditUsage.textContent = `(${paidCredits} Credit${paidCredits === 1 ? "" : "s"} Available) ElevenLabs narration needs ${estimate.creditCost} for ${estimate.wordCount} words.`;
    return;
  }

  renderCreditUsage.textContent = `(Need ${estimate.creditCost} Credit${estimate.creditCost === 1 ? "" : "s"}) ElevenLabs narration is not included in the free trial.`;
}

function updateNarrationBillingUI() {
  if (!enableNarrationInput || !narrationBillingPanel || !narrationModeStatus || !estimatedCreditCost) {
    updateActionCreditUsage();
    return;
  }

  const narrationEnabled = enableNarrationInput.checked;
  narrationBillingPanel.hidden = !narrationEnabled;
  if (!narrationEnabled) {
    updateActionCreditUsage();
    return;
  }

  if (hostedCreditsSection) {
    hostedCreditsSection.hidden = false;
  }

  const freeTrialRemaining = Math.max(0, Number((accountBillingStatus && accountBillingStatus.free_trial_remaining) || 0));
  narrationModeStatus.textContent = freeTrialRemaining > 0
    ? `Narration is billed using app credits. You still have ${formatFreeTrialUses(freeTrialRemaining)} for non-narration renders; narration itself requires credits.`
    : "Narration is billed using app credits only.";
  ensureHostedToken()
    .then((token) => refreshTokenCreditsUI(token))
    .catch((error) => {
      log(`Could not prepare credits: ${error.message}`);
    });

  const estimate = getNarrationCreditEstimate();
  estimatedCreditCost.textContent = `Estimated credit cost: ${estimate.creditCost} credit${estimate.creditCost === 1 ? "" : "s"} (${estimate.wordCount} words at 1 credit per ${estimate.wordsPerCredit} words).`;
  updateActionCreditUsage();
}

async function refreshTokenCreditsUI(token) {
  if (!token) {
    tokenCreditStatus.textContent = "Credits: unknown";
    return;
  }
  try {
    const status = await fetchTokenCredits(token);
    setAccountBillingStatus(status);
    const paidCredits = Number(status.paid_credits || 0);
    const freeTrialRemaining = Number(status.free_trial_remaining || 0);
    tokenCreditStatus.textContent = freeTrialRemaining > 0
      ? `Credits: ${paidCredits}. Free trial uses left: ${freeTrialRemaining}.`
      : `Credits: ${paidCredits}`;
    log(`Account status: ${paidCredits} credit(s), ${freeTrialRemaining} free trial use(s) left.`);
    setEmailLinkEligibility(paidCredits > 0);
    updateActionCreditUsage();
  } catch (error) {
    tokenCreditStatus.textContent = "Credits: lookup failed";
    log(`Credit lookup failed: ${error.message}`);
  }
}

function setEmailLinkEligibility(eligible) {
  const emailLinked = Boolean(accountBillingStatus && accountBillingStatus.email_linked);
  const linkedEmail = String((accountBillingStatus && accountBillingStatus.linked_email) || "").trim();
  const emailDeliveryReady = Boolean(billingConfig && billingConfig.email_recovery_configured);

  if (accessCodeBanner) {
    accessCodeBanner.hidden = !eligible;
  }
  if (accessEmailRow) {
    accessEmailRow.hidden = !eligible || emailLinked;
  }
  if (accessCodeSub) {
    accessCodeSub.textContent = emailLinked
      ? "Your paid credits are tied to this code and already secured to your email"
      : "Save this code now, then secure it with email so you can restore paid credits later";
  }
  if (accessCodeDismissNote) {
    accessCodeDismissNote.textContent = !eligible
      ? "Email recovery is unlocked after your first credit purchase. Save this access code now."
      : emailLinked
        ? emailDeliveryReady
          ? `This access code is secured to ${linkedEmail}. We can send this same code there if you need to restore credits later.`
          : `This access code is linked to ${linkedEmail}, but email sending is not configured on this server yet. Save your code manually.`
        : "Enter your email to secure these paid credits. We will email you this same access code so you can restore credits on another device later.";
  }
  if (linkEmailStatus) {
    if (eligible && emailLinked) {
      linkEmailStatus.textContent = emailDeliveryReady
        ? `Secured to ${linkedEmail}. Keep your access code saved as a backup.`
        : `Linked to ${linkedEmail}. Email delivery is currently off, so save your access code as backup.`;
    } else if (!eligible) {
      linkEmailStatus.textContent = "";
    }
  }
  if (eligible) {
    const token = getActiveAccessToken();
    if (token) {
      showAccessCodeBanner(token, false);
    }
  }
  maybePromptToSecureCredits();
}

function openSecureCreditsModal() {
  if (!secureCreditsModalOverlay) {
    return;
  }

  const token = getActiveAccessToken();
  if (secureCreditsCodePreview) {
    secureCreditsCodePreview.textContent = getMaskedToken(token);
    secureCreditsCodePreview.title = token;
  }
  if (secureCreditsEmailInput && !secureCreditsEmailInput.value.trim()) {
    secureCreditsEmailInput.value = String((accountBillingStatus && accountBillingStatus.linked_email) || "");
  }
  if (secureCreditsStatus) {
    secureCreditsStatus.textContent = "";
  }
  if (secureCreditsConfirmBtn) {
    secureCreditsConfirmBtn.disabled = false;
  }
  secureCreditsModalOverlay.hidden = false;
  if (secureCreditsEmailInput) {
    secureCreditsEmailInput.focus();
  }
}

function closeSecureCreditsModal() {
  if (secureCreditsModalOverlay) {
    secureCreditsModalOverlay.hidden = true;
  }
}

function maybePromptToSecureCredits(force = false) {
  const paidCredits = Math.max(0, Number((accountBillingStatus && accountBillingStatus.paid_credits) || 0));
  const emailLinked = Boolean(accountBillingStatus && accountBillingStatus.email_linked);
  if (!secureCreditsModalOverlay || paidCredits <= 0 || emailLinked) {
    return;
  }
  if (!force && secureCreditsPromptDismissed) {
    return;
  }
  openSecureCreditsModal();
}

async function submitCreditEmailLink(email, options = {}) {
  const token = getActiveAccessToken();
  const statusNode = options.statusNode || linkEmailStatus;
  const triggerButton = options.triggerButton || linkEmailBtn;

  if (!token) {
    if (statusNode) statusNode.textContent = "No active access code found.";
    return { ok: false };
  }
  if (!email || !email.includes("@")) {
    if (statusNode) statusNode.textContent = "Enter a valid email address first.";
    return { ok: false };
  }

  if (triggerButton) {
    triggerButton.disabled = true;
  }
  if (statusNode) {
    statusNode.textContent = "Saving...";
  }

  try {
    const fd = new FormData();
    fd.append("token", token);
    fd.append("email", email);
    const res = await fetch("/api/billing/link-email", { method: "POST", body: fd });
    const data = await res.json();
    if (!res.ok) {
      if (statusNode) statusNode.textContent = data.error || "Could not save email.";
      if (triggerButton) triggerButton.disabled = false;
      return { ok: false, data };
    }

    setAccountBillingStatus({
      ...(accountBillingStatus || {}),
      email_linked: true,
      linked_email: data.linked_email || email,
    });
    setEmailLinkEligibility(true);

    const emailDeliveryReady = Boolean(billingConfig && billingConfig.email_recovery_configured);
    const successMessage = data.confirmation_email_sent
      ? "✓ Email linked. We sent your access code to that email. Save the code as a backup too."
      : emailDeliveryReady
        ? "✓ Email linked. Your credits can now be recovered with this email."
        : "✓ Email linked locally. Email delivery is not configured yet, so save your access code manually.";

    if (linkEmailStatus) {
      linkEmailStatus.textContent = successMessage;
    }
    if (statusNode && statusNode !== linkEmailStatus) {
      statusNode.textContent = successMessage;
    }

    if (linkEmailBtn) {
      linkEmailBtn.disabled = true;
    }
    return { ok: true, data };
  } catch (_err) {
    if (statusNode) statusNode.textContent = "Network error — try again.";
    if (triggerButton) triggerButton.disabled = false;
    return { ok: false };
  }
}

function updateBuyCreditsSummary() {
  if (!buyCreditsSummary) return;
  const cents = Number((billingConfig && billingConfig.price_per_credit_cents) || 100);
  const dollars = ((selectedBuyCredits * cents) / 100).toFixed(2);
  const stripeUnavailable = Boolean(billingConfig) && !Boolean(billingConfig.stripe_configured);
  buyCreditsSummary.textContent = stripeUnavailable
    ? `Selected: ${selectedBuyCredits} credit${selectedBuyCredits === 1 ? "" : "s"} — $${dollars}. Checkout is not configured on this server yet.`
    : `Selected: ${selectedBuyCredits} credit${selectedBuyCredits === 1 ? "" : "s"} — $${dollars}`;

  if (confirmBuyCreditsBtn) {
    confirmBuyCreditsBtn.disabled = stripeUnavailable;
    confirmBuyCreditsBtn.title = stripeUnavailable ? "Stripe is not configured on this server yet" : "";
  }
}

function getAvailableCreditsSnapshot() {
  const freeTrialRemaining = Math.max(0, Number((accountBillingStatus && accountBillingStatus.free_trial_remaining) ?? billingConfig?.free_trial_credits ?? 0));
  const paidCredits = Math.max(0, Number((accountBillingStatus && accountBillingStatus.paid_credits) || 0));
  return { freeTrialRemaining, paidCredits };
}

function openBuyCreditsModal(defaultCredits = 1) {
  selectedBuyCredits = Number.isFinite(defaultCredits) && defaultCredits > 0 ? defaultCredits : 1;
  if (buyPackGrid) {
    buyPackGrid.querySelectorAll(".modal-pack-btn").forEach((btn) => {
      const credits = Number(btn.getAttribute("data-credits") || "0");
      btn.classList.toggle("is-selected", credits === selectedBuyCredits);
    });
  }
  updateBuyCreditsSummary();
  if (buyCreditsModalOverlay) {
    buyCreditsModalOverlay.hidden = false;
  }
}

function closeBuyCreditsModal() {
  if (buyCreditsModalOverlay) {
    buyCreditsModalOverlay.hidden = true;
  }
}

async function initializeAccountBilling() {
  const tokenInput = getTokenInput();
  if (!tokenInput) {
    updateActionCreditUsage();
    return;
  }

  const existing = tokenInput.value.trim() || localStorage.getItem(TOKEN_STORAGE_KEY) || "";
  if (existing) {
    tokenInput.value = existing;
    localStorage.setItem(TOKEN_STORAGE_KEY, existing);
    await refreshTokenCreditsUI(existing);
    return;
  }

  try {
    const result = await requestServerToken();
    const token = String(result.token || "").trim();
    if (!token) {
      throw new Error("Server returned an empty account token.");
    }
    tokenInput.value = token;
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
    setAccountBillingStatus(result);
    const paidCredits = Number(result.paid_credits || 0);
    const freeTrialRemaining = Number(result.free_trial_remaining || 0);
    tokenCreditStatus.textContent = freeTrialRemaining > 0
      ? `Credits: ${paidCredits}. Free trial uses left: ${freeTrialRemaining}.`
      : `Credits: ${paidCredits}`;
    setEmailLinkEligibility(paidCredits > 0);
    updateNarrationBillingUI();
  } catch (error) {
    log(`Could not initialize account billing: ${error.message}`);
    updateActionCreditUsage();
  }
}

async function fetchBillingConfig() {
  const response = await fetch("/api/billing/config");
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Could not fetch billing config");
  }
  return data;
}

async function requestServerToken() {
  const response = await fetch("/api/billing/create-token", { method: "POST" });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Could not create token");
  }
  return data;
}

async function startJob(payload) {
  let response;
  try {
    response = await fetch("/api/render", {
      method: "POST",
      body: payload,
    });
  } catch (_error) {
    throw new Error("Failed to reach server. Check if app is still running or if upload is too large.");
  }

  let data = null;
  const responseText = await response.text();
  try {
    data = responseText ? JSON.parse(responseText) : {};
  } catch (_parseError) {
    data = { error: responseText || "Unexpected server response" };
  }

  if (!response.ok) {
    throw new Error(mapApiErrorToUserMessage(data.error || "", response.status));
  }
  return data.job_id;
}

async function createCheckoutSession(token, credits = 1) {
  const payload = new FormData();
  payload.append("token", token);
  payload.append("credits", String(credits));

  const response = await fetch("/api/payments/create-checkout-session", {
    method: "POST",
    body: payload,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Could not create checkout session");
  }
  return data;
}

async function confirmCheckoutSession(sessionId) {
  const payload = new FormData();
  payload.append("session_id", sessionId);

  const response = await fetch("/api/payments/confirm-session", {
    method: "POST",
    body: payload,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Could not confirm checkout session");
  }
  return data;
}

async function handleCheckoutReturn() {
  const params = new URLSearchParams(window.location.search);
  const paymentState = params.get("payment");
  const sessionId = params.get("session_id");
  if (!paymentState) {
    return;
  }

  const token = (getTokenInput() && getTokenInput().value.trim()) || localStorage.getItem(TOKEN_STORAGE_KEY) || "";

  try {
    if (paymentState === "success") {
      if (sessionId) {
        const result = await confirmCheckoutSession(sessionId);
        if (result.status) {
          setAccountBillingStatus(result.status);
        }
      }
      if (token) {
        await refreshTokenCreditsUI(token);
        showAccessCodeBanner(token, true);
      }
      if (linkEmailStatus) {
        const emailLinked = Boolean(accountBillingStatus && accountBillingStatus.email_linked);
        linkEmailStatus.textContent = emailLinked
          ? "Payment complete. Your credits are available and already secured by email."
          : "Payment complete. Save this access code, then secure it with your email below so you can restore credits later.";
      }
      maybePromptToSecureCredits(true);
    } else if (paymentState === "cancel") {
      if (linkEmailStatus) {
        linkEmailStatus.textContent = "Checkout was canceled. Your existing credits and free uses are unchanged.";
      }
    }
  } catch (error) {
    if (linkEmailStatus) {
      linkEmailStatus.textContent = `Checkout finished, but credit confirmation failed: ${error.message}`;
    }
    log(`Could not confirm checkout return: ${error.message}`);
  } finally {
    const cleaned = `${window.location.pathname}${window.location.hash || ""}`;
    window.history.replaceState({}, document.title, cleaned);
    updateActionCreditUsage();
  }
}

async function fetchTokenCredits(token) {
  const response = await fetch(`/api/billing/status?token=${encodeURIComponent(token)}`);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Could not fetch token credits");
  }
  return data;
}

async function saveRenderToHistory(outputFilename, token) {
  if (!token || !activeRenderMeta) return;
  try {
    const body = {
      output_filename: outputFilename,
      title_line_1: activeRenderMeta.title_line_1 || "Top 5 Funniest",
      title_line_2: activeRenderMeta.title_line_2 || "Moments",
      used_narration: activeRenderMeta.usedNarration,
      output_width: activeRenderMeta.output_width,
      output_height: activeRenderMeta.output_height,
    };
    const response = await fetch("/api/renders/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...body,
        token,
      }),
    });
    if (!response.ok) {
      const data = await response.json();
      log(`Warning: Could not save render to history: ${data.error}`);
    } else {
      const data = await response.json();
      log("Render saved to your history (accessible via access code).");
      // Refresh render history display
      loadRenderHistory(token);
    }
  } catch (error) {
    log(`Warning: Render history save failed: ${error.message}`);
  }
}

async function loadRenderHistory(token) {
  if (!token || !renderHistory) return;
  try {
    const response = await fetch(`/api/renders/list?token=${encodeURIComponent(token)}`);
    const data = await response.json();
    if (!response.ok) {
      renderHistory.innerHTML = `<p class="history-error">Could not load render history.</p>`;
      renderHistory.hidden = false;
      return;
    }
    const renders = data.renders || [];
    if (renders.length === 0) {
      renderHistory.innerHTML = `<p class="history-empty">No previous renders yet. Complete your first render to build your history.</p>`;
      renderHistory.hidden = false;
      return;
    }
    const historyHtml = renders
      .map(
        (r, idx) => `
      <div class="history-item">
        <div class="history-item-title">#${renders.length - idx}. ${r.title_line_1} ${r.title_line_2}</div>
        <div class="history-item-meta">
          ${r.output_width}×${r.output_height} • ${r.used_narration ? "with" : "without"} narration
        </div>
        <div class="history-item-date">${new Date(r.completed_at).toLocaleString()}</div>
        <a href="/outputs/${encodeURIComponent(r.filename)}" download="${r.filename}" class="history-download-link">
          ⬇ Download
        </a>
      </div>
    `
      )
      .join("");
    renderHistory.innerHTML = `<div class="renders-history-header">Your Render History</div>${historyHtml}`;
    renderHistory.hidden = false;
  } catch (error) {
    renderHistory.innerHTML = `<p class="history-error">Error loading history: ${error.message}</p>`;
    renderHistory.hidden = false;
  }
}

function subscribeToEvents(jobId) {
  closeStream();
  const source = new EventSource(`/api/jobs/${jobId}/events`);
  currentSource = source;
  let streamFinished = false;

  source.addEventListener("progress", (event) => {
    const data = JSON.parse(event.data);
    progressBar.style.width = `${data.progress || 0}%`;
    statusText.textContent = `${data.status || "running"} (${data.progress || 0}%)`;
    jobText.textContent = data.message || "Rendering";
    log(`${data.message || "Progress"} - ${data.progress || 0}%`);
  });

  source.addEventListener("done", (event) => {
    streamFinished = true;
    const data = JSON.parse(event.data);
    statusText.textContent = "completed (100%)";
    jobText.textContent = "Render finished";
    progressBar.style.width = "100%";
    if (data.output_file) {
      const href = `/outputs/${encodeURIComponent(data.output_file)}`;
      completedFinalRenders.unshift({
        href,
        filename: data.output_file,
        label: data.output_file,
        usedNarration: Boolean(activeRenderMeta && activeRenderMeta.usedNarration),
        completedAt: new Date().toLocaleTimeString(),
      });
      lastCompletedRender = completedFinalRenders[0];
      hasChangesSinceLastRender = false;
      updateRenderProtectionNote();
      updateFinalExportsUI();
      
      // Save render to server history
      const token = getTokenInput().value.trim();
      if (token) {
        saveRenderToHistory(data.output_file, token).catch((error) => {
          log(`Render history save error: ${error.message}`);
        });
      }
    }
    log("Render completed successfully.");
    submitBtn.disabled = false;
    activeRenderMeta = null;
    const token = getTokenInput().value.trim();
    if (token) {
      refreshTokenCreditsUI(token).catch((error) => {
        log(`Could not refresh account status: ${error.message}`);
      });
    }
    closeStream();
  });

  source.addEventListener("error", (event) => {
    streamFinished = true;
    try {
      const data = JSON.parse(event.data);
      log(`Render failed: ${data.error || "Unknown error"}`);
      statusText.textContent = "failed";
      jobText.textContent = data.error || "Render failed";
    } catch {
      log("Render stream encountered an error.");
    }
    submitBtn.disabled = false;
    activeRenderMeta = null;
    closeStream();
  });

  source.onerror = () => {
    if (streamFinished) {
      return;
    }
    log("Render stream disconnected. You can retry if progress does not continue.");
    statusText.textContent = "stream disconnected";
    jobText.textContent = "Connection lost while waiting for updates";
    submitBtn.disabled = false;
    activeRenderMeta = null;
    closeStream();
  };
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const enableNarration = document.getElementById("enableNarration").checked;
  if (enableNarration) {
    const confirmMessage = hasChangesSinceLastRender && lastCompletedRender && lastCompletedRender.usedNarration
      ? "Start Render creates a new final export and will run ElevenLabs again. This may consume credits or API usage. Your previous exports remain available on the right. Continue?"
      : "Start Render creates the final export and will run ElevenLabs narration if enabled. This may consume credits or API usage. Previous exports remain available on the right. Continue?";
    if (!window.confirm(confirmMessage)) {
      return;
    }
  }

  submitBtn.disabled = true;
  logBox.textContent = "";
  progressBar.style.width = "0%";

  const titleLine1 = document.getElementById("titleLine1").value.trim();
  const titleLine2 = document.getElementById("titleLine2").value.trim();
  const includeMusicChecked = includeMusic.checked;
  const musicLevel = includeMusicChecked ? Number(musicLevelInput.value) / 100 : 0.15;
  const outputWidth = Number(outputWidthInput.value);
  const outputHeight = Number(outputHeightInput.value);
  const titleFontFamily = titleFontFamilyInput.value;
  const listFontFamily = listFontFamilyInput.value;
  const titleFontSize = Number(titleFontSizeInput.value);
  const listFontSize = Number(listFontSizeInput.value);
  const voiceId = voiceIdInput ? voiceIdInput.value.trim() : "";
  let rawPaidAccessToken = document.getElementById("paidAccessToken").value.trim();
  if (!rawPaidAccessToken) {
    try {
      rawPaidAccessToken = await ensureHostedToken();
    } catch (error) {
      log(`Could not prepare account token: ${error.message}`);
    }
  }
  if (enableNarration && !rawPaidAccessToken) {
    try {
      rawPaidAccessToken = await ensureHostedToken();
      await refreshTokenCreditsUI(rawPaidAccessToken);
    } catch (error) {
      log(`Could not prepare credits: ${error.message}`);
    }
  }
  const paidAccessToken = rawPaidAccessToken;
  const useIntermissions = document.getElementById("useIntermissions").checked;
  const intermissionOpacity = Number(document.getElementById("intermissionOpacity").value);
  const bgMusic = document.getElementById("backgroundMusic").files[0];

  const clipFiles = selectedClips.map((clip) => clip.file);
  const clipCaptions = selectedClips.map((clip) => (clip.caption || "").trim());
  const selectedBytes = getSelectedUploadBytes();
  const selectedMb = selectedBytes / (1024 * 1024);

  if (clipFiles.length < clipMin || clipFiles.length > clipMax) {
    statusText.textContent = "validation error";
    jobText.textContent = `Select between ${clipMin} and ${clipMax} clips.`;
    submitBtn.disabled = false;
    return;
  }

  if (clipFiles.some((f) => !f) || clipCaptions.some((c) => !c)) {
    statusText.textContent = "validation error";
    jobText.textContent = "Every selected clip needs a caption.";
    submitBtn.disabled = false;
    return;
  }

  if (selectedMb > maxUploadMb) {
    statusText.textContent = "validation error";
    jobText.textContent = `Selected files exceed server upload limit (${maxUploadMb} MB).`;
    log(`Upload blocked: selected ${formatBytes(selectedBytes)} exceeds ${maxUploadMb} MB limit.`);
    submitBtn.disabled = false;
    return;
  }

  if (enableNarration && !paidAccessToken) {
    statusText.textContent = "validation error";
    jobText.textContent = "Narration token unavailable right now. Retry in a moment.";
    submitBtn.disabled = false;
    return;
  }

  const estimate = getNarrationCreditEstimate();
  const { freeTrialRemaining, paidCredits } = getAvailableCreditsSnapshot();
  if (freeTrialRemaining <= 0 && paidCredits <= 0) {
    statusText.textContent = "payment required";
    jobText.textContent = "No free uses left. Buy credits to continue.";
    openBuyCreditsModal(Math.max(1, estimate.creditCost || 1));
    submitBtn.disabled = false;
    return;
  }

  if (estimate.hostedMode && paidCredits < estimate.creditCost) {
    statusText.textContent = "payment required";
    jobText.textContent = `Need ${estimate.creditCost} credits for app-hosted narration.`;
    openBuyCreditsModal(estimate.creditCost);
    submitBtn.disabled = false;
    return;
  }

  const payload = new FormData();
  payload.append("title_line_1", titleLine1);
  payload.append("title_line_2", titleLine2);
  payload.append("output_width", String(outputWidth));
  payload.append("output_height", String(outputHeight));
  payload.append("title_font_family", titleFontFamily);
  payload.append("list_font_family", listFontFamily);
  payload.append("title_font_size", String(titleFontSize));
  payload.append("list_font_size", String(listFontSize));
  payload.append("enable_narration", enableNarration ? "true" : "false");
  payload.append("include_music", includeMusicChecked ? "true" : "false");
  payload.append("background_music_level", String(musicLevel));
  payload.append("use_intermissions", useIntermissions ? "true" : "false");
  payload.append("intermission_opacity", String(intermissionOpacity));
  payload.append("elevenlabs_voice_id", voiceId);
  payload.append("paid_access_token", paidAccessToken);
  payload.append("captions_json", JSON.stringify(clipCaptions));
  clipCaptions.forEach((caption) => payload.append("captions", caption));

  clipFiles.forEach((file) => payload.append("clips", file));
  if (includeMusicChecked && bgMusic) {
    payload.append("background_music", bgMusic);
  }

  try {
    const jobId = await startJob(payload);
    const titleLine1 = document.getElementById("titleLine1").value.trim() || "Top 5 Funniest";
    const titleLine2 = document.getElementById("titleLine2").value.trim() || "Moments";
    activeRenderMeta = {
      usedNarration: enableNarration,
      title_line_1: titleLine1,
      title_line_2: titleLine2,
      output_width: parseInt(outputWidthInput.value) || 1920,
      output_height: parseInt(outputHeightInput.value) || 1080,
    };
    statusText.textContent = "running (0%)";
    jobText.textContent = `Job ${jobId}`;
    log(`Job created: ${jobId}`);
    subscribeToEvents(jobId);
  } catch (error) {
    statusText.textContent = "failed";
    jobText.textContent = error.message;
    log(`Failed to start job: ${error.message}`);
    submitBtn.disabled = false;
    activeRenderMeta = null;
  }
});

if (buyOneCreditBtn) {
  buyOneCreditBtn.addEventListener("click", () => {
    openBuyCreditsModal(1);
  });
}

if (checkCreditsBtn) {
  checkCreditsBtn.addEventListener("click", async () => {
    const token = await ensureHostedToken();
    await refreshTokenCreditsUI(token);
  });
}

if (openBuyCreditsTabBtn) {
  openBuyCreditsTabBtn.addEventListener("click", () => {
    openBuyCreditsModal(3);
  });
}

if (previewVoiceBtn) {
  // Reuse a single Audio instance to avoid stacking playbacks
  let previewAudio = null;

  previewVoiceBtn.addEventListener("click", async () => {
    const selectedVoiceId = voiceIdInput.value.trim();
    if (!selectedVoiceId) {
      alert("Please select a voice first.");
      return;
    }

    // Stop any currently playing preview
    if (previewAudio) {
      previewAudio.pause();
      previewAudio.currentTime = 0;
    }

    previewVoiceBtn.disabled = true;
    previewVoiceBtn.textContent = "Loading...";

    try {
      // Static pre-generated file — no API call at runtime
      const url = `/api/voice-preview/${encodeURIComponent(selectedVoiceId)}`;
      const response = await fetch(url);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || "Preview not available for this voice");
      }

      const audioBlob = await response.blob();
      const audioUrl = URL.createObjectURL(audioBlob);

      previewAudio = new Audio(audioUrl);
      previewVoiceBtn.textContent = "Playing...";
      previewAudio.addEventListener("ended", () => {
        previewVoiceBtn.disabled = false;
        previewVoiceBtn.textContent = "Preview Voice";
      });
      previewAudio.play().catch((err) => {
        console.error("Failed to play audio:", err);
        previewVoiceBtn.disabled = false;
        previewVoiceBtn.textContent = "Preview Voice";
      });

    } catch (error) {
      console.error("Voice preview error:", error);
      alert(`Voice preview: ${error.message}`);
      previewVoiceBtn.disabled = false;
      previewVoiceBtn.textContent = "Preview Voice";
    }
  });
}

if (hostedCreditsSection) {
  hostedCreditsSection.addEventListener("click", (event) => {
    const target = event.target;
    if (!target || !(target instanceof HTMLElement)) {
      return;
    }
    const btn = target.closest(".buy-pack-btn");
    if (!btn) {
      return;
    }

    const credits = Number(btn.getAttribute("data-credits") || "0");
    if (!Number.isFinite(credits) || credits <= 0) {
      return;
    }

    openBuyCreditsModal(credits);
  });
}

if (buyPackGrid) {
  buyPackGrid.addEventListener("click", (event) => {
    const target = event.target;
    if (!target || !(target instanceof HTMLElement)) {
      return;
    }
    const btn = target.closest(".modal-pack-btn");
    if (!btn) {
      return;
    }
    const credits = Number(btn.getAttribute("data-credits") || "0");
    if (!Number.isFinite(credits) || credits <= 0) {
      return;
    }
    selectedBuyCredits = credits;
    buyPackGrid.querySelectorAll(".modal-pack-btn").forEach((node) => {
      node.classList.remove("is-selected");
    });
    btn.classList.add("is-selected");
    updateBuyCreditsSummary();
  });
}

if (closeBuyCreditsModalBtn) {
  closeBuyCreditsModalBtn.addEventListener("click", closeBuyCreditsModal);
}

if (buyCreditsModalOverlay) {
  buyCreditsModalOverlay.addEventListener("click", (event) => {
    if (event.target === buyCreditsModalOverlay) {
      closeBuyCreditsModal();
    }
  });
}

if (secureCreditsLaterBtn) {
  secureCreditsLaterBtn.addEventListener("click", () => {
    secureCreditsPromptDismissed = true;
    closeSecureCreditsModal();
  });
}

if (secureCreditsModalOverlay) {
  secureCreditsModalOverlay.addEventListener("click", (event) => {
    if (event.target === secureCreditsModalOverlay) {
      secureCreditsPromptDismissed = true;
      closeSecureCreditsModal();
    }
  });
}

if (confirmBuyCreditsBtn) {
  confirmBuyCreditsBtn.addEventListener("click", async () => {
    confirmBuyCreditsBtn.disabled = true;
    try {
      const token = await ensureHostedToken();
      const result = await createCheckoutSession(token, selectedBuyCredits);
      if (result.url) {
        window.location.href = result.url;
        return;
      }
      alert("Checkout URL missing from server response.");
      confirmBuyCreditsBtn.disabled = false;
    } catch (error) {
      alert(`Unable to start checkout: ${error.message}`);
      confirmBuyCreditsBtn.disabled = false;
    }
  });
}

const existingToken = localStorage.getItem(TOKEN_STORAGE_KEY);
if (existingToken) {
  getTokenInput().value = existingToken;
  refreshTokenCreditsUI(existingToken);
  loadRenderHistory(existingToken);
}

getTokenInput().addEventListener("change", () => {
  const token = getTokenInput().value.trim();
  if (token) {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
    secureCreditsPromptDismissed = false;
    refreshTokenCreditsUI(token);
    loadRenderHistory(token);
    return;
  }
  tokenCreditStatus.textContent = "Credits: unknown";
  setAccountBillingStatus(null);
  if (linkEmailStatus) {
    linkEmailStatus.textContent = "";
  }
  if (renderHistory) {
    renderHistory.innerHTML = "";
    renderHistory.hidden = true;
  }
  updateActionCreditUsage();
});

fetchBillingConfig()
  .then((config) => {
    billingConfig = config;
    const dollars = (Number(config.price_per_credit_cents || 100) / 100).toFixed(2);
    if (buyOneCreditBtn) {
      buyOneCreditBtn.textContent = `Buy 1 Credit ($${dollars})`;
    }
    if (freeTrialHint) {
      const freeCredits = Number(config.free_trial_credits || 0);
      const wordsPerCredit = Math.max(1, Number(config.narration_words_per_credit || 30));
      freeTrialHint.textContent = freeCredits > 0
        ? `Free Trial: first ${freeCredits} uses are free (if available for your account/IP). ElevenLabs narration is billed at 1 credit per ${wordsPerCredit} words.`
        : "Free Trial: no free uses currently configured.";
    }
    if (Number(config.free_trial_credits || 0) > 0) {
      log(`Free trial policy: ${config.free_trial_credits} use(s) one-time per ${config.free_trial_claim_scope || "ip"}.`);
    } else {
      log("Free trial policy: disabled.");
    }
    if (!config.email_recovery_configured) {
      if (accessCodeDismissNote) {
        accessCodeDismissNote.textContent = "Email recovery is currently unavailable on this server. Save your access code manually.";
      }
      if (openRecoveryModalLink) {
        openRecoveryModalLink.textContent = "Email recovery unavailable";
        openRecoveryModalLink.style.pointerEvents = "none";
        openRecoveryModalLink.style.opacity = "0.45";
      }
      if (openRecoveryModalBannerLink) {
        openRecoveryModalBannerLink.textContent = "Email recovery unavailable";
        openRecoveryModalBannerLink.style.pointerEvents = "none";
        openRecoveryModalBannerLink.style.opacity = "0.45";
      }
    }
    if (!config.stripe_configured && buyOneCreditBtn) {
      buyOneCreditBtn.title = "Stripe is not configured on this server yet";
    }
    if (!config.stripe_configured && openBuyCreditsTabBtn) {
      openBuyCreditsTabBtn.title = "Stripe is not configured on this server yet";
    }
    updateBuyCreditsSummary();
    initializeAccountBilling()
      .then(() => handleCheckoutReturn())
      .catch((error) => {
        log(`Could not initialize account status: ${error.message}`);
        updateNarrationBillingUI();
      });
  })
  .catch((error) => {
    log(`Billing config unavailable: ${error.message}`);
  });

fetch("/api/app-config")
  .then(async (response) => {
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Could not load app config");
    }
    return data;
  })
  .then((cfg) => {
    maxUploadMb = Number(cfg.max_upload_mb || 1024);
      clipMin = Number((cfg.clip_count && cfg.clip_count.min) || 3);
      clipMax = Number((cfg.clip_count && cfg.clip_count.max) || 10);
    uploadLimitNote.textContent = `Upload limit: ${cfg.max_upload_mb} MB request size. Max output dimension: ${cfg.max_output_dimension}px.`;

      titleFontFamilyInput.innerHTML = "";
      listFontFamilyInput.innerHTML = "";
      (cfg.font_options || []).forEach((font, index) => {
        const titleOpt = document.createElement("option");
        titleOpt.value = font.id;
        titleOpt.textContent = font.label;
        if (index === 0) {
          titleOpt.selected = true;
        }
        titleFontFamilyInput.appendChild(titleOpt);

        const listOpt = document.createElement("option");
        listOpt.value = font.id;
        listOpt.textContent = font.label;
        if (index === 0) {
          listOpt.selected = true;
        }
        listFontFamilyInput.appendChild(listOpt);
      });

    outputPreset.innerHTML = "";
    cfg.output_presets.forEach((preset, index) => {
      const opt = document.createElement("option");
      opt.value = `${preset.width}x${preset.height}`;
      opt.textContent = preset.label;
      if (index === 1) {
        opt.selected = true;
      }
      outputPreset.appendChild(opt);
    });
    const selected = outputPreset.value.split("x");
    outputWidthInput.value = selected[0];
    outputHeightInput.value = selected[1];

    if (voiceIdInput) {
      const voiceOptions = Array.isArray(cfg.voice_options) ? cfg.voice_options : [];
      const defaultVoiceId = String(cfg.default_voice_id || "").trim();
      voiceIdInput.innerHTML = "";

      const defaultOpt = document.createElement("option");
      defaultOpt.value = "";
      defaultOpt.textContent = "Default Voice";
      voiceIdInput.appendChild(defaultOpt);

      voiceOptions.forEach((voice) => {
        if (!voice || !voice.id) return;
        const opt = document.createElement("option");
        opt.value = voice.id;
        opt.textContent = voice.label || voice.id;
        if (defaultVoiceId && voice.id === defaultVoiceId) {
          opt.selected = true;
        }
        voiceIdInput.appendChild(opt);
      });
    }

    renderClipGallery();
    refreshSelectedUploadSize();
  })
  .catch((error) => {
    uploadLimitNote.textContent = "Upload limit: unavailable";
    log(`App config unavailable: ${error.message}`);
  });

checkForAppUpdate();

clipPickerInput.addEventListener("change", () => {
  addSelectedFiles(clipPickerInput.files || []);
  clipPickerInput.value = "";
  refreshSelectedUploadSize();
});

openClipPickerBtn.addEventListener("click", () => {
  clipPickerInput.click();
});

clipDropzone.addEventListener("click", () => {
  clipPickerInput.click();
});

["dragenter", "dragover"].forEach((evtName) => {
  clipDropzone.addEventListener(evtName, (event) => {
    event.preventDefault();
    event.stopPropagation();
    clipDropzone.classList.add("drag-over");
    updateClipDropzoneState(true);
  });
});

["dragleave", "drop"].forEach((evtName) => {
  clipDropzone.addEventListener(evtName, (event) => {
    event.preventDefault();
    event.stopPropagation();
    clipDropzone.classList.remove("drag-over");
    updateClipDropzoneState(false);
  });
});

clipDropzone.addEventListener("drop", (event) => {
  const files = event.dataTransfer ? event.dataTransfer.files : [];
  addSelectedFiles(files);
  refreshSelectedUploadSize();
});

form.addEventListener("change", (event) => {
  const target = event.target;
  if (target && target.tagName === "INPUT" && target.type === "file" && target.id === "backgroundMusic") {
    markFinalRenderDirty();
    refreshSelectedUploadSize();
  }
});

outputPreset.addEventListener("change", () => {
  const [w, h] = outputPreset.value.split("x");
  if (w && h) {
    outputWidthInput.value = w;
    outputHeightInput.value = h;
    markFinalRenderDirty();
    schedulePreviewUpdate();
  }
});

["titleLine1", "titleLine2"].forEach((id) => {
  const element = document.getElementById(id);
  if (element) {
    element.addEventListener("input", () => {
      markFinalRenderDirty();
      schedulePreviewUpdate();
    });
  }
});

[titleFontFamilyInput, listFontFamilyInput, titleFontSizeInput, listFontSizeInput, outputWidthInput, outputHeightInput].forEach((element) => {
  element.addEventListener("change", () => {
    markFinalRenderDirty();
    schedulePreviewUpdate();
  });
});

const useIntermissionsCheckbox = document.getElementById("useIntermissions");
if (useIntermissionsCheckbox) {
  useIntermissionsCheckbox.addEventListener("change", () => {
    markFinalRenderDirty();
    syncIntermissionUI();
    updateIntermissionPreview();
    schedulePreviewUpdate();
  });
}

const intermissionOpacitySlider = document.getElementById("intermissionOpacity");
if (intermissionOpacitySlider) {
  intermissionOpacitySlider.addEventListener("input", () => {
    const opacityValue = document.getElementById("opacityValue");
    if (opacityValue) {
      opacityValue.textContent = `${intermissionOpacitySlider.value}%`;
    }
    markFinalRenderDirty();
    updateIntermissionPreview();
  });
  
  intermissionOpacitySlider.addEventListener("change", () => {
    schedulePreviewUpdate();
  });
}

if (includeMusic) {
  includeMusic.addEventListener("change", () => {
    musicLevelRow.hidden = !includeMusic.checked;
    markFinalRenderDirty();
    if (includeMusic.checked) {
      schedulePreviewUpdate();
    }
  });
}

if (musicLevelInput) {
  musicLevelInput.addEventListener("input", () => {
    const musicLevelValue = document.getElementById("musicLevelValue");
    if (musicLevelValue) {
      musicLevelValue.textContent = `${musicLevelInput.value}%`;
    }
    markFinalRenderDirty();
  });
  
  musicLevelInput.addEventListener("change", () => {
    schedulePreviewUpdate();
  });
}

if (enableNarrationInput) {
  enableNarrationInput.addEventListener("change", () => {
    markFinalRenderDirty();
    updateNarrationBillingUI();
    schedulePreviewUpdate();
  });
}

if (clipSliderPrev) {
  clipSliderPrev.addEventListener("click", () => {
    scrollClipGallery(-1);
  });
}

if (clipSliderNext) {
  clipSliderNext.addEventListener("click", () => {
    scrollClipGallery(1);
  });
}

if (clipGalleryViewport) {
  clipGalleryViewport.addEventListener("scroll", () => {
    updateClipSliderState();
  });
}

window.addEventListener("resize", () => {
  requestAnimationFrame(updateClipSliderState);
});

clipGallery.addEventListener("click", (event) => {
  const target = event.target;
  if (!target || !(target instanceof HTMLElement)) {
    return;
  }
  if (target.dataset.role !== "removeClip") {
    return;
  }

  const index = Number(target.dataset.index);
  if (!Number.isFinite(index) || !selectedClips[index]) {
    return;
  }
  URL.revokeObjectURL(selectedClips[index].objectUrl);
  selectedClips.splice(index, 1);
  renderClipGallery();
  markFinalRenderDirty();
  schedulePreviewUpdate();
});

clipGallery.addEventListener("input", (event) => {
  const target = event.target;
  if (!target || !(target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement)) {
    return;
  }

  const index = Number(target.dataset.index);
  if (!Number.isFinite(index) || !selectedClips[index]) {
    return;
  }

  if (target.dataset.role === "clipTitleInput") {
    const nextTitle = target.value.trim() || "Untitled";
    selectedClips[index].title = nextTitle;
    selectedClips[index].shortTitle = abbreviateTitle(nextTitle);

    const card = target.closest(".clip-card");
    const titlePreview = card ? card.querySelector(".clip-title") : null;
    if (titlePreview) {
      titlePreview.textContent = selectedClips[index].shortTitle;
      titlePreview.setAttribute("title", selectedClips[index].title);
    }
    return;
  }

  if (target.dataset.role === "clipCaptionInput") {
    selectedClips[index].caption = target.value;
    markFinalRenderDirty();
    updateNarrationBillingUI();
  }
});

let previewDebounceTimer = null;
let previewJobSource = null;

function closePreviewStream() {
  if (previewJobSource) {
    previewJobSource.close();
    previewJobSource = null;
  }
}

async function generatePreview() {
  const previewVideo = document.getElementById("previewVideo");
  const previewStatus = document.getElementById("previewStatus");
  const previewProgressWrap = document.getElementById("previewProgressWrap");
  const previewProgressBar = document.getElementById("previewProgressBar");
  const previewStatusBar = document.getElementById("previewStatusBar");

  closePreviewStream();
  attachVideoDiagnostics(previewVideo, "preview-player");

  if (selectedClips.length === 0) {
    previewProgressWrap.hidden = true;
    previewStatusBar.hidden = true;
    previewVideo.hidden = true;
    previewStatus.textContent = "Upload clips to auto-generate preview.";
    return;
  }

  // Show progress bar above the existing preview (don't hide it yet)
  previewProgressWrap.hidden = false;
  previewProgressBar.style.width = "0%";
  previewStatusBar.hidden = false;
  previewStatusBar.textContent = "Queuing preview...";
  previewStatus.textContent = "";

  const titleLine1 = document.getElementById("titleLine1").value.trim() || "Top 5 Funniest";
  const titleLine2 = document.getElementById("titleLine2").value.trim() || "Moments";
  const useIntermissions = document.getElementById("useIntermissions").checked;
  const intermissionOpacity = Number(document.getElementById("intermissionOpacity").value);
  const includeMusicChecked = Boolean(includeMusic && includeMusic.checked);
  const backgroundMusicFile = document.getElementById("backgroundMusic").files[0];
  const musicLevel = includeMusicChecked ? Number(musicLevelInput.value) / 100 : 0.15;

  if (selectedClips[0]?.objectUrl) {
    previewVideo.src = selectedClips[0].objectUrl;
    previewVideo.currentTime = 0;
    previewVideo.load();
    previewVideo.hidden = false;
    reportClientDiagnostic("preview_src_selected_clip", "preview-player", {
      fileLabel: selectedClips[0].file?.name || "clip-1",
      selectedClipBytes: selectedClips[0].file?.size || 0,
    });
  }

  const payload = new FormData();
  payload.append("title_line_1", titleLine1);
  payload.append("title_line_2", titleLine2);
  payload.append("output_width", outputWidthInput.value);
  payload.append("output_height", outputHeightInput.value);
  payload.append("title_font_family", titleFontFamilyInput.value);
  payload.append("list_font_family", listFontFamilyInput.value);
  payload.append("title_font_size", titleFontSizeInput.value);
  payload.append("list_font_size", listFontSizeInput.value);
  payload.append("use_intermissions", useIntermissions ? "true" : "false");
  payload.append("intermission_opacity", String(intermissionOpacity));
  payload.append("include_music", includeMusicChecked ? "true" : "false");
  payload.append("background_music_level", String(musicLevel));
  payload.append("captions_json", JSON.stringify(selectedClips.map((clip) => clip.caption || clip.title)));
  selectedClips.forEach((clip) => payload.append("clips", clip.file));
  if (includeMusicChecked && backgroundMusicFile) {
    payload.append("background_music", backgroundMusicFile);
  }

  let jobId;
  try {
    const response = await fetch("/api/preview", { method: "POST", body: payload });
    if (!response.ok) {
      const data = await response.json();
      throw new Error(mapApiErrorToUserMessage(data.error || "", response.status));
    }
    const result = await response.json();
    jobId = result.job_id;
  } catch (error) {
    previewProgressWrap.hidden = true;
    previewStatusBar.hidden = true;
    previewStatus.textContent = `Preview failed: ${error.message}`;
    return;
  }

  previewStatusBar.textContent = "Generating preview...";

  const source = new EventSource(`/api/jobs/${jobId}/events`);
  previewJobSource = source;
  let previewStreamFinished = false;

  source.addEventListener("progress", (event) => {
    const data = JSON.parse(event.data);
    const progress = Math.max(0, Math.min(100, Number(data.progress || 0)));
    previewProgressBar.style.width = `${progress}%`;
    const base = data.message || "Generating preview";
    previewStatusBar.textContent = `${base} (${progress}%)`;
  });

  source.addEventListener("done", (event) => {
    previewStreamFinished = true;
    const data = JSON.parse(event.data);
    previewProgressBar.style.width = "100%";
    if (data.output_file) {
      previewVideo.src = `/outputs/${encodeURIComponent(data.output_file)}?t=${Date.now()}`;
      previewVideo.currentTime = 0;
      previewVideo.load();
      previewVideo.hidden = false;
      reportClientDiagnostic("preview_src_render_output", "preview-player", {
        outputFile: data.output_file,
      });
    }
    previewStatus.textContent = includeMusicChecked
      ? "Preview ready. Audio playback reflects your background music mix. ElevenLabs narration still applies on final render only."
      : "Preview ready. ElevenLabs narration still applies on final render only.";
    setTimeout(() => {
      previewProgressWrap.hidden = true;
      previewStatusBar.hidden = true;
    }, 800);
    closePreviewStream();
  });

  source.addEventListener("error", (event) => {
    previewStreamFinished = true;
    let msg = "Preview generation failed.";
    try {
      const data = JSON.parse(event.data);
      msg = data.error || msg;
    } catch (_) {}
    previewProgressWrap.hidden = true;
    previewStatusBar.textContent = msg;
    closePreviewStream();
  });

  source.onerror = () => {
    if (!previewStreamFinished) {
      previewStatusBar.textContent = "Preview stream disconnected. Retrying soon when settings change.";
    }
    closePreviewStream();
  };
}

function schedulePreviewUpdate() {
  clearTimeout(previewDebounceTimer);
  previewDebounceTimer = setTimeout(() => {
    generatePreview();
  }, 500);
}

function updateIntermissionPreview() {
  const canvas = document.getElementById("intermissionPreview");
  if (!canvas) return;

  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const opacity = Number(document.getElementById("intermissionOpacity").value) / 100;

  // Clear with black background
  ctx.fillStyle = "#000000";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // Draw white rectangle with opacity
  ctx.fillStyle = `rgba(255, 255, 255, ${opacity})`;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
}

function syncIntermissionUI() {
  const intermissionsEnabled = Boolean(useIntermissionsCheckbox && useIntermissionsCheckbox.checked);

  if (intermissionPreviewRow) {
    intermissionPreviewRow.hidden = !intermissionsEnabled;
  }

  if (intermissionOpacityWrap) {
    intermissionOpacityWrap.hidden = !intermissionsEnabled;
  }
}

function initCaptionGuide() {
  const captionGuide = document.getElementById("captionGuide");
  const dismissBtn = document.getElementById("dismissCaptionGuideBtn");
  if (!captionGuide || !dismissBtn) {
    return;
  }

  const dismissed = localStorage.getItem(CAPTION_GUIDE_DISMISSED_KEY) === "true";
  captionGuide.hidden = dismissed;

  dismissBtn.addEventListener("click", () => {
    captionGuide.hidden = true;
    localStorage.setItem(CAPTION_GUIDE_DISMISSED_KEY, "true");
  });
}

renderClipGallery();
syncIntermissionUI();
updateIntermissionPreview();
initCaptionGuide();
updateNarrationBillingUI();

// ── Access code recovery ────────────────────────────────────────────────────

function showAccessCodeBanner(token, isNew = true) {
  if (!accessCodeBanner || !accessCodeDisplay) return;
  const display = token.length > 20
    ? token.slice(0, 10) + "..." + token.slice(-6)
    : token;
  accessCodeDisplay.textContent = display;
  accessCodeDisplay.title = token;
  if (isNew) {
    accessCodeBanner.classList.add("is-new-token");
  } else {
    accessCodeBanner.classList.remove("is-new-token");
  }
  accessCodeBanner.hidden = false;
}

function openRecoveryModalFromLink(event) {
  event.preventDefault();
  openRecoveryModal();
}

function openRestoreCodeFromLink(event) {
  event.preventDefault();
  openRestoreCodeSection();
}

if (copyAccessCodeBtn) {
  copyAccessCodeBtn.addEventListener("click", () => {
    const token = localStorage.getItem(TOKEN_STORAGE_KEY) || "";
    if (!token) return;
    navigator.clipboard.writeText(token).then(() => {
      const prev = copyAccessCodeBtn.textContent;
      copyAccessCodeBtn.textContent = "Copied!";
      setTimeout(() => { copyAccessCodeBtn.textContent = prev; }, 2000);
    }).catch(() => {
      if (accessCodeDisplay) {
        const range = document.createRange();
        range.selectNodeContents(accessCodeDisplay);
        const sel = window.getSelection();
        if (sel) { sel.removeAllRanges(); sel.addRange(range); }
      }
    });
  });
}

if (linkEmailBtn) {
  linkEmailBtn.addEventListener("click", async () => {
    const email = accessEmailInput ? accessEmailInput.value.trim() : "";
    await submitCreditEmailLink(email, { statusNode: linkEmailStatus, triggerButton: linkEmailBtn });
  });
}

if (secureCreditsConfirmBtn) {
  secureCreditsConfirmBtn.addEventListener("click", async () => {
    const email = secureCreditsEmailInput ? secureCreditsEmailInput.value.trim() : "";
    const result = await submitCreditEmailLink(email, {
      statusNode: secureCreditsStatus,
      triggerButton: secureCreditsConfirmBtn,
    });
    if (result.ok) {
      secureCreditsPromptDismissed = true;
      setTimeout(() => {
        closeSecureCreditsModal();
      }, 500);
    }
  });
}

function openRecoveryModal() {
  if (!recoveryModalOverlay) return;
  if (recoveryEmailInput) recoveryEmailInput.value = "";
  if (recoveryStatus) recoveryStatus.textContent = "";
  if (sendRecoveryBtn) sendRecoveryBtn.disabled = false;
  recoveryModalOverlay.hidden = false;
  if (recoveryEmailInput) recoveryEmailInput.focus();
}

function closeRecoveryModal() {
  if (recoveryModalOverlay) recoveryModalOverlay.hidden = true;
}

if (closeRecoveryModalBtn) {
  closeRecoveryModalBtn.addEventListener("click", closeRecoveryModal);
}

if (recoveryModalOverlay) {
  recoveryModalOverlay.addEventListener("click", (e) => {
    if (e.target === recoveryModalOverlay) closeRecoveryModal();
  });
}

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && recoveryModalOverlay && !recoveryModalOverlay.hidden) {
    closeRecoveryModal();
  }
  if (e.key === "Escape" && secureCreditsModalOverlay && !secureCreditsModalOverlay.hidden) {
    secureCreditsPromptDismissed = true;
    closeSecureCreditsModal();
  }
});

if (sendRecoveryBtn) {
  sendRecoveryBtn.addEventListener("click", async () => {
    const email = recoveryEmailInput ? recoveryEmailInput.value.trim() : "";
    if (!email || !email.includes("@")) {
      if (recoveryStatus) recoveryStatus.textContent = "Enter a valid email address.";
      return;
    }
    sendRecoveryBtn.disabled = true;
    if (recoveryStatus) recoveryStatus.textContent = "Sending...";
    try {
      const fd = new FormData();
      fd.append("email", email);
      const res = await fetch("/api/billing/recover", { method: "POST", body: fd });
      const data = await res.json();
      if (res.status === 503) {
        if (recoveryStatus) recoveryStatus.textContent = data.error || "Email recovery is not configured on this server yet.";
        sendRecoveryBtn.disabled = false;
        return;
      }
      if (recoveryStatus) recoveryStatus.textContent = data.message || "If that email is on file, you'll receive your access code shortly.";
      // Leave button disabled to prevent double-send
    } catch (_err) {
      if (recoveryStatus) recoveryStatus.textContent = "Network error — try again.";
      sendRecoveryBtn.disabled = false;
    }
  });
}

if (openRecoveryModalLink) {
  openRecoveryModalLink.addEventListener("click", openRecoveryModalFromLink);
}

if (openRecoveryModalBannerLink) {
  openRecoveryModalBannerLink.addEventListener("click", openRecoveryModalFromLink);
}

function openRestoreCodeSection() {
  if (!restoreCodeSection) return;
  if (restoreCodeInput) restoreCodeInput.value = "";
  if (restoreCodeStatus) restoreCodeStatus.textContent = "";
  if (applyRestoreCodeBtn) applyRestoreCodeBtn.disabled = false;
  restoreCodeSection.hidden = false;
  restoreCodeSection.scrollIntoView({ behavior: "smooth", block: "nearest" });
  if (restoreCodeInput) restoreCodeInput.focus();
}

if (openRestoreCodeLink) {
  openRestoreCodeLink.addEventListener("click", openRestoreCodeFromLink);
}

if (openRestoreCodeBannerLink) {
  openRestoreCodeBannerLink.addEventListener("click", openRestoreCodeFromLink);
}

if (openRestoreCodeInlineLink) {
  openRestoreCodeInlineLink.addEventListener("click", openRestoreCodeFromLink);
}

if (openRestoreCodeModalLink) {
  openRestoreCodeModalLink.addEventListener("click", openRestoreCodeFromLink);
}

if (applyRestoreCodeBtn) {
  applyRestoreCodeBtn.addEventListener("click", async () => {
    const raw = restoreCodeInput ? restoreCodeInput.value.trim() : "";
    if (!raw || !raw.startsWith("vf_") || raw.length < 10) {
      if (restoreCodeStatus) restoreCodeStatus.textContent = "That doesn't look valid — access codes start with vf_.";
      return;
    }
    applyRestoreCodeBtn.disabled = true;
    if (restoreCodeStatus) restoreCodeStatus.textContent = "Verifying...";
    try {
      const res = await fetch(`/api/billing/status?token=${encodeURIComponent(raw)}`);
      const data = await res.json();
      if (!res.ok) {
        if (restoreCodeStatus) restoreCodeStatus.textContent = data.error || "Access code not recognised.";
        applyRestoreCodeBtn.disabled = false;
        return;
      }
      const tokenInput = getTokenInput();
      if (tokenInput) tokenInput.value = raw;
      localStorage.setItem(TOKEN_STORAGE_KEY, raw);
      setAccountBillingStatus(data);
      if (restoreCodeStatus) restoreCodeStatus.textContent = "✓ Access restored!";
      if (restoreCodeSection) restoreCodeSection.hidden = true;
      showAccessCodeBanner(raw, false);
      await refreshTokenCreditsUI(raw);
    } catch (_err) {
      if (restoreCodeStatus) restoreCodeStatus.textContent = "Network error — try again.";
      applyRestoreCodeBtn.disabled = false;
    }
  });
}
