# Python built-in libraries
import logging


def run_prism(prism_path, mode_switcher_filename, mode_switcher_properties_filename,
              mode_switcher_strategy_filename, verbose):
    command = (f"{prism_path} "
               + f"{mode_switcher_filename} "
               + f"{mode_switcher_properties_filename} -prop strategy "
               + f"-exportstrat '{mode_switcher_strategy_filename}:type=actions' "
               + f"-exportstates \'{mode_switcher_strategy_filename.split('.')[0]}_states.prism\'")
    logging.info(command)
    if not verbose:
        command += " > /dev/null"
    return command

