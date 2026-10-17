suppressPackageStartupMessages(library(generics))
stopifnot(identical(as.character(packageVersion("generics")), "0.1.4"))
suppressMessages({
  setClass("AccP", slots = c(x = "numeric"))
  setClass("AccC", contains = "AccP")
})

fmt <- function(x) sprintf("%.17g", x)

err <- function(expr) {
  tryCatch(force(expr), error = function(e) conditionMessage(e))
}

one <- function() {
  forecast.mod <- function(object, ..., w = 1) {
    mean(abs(as.numeric(unclass(object)))) * w
  }
  forecast.sub <- function(object, ...) 100
  forecast.sq <- function(object, ...) {
    sqrt(mean(as.numeric(unclass(object))^2))
  }
  forecast.child <- function(object, ...) {
    as.numeric(unclass(object))[1] + NextMethod()
  }
  forecast.parent <- function(object, ...) sum(as.numeric(unclass(object)))
  forecast.double <- function(object, ...) {
    if (missing(object)) -8 else sum(as.numeric(object)) + 1
  }
  forecast.integer <- function(object, ...) sum(as.numeric(object)) - 1
  forecast.numeric <- function(object, ...) {
    if (missing(object)) -9 else sum(as.numeric(object))
  }
  forecast.array <- function(object, ...) sum(as.numeric(object)) + 0.25
  forecast.AccP <- function(object, ...) object@x * 2
  forecast.default <- function(object, ...) -1
  forecast.NULL <- function(object, ...) if (missing(object)) -2 else -3
  forecast.name <- function(object, ...) if (missing(object)) -7 else -6
  forecast.strict <- function(object) object
  forecast.only <- function(object, ...) NextMethod()

  mod <- structure(c(1, -2, 3.5), class = "mod")
  nums <- c(
    forecast(mod),
    forecast(mod, w = 2),
    forecast(mod, 2),
    forecast(obj = mod, w = 4),
    forecast(structure(c(1, -2, 3.5), class = c("sub", "mod"))),
    forecast(structure(c(1, -2, 3.5), class = c("nope", "mod"))),
    forecast(structure(c(3, 4), class = c("nope", "sq"))),
    forecast(structure(c(1.5, 2.5), class = c("child", "parent"))),
    forecast(c(1.5, 2.5)),
    forecast(1:3),
    forecast(matrix(1:4, nrow = 2)),
    forecast(matrix(c(1.5, 2.5), nrow = 1)),
    forecast(array(c(1.5, 2.5), c(1, 1, 2))),
    forecast(new("AccC", x = 1.25)),
    forecast(structure(9, class = "unknown")),
    forecast(NULL),
    forecast(),
    forecast(z = 1.5),
    forecast(1, object = c(1.5, 2.5)),
    forecast(objectt = 1),
    forecast(obj = c(1.5, 2.5)),
    forecast(obj = 1, object = c(1.5, 2.5)),
    forecast(as.name("x"))
  )

  rm(forecast.double, forecast.integer, forecast.array)
  nums <- c(
    nums,
    forecast(c(1.5, 2.5)),
    forecast(1:3),
    forecast(matrix(c(1.5, 2.5), nrow = 1)),
    forecast(array(c(1.5, 2.5), c(1, 1, 2))),
    forecast(z = 1.5),
    forecast(object = , z = 1.5)
  )

  rm(forecast.numeric, forecast.default, forecast.NULL, forecast.AccP, forecast.name)
  errs <- c(
    err(forecast(c(1.5, 2.5))),
    err(forecast(1:3)),
    err(forecast(matrix(1:4, nrow = 2))),
    err(forecast(array(c(1.5, 2.5), c(1, 1, 2)))),
    err(forecast(TRUE)),
    err(forecast("ab")),
    err(forecast(NULL)),
    err(forecast()),
    err(forecast(z = 1.5)),
    err(forecast(z = "ab")),
    err(forecast(structure(1, class = c("aa", "bb")))),
    err(forecast(structure(1, class = ""))),
    err(forecast(structure(1, class = "a'b"))),
    err(forecast(structure(1, class = c("a'b", "c")))),
    err(forecast(new("AccC", x = 1))),
    err(forecast(list(1))),
    err(forecast(1 + 2i)),
    err(forecast(mean)),
    err(forecast(object = )),
    err(forecast(o = 1, ob = 2)),
    err(forecast(structure(1, class = "strict"), 2)),
    err(forecast(structure(1, class = "strict"), 2, z = 3)),
    err(forecast(structure(1, class = "strict"), w = 4)),
    err(forecast(structure(1, class = c("only", "other"))))
  )
  forecast.default <- function(object, ...) force(object)
  errs <- c(errs, err(forecast()))

  paste(c(paste(vapply(nums, fmt, ""), collapse = ","), errs), collapse = " || ")
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat("VALUE ", value, "\n", sep = "")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))

cmd <- commandArgs(trailingOnly = FALSE)
script <- sub("^--file=", "", cmd[grep("^--file=", cmd)])
out_dir <- file.path(normalizePath(file.path(dirname(script), "..")), "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
forecast.demo <- function(object, ...) {
  c(n = length(object), total = sum(as.numeric(unclass(object))))
}
msg <- tryCatch(forecast(1:3), error = function(e) conditionMessage(e))
hit <- forecast(structure(c(1, 2, 4), class = "demo"))
writeLines(
  c(msg, paste0("n ", hit[["n"]]), paste0("total ", hit[["total"]])),
  file.path(out_dir, "forecast-r.txt")
)
