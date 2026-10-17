suppressPackageStartupMessages(library(reshape2))
stopifnot(identical(as.character(packageVersion("reshape2")), "1.4.5"))

n <- 20000L
month <- (seq_len(n) %% 12L) + 1L
variable <- LETTERS[(seq_len(n) %% 5L) + 1L]
value <- ((seq_len(n) * 13L) %% 97L) + (seq_len(n) %% 7L) / 10
df <- data.frame(month = month, variable = variable, value = value, stringsAsFactors = FALSE)

one <- function() dcast(df, month ~ variable, mean)

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}

cat("NAMES ", paste(names(value), collapse = " "), "\n", sep = "")
cat("MONTH ", paste(value$month, collapse = " "), "\n", sep = "")
for (nm in names(value)[-1]) {
  cat("COL ", nm, " ", paste(sprintf("%.17g", value[[nm]]), collapse = " "), "\n", sep = "")
}
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
