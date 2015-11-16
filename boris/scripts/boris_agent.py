"""Command-line entry point for development"""

from boristool.commands import agent


def main(*args, **kwargs):
    agent()


if __name__ == '__main__':
    main()
