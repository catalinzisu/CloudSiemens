# AWS S3 static DOOM package

Upload the contents of this folder directly to your S3 bucket.

Recommended S3 website settings:

- `Index document`: `person.html` (recommended)
- `Error document`: `error.html`

Compatibility note:

- `index.html` is included only as a redirect to `person.html`
- If you keep the default S3 index document as `index.html`, the site still lands on `person.html`

Important routing note:

- The landing page is `person.html`
- For pure S3 website hosting, the game route should be accessed as `/doom/`
- The file that powers that route is `doom/index.html`
- According to AWS S3 website hosting behavior, a request to `/doom` can redirect to `/doom/` when `doom/index.html` exists

This package is static-only:

- no Python
- no Flask
- no build step
- DOOM is loaded client-side via `js-dos`
