# Python built-in libraries
import logging

# project-specific libraries
from graph_analysis.graph_analysis import get_node_name


def get_guards(component_lists, verbose):
    guards = {}
    for mode in component_lists:
        configuration_guards = [f"({' && '.join(configuration)})"
                                for configuration in component_lists[mode]]
        mode_guard = "\n        || ".join(configuration_guards)
        logging.info(mode_guard) if verbose else None
        guards[mode] = mode_guard
    return guards


def get_initialization(component_lists, all_equipment, verbose):
    initialization = ("#include <stdio.h>\n"
                      "#include <stdbool.h>\n"
                      "\n"
                      "void available(const unsigned char x[], unsigned char* y);\n"
                      "\n"
                      "void available(const unsigned char x[], unsigned char* y) {")
    initialization += "\n    // read the equipment status\n"
    for index, item in enumerate(all_equipment):
        initialization += "    unsigned char " + item + " = x[" + str(index) + "];\n"

    initialization += ("\n"
                       f"    // initialize all {str(len(component_lists))} output fields with "
                       f"false\n")
    initialization += "    for (int i = 0; i<" + str(len(component_lists)) + "; ++i) {\n"
    initialization += "        y[i] = false;\n"
    initialization += "    }\n"
    logging.info(initialization) if verbose else None
    return initialization


def get_branches(graph, guards, verbose):
    branches = ("    // ---\n"
                "    // determine which functions are available based on the available equipment\n"
                "    // ---\n\n")
    for index, guard in enumerate(guards):
        branches += "    // " + get_node_name(graph, guard) + "\n"
        branches += "    if (   " + guards[guard] + " )\n    {\n"
        branches += "        y[" + str(index) + "] = true;\n"
        branches += "    }\n"
    logging.info(branches) if verbose else None
    return branches


def generate_available_modes(graph, all_equipment, component_lists, filename, verbose):
    guards = get_guards(component_lists, verbose)
    initialization = get_initialization(component_lists, all_equipment, verbose)
    branches = get_branches(graph, guards, verbose)
    end = "}"
    code = initialization + branches + end
    with open(filename, "w") as text_file:
        print(code, file=text_file)
