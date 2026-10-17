args <- commandArgs(trailingOnly=TRUE)
library(listenv)
name <- sub("-r\\.R$", "", basename(args[1]))
run <- function() {
  if (name == "listenv") return(unname(as.list(listenv(1, 2, a=3))))
  if (name == "as.listenv") return(unname(as.list(as.listenv(list(a=1, b=2)))))
  if (name == "mapping") return(as.list(mapping(listenv(a=1, b=2))))
  if (name == "map") return(as.list(map(listenv(a=1))))
  if (name == "get_variable") { x <- listenv(a=1); return(list(get_variable(x, "a"), get_variable(x, 3), length(x))) }
  if (name == "dim_na<-") { x <- listenv(1,2,3,4,5,6); dim_na(x) <- c(2, NA); return(as.integer(dim(x))) }
  if (name == "undim") { x <- listenv(1,2); dim(x) <- c(2,1); x <- undim(x); return(dim(x)) }
  if (name == "parse_env_subset") { x <- listenv(1, 2); z <- parse_env_subset(quote(x[[2]]), envir=environment(), substitute=FALSE); return(list(op=z$op, subset=z$subset, code=z$code)) }
  stop(name)
}
one <- run()
times <- numeric(20)
for (i in seq_len(20)) { t <- Sys.time(); run(); times[i] <- as.numeric(Sys.time()-t, units="secs")*1000 }
cat("result="); dput(one); cat("\nr_ms="); cat(median(times)); cat("\n")
