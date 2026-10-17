.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

proof_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/proof"
G <- 6
mod <- list(
  data = as.matrix(read.table(file.path(proof_dir, "clustCombi_data.csv"))),
  z = as.matrix(read.table(file.path(proof_dir, "clustCombi_z.csv"))),
  G = G
)
class(mod) <- "Mclust"
cc <- clustCombi(mod)

xlog <- function(x) {
  if (is.null(dim(x))) return(sapply(x, function(xi) if (xi == 0) 0 else xi * log(xi)))
  matrix(sapply(x, function(xi) if (xi == 0) 0 else xi * log(xi)), dim(x))
}

combiTree_hc <- function(object, yaxis = c("entropy", "step")) {
  yaxis <- match.arg(yaxis)
  G <- object$MclustOutput$G
  combiM <- object$combiM
  curr <- 1:G
  merged <- -(1:G)
  merge <- matrix(NA, G - 1, 2)
  for (k in 1:(G - 1)) {
    Kp <- G - k + 1
    l1 <- which(!combiM[[Kp - 1]] %*% rep(1, Kp) == 1)
    l2 <- (combiM[[Kp - 1]] %*% curr)[l1] - curr[l1]
    curr <- setdiff(curr, max(l1, l2))
    merge[k, ] <- merged[c(l1, l2)]
    merged[merged == merged[l1] | merged == merged[l2]] <- k
  }
  sel <- function(x) {
    if (x < 0) return(abs(x))
    c(sel(merge[x, 1]), sel(merge[x, 2]))
  }
  ord <- abs(c(sel(merge[nrow(merge), 1]), sel(merge[nrow(merge), 2])))
  if (yaxis == "step") {
    h <- 1:(G - 1)
  } else {
    entropy <- sapply(rev(object$combiz), function(z) -sum(xlog(z)))
    h <- entropy
    h <- 1 - (h - min(h)) / (max(h) - min(h))
    h <- h[-1]
  }
  list(merge = merge, height = h, order = ord, labels = 1:G)
}

flatten_hc <- function(hc) c(as.vector(hc$merge), hc$height, hc$order)

value <- flatten_hc(combiTree_hc(cc, yaxis = "entropy"))

one <- function() {
  pdf(tempfile())
  on.exit(dev.off(), add = TRUE)
  combiTree(cc, yaxis = "entropy")
  flatten_hc(combiTree_hc(cc, yaxis = "entropy"))
}

elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", value), sep = "")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
