.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(XML))
txt <- '<doc id="1"><item class="a">hello</item><item class="b">world<note>!</note></item></doc>'
ns <- '<doc xmlns:a="urn:ex"><a:item>z</a:item></doc>'
html <- '<html><head><title>Hi</title></head><body><a href="x">go</a></body></html>'
one <- function() {
  d1 <- Doctype(
    name = "section",
    public = c(
      "-//OASIS//DTD DocBook XML V4.2//EN",
      "http://oasis-open.org/docbook/xml/4.2/docbookx.dtd"
    )
  )
  d2 <- Doctype(
    name = "section",
    public = c("-//OASIS//DTD DocBook XML V4.2//EN"),
    system = "http://oasis-open.org/docbook/xml/4.2/docbookx.dtd"
  )
  paste(as(d1, "character"), as(d2, "character"), sep = "|")
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
