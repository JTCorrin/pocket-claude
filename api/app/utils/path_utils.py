"""
Path utility functions for Claude Code integration.
"""


def decode_project_path(folder_name: str) -> str:
    """
    Decode a project folder name to its original path.

    Claude Code encodes project paths by replacing slashes with hyphens
    and adding a leading hyphen. This function reverses that encoding.

    Args:
        folder_name: The encoded folder name (e.g., "-Users-test-project")

    Returns:
        The decoded project path (e.g., "/Users/test/project")

    Examples:
        >>> decode_project_path("-Users-test-project")
        '/Users/test/project'
        >>> decode_project_path("home-user-code")
        '/home/user/code'
    """
    # Remove leading hyphen if present and replace hyphens with slashes
    if folder_name.startswith("-"):
        folder_name = folder_name[1:]
    return "/" + folder_name.replace("-", "/")
