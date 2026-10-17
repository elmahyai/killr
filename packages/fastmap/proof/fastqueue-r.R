.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(fastmap))
if (packageDescription("fastmap")$Version != "1.2.0") stop("expected fastmap 1.2.0")

one <- function() {
  q <- fastqueue(3)
  for (i in 1:12) q$add(i + 0.5)
  first <- unlist(q$as_list())
  removed <- numeric(4)
  for (i in 1:4) removed[i] <- q$remove()
  q$madd(13.5, 14.5, .list = list(15.5, 16.5))
  second <- unlist(q$as_list())
  third <- unlist(q$mremove(3))
  size1 <- q$size()
  peek1 <- q$peek()
  while (q$size() > 0) q$remove()
  empty <- as.numeric(identical(q$remove(), NULL))
  q$add(NULL)
  null_kept <- as.numeric(identical(q$remove(missing = -1), NULL))
  empty2 <- q$remove(missing = -1)
  q$reset()
  q$add(1.25)

  q2 <- fastqueue(3)
  q2$madd(1, .list = list(3), 2)
  order1 <- unlist(q2$as_list())
  q2$madd(4, 5, 6, 7)
  q2$madd(8, 9)
  for (i in 1:5) q2$remove()
  q2$madd(10, 11, 12, 13, 14, 15, 16)
  wrap <- unlist(q2$as_list())

  q3 <- fastqueue(3)
  q3$madd(1, 2, 3, 4, 5, 6)
  six <- unlist(q3$as_list())
  onev <- q3$remove()
  q3$madd(7, 8, 9, 10, 11, 12, 13, 14)
  grown <- unlist(q3$as_list())
  for (i in 1:6) q3$remove()
  mid <- unlist(q3$as_list())
  shr <- q3$remove()
  after <- unlist(q3$as_list())
  c(
    first, removed, second, third, size1, peek1, empty, null_kept, empty2,
    q$size(), q$peek(), order1, wrap, six, onev, grown, mid, shr, after
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
  con = "proof/fastqueue-r.txt"
)

q <- fastqueue(3)
q$add(1)
q$add(2)
q$add(3)
q$add(4)
example <- paste0(
  "as_list ", paste(unlist(q$as_list()), collapse = " "), "\n",
  "remove ", q$remove(), "\n",
  "size ", q$size(), "\n",
  "peek ", q$peek(), "\n"
)
cat(example, file = "docs/output/fastqueue-r.txt")
