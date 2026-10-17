.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(gtools))
stopifnot(as.character(packageVersion("gtools")) == "3.9.5")

json_str <- function(s) {
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

flat <- function(x) {
  paste(vapply(x, json_str, ""), collapse = ",")
}

one <- function() {
  c(
    capwords("a function to capitalize words in a title"),
    capwords("a function to capitalize words in a title", AP = FALSE),
    capwords("testing the iProduct for defects"),
    capwords("testing the iProduct for defects", strict = TRUE),
    capwords("testing the iProduct for defects", onlyfirst = TRUE),
    capwords("testing the iProduct for defects", preserveMixed = TRUE),
    capwords("title_using_underscores_as_separators", sep = "_"),
    capwords(""),
    capwords("AND"),
    capwords("a  b"),
    capwords("word With MixedCase Inside"),
    capwords("word With MixedCase Inside", preserveMixed = TRUE),
    capwords("to be Or not To Be", AP = FALSE),
    capwords("to be Or not To Be"),
    capwords("single"),
    capwords("iPhone starts mixed", preserveMixed = TRUE),
    capwords("iPhone starts mixed", preserveMixed = FALSE)
  )
}

value <- flat(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":[%s],"median_ms":%.17g}\n', value, median(elapsed) * 1000))
