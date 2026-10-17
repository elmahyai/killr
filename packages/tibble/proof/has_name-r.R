        suppressPackageStartupMessages(library(tibble))
df <- data.frame(a = 1)
        one <- function() {
          paste(c(has_name(df, "a"), has_name(df, "nope")), collapse = ",")
        }
        ans <- one()
        elapsed <- numeric(20)
        for (i in seq_len(20)) {
          t0 <- as.numeric(Sys.time())
          one()
          elapsed[[i]] <- as.numeric(Sys.time()) - t0
        }
        cat(ans, "\n", sep = "")
        cat(sprintf("%.17g\n", median(elapsed) * 1000))
