# Python built-in libraries
import logging


def run_dtcontrol(directory_name, mode_switcher_strategy_filename, verbose):
    command = (f"dtcontrol --input {mode_switcher_strategy_filename}"
               f" --use-preset avg --rerun --benchmark-file benchmark.json"
               f" --timeout 6h --output {directory_name}")
    logging.info(command)
    if not verbose:
        command += " > /dev/null 2>&1"
    return command