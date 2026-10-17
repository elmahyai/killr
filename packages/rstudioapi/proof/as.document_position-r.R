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
      if (inherits(value, "document_position")) {
        out <- paste0("OK ", num(value[[1]]), " ", num(value[[2]]))
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
  pos <- document_position(3, 7)
  parts <- c(
    line("identity", as.document_position(pos), same = pos),
    line("dbl", as.document_position(c(3, 7))),
    line("int", as.document_position(c(1L, 2L))),
    line("na", as.document_position(c(NA_real_, 1))),
    line("len3", as.document_position(c(1, 2, 3))),
    line("logical", as.document_position(c(TRUE, FALSE))),
    line("char", as.document_position(c("a", "b")))
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
