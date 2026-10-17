.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

# Diagnostic: record every variance-parameter evaluation that lme() makes
# inside nlminb (start point, each objective call, nlminb's own summary).
ns <- asNamespace("nlme")
trace("logLik.lmeStructInt", where = ns, print = FALSE,
  tracer = quote({
    n <- if (exists("TRACE_N", envir = globalenv())) get("TRACE_N", envir = globalenv()) + 1L else 1L
    assign("TRACE_N", n, envir = globalenv())
    cat(sprintf("EVAL %d %s\n", n, paste(sprintf("%.17g", Pars), collapse = " ")))
  }),
  exit = quote({
    rv <- returnValue()
    cat(sprintf("VAL %.17g GRAD %s\n", as.numeric(rv),
                paste(sprintf("%.17g", attr(rv, "gradient")), collapse = " ")))
  }))
trace("nlminb", where = ns, print = FALSE,
  tracer = quote(cat("NLMINB start", paste(sprintf("%.17g", start), collapse = " "),
                     "gradient_arg", !is.null(gradient), "hessian_arg", !is.null(hessian), "\n")),
  exit = quote({
    rv <- returnValue()
    cat("NLMINB par", paste(sprintf("%.17g", rv$par), collapse = " "),
        "obj", sprintf("%.17g", rv$objective), "conv", rv$convergence,
        "iter", rv$iterations, "evals", paste(rv$evaluations, collapse = " "),
        rv$message, "\n")
  }))

fm <- lme(distance ~ age, data = Orthodont, control = lmeControl(apVar = FALSE))
cat(sprintf("FIT sigma %.17g logLik %.17g\n", fm$sigma, as.numeric(logLik(fm))))
cat("FIXED", paste(sprintf("%.17g", fixef(fm)), collapse = " "), "\n")
cat("PARAMS", paste(sprintf("%.17g", coef(fm$modelStruct$reStruct)), collapse = " "), "\n")
a <- anova(fm)
cat("ANOVA_F", paste(sprintf("%.17g", a[["F-value"]]), collapse = " "), "\n")
