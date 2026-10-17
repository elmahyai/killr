from ._common import copy_attachments


def write_file_attachments(file_attachments, output_path):
    copy_attachments(file_attachments, output_path)
    return None
