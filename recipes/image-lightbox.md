+++
name = "image-lightbox"
description = "Click an image in an article to open it full-size in a modal overlay."
+++

**What** — clicking any image in a rendered Markdown body opens it full-size in a
modal, dimming the page behind it. Click anywhere or press Escape to close.

**Where** — `base.html`, `main.css`, and one new file `static/js/lightbox.js`.
Needs JavaScript: images come out of Markdown, so there's no per-image markup to
hook and no build-time way to add a click handler.

**When** — sites with photos, screenshots, or diagrams that lose detail at the
reading column's width. Skip it for decorative images, and skip it if you want
gallery navigation (prev/next between images) — that needs a real image list and
is well past what this recipe does.

**How**

1. Create `static/js/lightbox.js`:

   ```js
   const dialog = document.createElement('dialog');
   dialog.className = 'lightbox';
   dialog.innerHTML = '<img alt="">';
   document.body.append(dialog);
   const full = dialog.firstElementChild;

   // Delegated from the document: one listener covers every image on the page,
   // including any added later, without touching the Markdown-rendered markup.
   document.addEventListener('click', (event) => {
     const image = event.target.closest('.body img');
     if (!image || image.closest('a')) return;  // a linked image keeps its link
     full.src = image.currentSrc || image.src;
     full.alt = image.alt;
     dialog.showModal();
   });
   dialog.addEventListener('click', () => dialog.close());
   ```

   `<dialog>` + `showModal()` is what keeps this short: Escape-to-close, the
   backdrop, focus trapping and `aria-modal` are the element's own behavior.

2. Load it from `base.html`, before `</body>`:

   ```html
   <script src="/js/lightbox.js" defer></script>
   ```

   Write the `src` **root-absolute**; cuttlefish rewrites it for subpath hosting
   at build time.

3. Add to `static/css/main.css`, using the site's tokens:

   ```css
   .body img { cursor: zoom-in; }

   .lightbox {
     max-width: 92vw;
     max-height: 92vh;
     padding: 0;
     border: none;
     background: none;
     overflow: hidden;
   }
   .lightbox img {
     display: block;
     max-width: 92vw;
     max-height: 92vh;
     width: auto;
     height: auto;
     border-radius: var(--radius);
     cursor: zoom-out;
   }
   .lightbox::backdrop { background: rgb(0 0 0 / 0.75); }
   ```

   A `<dialog>` has UA styles worth overriding — the `padding`, `border` and
   `background` above stop a white frame appearing around the image in light mode.

Preview with `ctf serve`: click an image in a post — it should fill most of the
viewport over a dimmed page, and close on click, Escape, or a click on the
backdrop. Check a portrait image and a very wide one; both dimensions are capped,
so neither should overflow. Images outside `.body` (an avatar, a logo in the
header) are deliberately left alone — widen the `.body img` selector if you want
them included.
