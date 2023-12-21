# Copyright [2023] Jonis Kiesbye
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

import subprocess
import logging
import re
import os
import json
from functools import reduce
from to_precision import to_precision
from graph_analysis.graph_analysis import get_node_name, find_leaf_nodes, get_fault_probability, \
    get_effects


class VariableHandler():
    def __init__(self):
        self.state_variables = {}
        self.configurations = {}
        self.configuration_index = {}

    def add_configuration(self, root_node, configuration_string):
        if root_node in self.configuration_index:
            self.configuration_index[root_node][configuration_string] = \
                len(self.configuration_index[root_node])
        else:
            self.configuration_index[root_node] = {}
            self.configuration_index[root_node][configuration_string] = 0

    def convert_to_prism_configuration(self, configuration, value):
        if not configuration in self.configurations:
            self.configurations[configuration] = []
        if not value in self.configurations[configuration]:
            self.configurations[configuration].append(value)
        return self.configurations[configuration].index(value)

    def convert_to_prism_guard(self, guard):
        prism_guard = guard
        # guard_list = []
        for condition in re.findall(r"\w+\s*=\s*\w+", guard):
            variable, value = condition.replace(' ', '').split('=')
            # check if the key already exists in the state_variables
            if variable in self.state_variables:
                # check if the value is known already
                if not value in self.state_variables[variable]:
                    # add the value to state_variables
                    self.state_variables[variable].append(value)
            else:
                # add the variable to state_variables
                self.state_variables[variable] = ['uninitialized', value]
            # get the index of the value
            index = self.state_variables[variable].index(value)
            prism_guard = prism_guard.replace(condition, f"{variable}={index}")
        return prism_guard

    def convert_to_prism_outcome(self, effects):
        outcome_list = []
        for effect in effects:
            # get text before the equal sign
            split_effect = effect.split('=')
            variable = split_effect[0].strip()
            # get text after the equal sign
            value = split_effect[1].strip()
            # check if the key already exists in the state_variables
            if variable in self.state_variables:
                # check if the value is known already
                if not value in self.state_variables[variable]:
                    # add the value to state_variables
                    self.state_variables[variable].append(value)
            else:
                # add the variable to state_variables
                self.state_variables[variable] = ['uninitialized', value]
            # get the index of the value
            index = self.state_variables[variable].index(value)
            outcome_list.append(f"({variable}\'={index})")
        return " & ".join(outcome_list)

    def convert_to_prism_declaration(self,
                                     graph,
                                     all_equipment,
                                     hidden_variable,
                                     include_configurations=False,
                                     debug=False):
        declaration_string = "  // equipment states\n"
        declaration_string += "  // 0=available, 1=suspicious\n"
        for component in all_equipment:
            declaration_string += f"  {component}: [0..1]{' init 1' if debug else ''};\n"
        if hidden_variable:
            declaration_string += f"  faulty_component: [0..{len(all_equipment) - 1}]" \
                                  f"{' init 0' if debug else ''};\n"
        if self.state_variables:
            declaration_string += "\n  // planning states\n"
        for variable in self.state_variables:
            variable_comments = [f"{index}={value}"
                                 for index, value in enumerate(self.state_variables[variable])]
            declaration_string += f"  // {', '.join(variable_comments)}\n"
            declaration_string += f"  {variable}: [0..{len(self.state_variables[variable]) - 1}]" \
                                  f"{' init 0' if debug else ''};\n"
        declaration_string += "\n  // configurations\n"
        for assembly in self.configurations:
            logging.debug(f"{assembly=}: {self.configurations[assembly]}")
            assembly_comments = [f"{index}={value}"
                                 for index, value in enumerate(self.configurations[assembly])]
            declaration_string += f"  // {get_assembly_name(graph, assembly)}: " \
                                  f"{', '.join(assembly_comments)}\n"
            assembly_comments = [f"({index},)={get_node_name(graph, successor)}"
                                 for index, successor in enumerate(graph.successors(assembly))]
            declaration_string += f"  //   {', '.join(assembly_comments)}\n"
            if include_configurations:
                declaration_string += f"  {get_assembly_name(graph, assembly)}: " \
                                      f"[0..{len(self.configurations[assembly]) - 1}]" \
                                      f"{' init 0' if debug else ''};\n"
        return declaration_string

    def get_configuration_index(self):
        return self.configuration_index


# ilen() is written by Al Hoo, published on stackoverflow
# https://stackoverflow.com/questions/19182188
def ilen(iterable):
    return reduce(lambda sum, element: sum + 1, iterable, 0)


def get_assembly_name(graph, node):
    # get the name of the predecessor because this indicates the function of the assembly
    assembly_name = get_node_name(graph, list(graph.predecessors(node))[0])
    # an example name would be e.g. reaction_wheels_>=3
    return f"{assembly_name}_{get_node_name(graph, node).strip('>=')}"


def get_actions(graph,
                root_node,
                unique_graph_per_root_node,
                component_list_per_root_node,
                configuration_list_per_root_node,
                variable_handler,
                equipment_fault_probabilities,
                mode_costs,
                hidden_variable,
                include_configurations=False):
    action_strings = ""
    cost_strings = ""
    logging.debug(f"[{get_node_name(graph, root_node)}] "
                  f"{configuration_list_per_root_node=}, {component_list_per_root_node=}")
    for unique_graph, configuration, component_list in \
            zip(unique_graph_per_root_node,
                configuration_list_per_root_node,
                component_list_per_root_node):
        logging.debug(f"[{get_node_name(graph, root_node)}] "
                      f"Write action for {configuration=}")
        logging.debug(f"{component_list=}")
        # name
        action_string = f"  [{get_node_name(graph, root_node)}"
        configuration_numbers = []
        for assembly in configuration:
            conf_number = variable_handler.convert_to_prism_configuration(assembly,
                                                                          configuration[assembly])
            configuration_numbers.append(str(conf_number))
            action_string += f"_{conf_number}"
        variable_handler.add_configuration(root_node, '_'.join(configuration_numbers))
        action_string += "] "
        cost_strings += f"{action_string}true: {mode_costs[get_node_name(graph, root_node)]};\n"
        # guard
        guards = []
        # configuration
        if include_configurations:
            for assembly in configuration:
                conf_number = variable_handler.convert_to_prism_configuration(
                    assembly, configuration[assembly])
                guards.append(f"{get_assembly_name(graph, assembly)}={conf_number}")
        # logical guards
        logical_guards = [get_node_name(graph, node)
                          for node in find_leaf_nodes(graph, root_node=root_node, type='guards')]
        guards += [variable_handler.convert_to_prism_guard(guard) for guard in logical_guards]
        # block action if one of the utilized components is faulty
        if hidden_variable:
            all_equipment = list(equipment_fault_probabilities.keys())
            guards += [f"faulty_component!={all_equipment.index(component)}"
                       for component in component_list]
        if guards:
            action_string += " & ".join(guards)
        else:
            action_string += "true"
        action_string += "\n    -> "
        # probability of success
        fault_probability = get_fault_probability(unique_graph,
                                                  root_node,
                                                  equipment_fault_probabilities)
        # high numerical precision needed so PRISM will not complain about the sum of the
        # probabilities not being 1
        action_string += f"{to_precision(1-fault_probability, 30, notation='std')}: "
        # positive outcome, components
        positive_outcomes = []
        for component in component_list:
            positive_outcomes.append(f"({component}\'=0)")
        # positive outcome, variable changes
        positive_outcomes.append(variable_handler.convert_to_prism_outcome(get_effects(graph,
                                                                                       root_node)))
        # if there are no effects, we might add an empty string that needs to be filtered
        if ilen(filter(None, positive_outcomes)):
            action_string += " & ".join(filter(None, positive_outcomes))
        else:
            action_string += "true"
        action_string += "\n    + "
        # probability of failure
        action_string += f"{to_precision(fault_probability, 30, notation='std')}: "
        # negative outcome
        action_string += "true;\n"

        action_strings += action_string
    return action_strings, cost_strings


def get_cost(costs):
    cost_string = "rewards \"total_cost\"\n"
    for cost in costs:
        cost_string += cost
    cost_string += "endrewards\n"
    return cost_string


def get_label(graph, all_equipment, hidden_variable, component_to_be_isolated="any"):
    if component_to_be_isolated == "any":
        label_string = "label \"isolation_complete\" =\n      "
        sub_strings = []
        for faulty_component in all_equipment:
            component_strings = []
            for checked_component in all_equipment:
                component_strings.append(f"{checked_component}="
                                         f"{'1' if checked_component == faulty_component else '0'}")
            if hidden_variable:
                component_strings.append(f"faulty_component="
                                         f"{all_equipment.index(faulty_component)}")
            sub_strings.append(f"({' & '.join(component_strings)})")
        label_string += "\n    | ".join(sub_strings)
        label_string += ";"
    elif component_to_be_isolated == "all_available":
        label_string = f"label \"all_available\" = "
        label_string += " & ".join([f"{component}=0" for component in all_equipment])
        label_string += ";"
    else:
        label_string = f"label \"isolation_complete_{component_to_be_isolated}\" = "
        component_strings = []
        for component in all_equipment:
            component_strings.append(f"{component}="
                                     f"{'1' if component == component_to_be_isolated else '0'}")
        label_string += " & ".join(component_strings)
        label_string += ";"
    return label_string


def get_init(graph):
    init_string = "init\n  "
    component_strings = []
    for component in find_leaf_nodes(graph, type='components'):
        component_strings.append(f"{get_node_name(graph, component)}=1")
    init_string += " & ".join(component_strings)
    init_string += "\nendinit\n"
    return init_string


def generate_prism_model(base_directory,
                         filename,
                         graph,
                         all_equipment,
                         unique_graph_list,
                         component_lists,
                         configuration_list,
                         equipment_fault_probabilities,
                         mode_costs,
                         hidden_variable,
                         debug=False):
    trimmed_filename = os.path.split(filename)[-1].split('.')[0]
    work_directory = os.path.split(filename)[0]

    if debug:
        prism_filename = f"{os.path.join(work_directory, trimmed_filename)}_debug.prism"
    else:
        prism_filename = f"{os.path.join(work_directory, trimmed_filename)}.prism"
    logging.info(f"Generating prism model {prism_filename}")

    variable_handler = VariableHandler()
    # first generate the actions so the variable handler knows the number of prism states needed
    actions = []
    costs = []
    for root_node in unique_graph_list:
        logging.info(f"Generate actions for mode {get_node_name(graph, root_node)}")
        action, cost = get_actions(graph,
                                   root_node,
                                   unique_graph_list[root_node],
                                   component_lists[root_node],
                                   configuration_list[root_node],
                                   variable_handler,
                                   equipment_fault_probabilities,
                                   mode_costs,
                                   hidden_variable)
        actions.append(action)
        costs.append(cost)

    with open(prism_filename, 'w') as prism_file:
        # generate initialization
        print("mdp\n\nmodule sat\n", file=prism_file)
        # declare variables for components, logical states, and configurations
        print(
            variable_handler.convert_to_prism_declaration(graph,
                                                          all_equipment,
                                                          hidden_variable,
                                                          include_configurations=False,
                                                          debug=debug),
            file=prism_file)
        print("\n", file=prism_file)
        # actions
        for action in actions:
            print(action, file=prism_file)
        print("endmodule\n", file=prism_file)
        # rewards
        print(get_cost(costs), file=prism_file)
        # labels
        for component in all_equipment:
            print(get_label(graph, all_equipment, hidden_variable, component), file=prism_file)
        print(get_label(graph, all_equipment, hidden_variable, "any"), file=prism_file)
        print(get_label(graph, all_equipment, hidden_variable, "all_available"), file=prism_file)
        print("", file=prism_file)
        # init
        if not debug:
            print(get_init(graph), file=prism_file)
    logging.info(f"Generated prism model {prism_filename}")
    return variable_handler.get_configuration_index()


def generate_props(base_directory, filename, all_equipment):
    trimmed_filename = os.path.split(filename)[-1].split('.')[0]
    work_directory = os.path.split(filename)[0]
    with open(f"{os.path.join(work_directory, trimmed_filename)}.props", 'w') as props_file:
        for component in all_equipment:
            print(f"\"{component}\": filter(printall, Rmin=? "
                  f"[ F \"isolation_complete_{component}\" ], \"init\")",
                  file=props_file)
        print(f"\"any\": Rmin=? [ F \"isolation_complete\" ]", file=props_file)
        # print(f"\"sparse\": Pmax=? [F \"isolation_complete\"]", file=props_file)
        print(f"\"all\": filter(printall, Rmin=? [ F \"all_available\" ], \"init\")",
                  file=props_file)
    logging.info(f"Generated props file {os.path.join(work_directory, trimmed_filename)}.props")


def run_prism(base_directory, filename, all_equipment, components="all", engine="sparse"):
    if components == "all":
        isolability = {}
        best_isolation_cost = {}
        worst_isolation_cost = {}
        for component in all_equipment:
            logging.info(f"Check isolability for {component}")
            isolability[component], best_isolation_cost[component], worst_isolation_cost[component] \
                = run_prism_helper(base_directory,
                                   filename,
                                   component=component,
                                   json_export=True,
                                   engine=engine)
            logging.info(f"Result for {component}: {isolability[component]}, "
                         f"Cost: {best_isolation_cost[component]}")
            if worst_isolation_cost[component] != best_isolation_cost[component]:
                logging.info(f"Worst-case isolation cost for uninitialized system: "
                             f"{worst_isolation_cost[component]}")
    elif components == "any":
        logging.info(f"Check isolability for any component")
        isolability, best_isolation_cost, worst_isolation_cost \
            = run_prism_helper(base_directory,
                               filename,
                               component="any",
                               json_export=False,
                               engine=engine)
        logging.info(f"Result for any component: {isolability}, Cost: {best_isolation_cost}")
        if worst_isolation_cost != best_isolation_cost:
            logging.info(f"Worst-case isolation cost for uninitialized system: "
                         f"{worst_isolation_cost}")
    logging.info(f"Check for isolability done")
    return isolability, best_isolation_cost, worst_isolation_cost


def run_prism_helper(base_directory, filename, component="any", json_export=False, engine="sparse"):
    trimmed_filename = os.path.split(filename)[-1].split('.')[0]
    work_directory = os.path.split(filename)[0]
    prism_path = "prism/bin/prism"
    # Adjust the -javamaxmem argument to your PC's specs. Using ~60% by default
    mem_bytes = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')
    mem_max = f"{int(0.6 * mem_bytes / (1024. ** 3))}g"
    # mem_max = "8g"  # uncomment to manually set the maximum memory of PRISM

    args = f"{os.path.join(base_directory, prism_path)} " \
           f"{os.path.join(work_directory, trimmed_filename)}.prism " \
           f"{os.path.join(work_directory, trimmed_filename)}.props -prop {component} -{engine} " \
           f"-javamaxmem {mem_max}"
           # f"-exportstrat {trimmed_filename}_{component}_strategy.prism:type=actions " \
           # f"-exportstates {trimmed_filename}_{component}_strategy_states.prism"
    logging.info(f"Command: prism {trimmed_filename}.prism {trimmed_filename}.props "
                 f"-prop {component} -{engine} -javamaxmem {mem_max}")
    result = subprocess.run(args.split(" "), stdout=subprocess.PIPE, text=True)
    result_filename = (f"{os.path.join(work_directory, trimmed_filename)}_{component}_{engine}_"
                       f"result.txt")
    with open(result_filename, 'w') as result_file:
        result_file.write(result.stdout)
    prism_result = re.findall(r"Result: \[*([\d.Infity]+),*([\d.Infity]+)*\]*", result.stdout)
    if prism_result:
        logging.debug(f"{component} - {prism_result[0]}")
        if prism_result[0][0] == "Infinity":  # First result
            best_isolation_cost = float('inf')
            isolability = False
        else:
            best_isolation_cost = float(prism_result[0][0])
            isolability = True
        worst_isolation_cost = best_isolation_cost  # Second result
        if len(prism_result[0]) > 1:
            if not prism_result[0][1]:
                pass
            elif prism_result[0][1] == "Infinity":
                worst_isolation_cost = float('inf')
            else:
                worst_isolation_cost = float(prism_result[0][1])
    else:
        best_isolation_cost = float('inf')
        worst_isolation_cost = float('inf')
        isolability = False
        logging.error(f"{component} - Error!")
        logging.error(result.stdout)
    if json_export:
        initial_state_num = int(re.findall(r"(\d+) initial", result.stdout)[0])
        cost_per_state = re.findall(r"\d+:\S+=(\d+.\d*)", result.stdout)
        all_costs = [float(cost_string) for cost_string in cost_per_state]
        coverage = len(cost_per_state)/initial_state_num
        json_filename = (f"{os.path.join(work_directory, trimmed_filename)}_{component}_{engine}"
                         f".json")
        with open(json_filename, 'w') as json_file:
            json.dump({"component": component,
                       "initial_state_num": initial_state_num,
                       "all_costs": all_costs,
                       "coverage": coverage,
                       "isolability": isolability,
                       "best_isolation_cost": best_isolation_cost,
                       "worst_isolation_cost": worst_isolation_cost,
                       "engine": engine},
                      json_file)
        logging.debug(f"Isolation cost for {initial_state_num} initial states written to "
                      f"{json_filename}")
    return isolability, best_isolation_cost, worst_isolation_cost
