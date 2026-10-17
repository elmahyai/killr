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
  hsv_obj <- HSV(seq(0, 360, length.out = 7)[-7], 1, 1)
  srgb_obj <- sRGB(c(1, 0, 0.25), c(0, 1, 0.5), c(0, 0, 0.75))
  lab_obj <- LAB(
    rbind(c(50, 40, 30), c(60, -20, 50), c(70, 10, -40)),
    names = c("a", "b", "c")
  )
  oog <- RGB(2, -0.1, 0.5)
  bulk_hsv <- HSV(seq(0, 360, length.out = 256), 0.8, 0.9)
  list(
    hsv_example = hex(hsv_obj),
    srgb_object = hex(srgb_obj),
    lab_named = hex(lab_obj),
    fixup_true = hex(oog, fixup = TRUE),
    fixup_false = hex(oog, fixup = FALSE),
    bulk = hex(bulk_hsv)
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
    '{"hsv_example":%s,"srgb_object":%s,"lab_named":%s,',
    '"fixup_true":%s,"fixup_false":%s,"bulk":%s,"median_ms":%.17g}'
  ),
  json_vec(unname(value$hsv_example)),
  json_vec(unname(value$srgb_object)),
  json_vec(unname(value$lab_named)),
  json_vec(unname(value$fixup_true)),
  json_vec(unname(value$fixup_false)),
  json_vec(unname(value$bulk)),
  median(elapsed) * 1000
))
