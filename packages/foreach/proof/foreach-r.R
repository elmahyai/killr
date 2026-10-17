suppressPackageStartupMessages(library(foreach))

fmt <- function(x) {
  if (is.null(x)) return("NULL")
  if (inherits(x, "error")) return(paste0("ERR:", conditionMessage(x)))
  if (is.matrix(x)) {
    rn <- rownames(x)
    cn <- colnames(x)
    rn <- if (is.null(rn)) "" else paste(rn, collapse = ",")
    cn <- if (is.null(cn)) "" else paste(cn, collapse = ",")
    vals <- paste(sprintf("%.17g", as.numeric(x)), collapse = ",")
    return(paste0("M(", nrow(x), ",", ncol(x), ",", vals, ";rn=", rn, ";cn=", cn, ")"))
  }
  if (is.list(x)) {
    if (length(x) == 0) return("L()")
    parts <- vapply(x, fmt, character(1))
    return(paste0("L(", paste(parts, collapse = ","), ")"))
  }
  if (is.character(x)) return(paste0("C(", paste(x, collapse = ","), ")"))
  paste0("V(", paste(sprintf("%.17g", as.numeric(x)), collapse = ","), ")")
}

run <- function(expr) {
  r <- tryCatch(expr, error = function(e) e)
  if (inherits(r, "error")) paste0("ERR:", conditionMessage(r)) else fmt(r)
}

one <- function() {
  m <- matrix(1:9, 3)
  parts <- c(
    run(foreach()),
    run(foreach(.init = 0)),
    run(foreach(i = 1, .final = 1)),
    run(foreach(i = 1, .inorder = c(TRUE, FALSE))),
    run(foreach(i = 1, .maxcombine = 1)),
    run(foreach(i = 1, .errorhandling = "nope")),
    run(foreach(i = 1, .errorhandling = c("stop", "remove"))),
    run(foreach(i = 1, .errorhandling = 1)),
    run(foreach(i = 1, .packages = 1)),
    run(foreach(i = 1, .export = 1)),
    run(foreach(i = 1, .noexport = 1)),
    run(foreach(i = 1, .verbose = 1)),
    run(foreach(i = 1, .multicombine = 1)),
    run(foreach(i = 1, .foo = 1)),
    run(foreach(i = 1, .foo = 1, .bar = 2)),
    run(foreach(i = 1, COMBINE = c)),
    run(foreach(i = 1, COMBINE = c, INIT = 1)),
    run(foreach(i = 1, .combine = "foo")),
    run(foreach(i = 1:3) %do% sqrt(i)),
    run(foreach(i = 1:4, j = 1:10) %do% sqrt(i + j)),
    run(foreach(i = 1:3, .combine = "c") %do% i),
    run(foreach(i = 1:5, .combine = "+") %do% i),
    run(foreach(i = 1:4, .combine = "*") %do% i),
    run(foreach(i = 1:3, .combine = "cbind") %do% c(i, i + 10L)),
    run(foreach(i = 1:3, .combine = "rbind") %do% c(i, i + 10L)),
    run(foreach(i = 1:4, .combine = "+", .init = 10) %do% i),
    run(foreach(i = 1:3, .combine = "c", .final = function(x) x * 10) %do% i),
    run(foreach(i = integer(0)) %do% i),
    run(foreach(i = integer(0), .combine = "c") %do% i),
    run(foreach(i = 1, .combine = "c") %do% (i * 2)),
    run(foreach(i = 1:2, .combine = "c") %do% (i * 2)),
    run(foreach(i = 1:2, j = 1:5, .combine = "c") %do% (i + j)),
    run(foreach(i = 1:5, .combine = "c", .maxcombine = 2) %do% i),
    run(foreach(i = 1:4, .combine = "+", .inorder = FALSE) %do% i),
    run(foreach(i = 1:5, .combine = function(...) sum(...), .multicombine = TRUE, .maxcombine = 3) %do% i),
    run(foreach(i = 1:5, .combine = function(a, b) a + b, .multicombine = FALSE) %do% i),
    run(foreach(i = 1:4, .combine = "cbind", .maxcombine = 2) %do% c(i, i + 10L)),
    run(foreach(1:3, .combine = "c") %do% 7),
    run(foreach(i = 1:3, .combine = "c") %do% mean(m[, i])),
    run(foreach(i = 1:4, .combine = "+", .multicombine = TRUE) %do% i),
    run(foreach(i = 1:4, .combine = "c", .errorhandling = "rem") %do% if (i == 2) stop("boom") else i),
    run(foreach(i = 1:3, .options.snow = list(a = 1), .combine = "c") %do% i),
    run(foreach(i = 1:2) %do% c(i, i + 10L)),
    run(foreach(i = c("a", "b")) %do% i),
    run(foreach(i = 1:2, .combine = "c", .init = list(0)) %do% i)
  )
  paste(parts, collapse = "|")
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
