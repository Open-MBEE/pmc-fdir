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
import json
from datetime import datetime
from collections import namedtuple

log_to_file = True
benchmark_folder = "benchmarks"
Benchmark = namedtuple('Benchmark',
                       'name n_faults includeMCTS includePrism engines')
benchmarks = [Benchmark('space_tug_ver1', 2, False, False, []),
              Benchmark('space_tug_ver1', 1, True, True, ["explicit", "sparse"]),
              Benchmark('space_tug_ver2', 2, False, False, []),
              Benchmark('space_tug_ver2', 1, True, True, ["explicit", "sparse"]),
              Benchmark('space_tug_ver3', 2, False, False, []),
              Benchmark('space_tug_ver3', 1, True, True, ["explicit", "sparse"]),
              Benchmark('space_tug_ver4', 2, False, False, []),
              Benchmark('space_tug_ver4', 1, True, True, ["explicit", "sparse"]),
              Benchmark('space_tug_ver5', 2, False, False, []),
              Benchmark('space_tug_ver5', 1, True, True, ["explicit", "sparse"]),
              Benchmark('space_tug_ver6', 2, False, False, []),
              Benchmark('space_tug_ver6', 1, True, True, ["explicit", "sparse"]),
              Benchmark('space_tug_ver7', 2, False, False, []),
              Benchmark('space_tug_ver7', 1, True, True, ["explicit", "sparse"]),
              Benchmark('space_tug_ver8', 2, False, False, []),
              Benchmark('space_tug_ver8', 1, False, False, []),
              Benchmark('space_tug_ver9', 2, False, False, []),
              Benchmark('space_tug_ver9', 1, False, False, [])
              ]
# benchmarks = [Benchmark('robot_sat_v1', 1, False, True, ["explicit", "sparse"]),
#               Benchmark('robot_sat_v2', 1, False, True, ["explicit", "sparse"]),
#               Benchmark('robot_sat_v3', 1, False, True, ["explicit", "sparse"]),
#               Benchmark('robot_sat_v4', 1, False, True, ["explicit", "sparse"]),
#               Benchmark('robot_sat_v5', 1, False, True, ["explicit", "sparse"]),
#               Benchmark('robot_sat_v6', 1, False, True, ["explicit", "sparse"]),
#               Benchmark('robot_sat_v7', 1, False, True, ["explicit", "sparse"])
#               ]
#
benchmarks = [#Benchmark('space_tug_ver8', 1, False, True, ["explicit", "sparse"]),
              Benchmark('space_tug_ver9', 1, False, True, ["explicit", "sparse"])
              ]
#
# benchmarks = [Benchmark('planning_example', 1, False, True, ["explicit", "sparse"])]


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
            for engine in benchmark.engines:
                print(f"\t{engine=}")
                window.run_isolation(None, engine=engine)

        # Save weakness report
        window.write_report(None)
        logging.info(f"The analysis for file {window.filename} took "
                     f"{time.time() - start_time_benchmark} s.")

        # Save variables as JSON
        json_filename = os.path.join(window.base_directory,
                                     benchmark_path,
                                     'output',
                                     f'{benchmark.name}.json')
        with open(json_filename, 'w') as json_file:
            json.dump({"benchmark_name": benchmark.name,
                       "benchmark_n_faults": benchmark.n_faults,
                       "benchmark_includeMCTS": benchmark.includeMCTS,
                       "benchmark_includePrism": benchmark.includePrism,
                       "filename": window.filename,

                       "isolable": window.isolable,
                       "non_isolable": window.non_isolable,
                       # "missing_components": window.missing_components,
                       "engines": benchmark.engines,
                       "best_isolation_cost": window.best_isolation_cost,
                       "worst_isolation_cost": window.worst_isolation_cost,

                       "recoverable": window.recoverable,
                       "non_recoverable": window.non_recoverable,
                       "single_string_components": window.single_string_components,
                       "recovery_cost": window.recovery_cost,

                       "all_equipment": window.all_equipment,
                       # "unique_graph_list": window.unique_graph_list,
                       "component_lists": window.component_lists,
                       "configuration_list": window.configuration_list,
                       "num_unique_configurations": window.num_unique_configurations,

                       "configuration_index": window.configuration_index,

                       "analysis_time": window.analysis_time,
                       "check_isolability_time": window.check_isolability_time,
                       "mcts_isolation_build_time": window.mcts_isolation_build_time,
                       "prism_isolation_time": window.prism_isolation_time,
                       "prism_isolation_time_sparse": window.prism_isolation_time_sparse,
                       "prism_isolation_time_explicit": window.prism_isolation_time_explicit,
                       "check_recoverability_time": window.check_recoverability_time},
                      json_file)

        print(f"Benchmark done\n\n") if log_to_file else None

    logging.info(f"The whole analysis for all files took {time.time()-start_time} s.")
    logging.shutdown()


if __name__ == '__main__':
    main()
