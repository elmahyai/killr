.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(fastmap))
if (packageDescription("fastmap")$Version != "1.2.0") stop("expected fastmap 1.2.0")

codes <- function(x) {
  if (length(x) == 0) return(numeric(0))
  as.numeric(utf8ToInt(paste(x, collapse = "\n")))
}

one <- function() {
  m <- fastmap()
  m$set("a", 1.5)
  m$set("b", 2.25)
  m$set("v", c(1.5, 2.25, 3.125))
  m$set("z", 9)
  m$set("é", 8)
  m$set("none", NULL)
  for (i in 1:40) m$set(sprintf("k%02d", i), i + 0.5)
  out <- c(
    m$size(),
    m$get("a"), m$get("b"), m$get("z"), m$get("é"), m$get("v"),
    as.numeric(m$has("none")),
    as.numeric(identical(m$get("none"), NULL)),
    as.numeric(m$has("missing")),
    as.numeric(identical(m$get("missing"), NULL)),
    codes(m$keys()),
    codes(m$keys(TRUE))
  )
  removed <- m$remove(c("b", "k02", "b", "missing"))
  for (i in seq(1, 40, by = 2)) m$remove(sprintf("k%02d", i))
  m2 <- m$clone()
  m2$set("a", 99.5)
  m$set("z", 7.5)
  err1 <- tryCatch(m$set(1, 1), error = function(e) conditionMessage(e))
  err2 <- tryCatch(m$set("", 1), error = function(e) conditionMessage(e))
  c(
    out,
    as.numeric(removed),
    m$size(),
    codes(m$keys()),
    codes(m$keys(TRUE)),
    m$get("a"), m2$get("a"), m$get("z"), m2$get("z"),
    unlist(m$mget(c("a", "é", "k04"))),
    nchar(err1), utf8ToInt(err1),
    nchar(err2), utf8ToInt(err2)
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
  con = "proof/fastmap-r.txt"
)

m <- fastmap()
m$set("x", 100)
m$set("letters", c("a", "b", "c"))
m$mset(numbers = c(10, 20, 30))
example <- paste0(
  "get x ", m$get("x"), "\n",
  "get numbers ", paste(m$get("numbers"), collapse = " "), "\n",
  "keys ", paste(m$keys(TRUE), collapse = " "), "\n",
  "size ", m$size(), "\n",
  "remove x ", m$remove("x"), "\n",
  "size ", m$size(), "\n",
  "missing ", identical(m$get("x"), NULL), "\n"
)
cat(example, file = "docs/output/fastmap-r.txt")
