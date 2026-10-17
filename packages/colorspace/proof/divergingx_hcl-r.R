suppressPackageStartupMessages(library(colorspace))
stopifnot(identical(packageDescription("colorspace")$Version, "2.1-4"))

json_str <- function(s) {
  if (length(s) != 1L) stop("json_str expects length 1")
  if (is.na(s)) return("null")
  s <- enc2utf8(s)
  s <- gsub("\\", "\\\\", s, fixed = TRUE)
  s <- gsub("\"", "\\\"", s, fixed = TRUE)
  paste0('"', s, '"')
}
json_vec <- function(x) {
  paste0("[", paste(vapply(x, json_str, ""), collapse = ","), "]")
}

one <- function() {
  list(
    default = divergingx_hcl(7),
    geyser = divergingx_hcl(7, palette = "Geyser"),
    armyrose = divergingx_hcl(7, palette = "ArmyRose"),
    rdylbu = divergingx_hcl(11, palette = "RdYlBu"),
    tropic = divergingx_hcl(7, palette = "Tropic"),
    zissou = divergingx_hcl(7, palette = "Zissou 1"),
    override_h1 = divergingx_hcl(7, palette = "Geyser", h1 = 200),
    odd_n = divergingx_hcl(11, palette = "Spectral"),
    even_n = divergingx_hcl(10, palette = "Spectral"),
    single = divergingx_hcl(1, palette = "PuOr"),
    rev = divergingx_hcl(7, palette = "Geyser", rev = TRUE),
    alpha = divergingx_hcl(
      5, palette = "Geyser", alpha = c(1, 0.5, 0.25, 0.5, 1)
    ),
    explicit_alpha1 = divergingx_hcl(3, palette = "Geyser", alpha = 1),
    no_fixup = divergingx_hcl(7, palette = "Geyser", fixup = FALSE, c1 = 120),
    bulk = divergingx_hcl(256, palette = "Temps")
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}

cat(sprintf(
  paste0(
    '{"default":%s,"geyser":%s,"armyrose":%s,"rdylbu":%s,"tropic":%s,',
    '"zissou":%s,"override_h1":%s,"odd_n":%s,"even_n":%s,"single":%s,',
    '"rev":%s,"alpha":%s,"explicit_alpha1":%s,"no_fixup":%s,"bulk":%s,',
    '"median_ms":%.17g}\n'
  ),
  json_vec(unname(value$default)),
  json_vec(unname(value$geyser)),
  json_vec(unname(value$armyrose)),
  json_vec(unname(value$rdylbu)),
  json_vec(unname(value$tropic)),
  json_vec(unname(value$zissou)),
  json_vec(unname(value$override_h1)),
  json_vec(unname(value$odd_n)),
  json_vec(unname(value$even_n)),
  json_vec(unname(value$single)),
  json_vec(unname(value$rev)),
  json_vec(unname(value$alpha)),
  json_vec(unname(value$explicit_alpha1)),
  json_vec(unname(value$no_fixup)),
  json_vec(unname(value$bulk)),
  median(elapsed) * 1000
))
