# Map hole order

A fastmap key list is the occupied slots of the backing vector, not the hash iteration order. New keys take the last free hole, so the first keys sit at the end of the initial buffer of 32. The C++ map only stores the string-to-index lookup. `keys(sort = TRUE)` orders those strings by Unicode code point.
