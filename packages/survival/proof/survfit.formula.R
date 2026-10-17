suppressPackageStartupMessages(library(survival))
stopifnot(identical(packageDescription("survival")$Version, "3.8-12"))

n <- 240
time <- ((seq_len(n) * 17) %% 80) + 1
status01 <- as.numeric(seq_len(n) %% 4 != 0)
status <- factor(
  c("censor", "death", "pcm")[(seq_len(n) %% 3) + 1],
  levels = c("censor", "death", "pcm")
)
group <- factor(ifelse(seq_len(n) %% 2 == 0, "A", "B"), levels = c("A", "B"))
group[seq_len(n) %% 50 == 0] <- NA
site <- c("north", "east", "south")[(seq_len(n) %% 3) + 1]
w <- 1 + (seq_len(n) %% 3) * 0.5
keep <- seq_len(n) %% 7 != 0
start <- floor(time / 4)
pid <- (seq_len(n) %% 60) + 1
df <- data.frame(
  time = time, status01 = status01, status = status, group = group,
  site = site, w = w, keep = keep, start = start, pid = pid
)

nums <- function(fit) {
  num <- function(x) if (is.null(x)) numeric(0) else as.numeric(x)
  c(
    num(fit$n),
    num(fit$time),
    num(fit$n.risk),
    num(fit$n.event),
    num(fit$n.censor),
    num(fit$pstate),
    num(fit$n.transition),
    num(fit$n.id),
    num(fit$n.enter),
    num(fit$cumhaz),
    num(fit$std.err),
    num(fit$std.chaz),
    num(fit$std.auc),
    num(fit$lower),
    num(fit$upper),
    num(fit$strata),
    num(fit$p0),
    num(fit$logse),
    num(fit$conf.int),
    num(fit$t0),
    num(fit$transitions),
    num(fit$counts),
    num(fit$na.action)
  )
}

meta_one <- function(fit) {
  c(
    if (is.null(fit$strata)) "-" else paste(names(fit$strata), collapse = ","),
    as.character(fit$type),
    if (is.null(fit$conf.type)) "-" else as.character(fit$conf.type),
    if (is.null(fit$states)) "-" else paste(fit$states, collapse = ","),
    paste(colnames(fit$cumhaz), collapse = ",")
  )
}

one <- function() {
  fits <- list(
    survfit(Surv(time, status01) ~ 1, data = df),
    survfit(Surv(time, status01) ~ group, data = df),
    survfit(Surv(time, status01) ~ group + site, data = df),
    survfit(Surv(time, status01) ~ strata(site), data = df),
    survfit(Surv(time, status) ~ group, data = df),
    survfit(Surv(start, time, status01) ~ group, data = df, entry = TRUE),
    survfit(Surv(start, time, status01) ~ group, data = df),
    survfit(Surv(time, status01) ~ group, data = df, weights = w),
    survfit(Surv(time, status01) ~ group, data = df, subset = keep),
    survfit(Surv(time, status01) ~ group, data = df, conf.type = "log-log", conf.int = 0.9),
    survfit(Surv(time, status01) ~ site, data = df, id = pid, stype = 2, ctype = 2),
    survfit(Surv(time, status01) ~ 1, data = df, start.time = 20)
  )
  list(
    nums = unlist(lapply(fits, nums), use.names = FALSE),
    meta = unlist(lapply(fits, meta_one), use.names = FALSE)
  )
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
