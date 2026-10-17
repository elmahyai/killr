.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(gtools))
stopifnot(as.character(packageVersion("gtools")) == "3.9.5")

json_str <- function(s) {
  if (length(s) != 1) stop("scalar expected")
  if (is.na(s)) return("null")
  chars <- strsplit(enc2utf8(s), "")[[1]]
  parts <- character(length(chars))
  for (i in seq_along(chars)) {
    cp <- utf8ToInt(chars[[i]])
    parts[[i]] <- if (cp == 34) paste0("\\", '"')
      else if (cp == 92) paste0("\\", "\\")
      else if (cp == 10) paste0("\\", "n")
      else if (cp == 13) paste0("\\", "r")
      else if (cp == 9) paste0("\\", "t")
      else if (cp < 32 || cp == 127) sprintf("\\u%04x", cp)
      else chars[[i]]
  }
  paste0('"', paste(parts, collapse = ""), '"')
}

vec_json <- function(v) {
  paste0("[", paste(vapply(v, json_str, ""), collapse = ","), "]")
}

one <- function() {
  list(
    vec_json(split_path("/home/user/file.txt")),
    vec_json(split_path("/home/user/file.txt", depth_first = FALSE)),
    vec_json(split_path("/home/user/")),
    vec_json(split_path("/home/user/", depth_first = FALSE)),
    vec_json(split_path("file.txt")),
    vec_json(split_path("./file.txt")),
    vec_json(split_path("../file.txt")),
    vec_json(split_path("../file.txt", depth_first = FALSE)),
    vec_json(split_path("/")),
    vec_json(split_path("a/b/c")),
    vec_json(split_path("a/b/c", depth_first = FALSE)),
    vec_json(split_path("a")),
    vec_json(split_path("")),
    vec_json(split_path("/a//b/c")),
    vec_json(split_path("relative/path/here")),
    vec_json(split_path("C:/Users/file")),
    vec_json(split_path(NA_character_)),
    vec_json(split_path(".", depth_first = FALSE)),
    vec_json(split_path(".."))
  )
}

invisible(one())
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  '{"value":[%s],"median_ms":%.17g}\n',
  paste(value, collapse = ","),
  median(elapsed) * 1000
))
