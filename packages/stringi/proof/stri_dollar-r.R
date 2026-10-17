suppressPackageStartupMessages(library(stringi))
stopifnot(as.character(packageVersion("stringi")) == "1.8.9")
suppressPackageStartupMessages(library(jsonlite))


example <- "value='%d'" %stri$% 3
writeLines(
  paste0("value='%d' %stri$% 3 returns ", example, "."),
  "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/%stri$%-r.txt"
)

one <- function() {
  list(
    one = "value='%d'" %stri$% 3,
    vec = "value='%d'" %stri$% 1:3,
    pair = "%s=%d" %stri$% list(c("a", "b"), 1:2),
    na = "%s" %stri$% NA_character_,
    sci = "%s" %stri$% c(1e5, 1e-4)
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste0(as.character(toJSON(list(value = value, median_ms = median(elapsed) * 1000), auto_unbox = TRUE, na = "null", digits = 16)), "\n"))
