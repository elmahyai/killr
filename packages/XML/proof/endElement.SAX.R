.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(XML))
txt <- '<doc id="1"><item class="a">hello</item><item class="b">world<note>!</note></item></doc>'
ns <- '<doc xmlns:a="urn:ex"><a:item>z</a:item></doc>'
html <- '<html><head><title>Hi</title></head><body><a href="x">go</a></body></html>'
setClass("T2", contains = "SAXState")
setClass("MySAXState", representation(closed = "character"), contains = "SAXState")
setMethod("endElement.SAX", signature(.state = "MySAXState"), function(name, .state = NULL) {
  .state@closed <- c(.state@closed, name)
  .state
})
one <- function() {
  st <- new("T2")
  my <- new("MySAXState")
  paste(
    c(
      identical(endElement.SAX("item", st), st),
      class(endElement.SAX("item", st))[1],
      paste(endElement.SAX("item", my)@closed, collapse = ":"),
      paste(endElement.SAX("doc", endElement.SAX("item", my))@closed, collapse = ":")
    ),
    collapse = ","
  )
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
