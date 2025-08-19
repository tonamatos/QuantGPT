# src/quantgpt/__main__.py

import argparse
from . import main

def run():
  parser = argparse.ArgumentParser(prog="quantgpt", description="QuantGPT CLI")
  parser.add_argument(
    "-f", "--file",
    help="Filename inside technical_design_docs",
    required=True,
  )
  parser.add_argument(
    "--debug",
    action="store_true",
    help="Enable debug mode"
  )
  args = parser.parse_args()
  main.run(args.file, debug=args.debug)

if __name__ == "__main__":
  run()
