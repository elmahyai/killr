.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(fastmap))
if (packageDescription("fastmap")$Version != "1.2.0") stop("expected fastmap 1.2.0")

one <- function() {
  s <- faststack(4)
  s$push(1.5)
  s$push(2.5)
  s$push(3.5)
  s$mpush(4.5, 5.5, .list = list(6.5))
  size1 <- s$size()
  listed <- unlist(s$as_list())
  top <- s$peek()
  p1 <- s$pop()
  p2 <- s$pop()
  multi <- unlist(s$mpop(3))
  left <- unlist(s$as_list())
  size2 <- s$size()
  for (i in 1:30) s$push(i + 0.25)
  size3 <- s$size()
  popped <- numeric(10)
  for (i in 1:10) popped[i] <- s$pop()
  rest_size <- s$size()
  rest_top <- s$peek()
  s$reset()
  empty <- s$pop(missing = -999)
  km <- faststack(missing_default = key_missing())
  flag <- as.numeric(is.key_missing(km$pop()))
  flag2 <- as.numeric(is.key_missing(km$peek()))
  c(
    size1, listed, top, p1, p2, multi, left, size2, size3, popped,
    rest_size, rest_top, empty, flag, flag2, s$size()
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
parts <- sprintf("%.17g", value)
writeLines(
  sprintf(
    "{\"value\":[%s],\"median_ms\":%.17g}\n",
    paste(parts, collapse = ","),
    median(elapsed) * 1000
  ),
  con = "proof/faststack-r.txt"
)

s <- faststack()
s$push(5)
s$push(6)
s$push(7)
example <- paste0(
  "size ", s$size(), "\n",
  "as_list ", paste(unlist(s$as_list()), collapse = " "), "\n",
  "pop ", s$pop(), "\n",
  "peek ", s$peek(), "\n",
  "size ", s$size(), "\n"
)
cat(example, file = "docs/output/faststack-r.txt")
