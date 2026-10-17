suppressPackageStartupMessages(library(survival))
stopifnot(identical(packageDescription("survival")$Version, "3.8-12"))

# Inputs from a Cox fit on the lung data (complete cases), built the way
# survfit.coxph builds them. With the argument "export", the same inputs are
# written next to this script for the Python proof.
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
  # time-dependent newdata: id 1 has two intervals, id 2 has one
  id2 <- c(1, 1, 2)
  y2 <- rbind(c(0, 250), c(250, 600), c(0, 400))
  strata2 <- c(d$strata[1], d$strata[1], d$strata[2])
  list(d = d, fit = fit, y = y, X = X, wt = wt, risk = risk, x2 = x2,
       risk2 = risk2, id2 = id2, y2 = y2, strata2 = strata2,
       strata = d$strata, varmat = fit$var)
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
  a <- coxsurv.fit(1, 2, TRUE, inp$varmat, FALSE, inp$y, inp$X, inp$wt, inp$risk,
                   NULL, inp$strata, NULL, NULL, inp$x2[1:2, , drop = FALSE],
                   inp$risk2[1:2])
  b <- coxsurv.fit(2, 2, TRUE, inp$varmat, FALSE, inp$y, inp$X, inp$wt, inp$risk,
                   NULL, inp$strata, NULL, NULL, inp$x2[1, , drop = FALSE], inp$risk2[1])
  c2 <- coxsurv.fit(1, 2, TRUE, inp$varmat, FALSE, inp$y, inp$X, inp$wt, inp$risk,
                    NULL, inp$strata, NULL, inp$y2, inp$x2, inp$risk2,
                    inp$strata2, inp$id2)
  sprintf("%.17g", c(flat(a), flat(b), flat(c2)))
}

args <- commandArgs(trailingOnly = TRUE)
inp <- inputs()
if ("export" %in% args) {
  d <- inp$d
  train <- data.frame(time = d$time, status = d$status, strata = inp$strata,
                      wt = inp$wt, risk = inp$risk, age = d$age, sex = d$sex,
                      ph_ecog = d$ph_ecog)
  fmt <- function(m) apply(m, 1, function(r) paste(sprintf("%.17g", r), collapse = ","))
  writeLines(c(paste(names(train), collapse = ","), fmt(as.matrix(train))),
             "coxsurv.fit.train.csv")
  newd <- data.frame(age = inp$x2[, 1], sex = inp$x2[, 2], ph_ecog = inp$x2[, 3],
                     risk2 = inp$risk2, strata2 = inp$strata2, id2 = inp$id2,
                     start = inp$y2[, 1], stop = inp$y2[, 2])
  writeLines(c(paste(names(newd), collapse = ","), fmt(as.matrix(newd))),
             "coxsurv.fit.newdata.csv")
  writeLines(c("v1,v2,v3", fmt(inp$varmat)), "coxsurv.fit.varmat.csv")
  cat("exported\n")
  quit(save = "no")
}

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
