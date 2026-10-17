suppressPackageStartupMessages(library(survival))
stopifnot(identical(packageDescription("survival")$Version, "3.8-12"))

serialize <- function(parts) {
  out <- character()
  for (item in parts) {
    if (is.factor(item)) {
      out <- c(out, paste(as.character(item), collapse = ","))
    } else if (is.logical(item)) {
      out <- c(out, paste(ifelse(is.na(item), "NA", ifelse(item, "TRUE", "FALSE")), collapse = ","))
    } else if (is.numeric(item)) {
      out <- c(out, paste(sprintf("%.17g", item), collapse = ","))
    } else {
      out <- c(out, paste(item, collapse = ","))
    }
  }
  out
}

one <- function() {
  id <- c(2, 1, 1, 2, 1, 2, 1, 1)
  time <- c(3, 2, 1, 1, 4, 2, 3, 5)
  platelet <- c(200, NA, 150, NA, NA, 180, 160, NA)
  diabetes <- c(NA, 0, 1, NA, NA, 0, 1, 1)
  active <- c(NA, TRUE, FALSE, NA, NA, TRUE, NA, FALSE)
  stage <- factor(c("B", NA, "A", "B", NA, "A", NA, "B"), levels = c("A", "B", "C"))

  a <- lvcf(id, platelet, time)
  b <- lvcf(id, diabetes, time, first = TRUE)
  c <- lvcf(id, active, time, first = TRUE)
  d <- lvcf(id, stage, time)
  e <- lvcf(c(3, 1, 2, 1, 3), c(10, NA, NA, 20, NA))
  serialize(list(a, b, c, d, e))
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(value, collapse = "\n"), "\n", sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
