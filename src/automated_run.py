#!/usr/bin/env python3.9

# Copyright [2023] Jonis Kiesbye, Kush Grover
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from analysis_tool_gui import initialize_window
import logging
import os
import time
from datetime import datetime
from collections import namedtuple

log_to_file = True
benchmark_folder = "benchmarks"
Benchmark = namedtuple('Benchmark', 'name n_faults includeMCTS includePrism')
benchmarks = [Benchmark('space_tug_ver1', 2, False, False),
              Benchmark('space_tug_ver1', 1, True, True),
              Benchmark('space_tug_ver2', 2, False, False),
              Benchmark('space_tug_ver2', 1, True, True),
              Benchmark('space_tug_ver3', 2, False, False),
              Benchmark('space_tug_ver3', 1, True, True),
              Benchmark('space_tug_ver4', 2, False, False),
              Benchmark('space_tug_ver4', 1, True, True),
              Benchmark('space_tug_ver5', 2, False, False),
              Benchmark('space_tug_ver5', 1, True, True),
              Benchmark('space_tug_ver6', 2, False, False),
              Benchmark('space_tug_ver6', 1, True, True),
              Benchmark('space_tug_ver7', 2, False, False),
              Benchmark('space_tug_ver7', 1, True, True),
              Benchmark('space_tug_ver8', 2, False, False),
              Benchmark('space_tug_ver8', 1, False, False),
              Benchmark('space_tug_ver9', 2, False, False),
              Benchmark('space_tug_ver9', 1, False, False)
              ]


def main():
    format_string = "[%(levelname)s] %(funcName)s-l%(lineno)d: %(message)s"
    if log_to_file:
        # Log to file
        logging.basicConfig(
            filename=f"../{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_automated_run_log.txt",
            format=f"%(asctime)s.%(msecs)03d - {format_string}",
            datefmt='%H:%M:%S',
            level=logging.DEBUG)
    else:
        # Log to console
        logging.basicConfig(format=format_string,
                            level=logging.INFO)
    os.environ["TQDM_DISABLE"] = "1"

    logging.info(f"Automated run in {benchmark_folder} for graphs {benchmarks}.")
    logging.info("Note that this script assumes the graph filename matches the folder name.")
    start_time = time.time()

    window = initialize_window()
    window.base_directory = os.path.split(os.getcwd())[0]  # path of the analysis tool
    for benchmark in benchmarks:
        start_time_benchmark = time.time()
        benchmark_path = os.path.join(benchmark_folder, benchmark.name)
        window.filename = os.path.join(window.base_directory,
                                       benchmark_path,
                                       f"{benchmark.name}.dot")
        window.directory = benchmark_path
        window.number_of_faults_entry.set_text(f"{benchmark.n_faults}")
        logging.info(f"Analyzing graph {window.filename}")
        print(f"{benchmark=}") if log_to_file else None

        # Open file
        window.on_open_helper(window.filename)

        # Analyze
        window.on_analyze(None)

        # Check isolation
        window.check_isolation(None)

        # Check recovery
        window.check_recovery(None)

        # Save sensitivity analysis
        window.write_sensitivity(None)
        print(f"Analysis done") if log_to_file else None

        if benchmark.n_faults == 1 and benchmark.includeMCTS:
            # Build isolation with MCTS
            print(f"MCTS run with 1 successor") if log_to_file else None
            window.children_to_keep_entry.set_text("1")
            window.simulations_per_node_entry.set_text("200")
            window.build_prune_and_compress(None, gui=False)

            print(f"MCTS run with 2 successors") if log_to_file else None
            window.children_to_keep_entry.set_text("2")
            window.simulations_per_node_entry.set_text("200")
            window.build_prune_and_compress(None, gui=False)

            print(f"MCTS run with 10 successors") if log_to_file else None
            window.children_to_keep_entry.set_text("10")
            window.simulations_per_node_entry.set_text("200")
            window.build_prune_and_compress(None, gui=False)

            # print(f"MCTS run with all successors") if log_to_file else None
            # window.children_to_keep_entry.set_text(0)
            # window.simulations_per_node_entry.set_text(0)
            # window.build_prune_and_compress(None)

        if benchmark.n_faults == 1:
            # Build recovery
            window.build_recovery(None, False)

        if benchmark.includePrism:
            print(f"Run PRISM isolation") if log_to_file else None
            # Generate prism model
            window.export_isolation(None)

            # Check prism model
            window.run_isolation(None)

        # Save weakness report
        window.write_report(None)
        logging.info(f"The analysis for file {window.filename} took "
                     f"{time.time() - start_time_benchmark} s.")
        print(f"Benchmark done\n\n") if log_to_file else None

    logging.info(f"The whole analysis for all files took {time.time()-start_time} s.")
    logging.shutdown()


if __name__ == '__main__':
    main()
