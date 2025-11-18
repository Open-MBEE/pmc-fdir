# Python built-in libraries
import logging

# project-specific libraries
from base import check_useful_action, find_successors


def find_useful_actions(statistics, state):
    a_list = []
    for a in statistics["all_actions"]:
        if check_useful_action(statistics, state, a):
            a_list.append(a)
    return a_list


def actions_to_add(statistics, state, available_actions):
    useful_actions = []
    successors1_useful_actions = []
    for action in available_actions:
        successor1, _ = find_successors(statistics, state, action)
        found = False
        for i in range(len(useful_actions)):
            if successor1 is successors1_useful_actions[i]:
                found = True
        if not found:
            useful_actions.append(action)
            successors1_useful_actions.append(successor1)
    return useful_actions


def add_state(mcts_graph, mcts_data, statistics, state):
    if mcts_data.get(state) is None:
        mcts_graph.add_node(state)
        mcts_data[state] = [0, 0]
        if statistics["available_actions"].get(state) is None:
            statistics["available_actions"][state] = find_useful_actions(statistics, state)


def add_edge(mcts_graph, node1, node2):
    mcts_graph.add_edge(node1, node2)


def mcts_expand(mcts_graph, mcts_stats, statistics, parameters, state):
    available_actions = statistics["available_actions"][state]
    actions = actions_to_add(statistics, state, available_actions)
    for action in actions:
        if check_useful_action(statistics, state, action):
            successor1, successor2 = find_successors(statistics, state, action)
            add_state(mcts_graph, mcts_stats, statistics, successor1)
            add_state(mcts_graph, mcts_stats, statistics, successor2)
            mcts_graph.add_edge(state, successor1)
            mcts_graph.add_edge(state, successor2)

    if parameters["debug"]:
        logging.debug("States added while expanding: " + ' '.join(map(str, mcts_graph.succ[state])))

    return len(mcts_graph.succ[state])
