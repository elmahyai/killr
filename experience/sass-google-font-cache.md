# sass: font_google(local = TRUE) without network

- font_google() with the default local = TRUE returns a dependency that is built only when rendered. Rendering reads the Google stylesheet and each font file from the sass file cache, and downloads only on a miss.
- To prove it offline, pass a cache whose hits are the fixture files. R keys its cache with rlang hashes, so the R proof wraps the fixture in a stub that maps each `hash_with_user_agent(href)` and `hash_with_user_agent(basename)` to a file. Python looks up the href and the basename directly. Both read `packages/sass/proof/fixtures/google_local/manifest.json`.
- The fixture stylesheet is the localized CSS (`url(<basename>)`), since that is what a previous online run stores. With that, R takes the cache-hit branch and does not rewrite the CSS.
- The fixture covers only the default href (`family=Roboto&display=swap`). Any other axis or display value misses the cache and needs the download, which is not translated.
- `list.files()` in R sorts with the locale. Sort names with method "radix" on the R side and with `sorted()` on the Python side before comparing file lists.
