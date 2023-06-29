import re
import logging
import networkx as nx
from graph_analysis.graph_analysis import find_leaf_nodes, get_node_name, find_root_nodes, \
    get_layers


def get_equipment_indices(graph):
    leaves = sorted([get_node_name(graph, leaf)
                     for leaf in find_leaf_nodes(graph, get_layers(graph))])
    equipment_indices = {}
    for index, leaf in enumerate(leaves):
        equipment_indices[leaf] = index
    # logging.info(equipment_indices)
    return equipment_indices


def get_root_node_names(graph):
    root_nodes = find_root_nodes(graph)
    root_node_names = {}
    for root_node in root_nodes:
        root_node_names[get_node_name(graph, root_node)] = root_node
    # logging.info(f"{root_node_names=}")
    return root_node_names


def get_initialization(equipment_indices, mapping, mode_indices):
    initialization = """#include <stdio.h>
#include <stdbool.h>

unsigned char map_mode(const unsigned char mode_in);
void reconfigure(const unsigned char mode, unsigned char* equipment);

unsigned char map_mode(const unsigned char mode_in) {"""
    initialization += "\n    unsigned char mapping[] = "
    initialization += re.sub("\]", "}", re.sub("\[", "{", str(mapping))) + ";\n"
    initialization += "    return mapping[mode_in];\n"

    initialization += """}

void reconfigure(const unsigned char mode, unsigned char* equipment) {
"""
    logging.debug("equipment:")
    for equipment in equipment_indices:
        initialization += "    unsigned char " + equipment + " = equipment["
        initialization += str(equipment_indices[equipment]) + "];\n"
        logging.debug(equipment + ": " + str(equipment_indices[equipment]))
    

    initialization += "\n    enum mode_names {\n"
    for mode in mode_indices:
        initialization += "        " + mode + ",\n"
    initialization += "    };\n"
    # logging.info(initialization)
    # logging.info("initialization done")
    return initialization


def get_branches(graph, mode_indices, all_equipment):
    branches = ""
    for mode in mode_indices:
        branches += "    if (mode==" + mode + ") {\n"
        mode_name = get_root_node_names(graph)[mode]
        mode_equipment = sorted([get_node_name(graph, node)
                                 for node in find_leaf_nodes(graph,
                                                             root_node=mode_name,
                                                             type='components')])
        for item in all_equipment:
            if item not in mode_equipment:
                branches += "        " + item + " = false;\n"
        branches += "    };\n"
    # logging.info(branches)
    # logging.info("branches done")
    return branches


def get_set_outputs(all_equipment):
    set_outputs = ""
    for index, item in enumerate(all_equipment):
        set_outputs += "    equipment[" + str(index) + "] = " + item + ";\n"
    # logging.info(set_outputs)
    # logging.info("set_outputs done")
    return set_outputs


def generate_reconfigure(graph,
                         actions_list,
                         mode_indices,
                         mode_indices_appended,
                         reconfigure_filename):
    mapping = [mode_indices_appended[mode[12:]] for mode in actions_list]
    all_equipment = sorted([get_node_name(graph, node)
                            for node in find_leaf_nodes(graph, get_layers(graph))])
    code = get_initialization(get_equipment_indices(graph), mapping, mode_indices) \
           + get_branches(graph, mode_indices, all_equipment) \
           + get_set_outputs(all_equipment) \
           + "}"
    with open(reconfigure_filename, "w") as text_file:
        print(code, file=text_file)