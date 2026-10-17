        suppressPackageStartupMessages(library(tibble))
df <- data.frame(x = 1, y = 2)
names(df) <- c("a", "a")
        one <- function() {
          paste(names(repair_names(df)), collapse = ",")
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
