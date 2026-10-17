"""Translation of sass::sass_import."""


def sass_import(input, quote=True):
    if quote is True:
        input = str(input).replace("\\", "\\\\").replace('"', '\\"').replace("'", "\\'")
        return '@import "' + input + '";'
    return "@import " + str(input) + ";"
