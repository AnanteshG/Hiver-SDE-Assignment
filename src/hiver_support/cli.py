"""Command-line entry point. No model calls are made at startup."""
import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Evidence-first support agent and evaluation")
    parser.add_argument("--version", action="version", version="hiver-support 0.1.0")
    parser.parse_args()
    parser.print_help()


if __name__ == "__main__":
    main()
