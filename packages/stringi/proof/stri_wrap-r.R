suppressPackageStartupMessages(library(stringi))
stopifnot(as.character(packageVersion("stringi")) == "1.8.9")
suppressPackageStartupMessages(library(jsonlite))


s <- "Lorem ipsum dolor sit amet, consectetur adipisicing elit. Proin nibh augue, suscipit a, scelerisque sed, lacinia in, mi. Cras vel lorem. Etiam pellentesque aliquet tellus."
writeLines(
  paste0("stri_wrap(s, 20, 0) returns ", length(stri_wrap(s, 20, 0, locale = "en_US")), " lines."),
  "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_wrap-r.txt"
)

one <- function() {
  list(
    greedy = stri_wrap(s, 20, 0, locale = "en_US"),
    dynamic = stri_wrap(s, 20, 2, locale = "en_US"),
    indent = stri_wrap(s, 24, 0, indent = 2, exdent = 4, prefix = "> ", initial = "* ", normalize = FALSE, locale = "en_US"),
    ws = stri_wrap("hello   world  wide", 10, 0, whitespace_only = TRUE, normalize = FALSE, locale = "en_US"),
    cjk = stri_wrap("一一 一一 一", 4, 0, use_length = FALSE, normalize = FALSE, locale = "en_US"),
    emoji = stri_wrap("a\U0001F600 b cd", 3, 0, normalize = FALSE, locale = "en_US"),
    norm = stri_wrap("hello\nworld  there", 10, 0, normalize = TRUE, locale = "en_US"),
    missing = stri_wrap(c("ab cd ef", NA), 4, 0, normalize = FALSE, locale = "en_US")
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
