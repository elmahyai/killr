suppressPackageStartupMessages(library(stringi))
stopifnot(as.character(packageVersion("stringi")) == "1.8.9")

example <- stri_length(c("abc", NA))
writeLines(
  paste0(
    "stri_length(c(\"abc\", NA)) returns ",
    paste(ifelse(is.na(example), "NA", example), collapse = ", "),
    "."
  ),
  "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_length-r.txt"
)

json_vec <- function(x) {
  if (length(x) == 0) return("[]")
  parts <- ifelse(is.na(x), "null", as.character(x))
  paste0("[", paste(parts, collapse = ","), "]")
}

base <- c(
  "abc", NA, "", "NA",
  "\u0105",
  "\U0001F606",
  "\uFF21",
  "A\u0301",
  "\U0001F1FA\U0001F1F8",
  "\U0001F468\u200D\U0001F469\u200D\U0001F467",
  "\u1161\u11A8",
  "\u00AD",
  "\u200B",
  "\u1100",
  "\u200D\u2640",
  "\u0301",
  "\U0001F1E6\U0001F1E7\U0001F1E8",
  "\u2600",
  intToUtf8(0x1FAE9),
  intToUtf8(0x1171E),
  paste0("\u200D", intToUtf8(0x1FAE9)),
  intToUtf8(0x1F8B2)
)

one <- function() {
  list(
    main = stri_length(rep(base, 80)),
    ints = stri_length(1:3),
    logical = stri_length(c(TRUE, FALSE, NA)),
    int_big = stri_length(10000000L),
    doubles = stri_length(c(1.5, 1e-4, 1e5, Inf, -Inf, NaN, 1/3, 2^-1074)),
    complex = stri_length(1 + 2i),
    mixed = stri_length(c("a", 1L, TRUE, NA_character_, 1.5)),
    promoted = stri_length(c(10000000L, 1)),
    int_bool = stri_length(c(1L, TRUE)),
    empty = stri_length(NULL)
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
  "{\"value\":{\"main\":%s,\"ints\":%s,\"logical\":%s,\"int_big\":%s,\"doubles\":%s,\"complex\":%s,\"mixed\":%s,\"promoted\":%s,\"int_bool\":%s,\"empty\":%s},\"median_ms\":%.17g}\n",
  json_vec(value$main),
  json_vec(value$ints),
  json_vec(value$logical),
  json_vec(value$int_big),
  json_vec(value$doubles),
  json_vec(value$complex),
  json_vec(value$mixed),
  json_vec(value$promoted),
  json_vec(value$int_bool),
  json_vec(value$empty),
  median(elapsed) * 1000
))
