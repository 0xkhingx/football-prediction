# Glossary (explained once, reused afterwards)

## Web / Frontend
- **WOFF2**: the standard compressed file format for fonts on the web; small and supported by all modern browsers.
- **Variable font**: a single font file containing a whole weight range (here 300–800) instead of one file per weight; the browser picks any weight along the range.
- **Self-hosting (fonts)**: serving font files from our own site/repo rather than loading them from Google's servers at visit time.
- **next/font**: Next.js's built-in font loader; it downloads/hosts the files at build time and generates the CSS, so pages don't wait on an external font server.
- **next/font/local**: the part of next/font for font files we keep in our own repo.
- **next/font/google**: the part of next/font that fetches a Google Font once at build time and then serves it from our site like a local file.
- **CSS variable for fonts**: a named slot (e.g. `--font-display`) holding the font name; our styles refer to the slot so swapping the font means changing one line.
- **Tailwind utility class**: a short class name (e.g. `font-display`) that applies one style rule; our `font-display` class sets the header font family.
- **Typecheck (`npm run typecheck`)**: a command that re-reads all our TypeScript and reports type mistakes without running or building the site.
