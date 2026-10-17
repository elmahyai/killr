.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

data(Orthodont, package = "nlme")

fmt <- function(x) {
  if (is.null(x)) {
    "NULL"
  } else if (is.list(x)) {
    paste(names(x), sapply(x, deparse), sep = "=", collapse = "&")
  } else {
    deparse(x)
  }
}

one <- function() {
  fm1 <- lme(distance ~ age, data = Orthodont, subset = Sex == "Female")
  lml <- lmList(distance ~ age | Subject, Orthodont)
  rs <- reStruct(~ 1 | Subject)
  cs <- corAR1(0.3, form = ~ 1 | Subject)
  paste(
    fmt(getGroupsFormula(distance ~ age | Subject)),
    fmt(getGroupsFormula(distance ~ age | Subject, asList = TRUE)),
    fmt(getGroupsFormula(distance ~ age | Subject / Sex)),
    fmt(getGroupsFormula(distance ~ age | Subject / Sex, asList = TRUE)),
    fmt(getGroupsFormula(distance ~ age)),
    fmt(getGroupsFormula(fm1)),
    fmt(getGroupsFormula(fm1, asList = TRUE)),
    fmt(getGroupsFormula(lml)),
    fmt(getGroupsFormula(lml, asList = TRUE)),
    fmt(getGroupsFormula(rs)),
    fmt(getGroupsFormula(rs, asList = TRUE)),
    fmt(getGroupsFormula(cs)),
    fmt(getGroupsFormula(cs, asList = TRUE)),
    sep = ";"
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
escaped <- gsub("\\\\", "\\\\\\\\", value, fixed = TRUE)
escaped <- gsub("\"", "\\\\\"", escaped, fixed = TRUE)
cat(sprintf(
  "{\"value\":\"%s\",\"median_ms\":%.17g}\n",
  escaped,
  median(elapsed) * 1000
))
