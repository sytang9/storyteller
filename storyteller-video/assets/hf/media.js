// Media helpers: icons and images that build.py put in data.js (window.TEASER.media, from media_build.collect_media).
// Plain browser JS, no network: icons are inlined SVG strings, images are local files under assets/media/.
// Helpers from index.html: el, col, C. Each helper returns its node; animate it like any other (popIn, tl.to).
// x, y place the node absolutely in scene px; without them it flows inside its parent.

const mediaData = () => (window.TEASER && window.TEASER.media) || { icons: {}, images: {}, credits: [] };
const mediaPlace = (n, x, y) => {
  if (x === undefined && y === undefined) return;
  Object.assign(n.style, { position: "absolute", left: (x || 0) + "px", top: (y || 0) + "px" });
};

// iconEl: the icon painted in one look role ("ink", "accent", ...) or a literal colour, size px square.
// media_build.py already rewrote every fill and stroke to currentColor, so the CSS colour recolours it.
function iconEl(parent, id, { size = 96, color = "ink", x, y } = {}) {
  const src = mediaData().icons[id];
  if (!src) throw new Error(`media: no icon "${id}" (add it to media.json, run fetch_assets.py, rebuild)`);
  // DOMParser instead of innerHTML: the string never runs as HTML
  const doc = new DOMParser().parseFromString(src, "image/svg+xml");
  if (doc.documentElement.nodeName !== "svg") throw new Error(`media: icon "${id}" is not valid svg`);
  const svg = document.importNode(doc.documentElement, true);
  svg.setAttribute("width", size);
  svg.setAttribute("height", size);
  svg.style.display = "block";
  const n = el("div", "media-icon", parent, { width: size + "px", height: size + "px", color: col(color) });
  n.appendChild(svg);
  mediaPlace(n, x, y);
  return n;
}

// imageEl: a photo or illustration in a w x h box. fit "cover" crops to fill, "contain" shows all of it.
function imageEl(parent, id, { w, h, fit = "cover", x, y, radius = 0 } = {}) {
  const src = mediaData().images[id];
  if (!src) throw new Error(`media: no image "${id}" (add it to media.json, run fetch_assets.py, rebuild)`);
  if (!w || !h) throw new Error(`media: image "${id}" needs w and h`);
  const n = el("img", "media-image", parent, {
    display: "block", width: w + "px", height: h + "px", objectFit: fit, borderRadius: radius + "px",
  });
  n.decoding = "sync"; // the renderer seeks frames; the picture must not pop in late
  n.alt = "";
  n.src = src;
  mediaPlace(n, x, y);
  return n;
}

// creditsCard: one small line for the end card. Icon sets are grouped (one entry per set); every image is named
// with its credit_text, because CC BY asks for title, author and licence. Returns null when there are no credits.
// x, y are frame px: the "head" class keeps the line out of the scene fit, so it stays small and at the bottom.
function creditsCard(root, { x = 120, y = FRAME_H - 72, size = 22, color = "mute" } = {}) {
  const credits = mediaData().credits || [];
  if (!credits.length) return null;
  const sets = [...new Set(credits.filter((a) => a.kind === "icon").map((a) => a.credit_text))];
  const images = credits.filter((a) => a.kind !== "icon").map((a) => a.credit_text);
  const parts = [...(images.length ? ["Images: " + images.join("; ")] : []), ...(sets.length ? ["Icons: " + sets.join("; ")] : [])];
  return el("div", "abs head media-credits", root, {
    left: x + "px", top: y + "px", maxWidth: 1920 - 2 * x + "px", fontSize: size + "px", lineHeight: 1.3, color: col(color),
  }, parts.join("   |   "));
}
