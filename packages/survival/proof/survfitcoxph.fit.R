suppressPackageStartupMessages(library(survival))
stopifnot(identical(packageDescription("survival")$Version, "3.8-12"))

inputs <- function() {
  d <- lung
  d$status <- d$status - 1
  d$ph_ecog <- d$ph.ecog
  d <- d[complete.cases(d[, c("time", "status", "age", "sex", "ph_ecog", "inst")]), ]
  d$strata <- match(d$inst, sort(unique(d$inst)))
  fit <- coxph(Surv(time, status) ~ age + sex + ph_ecog + strata(inst), data = d,
               x = TRUE, y = TRUE)
  y <- cbind(d$time, d$status)
  X <- fit$x
  coef <- fit$coefficients
  means <- fit$means
  risk <- exp(fit$linear.predictors)
  wt <- rep(1, nrow(d))
  x2 <- rbind(c(60, 1, 1), c(70, 2, 2), c(55, 1, 3))
  risk2 <- as.vector(exp(x2 %*% coef - sum(coef * means)))
  id2 <- c(1, 1, 2)
  y2 <- rbind(c(0, 250), c(250, 600), c(0, 400))
  strata2 <- c(d$strata[1], d$strata[1], d$strata[2])
  list(y = y, X = X, wt = wt, risk = risk, x2 = x2, risk2 = risk2, id2 = id2,
       y2 = y2, strata2 = strata2, strata = d$strata, varmat = fit$var)
}

fields <- c("n", "time", "n.risk", "n.event", "n.censor", "strata", "surv", "cumhaz", "std.err")
flat <- function(res) {
  out <- c()
  for (f in fields) {
    if (!is.null(res[[f]])) out <- c(out, as.numeric(res[[f]]))
  }
  out
}

one <- function(inp) {
  a <- survfitcoxph.fit(
    y = inp$y, x = inp$X, wt = inp$wt, x2 = inp$x2[1:2, , drop = FALSE],
    risk = inp$risk, newrisk = inp$risk2[1:2], strata = inp$strata,
    se.fit = TRUE, survtype = 2, vartype = 1, varmat = inp$varmat
  )
  b <- survfitcoxph.fit(
    y = inp$y, x = inp$X, wt = inp$wt, x2 = inp$x2[1, , drop = FALSE],
    risk = inp$risk, newrisk = inp$risk2[1], strata = inp$strata,
    se.fit = TRUE, survtype = 3, vartype = 1, varmat = inp$varmat
  )
  c2 <- survfitcoxph.fit(
    y = inp$y, x = inp$X, wt = inp$wt, x2 = inp$x2, risk = inp$risk,
    newrisk = inp$risk2, strata = inp$strata, se.fit = TRUE, survtype = 2,
    vartype = 3, varmat = inp$varmat, id = inp$id2, y2 = inp$y2,
    strata2 = inp$strata2
  )
  sprintf("%.17g", c(flat(a), flat(b), flat(c2)))
}

inp <- inputs()
value <- one(inp)
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one(inp)
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(value, collapse = "\n"), "\n", sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
