suppressPackageStartupMessages(library(colorspace))
stopifnot(identical(packageDescription("colorspace")$Version, "2.1-4"))

json_num <- function(x) {
  if (length(x) == 0) return("[]")
  paste0(
    "[",
    paste(vapply(x, function(v) {
      if (is.na(v)) "null" else sprintf("%.17g", v)
    }, ""), collapse = ","),
    "]"
  )
}

one <- function() {
  list(
    example_h = max_chroma(h = 0:36 * 10, l = 50),
    example_l = max_chroma(h = 120, l = 0:10 * 10),
    floor_true = max_chroma(h = c(0, 45, 90, 180), l = 50, floor = TRUE),
    recycle = max_chroma(h = c(0, 120, 240), l = c(30, 50, 70, 90)),
    wrap_h = max_chroma(h = c(-30, 390, 720.5), l = 50),
    clamp_l = max_chroma(h = 180, l = c(-10, 0, 50, 100, 150)),
    na_prop = max_chroma(h = c(NA, 60), l = c(50, NA)),
    bulk = max_chroma(
      h = rep(seq(0, 350, by = 10), length.out = 512),
      l = rep(seq(5, 95, by = 5), length.out = 512)
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
    '{"example_h":%s,"example_l":%s,"floor_true":%s,"recycle":%s,',
    '"wrap_h":%s,"clamp_l":%s,"na_prop":%s,"bulk":%s,"median_ms":%.17g}\n'
  ),
  json_num(value$example_h),
  json_num(value$example_l),
  json_num(value$floor_true),
  json_num(value$recycle),
  json_num(value$wrap_h),
  json_num(value$clamp_l),
  json_num(value$na_prop),
  json_num(value$bulk),
  median(elapsed) * 1000
))
