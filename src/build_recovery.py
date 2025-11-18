#!/usr/bin/python3.9

# Copyright [2023-2025] Jonis Kiesbye
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

# Python built-in libraries
import time
import sys
import os
import shutil
import logging

# third-party libraries
import networkx as nx

# project-specific libraries
from graph_analysis.graph_analysis import create_graph_list, get_layers, get_node_name, \
    find_leaf_nodes, find_isolated_nodes, get_mode_indices, get_mode_indices_appended
from graph_analysis.generate_available_modes import generate_available_modes
from graph_analysis.generate_mode_switcher import generate_mode_switcher
from graph_analysis.generate_config_json import generate_config_json_recovery
from graph_analysis.run_prism import run_prism
from graph_analysis.run_dtcontrol import run_dtcontrol
from graph_analysis.create_actions_list import create_actions_list
from graph_analysis.generate_reconfigure import generate_reconfigure

base_directory = sys.argv[1]
directory = sys.argv[2]
filename = sys.argv[3]

logging.basicConfig(format="[%(levelname)s] %(funcName)s: %(message)s")
logging.getLogger().setLevel(logging.INFO)

multi_digraph = nx.nx_agraph.read_dot(filename)
graph = nx.DiGraph(multi_digraph)
if len(find_isolated_nodes(graph)) > 0:
    logging.info(
        f"Found {len(find_isolated_nodes(graph))} isolated nodes: "
        f"{find_isolated_nodes(graph)}. Removing them.")
    for node in find_isolated_nodes(graph):
        graph.remove_node(node)
else:
    logging.info(f"No isolated nodes found")

layers = get_layers(graph)
all_equipment = sorted([get_node_name(graph, node) for node in find_leaf_nodes(graph, layers)])
unique_graph_list, unique_node_lists, component_lists, configuration_list, configuration_space \
    = create_graph_list(graph, threading=False)

start_time = time.time()
verbose = True
directory_name = directory + "/recovery_" + filename.split('/')[-1].split('.')[0] + "/"
if os.path.exists(directory_name):
    shutil.rmtree(directory_name)
os.makedirs(directory_name)
available_modes_filename = "available_modes.c"
logging.info("Generate " + available_modes_filename)
generate_available_modes(graph,
                         all_equipment,
                         component_lists,
                         directory_name + available_modes_filename,
                         verbose)


mode_switcher_filename = "mode_switcher_" + filename.split('/')[-1].split('.')[0] + ".prism"
logging.info("Generate " + mode_switcher_filename)
generate_mode_switcher(get_mode_indices(graph),
                       get_mode_indices_appended(graph),
                       directory_name + mode_switcher_filename)

mode_switcher_properties_filename = f"{mode_switcher_filename.split('.')[0]}.props"
logging.info("Generate " + mode_switcher_properties_filename)
with open(directory_name + mode_switcher_properties_filename, "w") as text_file:
    print('// Maximum probability of reaching the target\n'
          '"strategy": Pmax=? [ F "mode_selected" ]\n', file=text_file)
    print('// Print values of all states, print max probability of reaching the target\n'
          '"printall": filter(printall, Pmax=? [ F "mode_selected" ], "init")\n', file=text_file)

logging.info("Model-checking with PRISM")
prism_path = f"{base_directory}/prism/bin/prism"
mode_switcher_strategy_filename = f"strategy_{mode_switcher_filename}"
command = run_prism(prism_path,
                    directory_name + mode_switcher_filename,
                    directory_name + mode_switcher_properties_filename,
                    directory_name + mode_switcher_strategy_filename,
                    verbose)
os.system(command)

logging.info("Generate config JSON")
mode_switcher_config_filename = f"strategy_{mode_switcher_filename.split('.')[0]}_config.json"
generate_config_json_recovery(get_mode_indices(graph),
                              get_mode_indices_appended(graph),
                              directory_name + mode_switcher_config_filename)

logging.info("Run dtControl and move decision tree")
command = run_dtcontrol(directory_name, directory_name + mode_switcher_strategy_filename, verbose)
os.system(command)

reconfigure_filename = "reconfigure.c"
logging.info(f"Generate {reconfigure_filename}")
actions_list = create_actions_list(directory_name + mode_switcher_strategy_filename)
logging.info(actions_list)
generate_reconfigure(graph,
                     actions_list,
                     get_mode_indices(graph),
                     get_mode_indices_appended(graph),
                     directory_name + reconfigure_filename)

logging.info(f"This model took {str(time.time() - start_time)}s")

os.system(f'''echo $(echo "scale=5; 100* $({prism_path} {directory_name + mode_switcher_filename} {directory_name + mode_switcher_properties_filename} -prop printall | grep -c "=1.0") / $({prism_path} {directory_name + mode_switcher_filename} {directory_name + mode_switcher_properties_filename} -prop strategy | grep -oP '\d+(?= initial\))')" | bc)"% solvable of all initial states"''')
