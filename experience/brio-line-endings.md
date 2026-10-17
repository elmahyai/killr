`brio::read_lines` splits only on LF, strips a preceding CR, and does not
create a final empty element for a trailing newline. `write_lines` treats each
embedded LF as a boundary, removes its preceding CR, and always appends the
requested EOL, including for empty strings.
