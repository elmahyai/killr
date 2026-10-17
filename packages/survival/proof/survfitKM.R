suppressPackageStartupMessages(library(survival))
stopifnot(identical(packageDescription("survival")$Version, "3.8-12"))

aml_time <- c(
  9, 13, 13, 18, 23, 28, 31, 34, 45, 48, 161,
  5, 5, 8, 8, 12, 16, 23, 27, 30, 33, 43, 45
)
aml_status <- c(
  1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 0,
  1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1
)
aml_x <- factor(c(rep("Maintained", 11), rep("Nonmaintained", 12)))
aml_y <- Surv(aml_time, aml_status)
one_level <- function(n) factor(rep(1, n))

n_syn <- 180
syn_time <- ((seq_len(n_syn) * 17) %% 97) + 1
syn_status <- as.integer(seq_len(n_syn) %% 5 != 0)
syn_grp <- factor(c("a", "b", "c")[(seq_len(n_syn) %% 3) + 1])
syn_y <- Surv(syn_time, syn_status)

ct_start <- c(0, 5, 0, 0, 3)
ct_stop <- c(5, 12, 4, 8, 9)
ct_status <- c(0, 1, 1, 0, 1)
ct_id <- c(1, 1, 2, 3, 3)
ct_grp <- factor(c("a", "a", "b", "a", "b"), levels = c("a", "b"))
ct_y <- Surv(ct_start, ct_stop, ct_status)

nums <- function(fit) {
  pull <- function(x) if (is.null(x)) numeric(0) else as.numeric(x)
  infs <- function(x) {
    if (is.null(x)) return(numeric(0))
    if (is.list(x)) unlist(lapply(x, as.numeric), use.names = FALSE) else as.numeric(x)
  }
  c(
    pull(fit$n),
    pull(fit$time),
    pull(fit$n.risk),
    pull(fit$n.event),
    pull(fit$n.censor),
    pull(fit$surv),
    pull(fit$std.err),
    pull(fit$cumhaz),
    pull(fit$std.chaz),
    pull(fit$lower),
    pull(fit$upper),
    pull(fit$strata),
    pull(fit$n.enter),
    pull(fit$counts),
    pull(fit$n.id),
    pull(fit$logse),
    pull(fit$conf.int),
    pull(fit$t0),
    infs(fit$influence.surv),
    infs(fit$influence.chaz)
  )
}

rn_one <- function(x) {
  if (is.list(x)) {
    paste(vapply(x, function(m) paste(rownames(m), collapse = ","), character(1)), collapse = ";")
  } else {
    paste(rownames(x), collapse = ",")
  }
}

meta_one <- function(fit) {
  bits <- character(0)
  if (!is.null(fit$influence.surv)) bits <- c(bits, rn_one(fit$influence.surv))
  if (!is.null(fit$influence.chaz)) bits <- c(bits, rn_one(fit$influence.chaz))
  rn <- if (length(bits) == 0) "-" else paste(bits, collapse = "|")
  c(
    if (is.null(fit$strata)) "-" else paste(names(fit$strata), collapse = ","),
    as.character(fit$type),
    if (is.null(fit$conf.type)) "-" else as.character(fit$conf.type),
    if (is.null(fit$conf.lower)) "-" else as.character(fit$conf.lower),
    rn
  )
}

one <- function() {
  fits <- list(
    survfitKM(one_level(length(aml_time)), aml_y),
    survfitKM(aml_x, aml_y),
    survfitKM(one_level(length(aml_time)), aml_y, type = "fh2"),
    survfitKM(aml_x, aml_y, ctype = 2, conf.lower = "modified"),
    survfitKM(one_level(length(aml_time)), aml_y, weights = 1 + (seq_along(aml_time) %% 2)),
    survfitKM(
      one_level(length(aml_time)), aml_y,
      cluster = (seq_along(aml_time) %% 4) + 1, influence = 3
    ),
    survfitKM(
      one_level(length(aml_time)), aml_y, start.time = 30,
      weights = rep(1, length(aml_time)), id = seq_along(aml_time), cluster = NULL
    ),
    survfitKM(one_level(5), ct_y, id = ct_id),
    survfitKM(ct_grp, ct_y, id = ct_id, entry = TRUE),
    survfitKM(syn_grp, syn_y)
  )
  list(nums = unlist(lapply(fits, nums), use.names = FALSE), meta = unlist(lapply(fits, meta_one), use.names = FALSE))
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(sprintf("%.17g", value$nums), collapse = "\n"), "\n", sep = "")
cat("META\n")
cat(paste(value$meta, collapse = "\n"), "\n", sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
