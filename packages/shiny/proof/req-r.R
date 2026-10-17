suppressPackageStartupMessages(library(shiny))

fmt_double <- function(x) {
  vapply(x, function(v) {
    if (is.nan(v)) return("NaN")
    if (is.na(v)) return("NA")
    if (is.infinite(v)) return(if (v > 0) "Inf" else "-Inf")
    if (v == 0 && (1 / v) < 0) return("-0")
    formatC(v, format = "g", digits = 15, width = 1)
  }, character(1))
}

tok <- function(x) {
  if (is.null(x)) return("NULL")
  if (is.data.frame(x)) return(paste0("DF:", nrow(x), "x", ncol(x)))
  suffix <- ""
  cls <- attr(x, "class")
  if (!is.null(cls)) suffix <- paste0(suffix, "{", paste(cls, collapse = ","), "}")
  nms <- names(x)
  if (!is.null(nms)) suffix <- paste0(suffix, "{names:", paste(nms, collapse = "|"), "}")
  kind <- typeof(x)
  data <- x
  attributes(data) <- NULL
  if (kind == "raw") {
    body <- if (length(data) == 0) "" else paste(sprintf("%02x", as.integer(data)), collapse = "|")
    return(paste0("RAW:", body, suffix))
  }
  if (kind == "complex") {
    return(paste0("CPLX:", paste(gsub(" ", "", as.character(data)), collapse = "|"), suffix))
  }
  if (kind == "character") {
    parts <- vapply(data, function(s) if (is.na(s)) "<NA>" else s, character(1))
    return(paste0("C:", paste(parts, collapse = "|"), suffix))
  }
  if (kind == "logical") {
    parts <- vapply(data, function(s) {
      if (is.na(s)) "NA" else if (isTRUE(s)) "TRUE" else "FALSE"
    }, character(1))
    return(paste0("L:", paste(parts, collapse = "|"), suffix))
  }
  if (kind == "integer") {
    parts <- vapply(data, function(s) if (is.na(s)) "NA" else as.character(s), character(1))
    return(paste0("I:", paste(parts, collapse = "|"), suffix))
  }
  if (kind == "double") {
    return(paste0("D:", paste(fmt_double(data), collapse = "|"), suffix))
  }
  if (kind == "list") return(paste0("LIST:", length(x), suffix))
  "OTHER"
}

grab <- function(expr) {
  tryCatch(
    {
      val <- eval(expr, envir = parent.frame())
      paste0("OK ", tok(val))
    },
    error = function(e) {
      paste0("ERR ", paste(class(e), collapse = "/"), "|", conditionMessage(e))
    }
  )
}

one <- function() {
  btn <- function(n) structure(n, class = "shinyActionButtonValue")
  parts <- character()
  parts <- c(parts, grab(quote(req())))
  parts <- c(parts, grab(quote(req(cancelOutput = TRUE))))
  parts <- c(parts, grab(quote(req(1, TRUE))))
  parts <- c(parts, grab(quote(req(1L, 2L, 3L))))
  parts <- c(parts, grab(quote(req(1, 2, 3))))
  parts <- c(parts, grab(quote(req(0))))
  parts <- c(parts, grab(quote(req(0L))))
  parts <- c(parts, grab(quote(req(-0))))
  parts <- c(parts, grab(quote(req(" "))))
  parts <- c(parts, grab(quote(req("ab", "cd"))))
  parts <- c(parts, grab(quote(req(c(FALSE, TRUE)))))
  parts <- c(parts, grab(quote(req(TRUE, "progress"))))
  parts <- c(parts, grab(quote(req(c("", "a")))))
  parts <- c(parts, grab(quote(req(c(NA_character_, "a")))))
  parts <- c(parts, grab(quote(req(c("  ", NA)))))
  parts <- c(parts, grab(quote(req(as.raw(0)))))
  parts <- c(parts, grab(quote(req(as.raw(c(0, 1))))))
  parts <- c(parts, grab(quote(req(0+0i))))
  parts <- c(parts, grab(quote(req(1+1i))))
  parts <- c(parts, grab(quote(req(Inf))))
  parts <- c(parts, grab(quote(req(-Inf))))
  parts <- c(parts, grab(quote(req(list()))))
  parts <- c(parts, grab(quote(req(list(FALSE)))))
  parts <- c(parts, grab(quote(req(list(NULL)))))
  parts <- c(parts, grab(quote(req(a = 5))))
  parts <- c(parts, grab(quote(req(1:3, 4:6))))
  parts <- c(parts, grab(quote(req(c(a = TRUE)))))
  parts <- c(parts, grab(quote(req(c(0, NA), 1))))
  parts <- c(parts, grab(quote(req(c(NaN, 1)))))
  parts <- c(parts, grab(quote(req(btn(1L)))))
  parts <- c(parts, grab(quote(req(btn("a")))))
  parts <- c(parts, grab(quote(req(btn("0.0")))))
  parts <- c(parts, grab(quote(req(factor("a")))))
  parts <- c(parts, grab(quote(req(data.frame()))))
  parts <- c(parts, grab(quote(req(1, cancelOutput = "progress"))))
  parts <- c(parts, grab(quote(req(0, cancelOutput = "progress"))))
  parts <- c(parts, grab(quote(req(1, cancelOutput = FALSE, 2))))
  parts <- c(parts, grab(quote(req(0, cancelO = "progress"))))
  parts <- c(parts, grab(quote(do.call(req, as.list(1:1000)))))
  parts <- c(parts, grab(quote(do.call(req, list(1, 2, 3)))))

  parts <- c(parts, grab(quote(req(FALSE))))
  parts <- c(parts, grab(quote(req(NULL))))
  parts <- c(parts, grab(quote(req(""))))
  parts <- c(parts, grab(quote(req(TRUE, FALSE))))
  parts <- c(parts, grab(quote(req(NA))))
  parts <- c(parts, grab(quote(req(NA_integer_))))
  parts <- c(parts, grab(quote(req(NA_real_))))
  parts <- c(parts, grab(quote(req(NA_character_))))
  parts <- c(parts, grab(quote(req(character(0)))))
  parts <- c(parts, grab(quote(req(logical(0)))))
  parts <- c(parts, grab(quote(req(numeric(0)))))
  parts <- c(parts, grab(quote(req(raw(0)))))
  parts <- c(parts, grab(quote(req(c(FALSE, FALSE)))))
  parts <- c(parts, grab(quote(req(c("", "")))))
  parts <- c(parts, grab(quote(req(NaN))))
  parts <- c(parts, grab(quote(req(c(NaN, NaN)))))
  parts <- c(parts, grab(quote(req(btn(0L)))))
  parts <- c(parts, grab(quote(req(btn(0)))))
  parts <- c(parts, grab(quote(req(btn("0")))))
  parts <- c(parts, grab(quote(req(btn(NA_integer_)))))
  parts <- c(parts, grab(quote(req(try(stop("boom"), silent = TRUE)))))
  parts <- c(parts, grab(quote(req(factor(NA)))))
  parts <- c(parts, grab(quote(req(factor(character(0))))))
  parts <- c(parts, grab(quote(req(matrix(FALSE, 1, 1)))))
  parts <- c(parts, grab(quote(req(a = FALSE))))
  parts <- c(parts, grab(quote(req(FALSE, cancelOutput = TRUE))))
  parts <- c(parts, grab(quote(req("", cancelOutput = "progress"))))
  parts <- c(parts, grab(quote(req(1, FALSE, cancelOutput = "progress"))))
  parts <- c(parts, grab(quote(req("ok", "", cancelOutput = "progress"))))
  parts <- c(parts, grab(quote(req(FALSE, cancelOutput = "TRUE"))))
  parts <- c(parts, grab(quote(req(FALSE, cancelOutput = 1))))
  parts <- c(parts, grab(quote(req(FALSE, cancelOutput = NA))))
  parts <- c(parts, grab(quote(req(FALSE, cancelOutput = NULL))))
  parts <- c(parts, grab(quote(req(FALSE, cancelOutput = c(TRUE, TRUE)))))
  parts <- c(parts, grab(quote(req(FALSE, cancelOutput = c(TRUE)))))
  parts <- c(parts, grab(quote(req(FALSE, cancelOutput = structure(TRUE, class = "foo")))))
  parts <- c(parts, grab(quote(req(FALSE, cancelOutput = c(a = "progress")))))
  parts <- c(parts, grab(quote(req(FALSE, cancelOutput = structure("progress", class = "foo")))))
  parts <- c(parts, grab(quote(req(FALSE, cancelOutput = c(cancelOutput = TRUE)))))
  parts <- c(parts, grab(quote(req(FALSE, cancel = TRUE))))
  parts <- c(parts, grab(quote(req(FALSE, cancelO = TRUE))))
  parts <- c(parts, grab(quote(req(1, cancel = FALSE))))
  parts <- c(parts, grab(quote(req(btn(c(0L, 1L))))))
  parts <- c(parts, grab(quote(req(TRUE, stop("boom")))))
  parts <- c(parts, grab(quote(req(1, ))))
  parts <- c(parts, grab(quote(req(, 1))))

  hit <- 0
  res <- grab(quote(req(NULL, hit <- hit + 1)))
  parts <- c(parts, paste0(res, " hit=", hit))
  hit <- 0
  res <- grab(quote(req(hit <- hit + 1)))
  parts <- c(parts, paste0(res, " hit=", hit))
  hit <- 0
  res <- grab(quote(req({hit <- hit + 1; TRUE})))
  parts <- c(parts, paste0(res, " hit=", hit))
  hit <- 0
  res <- grab(quote(req(TRUE, {hit <- hit + 1; 9})))
  parts <- c(parts, paste0(res, " hit=", hit))
  hit <- 0
  res <- grab(quote(req(FALSE, {hit <- hit + 1; stop("boom")})))
  parts <- c(parts, paste0(res, " hit=", hit))
  hit <- 0
  res <- grab(quote(req(, {hit <- hit + 1; 1})))
  parts <- c(parts, paste0(res, " hit=", hit))

  paste(parts, collapse = "\n")
}

value <- one()
elapsed <- numeric(20)
for (step_i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[step_i]] <- as.numeric(Sys.time()) - t0
}
shown <- gsub("\n", " / ", value, fixed = TRUE)
cat("VALUE ", shown, "\n", sep = "")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
