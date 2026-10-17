suppressPackageStartupMessages(library(survival))

lines_for <- function(label, res) {
  c(paste(label, "lower", paste(sprintf("%.17g", res$lower), collapse = " ")),
    paste(label, "upper", paste(sprintf("%.17g", res$upper), collapse = " ")))
}

one <- function() {
  p <- c(0.95, 0.8, 0.5, 0.2)
  se <- c(0.02, 0.05, 0.1, 0.04)
  selow <- c(0.01, 0, 0.08, 0.03)
  out <- character(0)
  for (ct in c("plain", "log", "log-log", "logit", "arcsin")) {
    for (lg in c(TRUE, FALSE)) {
      flag <- if (lg) "logse" else "nologse"
      out <- c(out, lines_for(paste(ct, flag, "nosel"),
        survival::survfit_confint(p, se, logse = lg, conf.type = ct, conf.int = 0.9)))
      out <- c(out, lines_for(paste(ct, flag, "selow"),
        survival::survfit_confint(p, se, logse = lg, conf.type = ct, conf.int = 0.9,
                                  selow = selow)))
    }
  }
  out <- c(out, lines_for("plain ulimit_false",
    survival::survfit_confint(p, se, conf.type = "plain", ulimit = FALSE)))
  out <- c(out, lines_for("log ulimit_false",
    survival::survfit_confint(p, se, conf.type = "log", ulimit = FALSE)))
  out <- c(out, lines_for("log-log p1",
    survival::survfit_confint(c(1, 0.6), c(0, 0.1), conf.type = "log-log")))
  out <- c(out, lines_for("logit p1",
    survival::survfit_confint(c(1, 0.6), c(0, 0.1), conf.type = "logit")))
  out
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
