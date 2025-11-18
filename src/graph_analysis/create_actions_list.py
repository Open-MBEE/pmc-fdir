# third-party libraries
import re


def create_actions_list(input_strategy):
    action_names = []
    with open(input_strategy) as source:
        lines = source.readlines()
        for line in lines:
            current_action = re.findall("[a-zA-Z_]+", line)[0]
            if current_action not in action_names:
                action_names.append(current_action)
    return action_names
