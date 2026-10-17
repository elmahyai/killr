.libPaths(c(path.expand("~/R/library"), .libPaths()))
library(openssl)
cat(if (isTRUE(fips_mode())) 'TRUE' else 'FALSE')
