suppressPackageStartupMessages(library(stringi))
stopifnot(as.character(packageVersion("stringi")) == "1.8.9")
suppressPackageStartupMessages(library(jsonlite))


s <- c(
  "Lorem \\textbf{ipsum} dolor sit \\textit{amet}, consectetur adipisicing elit.",
  "\\begin{small}Proin nibh augue,\\end{small} suscipit a, scelerisque sed, lacinia in, mi.",
  ""
)
x <- stri_stats_latex(s)
writeLines(
  paste0("stri_stats_latex(s)$Words returns ", x["Words"], " and Cmds returns ", x["Cmds"], "."),
  "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_stats_latex-r.txt"
)

one <- function() {
  list(
    lorem = as.list(stri_stats_latex(s)),
    mixed = as.list(stri_stats_latex(c("a % comment", "\\% not", "42test 42.2", NA)))
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
