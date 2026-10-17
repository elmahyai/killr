"""Python translation of the R package remotes."""

from remotes.add_metadata import add_metadata
from remotes.available_packages import (
    available_packages,
    available_packages_reset,
    available_packages_set,
)
from remotes.bioc import bioc_install_repos, bioc_version
from remotes.deps import dev_package_deps, local_package_deps, package_deps
from remotes.download_version import download_version
from remotes.git_credentials import git_credentials
from remotes.github_refs import github_pull, github_release
from remotes.github_remote import github_remote
from remotes.install_bioc import install_bioc
from remotes.install_bitbucket import install_bitbucket
from remotes.install_cran import install_cran
from remotes.install_deps import install_deps
from remotes.install_dev import install_dev
from remotes.install_git import install_git
from remotes.install_github import install_github
from remotes.install_gitlab import install_gitlab
from remotes.install_local import install_local
from remotes.install_remote import install_remote
from remotes.install_svn import install_svn
from remotes.install_url import install_url
from remotes.install_version import install_version
from remotes.gitlab_pat import gitlab_pat
from remotes.parse import parse_github_repo_spec, parse_github_url, parse_repo_spec
from remotes.remote import remote_download, remote_metadata, remote_package_name, remote_sha
from remotes.standardise_dep import NA, standardise_dep
from remotes.system_requirements import system_requirements
from remotes.update_packages import update_packages

__all__ = [
    "NA",
    "add_metadata",
    "available_packages",
    "available_packages_reset",
    "available_packages_set",
    "bioc_install_repos",
    "bioc_version",
    "dev_package_deps",
    "download_version",
    "git_credentials",
    "github_pull",
    "github_release",
    "github_remote",
    "gitlab_pat",
    "install_bioc",
    "install_bitbucket",
    "install_cran",
    "install_deps",
    "install_dev",
    "install_git",
    "install_github",
    "install_gitlab",
    "install_local",
    "install_remote",
    "install_svn",
    "install_url",
    "install_version",
    "local_package_deps",
    "package_deps",
    "parse_github_repo_spec",
    "parse_github_url",
    "parse_repo_spec",
    "remote_download",
    "remote_metadata",
    "remote_package_name",
    "remote_sha",
    "standardise_dep",
    "system_requirements",
    "update_packages",
]
