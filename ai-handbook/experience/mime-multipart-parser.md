# MIME multipart parser

The mime package's multipart parser returns ordinary form values as strings and
uploaded files as records containing `name`, byte `size`, MIME `type`, and a
temporary `datapath`. The R implementation strips the final CRLF from form
values but preserves uploaded file bytes.
