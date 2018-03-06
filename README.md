# labrat

A command line client for GitLab.

## Requirements

This project requires Python 3.

## Installation

Install with `pip`:

    pip install git+https://github.com/larsks/labrat

## Configuration

Configure your API token in `gitlab.token`:

    git config --set gitlab.token your_secret_token

If you are using a self-hosted instance of gitlab, rather than
`gitlab.com`, set `gitlab.url`:

    git config --set gitlab.url http://gitlab.example.com/

## Running Labrat

When you install labrat you will end up with a `git-lab` command in
your `$PATH`. You can call it directly, or you can instead call it
like:

    git lab ...

## Examples

List available repositories:

    git lab list

Create a new repository:

    git lab create --description "This is a test" --visibilty private sandbox

Delete a repository:

    git lab delete myusername/sandbox
