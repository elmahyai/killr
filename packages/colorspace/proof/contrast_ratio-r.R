suppressPackageStartupMessages(library(colorspace))
stopifnot(identical(packageDescription("colorspace")$Version, "2.1-4"))

json_num <- function(x) sprintf("%.17g", x)
json_vec <- function(x) {
  paste0("[", paste(vapply(x, json_num, ""), collapse = ","), "]")
}
json_mat <- function(m) {
  parts <- character(nrow(m))
  for (i in seq_len(nrow(m))) {
    parts[[i]] <- json_vec(m[i, ])
  }
  paste0("[", paste(parts, collapse = ","), "]")
}
json_ratio <- function(x, apca = FALSE) {
  if (apca) json_mat(x) else json_vec(x)
}

one <- function() {
  list(
    palette_wcag = contrast_ratio(palette(), "white"),
    hex_pair = contrast_ratio(c("#FF0000", "#00FF00"), c("white", "black")),
    named_apca = contrast_ratio(c("red", "blue"), "white", algorithm = "APCA"),
    recycle = contrast_ratio("red", c("white", "black", "gray")),
    palette_int = contrast_ratio(1:8, "white"),
    transparent = contrast_ratio("transparent", "#000000"),
    short_hex = contrast_ratio(c("#abc", "#123456"), "white"),
    near_white_apca = contrast_ratio("#fefefe", "#ffffff", algorithm = "APCA")
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
    '{"palette_wcag":%s,"hex_pair":%s,"named_apca":%s,"recycle":%s,',
    '"palette_int":%s,"transparent":%s,"short_hex":%s,"near_white_apca":%s,',
    '"median_ms":%.17g}\n'
  ),
  json_ratio(value$palette_wcag),
  json_ratio(value$hex_pair),
  json_ratio(value$named_apca, TRUE),
  json_ratio(value$recycle),
  json_ratio(value$palette_int),
  json_ratio(value$transparent),
  json_ratio(value$short_hex),
  json_ratio(value$near_white_apca, TRUE),
  median(elapsed) * 1000
))
