        suppressPackageStartupMessages(library(rematch2))
dates <- c("2016-04-20", "1977-08-08", "not a date", "2016", "76-03-02", "2012-06-30", "2015-01-21 19:58")
pattern <- "(?<year>[0-9]{4})-(?<month>[0-1][0-9])-(?<day>[0-3][0-9])"
        one <- function() {
          paste(ifelse(is.na(one_value <- re_match(dates, pattern)$year), "NA", one_value), collapse = ",")
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
