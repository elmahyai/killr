.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))
suppressPackageStartupMessages(library(jsonlite))

`%||%` <- function(x, y) if (is.null(x)) y else x

load_data <- function(name) {
  if (name == "Orthodont") {
    data(Orthodont, package = "nlme")
    return(Orthodont)
  }
  stop(sprintf("unknown data set %s", name))
}

build_lme_spec <- function(spec) {
  if (is.list(spec) && !is.null(spec$type) && spec$type == "lme") {
    stop("lme object round-trip is not supported in the worker")
  }
  out <- list()
  if (!is.null(spec$fixed)) {
    out$fixed <- as.formula(spec$fixed)
  }
  if (!is.null(spec$data)) {
    if (is.character(spec$data)) {
      out$data <- load_data(spec$data)
    } else {
      stop("data must be a known data set name")
    }
  }
  if (!is.null(spec$random)) {
    out$random <- as.formula(spec$random)
  }
  if (!is.null(spec$control)) {
    out$control <- spec$control
  }
  out
}

matrix_to_list <- function(m) {
  if (is.null(m)) {
    return(NULL)
  }
  lapply(seq_len(nrow(m)), function(i) {
    list(info = unname(m[i, "info"]), logLik = unname(m[i, "logLik"]))
  })
}

run_one <- function(req) {
  spec <- req$object
  nsim <- as.integer(req$nsim %||% 1L)
  seed <- if (is.null(req$seed)) NULL else as.integer(req$seed)
  method <- req$method %||% c("REML", "ML")
  niterEM <- req$niterEM %||% c(40L, 200L)
  useGen <- req$useGen

  has_m2 <- !is.null(req$m2)
  has_use_gen <- !is.null(useGen)
  null_spec <- quote(list(
    fixed = as.formula(spec$fixed),
    data = load_data(spec$data),
    random = as.formula(spec$random)
  ))

  sim <- if (has_m2 && has_use_gen) {
    eval(bquote(simulate.lme(
      .(null_spec),
      nsim = .(nsim),
      seed = .(seed),
      m2 = list(random = as.formula(.(req$m2$random))),
      method = .(method),
      niterEM = .(niterEM),
      useGen = as.logical(.(useGen))
    )))
  } else if (has_m2) {
    eval(bquote(simulate.lme(
      .(null_spec),
      nsim = .(nsim),
      seed = .(seed),
      m2 = list(random = as.formula(.(req$m2$random))),
      method = .(method),
      niterEM = .(niterEM)
    )))
  } else if (has_use_gen) {
    eval(bquote(simulate.lme(
      .(null_spec),
      nsim = .(nsim),
      seed = .(seed),
      method = .(method),
      niterEM = .(niterEM),
      useGen = as.logical(.(useGen))
    )))
  } else {
    eval(bquote(simulate.lme(
      .(null_spec),
      nsim = .(nsim),
      seed = .(seed),
      method = .(method),
      niterEM = .(niterEM)
    )))
  }

  list(
    df = attr(sim, "df"),
    useGen = isTRUE(attr(sim, "useGen")),
    seed = attr(sim, "seed"),
    null = list(
      REML = matrix_to_list(sim$null$REML),
      ML = matrix_to_list(sim$null$ML)
    ),
    alt = if (is.null(sim$alt)) {
      NULL
    } else {
      list(
        REML = matrix_to_list(sim$alt$REML),
        ML = matrix_to_list(sim$alt$ML)
      )
    }
  )
}

repeat {
  line <- readLines(con = "stdin", n = 1L, warn = FALSE)
  if (length(line) == 0L) {
    break
  }
  if (!nzchar(line)) {
    next
  }
  out <- tryCatch(
    {
      req <- fromJSON(line, simplifyVector = TRUE)
      list(ok = TRUE, result = run_one(req))
    },
    error = function(e) {
      list(ok = FALSE, error = conditionMessage(e))
    }
  )
  cat(toJSON(out, auto_unbox = TRUE, digits = 17, null = "null"), "\n", sep = "")
  flush.console()
}
