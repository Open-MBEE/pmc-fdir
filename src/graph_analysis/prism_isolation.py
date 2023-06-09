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
    return assembly_name + f"_{get_node_name(graph, node).strip('>=')}"


def get_action(G,
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
    logging.debug(f"[{get_node_name(G, root_node)}] "
                  f"{configuration_list_per_root_node=}, {component_list_per_root_node=}")
    for unique_graph, configuration, component_list in \
            zip(unique_graph_per_root_node,
                configuration_list_per_root_node,
                component_list_per_root_node):
        logging.debug(f"[{get_node_name(G, root_node)}] "
                      f"Write action for {configuration=}")
        logging.debug(f"{component_list=}")
        # name
        action_string = f"  [{get_node_name(G, root_node)}"
        configuration_numbers = []
        for assembly in configuration:
            configuration_numbers.append(
                str(variable_handler.convert_to_prism_configuration(assembly,
                                                                    configuration[assembly])))
        action_string += f"_{'_'.join(configuration_numbers)}"
        variable_handler.add_configuration(root_node, '_'.join(configuration_numbers))
        action_string += "] "
        cost_strings += action_string + f"true: {mode_costs[get_node_name(G, root_node)]};\n"
        # guard
        guards = []
        # configuration
        if include_configurations:
            for assembly in configuration:
                prism_configuration = variable_handler.convert_to_prism_configuration(
                    assembly, configuration[assembly])
                guards.append(f"{get_assembly_name(G, assembly)}="
                              f"{prism_configuration}")
        # logical guards
        logical_guards = [get_node_name(G, node)
                          for node in find_leaf_nodes(G, root_node=root_node, type='guards')]
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
        action_string += f"{to_precision(1-fault_probability, 30, notation='std')}: "
        # positive outcome, components
        positive_outcomes = []
        for component in component_list:
            positive_outcomes.append(f"({component}\'=0)")
        # positive outcome, variable changes
        positive_outcomes.append(variable_handler.convert_to_prism_outcome(get_effects(G,
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


def get_cost(G, costs):
    cost_string = "rewards \"total_cost\"\n"
    for cost in costs:
        cost_string += cost
    cost_string += "endrewards\n"
    return cost_string


def get_labels(G, all_equipment, hidden_variable, component_to_be_isolated="any"):
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
    else:
        label_string = f"label \"isolation_complete_{component_to_be_isolated}\" = "
        component_strings = []
        for component in all_equipment:
            component_strings.append(f"{component}="
                                     f"{'1' if component == component_to_be_isolated else '0'}")
        label_string += " & ".join(component_strings)
        label_string += ";"
    return label_string


def get_init_string(G):
    init_string = "init\n"
    component_strings = []
    for component in find_leaf_nodes(G, type='components'):
        component_strings.append(f"{get_node_name(G, component)}=1")
    init_string += " & ".join(component_strings)
    init_string += "\nendinit\n"
    return init_string


def generate_prism_model(base_directory,
                         filename,
                         G,
                         all_equipment,
                         unique_graph_list,
                         component_lists,
                         configuration_list,
                         equipment_fault_probabilities,
                         mode_costs,
                         hidden_variable,
                         debug=False):
    trimmed_filename = filename.split('/')[-1].split('.')[0]
    work_directory = base_directory + "temp/"

    if not os.path.exists(work_directory):
        os.makedirs(work_directory)

    if debug:
        prism_filename = f"{work_directory + trimmed_filename}_debug.prism"
    else:
        prism_filename = f"{work_directory + trimmed_filename}.prism"

    with open(prism_filename, 'w') as prism_file:
        variable_handler = VariableHandler()
        # first generate the actions so the variable handler knows the number of prism states needed
        actions = []
        costs = []
        for root_node in unique_graph_list:
            logging.info(f"Generate actions for mode {get_node_name(G, root_node)}")
            action, cost = get_action(G,
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
        # generate initialization
        print("mdp\n\nmodule sat\n", file=prism_file)
        # declare variables for components, logical states, and configurations
        print(
            variable_handler.convert_to_prism_declaration(G,
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
        print(get_cost(G, costs), file=prism_file)
        # labels
        for component in all_equipment:
            print(get_labels(G, all_equipment, hidden_variable, component), file=prism_file)
        print(get_labels(G, all_equipment, hidden_variable, "any"), file=prism_file)
        print("", file=prism_file)
        # init
        if not debug:
            print(get_init_string(G), file=prism_file)
    logging.info(f"Generated prism model {prism_filename}")
    return variable_handler.get_configuration_index()


def get_configuration_index(G,
                            unique_graph_list,
                            component_lists,
                            configuration_list,
                            equipment_fault_probabilities,
                            mode_costs):
    variable_handler = VariableHandler()
    for root_node in unique_graph_list:
        get_action(G,
                   root_node,
                   unique_graph_list[root_node],
                   component_lists[root_node],
                   configuration_list[root_node],
                   variable_handler,
                   equipment_fault_probabilities,
                   mode_costs,
                   hidden_variable=False)
    return variable_handler.get_configuration_index()


def generate_props(base_directory, filename, all_equipment):
    trimmed_filename = filename.split('/')[-1].split('.')[0]
    work_directory = base_directory + "temp/"
    with open(f"{work_directory + trimmed_filename}.props", 'w') as props_file:
        for component in all_equipment:
            print(f"\"{component}\": Rmin=? [ F \"isolation_complete_{component}\" ]",
                  file=props_file)
        print(f"\"any\": Rmin=? [ F \"isolation_complete\" ]", file=props_file)
        print(f"\"sparse\": Pmax=? [F \"isolation_complete\"]", file=props_file)
    logging.info(f"Generated props file {work_directory + trimmed_filename}.props")


def run_prism(base_directory, filename, all_equipment, components="all"):
    if components == "all":
        isolability = {}
        isolation_cost = {}
        for component in all_equipment:
            logging.info(f"Check isolability for {component}")
            isolability[component], isolation_cost[component] = run_prism_helper(base_directory,
                                                                                 filename,
                                                                                 component)
            logging.info(f"Result for {component}: {isolability[component]}, "
                         f"Cost: {isolation_cost[component]}")
    elif components == "any":
        logging.info(f"Check isolability for any component")
        isolability, isolation_cost = run_prism_helper(base_directory, filename, "any")
        logging.info(f"Result for any component: {isolability}, Cost: {isolation_cost}")
    logging.info(f"Check for isolability done")
    return isolability, isolation_cost


def run_prism_helper(base_directory, filename, component):
    trimmed_filename = filename.split('/')[-1].split('.')[0]
    work_directory = base_directory + "temp/"
    prism_path = "prism/bin/prism"
    pattern = r'Result: \S*'
    args = f"{base_directory + prism_path} {work_directory + trimmed_filename}.prism " \
           f"{work_directory + trimmed_filename}.props -prop {component} -explicit -javamaxmem 50g"
    logging.info(f"Command: prism {trimmed_filename}.prism {trimmed_filename}.props "
                 f"-prop {component} -explicit -javamaxmem 50g")
    result = subprocess.run(args.split(" "), stdout=subprocess.PIPE, text=True)
    with open(f"{work_directory + trimmed_filename}_{component}_result.txt", 'w') as result_file:
        result_file.write(result.stdout)
    prism_result = re.findall(pattern, result.stdout)
    if prism_result:
        logging.debug(f"{component} - {prism_result[0]}")
        first_number = re.findall("\\d+.\\d+", prism_result[0])
        if first_number:
            isolation_cost = float(first_number[0])
            isolability = True
        else:
            isolation_cost = float('inf')
            isolability = False
    else:
        isolation_cost = float('inf')
        isolability = False
        logging.error(f"{component} - Error!")
        logging.error(result.stdout)
    return isolability, isolation_cost
