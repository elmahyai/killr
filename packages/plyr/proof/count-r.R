suppressPackageStartupMessages(library(plyr))
stopifnot(identical(as.character(packageVersion("plyr")), "1.8.9"))

n <- 20000L
year <- 1871L + (seq_len(n) %% 50L)
team <- LETTERS[((seq_len(n) %/% 50L) %% 26L) + 1L]
g <- ((seq_len(n) * 13L) %% 160L) + 1L
df <- data.frame(year = year, team = team, g = g, stringsAsFactors = FALSE)

one <- function() count(df, c("year", "team"), "g")

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}

shown <- paste(sprintf("%d|%s|%.17g", value$year, value$team, value$freq), collapse = ";")
cat("VALUE ", shown, "\n", sep = "")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
