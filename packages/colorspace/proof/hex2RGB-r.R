suppressPackageStartupMessages(library(colorspace))
stopifnot(identical(packageDescription("colorspace")$Version, "2.1-4"))

json_num <- function(x) sprintf("%.17g", x)
json_str <- function(s) {
  s <- enc2utf8(s)
  s <- gsub("\\", "\\\\", s, fixed = TRUE)
  s <- gsub("\"", "\\\"", s, fixed = TRUE)
  paste0('"', s, '"')
}
json_names <- function(nm) {
  if (is.null(nm)) return("null")
  paste0("[", paste(vapply(nm, json_str, ""), collapse = ","), "]")
}
json_mat <- function(m) {
  parts <- character(nrow(m))
  for (i in seq_len(nrow(m))) {
    parts[[i]] <- paste0(
      "[", paste(vapply(m[i, ], json_num, ""), collapse = ","), "]"
    )
  }
  paste0("[", paste(parts, collapse = ","), "]")
}
json_color <- function(obj) {
  sprintf(
    '{"space":%s,"names":%s,"columns":[%s],"coords":%s}',
    json_str(class(obj)[[1L]]),
    json_names(rownames(obj@coords)),
    paste(vapply(colnames(obj@coords), json_str, ""), collapse = ","),
    json_mat(obj@coords)
  )
}

hexes <- sprintf("#%02X%02X%02X", 0:255, 255:0, (0:255 + 17) %% 256)

one <- function() {
  list(
    plain = hex2RGB(c(
      "#FF0000", "#00FF00", "#0000FF50", "#aabbcc", "#112233zzzz", "#aAbBcC"
    )),
    named = hex2RGB(c(red = "#FF0000", blue = "#0000FF80")),
    encoded = hex2RGB(hexes),
    linear = hex2RGB(hexes, gamma = TRUE),
    flag0 = hex2RGB("#0A0000", gamma = 0),
    flag_true = hex2RGB("#0A0000", gamma = "TRUE"),
    flag2 = hex2RGB("#0A0000", gamma = 2)
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
  '{"plain":%s,"named":%s,"encoded":%s,"linear":%s,"flag0":%s,"flag_true":%s,"flag2":%s,"median_ms":%.17g}\n',
  json_color(value$plain),
  json_color(value$named),
  json_color(value$encoded),
  json_color(value$linear),
  json_color(value$flag0),
  json_color(value$flag_true),
  json_color(value$flag2),
  median(elapsed) * 1000
))
