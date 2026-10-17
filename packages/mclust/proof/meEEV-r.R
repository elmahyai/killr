suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
i <- seq_len(40L); g <- as.numeric(i > 20L)
X <- cbind(((i * 37L) %% 11L) / 11 + 2.5 * g,
           ((i * 23L) %% 13L) / 13 + 1.5 * g)
w <- ((i * 7L) %% 19L) / 19; Z <- cbind(0.2+0.6*w, 0.8-0.6*w)
flat <- function(a) c(a$loglik, attr(a,"returnCode"),
  attr(a,"info")[["iterations"]], attr(a,"info")[["error"]],
  as.vector(a$parameters$pro), as.vector(a$parameters$mean),
  a$parameters$variance$scale, as.vector(a$parameters$variance$shape),
  as.vector(a$parameters$variance$orientation),
  as.vector(a$parameters$variance$sigma), as.vector(a$z))
one <- function() flat(mclust:::meEEV(X,Z,control=emControl(),warn=FALSE))
value <- one(); elapsed <- numeric(20)
for (k in seq_len(20)) { t0<-as.numeric(Sys.time()); one(); elapsed[k]<-as.numeric(Sys.time())-t0 }
cat(sprintf("%.17g\n",value),sep=""); cat(sprintf("%.17g\n",median(elapsed)*1000))
