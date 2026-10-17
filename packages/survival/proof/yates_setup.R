suppressPackageStartupMessages(library(survival))

cfit <- coxph(Surv(time, status) ~ age + sex, data = lung)
gfit <- glm(I(status == 2) ~ age, family = binomial, data = lung)
lfit <- lm(time ~ age, data = lung)
eta <- seq(-2, 2, length.out = 9)

fmt <- function(x) {
  if (is.null(x)) {
    return("NULL")
  }
  if (is.character(x)) {
    return(x)
  }
  vapply(as.numeric(x), function(z) sprintf("%.17g", z), character(1))
}

err <- function(expr) {
  tryCatch(
    {
      expr
      "error: none"
    },
    error = function(e) paste0("error: ", conditionMessage(e))
  )
}

one <- function() {
  out <- character(0)
  add <- function(x) out <<- c(out, fmt(x))
  add(yates_setup(cfit))
  add(yates_setup(cfit, predict = "linear"))
  add(yates_setup(cfit, predict = "risk")(eta, NULL))
  add(err(yates_setup(cfit, predict = "terms")))
  add(yates_setup(gfit))
  add(yates_setup(gfit, predict = "response")(eta, NULL))
  add(err(yates_setup(gfit, predict = "terms")))
  w <- ""
  val <- withCallingHandlers(
    yates_setup(lfit, "response"),
    warning = function(cond) {
      w <<- conditionMessage(cond)
      invokeRestart("muffleWarning")
    }
  )
  add(val)
  add(paste0("warning: ", w))
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
