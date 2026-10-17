.libPaths(c(path.expand("~/R/library"), .libPaths()))
library(curl)
cat(if (find_port() > 1023) 'TRUE' else 'FALSE')
