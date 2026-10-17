suppressPackageStartupMessages(library(survival))
stopifnot(identical(packageDescription("survival")$Version, "3.8-12"))

d <- lung
d$status <- d$status - 1
d$ph_ecog <- d$ph.ecog
d <- d[complete.cases(d[, c("time", "status", "age", "sex", "ph_ecog")]), ]
fit <- coxph(Surv(time, status) ~ age + sex + ph_ecog, data = d)
eta <- seq(-1, 1, length.out = 5)
vfun <- function(p) 0.01 * p^2 + 0.001

one <- function() {
  out <- character(0)
  add <- function(x) out <<- c(out, sprintf("%.17g", as.numeric(x)))
  for (k in 1:2) {
    s <- if (k == 1) yates_setup(fit, predict = "survival")
         else yates_setup(fit, predict = "survival", options = list(rmean = 300))
    p <- s$predict(eta, NULL)
    sm <- s$summary(p, vfun(p))
    add(p)
    add(sm$n)
    add(sm$time)
    add(sm$n.risk)
    add(sm$n.event)
    add(sm$n.censor)
    add(sm$cumhaz)
    add(sm$surv)
    add(sm$std.err)
    add(sm$lower)
    add(sm$upper)
    add(sm$conf.int)
  }
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
