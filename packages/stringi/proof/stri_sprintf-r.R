suppressPackageStartupMessages(library(stringi))
stopifnot(as.character(packageVersion("stringi")) == "1.8.9")
suppressPackageStartupMessages(library(jsonlite))
# A large compiled function can fold away the sign of the second zero.
signed_zeros <- function() stri_sprintf("%+f", c(-0, 0))


example <- stri_sprintf("%s=%d", "a", 1e5)
writeLines(
  paste0("stri_sprintf('%s=%d', 'a', 1e5) returns ", example, "."),
  "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_sprintf-r.txt"
)

one <- function() {
  list(
    s = stri_sprintf("%s", "hello"),
    d = stri_sprintf("%d", 3),
    f = stri_sprintf("%f", 1.5),
    na = stri_sprintf("%s", NA),
    nan = stri_sprintf("%f", NaN),
    inf = stri_sprintf("%f", Inf),
    ninf = stri_sprintf("%f", -Inf),
    sci = stri_sprintf("%s", c(1e5, 1e-4)),
    a = stri_sprintf("%a", 1.5),
    A = stri_sprintf("%A", 1.5),
    g = stri_sprintf("%g", 1e6),
    width = stri_sprintf("[%10s]", c("abcd", "ąĆ")),
    star = stri_sprintf("%1$#- *2$.*3$f", 1.23456, 10, 3),
    pi = stri_sprintf(c("%s", "%f"), pi),
    hex = stri_sprintf("%#x", 255),
    negx = stri_sprintf("%x", -1L),
    zero = signed_zeros(),
    bulk = stri_sprintf("%s=%d", rep(c("a", "b"), 400), rep(1:2, 400))
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
