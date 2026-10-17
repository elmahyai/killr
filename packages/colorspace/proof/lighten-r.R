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

cl <- c("#61A9D9", "#ADD668", "#E6D152", "#CE6BAF", "#797CBA")
hexes <- c("#FF0000", "#00FF0080", "#336699", "#AABBCCDD")

one <- function() {
  list(
    default = lighten(cl, 0.15),
    hls = lighten(cl, 0.15, space = "HLS"),
    combined = lighten(cl, 0.3, space = "combined"),
    absolute = lighten(hexes, 0.2, method = "absolute"),
    zero = lighten(c("#112233", "#445566"), c(0.2, 0)),
    recycle = lighten("#112233", c(0.1, 0.2, 0.3)),
    negative = lighten(cl, -0.1),
    named = lighten(c(red = "#FF0000", blue = "#0000FF")),
    palette = lighten(1:3, 0.25),
    no_fixup = lighten(c("#FF0000", "#010101"), 0.5, fixup = FALSE),
    bulk = lighten(
      sprintf("#%02X%02X%02X", 0:255, 255:0, (0:255 + 17) %% 256),
      0.12
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
    '{"default":%s,"hls":%s,"combined":%s,"absolute":%s,',
    '"zero":%s,"recycle":%s,"negative":%s,"named":%s,',
    '"palette":%s,"no_fixup":%s,"bulk":%s,"median_ms":%.17g}\n'
  ),
  json_vec(unname(value$default)),
  json_vec(unname(value$hls)),
  json_vec(unname(value$combined)),
  json_vec(unname(value$absolute)),
  json_vec(unname(value$zero)),
  json_vec(unname(value$recycle)),
  json_vec(unname(value$negative)),
  json_vec(unname(value$named)),
  json_vec(unname(value$palette)),
  json_vec(unname(value$no_fixup)),
  json_vec(unname(value$bulk)),
  median(elapsed) * 1000
))
