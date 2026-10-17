suppressPackageStartupMessages(library(survival))
data(heart)

eps <- 1e-9
toler <- .Machine$double.eps^0.75
control <- coxph.control(eps = eps, toler.chol = toler, iter.max = 20)

heart_x <- cbind(
  heart$age,
  heart$year,
  heart$surgery,
  as.numeric(as.character(heart$transplant))
)
heart_y <- Surv(heart$start, heart$stop, heart$event)

synth_start <- c(0, 0.5, 1, 2, 6, 0, 0.2, 1, 0.4)
synth_stop <- c(5, 5, 10, 6, 7, 4, 4, 12, 2)
synth_event <- c(1, 1, 0, 1, 0, 1, 1, 1, 0)
synth_x <- cbind(
  c(0, 1, 1, 0, 1, 0, 1, 0, 1),
  c(1.2, 0.4, 2.0, -0.5, 3.0, 1.0, 0.0, 2.5, 0.5)
)
synth_y <- Surv(synth_start, synth_stop, synth_event)
synth_strata <- c(1L, 1L, 1L, 1L, 1L, 2L, 2L, 2L, 2L)
synth_weights <- c(1, 1, 2, 1, 1, 1.5, 1, 1, 1)
synth_offset <- c(0, 0.2, 0, 0, 0, -0.1, 0, 0, 0.3)
synth_init <- c(0.05, -0.1)

serialize_fit <- function(fit) {
  c(
    sprintf("%.17g", fit$coefficients),
    sprintf("%.17g", fit$first),
    sprintf("%.17g", as.vector(fit$var)),
    sprintf("%.17g", fit$loglik),
    sprintf("%.17g", fit$score),
    sprintf("%.17g", as.integer(fit$info)),
    sprintf("%.17g", fit$iter),
    sprintf("%.17g", fit$residuals)
  )
}

one <- function() {
  heart_fit <- agreg.fit(
    heart_x,
    heart_y,
    strata = NULL,
    offset = rep(0, nrow(heart_x)),
    init = rep(0, ncol(heart_x)),
    control = control,
    weights = rep(1, nrow(heart_x)),
    method = "efron",
    rownames = NULL,
    resid = TRUE,
    nocenter = c(-1, 0, 1)
  )
  synth_fit <- agreg.fit(
    synth_x,
    synth_y,
    strata = synth_strata,
    offset = synth_offset,
    init = synth_init,
    control = control,
    weights = synth_weights,
    method = "efron",
    rownames = NULL,
    resid = TRUE,
    nocenter = c(-1, 0, 1)
  )
  c(serialize_fit(heart_fit), serialize_fit(synth_fit))
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
