from ._common import options


def sass_options(precision=5, output_style="expanded", indented_syntax=False,
                 include_path="", source_comments=False, indent_type="space",
                 indent_width=2, linefeed="lf", output_path="",
                 source_map_file="", source_map_root="", source_map_embed=False,
                 source_map_contents=False, omit_source_map_url=False):
    return options(
        precision=precision, output_style=output_style,
        indented_syntax=indented_syntax, include_path=include_path,
        source_comments=source_comments, indent_type=indent_type,
        indent_width=indent_width, linefeed=linefeed, output_path=output_path,
        source_map_file=source_map_file, source_map_root=source_map_root,
        source_map_embed=source_map_embed,
        source_map_contents=source_map_contents,
        omit_source_map_url=omit_source_map_url,
    )
