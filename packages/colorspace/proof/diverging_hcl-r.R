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
    default = diverging_hcl(7, h = c(260, 0), c = 80, l = c(35, 95), power = 1),
    power_vec = diverging_hcl(7, h = c(260, 0), c = 80, l = c(35, 95), power = c(0.8, 1.4)),
    cmax = diverging_hcl(7, h = c(260, 0), c = c(80, 100), l = c(35, 95), power = 1),
    palette = diverging_hcl(7, palette = "Tropic", h2 = 0),
    odd_n = diverging_hcl(11, h = c(260, 0), c = 80, l = c(30, 90), power = 1.5),
    even_n = diverging_hcl(10, h = c(260, 0), c = 80, l = c(30, 90), power = 1.5),
    single = diverging_hcl(1, h = c(260, 0), c = 80, l = c(35, 95), power = 1),
    rev = diverging_hcl(7, h = c(260, 0), c = 80, l = c(35, 95), power = 1, rev = TRUE),
    alpha = diverging_hcl(5, h = c(260, 0), c = 80, l = c(35, 95), power = 1, alpha = c(1, 0.5, 0.25, 0.5, 1)),
    no_fixup = diverging_hcl(7, h = c(260, 0), c = 120, l = c(35, 95), power = 1, fixup = FALSE),
    named = diverging_hcl(7, palette = "Blue-Red 3"),
    bulk = diverging_hcl(
      256,
      h = c(260, 0),
      c = 80,
      l = c(30, 90),
      power = 1.5
    )
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
    '{"default":%s,"power_vec":%s,"cmax":%s,"palette":%s,',
    '"odd_n":%s,"even_n":%s,"single":%s,"rev":%s,"alpha":%s,',
    '"no_fixup":%s,"named":%s,"bulk":%s,"median_ms":%.17g}\n'
  ),
  json_vec(unname(value$default)),
  json_vec(unname(value$power_vec)),
  json_vec(unname(value$cmax)),
  json_vec(unname(value$palette)),
  json_vec(unname(value$odd_n)),
  json_vec(unname(value$even_n)),
  json_vec(unname(value$single)),
  json_vec(unname(value$rev)),
  json_vec(unname(value$alpha)),
  json_vec(unname(value$no_fixup)),
  json_vec(unname(value$named)),
  json_vec(unname(value$bulk)),
  median(elapsed) * 1000
))
