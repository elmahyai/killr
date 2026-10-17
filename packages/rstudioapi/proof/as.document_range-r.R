.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(rstudioapi))
stopifnot(identical(as.character(packageVersion("rstudioapi")), "0.19.0"))

num <- function(x) {
  if (length(x) == 1 && is.na(x)) "NA" else sprintf("%.17g", as.numeric(x))
}

line <- function(name, expr, same = NULL) {
  text <- tryCatch(
    {
      value <- expr
      if (inherits(value, "document_range")) {
        s <- value$start
        e <- value$end
        out <- paste0(
          "OK ",
          num(s[[1]]), " ", num(s[[2]]), " ",
          num(e[[1]]), " ", num(e[[2]])
        )
        if (!is.null(same)) {
          out <- paste0(out, " ", identical(value, same))
        }
        out
      } else {
        paste0("OTHER ", paste(as.character(value), collapse = ","))
      }
    },
    error = function(e) paste0("ERR ", conditionMessage(e))
  )
  paste0(name, "=", text)
}

one <- function() {
  rng <- document_range(c(1, 2, 3, 4))
  parts <- c(
    line("identity", as.document_range(rng), same = rng),
    line("dbl4", as.document_range(c(1, 2, 3, 4))),
    line("int4", as.document_range(c(1L, 2L, 3L, 4L))),
    line("na4", as.document_range(c(NA_real_, 2, 3, 4))),
    line("vec2", as.document_range(c(1, 2))),
    line("len3", as.document_range(c(1, 2, 3))),
    line("logical", as.document_range(c(TRUE, FALSE, TRUE, FALSE)))
  )
  paste(parts, collapse = "\n")
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
shown <- enc2utf8(paste(as.character(value), collapse = "|"))
shown <- gsub("\n", " / ", shown, fixed = TRUE)
cat("VALUE ", shown, "\n", sep = "")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
