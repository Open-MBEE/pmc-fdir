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

# built-in libraries
from graph_analysis.isolation_graph import MyDotWidget
from graph_analysis.prism_isolation import generate_prism_model, generate_props, run_prism
from graph_analysis.sensitivity_analysis import get_sensitivity_analysis, \
    get_uncertainty_propagation
from graph_analysis.graph_analysis import create_graph_list, get_layers, get_node_name, \
    find_root_nodes, find_leaf_nodes, check_isolability, check_recoverability, \
    get_root_node_names, get_fault_probability, find_isolated_nodes
from graph_analysis.generate_config_json import generate_config_json_isolation
from to_precision import to_precision
import xdot
import networkx as nx
import re
import logging
import os
import time
from datetime import datetime

# Gtk3
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Vte', '2.91')
from gi.repository import Gtk, Vte
from gi.repository import GLib


class MainWindow(Gtk.Window):
    do_not_prune = False

    def __init__(self):
        self.directory = os.getcwd() + "/../"  # path of the current dot file
        self.base_directory = os.getcwd() + "/../"  # path of the analysis tool
        self.filename = ""  # including path
        self.trimmed_filename = ""  # not including path and file extension
        self.filename_fault_probs = ""  # including path
        self.filename_mode_costs = ""  # including path
        self.filename_report = ""  # including path
        self.filename_initial_state = ""  # including path
        self.filename_sensitivity = ""  # including path
        self.graph = None

        self.analysis_done = False
        self.check_isolability_done = False
        self.export_isolation_done = False
        self.run_isolation_done = False
        self.check_recoverability_done = False
        self.export_recovery_done = False
        self.run_recovery_done = False

        self.isolable = []
        self.non_isolable = []
        self.missing_components = {}
        self.isolation_cost = {}

        self.recoverable = []
        self.non_recoverable = []
        self.single_string_components = {}
        self.recovery_cost = {}

        self.all_equipment = []
        self.unique_graph_list = {}
        self.component_lists = {}
        self.configuration_list = {}

        self.configuration_index = {}

        self.analysis_time = 0.0
        self.check_isolability_time = 0.0
        self.mcts_isolation_build_time = 0.0
        self.prism_isolation_time = 0.0
        self.check_recoverability_time = 0.0

        Gtk.Window.__init__(self, title="Analysis Tool")
        self.set_border_width(10)
        paned = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        paned.set_position(650)
        self.add(paned)

        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(10)
        grid.set_column_homogeneous(True)

        self.button_import = Gtk.Button(label="Import Graph")
        self.button_import.connect("clicked", self.on_open)
        grid.attach(self.button_import, 0, 2, 1, 1)
        self.button_analyze = Gtk.Button(label="Analyze Graph")
        self.button_analyze.set_sensitive(False)
        self.button_analyze.connect("clicked", self.on_analyze)
        grid.attach_next_to(self.button_analyze, self.button_import, Gtk.PositionType.RIGHT, 1, 1)

        self.graph_stats = Gtk.Label()
        self.graph_stats.set_xalign(0)  # left-aligned
        self.graph_stats.set_markup(
            f"<b><big>No graph selected</big></b>\n"
            + f" - ? modes\n"
            + f" - ? components\n"
            + f" - ? to ? configurations per mode\n")
        grid.attach(self.graph_stats, 0, 3, 2, 1)

        self.number_of_faults_label = Gtk.Label(label="Number of faults: ")
        grid.attach(self.number_of_faults_label, 0, 4, 1, 1)
        self.number_of_faults_entry = Gtk.Entry()
        self.number_of_faults_entry.set_text("1")
        self.number_of_faults_entry.connect("activate", self.reset_check_buttons)
        grid.attach_next_to(self.number_of_faults_entry, self.number_of_faults_label, 
                            Gtk.PositionType.RIGHT, 1, 1)

        self.children_to_keep_label = Gtk.Label(label="Actions to keep: ")
        grid.attach(self.children_to_keep_label, 0, 5, 1, 1)
        self.children_to_keep_entry = Gtk.Entry()
        self.children_to_keep_entry.set_text("2")
        grid.attach_next_to(self.children_to_keep_entry, self.children_to_keep_label, 
                            Gtk.PositionType.RIGHT, 1, 1)

        self.simulations_per_node_label = Gtk.Label(label="Simulations per node: ")
        grid.attach(self.simulations_per_node_label, 0, 6, 1, 1)
        self.simulations_per_node_entry = Gtk.Entry()
        self.simulations_per_node_entry.set_text("10")
        grid.attach_next_to(self.simulations_per_node_entry, self.simulations_per_node_label, 
                            Gtk.PositionType.RIGHT, 1, 1)

        self.button_check_isolation = Gtk.Button(label="Check Isolation")
        self.button_check_isolation.connect("clicked", self.check_isolation)
        self.button_check_isolation.set_sensitive(False)
        grid.attach(self.button_check_isolation, 0, 7, 1, 1)
        self.button_build_isolation = Gtk.Button(label="Build Isolation")
        self.button_build_isolation.set_sensitive(False)
        self.button_build_isolation.connect("clicked", self.build_prune_and_compress)
        grid.attach_next_to(self.button_build_isolation, self.button_check_isolation, 
                            Gtk.PositionType.RIGHT, 1, 1)
        self.button_export_isolation = Gtk.Button(label="Export PRISM")
        self.button_export_isolation.set_sensitive(False)
        self.button_export_isolation.connect("clicked", self.export_isolation)
        grid.attach(self.button_export_isolation, 0, 8, 1, 1)
        self.button_run_isolation = Gtk.Button(label="Run PRISM")
        self.button_run_isolation.set_sensitive(False)
        self.button_run_isolation.connect("clicked", self.run_isolation)
        grid.attach_next_to(self.button_run_isolation, self.button_export_isolation, 
                            Gtk.PositionType.RIGHT, 1, 1)
        self.isolation_info = Gtk.Label()
        self.isolation_info.set_xalign(0)  # left-aligned
        self.reset_isolation()
        grid.attach(self.isolation_info, 0, 9, 2, 1)

        self.button_check_recovery = Gtk.Button(label="Check Recovery")
        self.button_check_recovery.connect("clicked", self.check_recovery)
        self.button_check_recovery.set_sensitive(False)
        grid.attach(self.button_check_recovery, 0, 10, 1, 1)
        self.button_build_recovery = Gtk.Button(label="Build Recovery")
        self.button_build_recovery.connect("clicked", self.build_recovery)
        self.button_build_recovery.set_sensitive(False)
        grid.attach_next_to(self.button_build_recovery, self.button_check_recovery, 
                            Gtk.PositionType.RIGHT, 1, 1)
        self.recovery_info = Gtk.Label()
        self.recovery_info.set_xalign(0)  # left-aligned
        self.reset_recovery()
        grid.attach(self.recovery_info, 0, 11, 2, 1)

        self.notebook = Gtk.Notebook()
        # First page, xdot view of the graph
        self.page1 = xdot.DotWidget()
        self.notebook.append_page(child=self.page1, tab_label=Gtk.Label(label='Show graph'))

        # Second page, enter fault probabilities
        self.fault_probabilities_text = Gtk.TextView()
        self.fault_probabilities_text.set_editable(True)

        fault_probabilities_scroller = Gtk.ScrolledWindow()
        fault_probabilities_scroller.set_border_width(10)
        fault_probabilities_scroller.set_hexpand(True)
        fault_probabilities_scroller.set_vexpand(True)
        fault_probabilities_scroller.add(self.fault_probabilities_text)
        fault_probabilities_scroller_box = Gtk.Box()
        fault_probabilities_scroller_box.add(fault_probabilities_scroller)

        fault_probabilities_save_button = Gtk.Button(label="Save to File")
        fault_probabilities_save_button.connect('clicked', self.write_probabilities)
        self.page2 = Gtk.Grid()
        self.page2.set_border_width(10)
        self.page2.attach(fault_probabilities_save_button, 0, 0, 1, 1)
        self.page2.attach(fault_probabilities_scroller_box, 0, 1, 1, 10)
        self.notebook.append_page(child=self.page2, 
                                  tab_label=Gtk.Label(label='Fault Probabilities'))

        # Third page, enter mode costs
        self.mode_costs_text = Gtk.TextView()
        self.mode_costs_text.set_editable(True)
        mode_costs_scroller = Gtk.ScrolledWindow()
        mode_costs_scroller.set_border_width(10)
        mode_costs_scroller.set_hexpand(True)
        mode_costs_scroller.set_vexpand(True)
        mode_costs_scroller.add(self.mode_costs_text)
        mode_costs_scroller_box = Gtk.Box()
        mode_costs_scroller_box.add(mode_costs_scroller)

        mode_costs_save_button = Gtk.Button(label="Save to File")
        mode_costs_save_button.connect('clicked', self.write_costs)
        self.page3 = Gtk.Grid()
        self.page3.set_border_width(10)
        self.page3.attach(mode_costs_save_button, 0, 0, 1, 1)
        self.page3.attach(mode_costs_scroller_box, 0, 1, 1, 10)

        self.notebook.append_page(child=self.page3, tab_label=Gtk.Label(label='Mode Costs'))

        # Fourth page, show weakness report
        self.report_text = Gtk.TextView()
        self.report_text.set_editable(False)
        self.get_report_initial()
        report_scroller = Gtk.ScrolledWindow()
        report_scroller.set_border_width(10)
        report_scroller.set_hexpand(True)
        report_scroller.set_vexpand(True)
        report_scroller.add(self.report_text)
        report_scroller_box = Gtk.Box()
        report_scroller_box.add(report_scroller)

        report_save_button = Gtk.Button(label="Save to File")
        report_save_button.connect('clicked', self.write_report)
        self.page4 = Gtk.Grid()
        self.page4.set_border_width(10)
        self.page4.attach(report_save_button, 0, 0, 1, 1)
        self.page4.attach(report_scroller_box, 0, 1, 1, 10)
        self.notebook.append_page(child=self.page4, tab_label=Gtk.Label(label='Weakness Report'))

        # Fifth page, enter equipment state
        self.page5 = Gtk.Box()
        self.page5.set_border_width(10)

        self.grid = Gtk.Grid()
        self.grid.set_column_homogeneous(True)
        self.grid.set_row_homogeneous(True)
        self.page5.add(self.grid)

        self.states_liststore = Gtk.ListStore(str)
        self.states_liststore.append(['suspicious'])
        self.states_liststore.append(['available'])

        self.initialize_liststore(self.all_equipment)
        self.scrollable_treelist = self.initialize_treelist(self.states_liststore,
                                                            self.on_combo_changed)
        self.grid.attach(self.scrollable_treelist, 0, 0, 4, 9)

        # export button
        export_button = Gtk.Button(label="Export State")
        export_button.connect("clicked", self.export_action)
        self.grid.attach(export_button, 0, 9, 1, 1)

        # build isolation per state button
        build_isolation_per_state_button = Gtk.Button(label="Build via MCTS")
        build_isolation_per_state_button.connect("clicked", self.build_isolation_per_state)
        self.grid.attach_next_to(build_isolation_per_state_button, export_button,
                                 Gtk.PositionType.RIGHT, 1, 1)
        build_isolation_per_state_button_visualize = Gtk.Button(label="Visualize MCTS strategy")
        build_isolation_per_state_button_visualize.connect("clicked",
                                                           self.visualize_isolation_per_state)
        self.grid.attach_next_to(build_isolation_per_state_button_visualize,
                                 build_isolation_per_state_button,
                                 Gtk.PositionType.RIGHT, 1, 1)
        self.notebook.append_page(child=self.page5, tab_label=Gtk.Label(label='Enter State'))

        # Sixth page, xdot view of the isolation graph
        self.page6 = MyDotWidget()
        self.notebook.append_page(child=self.page6, tab_label=Gtk.Label(label='Isolation graph'))

        # Seventh page, sensitivity table

        self.sensitivity_text = Gtk.TextView()
        self.sensitivity_text.set_editable(False)
        self.sensitivity_text.set_monospace(True)
        self.get_sensitivity_initial()
        sensitivity_scroller = Gtk.ScrolledWindow()
        sensitivity_scroller.set_hexpand(True)
        sensitivity_scroller.set_vexpand(True)
        sensitivity_scroller.add(self.sensitivity_text)
        sensitivity_scroller_box = Gtk.Box()
        sensitivity_scroller_box.add(sensitivity_scroller)

        sensitivity_save_button = Gtk.Button(label="Save to File")
        sensitivity_save_button.connect('clicked', self.write_sensitivity)
        self.page7 = Gtk.Grid()
        self.page7.set_border_width(10)
        self.page7.attach(sensitivity_save_button, 0, 0, 1, 1)
        self.page7.attach(sensitivity_scroller_box, 0, 1, 1, 10)
        self.notebook.append_page(child=self.page7, tab_label=Gtk.Label(label='Sensitivity'))

        grid.attach(self.notebook, 2, 1, 5, 12)
        paned.add1(grid)

        # Terminal view
        self.terminal = Vte.Terminal()
        self.pty = Vte.Pty.new_sync(Vte.PtyFlags.DEFAULT)
        self.terminal.set_pty(self.pty)
        self.pty.spawn_async(
            self.base_directory,
            ["/bin/sh"],
            None,
            GLib.SpawnFlags.DO_NOT_REAP_CHILD,
            None,
            None,
            -1,
            None,
            self.ready
        )
        self.terminal.set_cursor_blink_mode(Vte.CursorBlinkMode.OFF)

        # a scroll window is required for the terminal
        self.scroller = Gtk.ScrolledWindow()
        self.scroller.set_hexpand(True)
        self.scroller.set_vexpand(True)
        self.scroller.add(self.terminal)

        paned.add2(self.scroller)

    def clear_variables(self):
        self.isolable = []
        self.non_isolable = []
        self.missing_components = {}
        self.isolation_cost = {}

        self.recoverable = []
        self.non_recoverable = []
        self.single_string_components = {}
        self.recovery_cost = {}

        self.graph = None
        self.all_equipment = []
        self.unique_graph_list = {}
        self.component_lists = {}
        self.configuration_list = {}

        self.configuration_index = {}

        self.analysis_time = 0.0
        self.check_isolability_time = 0.0
        self.mcts_isolation_build_time = 0.0
        self.prism_isolation_time = 0.0
        self.check_recoverability_time = 0.0

        self.page6.set_graph_and_all_equipment(self.graph, self.all_equipment)
        self.page6.set_leaf_name_and_configuration_list(self.component_lists,
                                                        self.configuration_list)

    def on_open(self, action):
        chooser = Gtk.FileChooserDialog(parent=self,
                                        title="Open Architecture as .dot Graph",
                                        action=Gtk.FileChooserAction.OPEN)
        chooser.add_buttons(Gtk.STOCK_CANCEL,
                            Gtk.ResponseType.CANCEL,
                            Gtk.STOCK_OPEN,
                            Gtk.ResponseType.OK)
        chooser.set_default_response(Gtk.ResponseType.OK)
        chooser.set_current_folder(self.directory)
        filter = Gtk.FileFilter()
        filter.set_name(".dot files")
        # filter.add_pattern("*.gv")
        filter.add_pattern("*.dot")
        chooser.add_filter(filter)
        filter = Gtk.FileFilter()
        filter.set_name("All files")
        filter.add_pattern("*")
        chooser.add_filter(filter)
        if chooser.run() == Gtk.ResponseType.OK:
            self.filename = chooser.get_filename()
            self.trimmed_filename = self.filename.split('/')[-1].split(".")[0]
            self.directory = chooser.get_current_folder()
            chooser.destroy()
            self.filename_fault_probs = self.filename.split(".")[0] + "_fault_probabilities.txt"
            self.filename_mode_costs = self.filename.split(".")[0] + "_mode_costs.txt"
            self.filename_report = self.filename.split(".")[0] + "_report.txt"
            self.filename_initial_state = self.filename.split(".")[0] + "_initial_state.txt"
            self.filename_sensitivity = self.filename.split(".")[0] + "_sensitivity.txt"

            # Reset variables
            self.clear_variables()
            self.analysis_done = False
            self.check_isolability_done = False
            self.export_isolation_done = False
            self.check_recoverability_done = False
            self.export_recovery_done = False

            # Reset buttons
            self.button_analyze.set_sensitive(True)
            self.button_check_isolation.set_sensitive(False)
            self.button_build_isolation.set_sensitive(False)
            self.button_export_isolation.set_sensitive(False)
            self.button_run_isolation.set_sensitive(False)
            self.button_check_recovery.set_sensitive(False)
            self.button_build_recovery.set_sensitive(False)

            self.reset_isolation()
            self.reset_recovery()
            self.get_report_initial()
            self.open_file(self.filename, self.page1)
            self.page1.zoom_to_fit()
            self.get_graph_stats_filename(self.filename)
            self.import_graph(self.filename)
            self.get_graph_stats_initial(self.filename, self.graph)
            self.read_probabilities()
            self.read_costs()
            self.update_enter_state(self.all_equipment)
        else:
            chooser.destroy()

    def open_file(self, filename, page):
        try:
            fp = open(filename, 'rb')
            page.set_dotcode(fp.read(), filename)
            fp.close()
        except IOError as ex:
            self.error_dialog(str(ex))

    def import_graph(self, filename):
        logging.info("Reading from graph " + filename)

        multi_digraph = nx.nx_agraph.read_dot(filename)
        self.graph = nx.DiGraph(multi_digraph)
        if len(find_isolated_nodes(self.graph)) > 0:
            logging.warning(f"Found {len(find_isolated_nodes(self.graph))} isolated nodes: "
                            f"{find_isolated_nodes(self.graph)}. Removing them.")
            for node in find_isolated_nodes(self.graph):
                self.graph.remove_node(node)
        else:
            logging.info(f"No isolated nodes found")

        layers = get_layers(self.graph)
        self.all_equipment = sorted([get_node_name(self.graph, node)
                                     for node in find_leaf_nodes(self.graph,
                                                                 layers,
                                                                 type='components')])
        self.page6.set_graph_and_all_equipment(self.graph, self.all_equipment)
        logging.info(f"All equipment: "
                     f"{[(i, component) for i, component in enumerate(self.all_equipment)]}")

    def get_graph_stats_filename(self, filename):
        self.graph_stats.set_markup(
            f"<b><big>Selected graph: {filename.split('/')[-1]}</big></b>\n"
            + f" - ? modes\n"
            + f" - ? components\n"
            + f" - ? to ? configurations per mode\n")

    def get_graph_stats_initial(self, filename, G):
        layers = get_layers(G)
        self.graph_stats.set_markup(
            f"<b><big>Selected graph: {filename.split('/')[-1]}</big></b>\n"
            + f" - {len(find_root_nodes(G))} modes\n"
            + f" - {len(find_leaf_nodes(G, layers))} components\n"
            + f" - ? to ? configurations per mode\n")

    def get_graph_stats(self, filename, G):
        layers = get_layers(G)
        num_configs = [len(self.component_lists[this_list]) for this_list in self.component_lists]
        self.graph_stats.set_markup(
            f"<b><big>Selected graph: {filename.split('/')[-1]}</big></b>\n"
            + f" - {len(find_root_nodes(G))} modes\n"
            + f" - {len(find_leaf_nodes(G, layers))} components\n"
            + f" - {min(num_configs)} to {max(num_configs)} configurations per mode\n")

    def on_analyze(self, action):
        self.button_analyze.set_sensitive(False)
        start_time_analysis = time.time()
        self.analyze_graph(self.graph)
        self.analysis_time = time.time() - start_time_analysis
        self.get_graph_stats(self.filename, self.graph)
        self.get_report()

    def analyze_graph(self, G):
        logging.info("Analyze the configuration graph")
        threading = True
        self.unique_graph_list, unique_node_lists, self.component_lists, \
            self.configuration_list, configuration_space = \
            create_graph_list(G, threading)
        self.page6.set_leaf_name_and_configuration_list(self.component_lists,
                                                        self.configuration_list)

        logging.info(f"{self.all_equipment=}")

        # set button states
        self.button_check_isolation.set_sensitive(True)
        self.button_build_isolation.set_sensitive(True)
        self.button_export_isolation.set_sensitive(True)
        self.button_run_isolation.set_sensitive(True)
        self.button_check_recovery.set_sensitive(True)
        self.button_build_recovery.set_sensitive(True)
        self.analysis_done = True
        self.get_report()
        self.get_sensitivity()

    def reset_check_buttons(self, widget):
        self.check_isolability_done = False
        self.export_isolation_done = False
        self.run_isolation_done = False
        self.check_recoverability_done = False
        if self.analysis_done:
            self.button_check_isolation.set_sensitive(True)
            self.button_export_isolation.set_sensitive(True)
            self.button_run_isolation.set_sensitive(True)
            self.button_check_recovery.set_sensitive(True)

    def reset_isolation(self):
        self.isolation_info.set_markup("<b><big>Isolation info</big></b>\n"
                                       + " - ? components can be isolated\n"
                                       + " - ? components cannot be isolated\n")

    def check_isolation(self, button):
        self.button_check_isolation.set_sensitive(False)
        logging.info("Checking isolation")
        start_time_check_isolability = time.time()
        self.isolable, self.non_isolable, self.missing_components = \
            check_isolability(self.all_equipment,
                              self.component_lists,
                              int(self.number_of_faults_entry.get_text()))
        self.check_isolability_time = time.time() - start_time_check_isolability
        if int(self.number_of_faults_entry.get_text()) > 1:
            component_text = "fault combinations"
        else:
            component_text = "components"
        percentage = to_precision(100 * (len(self.isolable) /
                                         (len(self.isolable) + len(self.non_isolable))),
                                  3,
                                  notation='std')
        self.isolation_info.set_markup(
            f"<b><big>Isolation info</big></b>\n"
            + f" - {len(self.isolable)} {component_text} ({percentage}%) can be isolated\n"
            + f" - {len(self.non_isolable)} {component_text} cannot be isolated\n")
        self.check_isolability_done = True
        self.get_report()

    def build_prune_and_compress(self, button):
        self.button_build_isolation.set_sensitive(False)
        start_time_mcts_isolation_build = time.time()
        self.prune_graph(button)
        self.feed_input(f'\n')
        generate_config_json_isolation(
            self.all_equipment,
            self.base_directory + "temp/",
            self.base_directory + "temp/prism_strategy_config.json")
        strategy_name = 'temp/prism_strategy.prism'
        self.feed_input(f'dtcontrol --input {strategy_name} --use-preset avg --benchmark-file '
                        f'benchmark.json --rerun\n')
        self.mcts_isolation_build_time = time.time() - start_time_mcts_isolation_build

    def prune_graph(self, button):
        self.feed_input(f'python3 src/mcts.py '
                        f'--modecosts {self.filename_mode_costs} '
                        f'--equipfailprobs {self.filename_fault_probs} '
                        f'--successorstokeep {self.children_to_keep_entry.get_text()} '
                        f'--simulationsize {self.simulations_per_node_entry.get_text()} '
                        f'{self.filename}\n')

    def ready(self, pty, task):
        pass

    def feed_input(self, text):
        text = bytearray(text, "utf-8")
        self.terminal.feed_child(text)

    def export_isolation(self, button):
        self.button_export_isolation.set_sensitive(False)
        self.configuration_index = generate_prism_model(
            self.base_directory,
            self.base_directory + "temp/" + self.trimmed_filename + "_isolation_model.prism",
            self.graph,
            self.all_equipment,
            self.unique_graph_list,
            self.component_lists,
            self.configuration_list,
            self.get_probabilities(probabilities_type="mean"),
            self.get_costs(),
            hidden_variable=False,
            debug=False)

        generate_props(
            self.base_directory,
            self.base_directory + "temp/" + self.trimmed_filename + "_isolation_model.prism",
            self.all_equipment)
        self.export_isolation_done = True

    def run_isolation(self, button):
        self.button_run_isolation.set_sensitive(False)
        start_time_prism_isolation = time.time()
        isolability, self.isolation_cost = run_prism(
            self.base_directory,
            self.base_directory + "temp/" + self.trimmed_filename + "_isolation_model.prism",
            self.all_equipment,
            components="all")
        self.prism_isolation_time = time.time() - start_time_prism_isolation
        self.run_isolation_done = True
        self.get_report()

    def reset_recovery(self):
        self.recovery_info.set_markup("<b><big>Recovery info</big></b>\n"
                                      + " - ? modes are fault-tolerant\n"
                                      + " - ? modes are not fault-tolerant\n")

    def check_recovery(self, button):
        self.button_check_recovery.set_sensitive(False)
        logging.info("Checking recovery")
        start_time_check_recoverability = time.time()
        fault_number = int(self.number_of_faults_entry.get_text())
        self.recoverable, self.non_recoverable, self.single_string_components = \
            check_recoverability(self.graph,
                                 self.all_equipment,
                                 self.component_lists,
                                 fault_number)
        self.check_recoverability_time = time.time() - start_time_check_recoverability
        percentage = to_precision(100 * (len(self.recoverable) / len(self.component_lists)),
                                  3,
                                  notation='std')
        self.recovery_info.set_markup(
            f"<b><big>Recovery info</big></b>\n"
            f" - {len(self.recoverable)} modes ({percentage}%) are {fault_number}-fault-tolerant\n"
            f" - {len(self.non_recoverable)} modes are not {fault_number}-fault-tolerant\n")
        self.check_recoverability_done = True
        self.get_report()

    def build_recovery(self, button):
        self.button_build_recovery.set_sensitive(False)
        self.feed_input(f"python3 src/build_recovery.py {self.base_directory} {self.directory} "
                        f"{self.filename}\n")

    def read_probabilities(self):
        try:
            with open(self.filename_fault_probs, 'r') as file_ref:
                file_content = file_ref.read()
                logging.info(f"Read fault probabilities from {self.filename_fault_probs}")
        except FileNotFoundError:
            file_content = self.generate_fault_probs()
            logging.warning(f"File {self.filename_fault_probs} doesn't exist yet")
        finally:
            self.fault_probabilities_text.get_buffer().set_text(file_content, len(file_content))

    def generate_fault_probs(self):
        string_list = [component + ": 0.01" for component in self.all_equipment]
        logging.info(f"Generated fault probabilites template: {', '.join(string_list)}")
        return ",\n".join(string_list)

    def write_probabilities(self, button):
        with open(self.filename_fault_probs, 'w') as file_ref:
            file_ref.write(self.fault_probabilities_text.get_buffer().get_text(
                self.fault_probabilities_text.get_buffer().get_start_iter(),
                self.fault_probabilities_text.get_buffer().get_end_iter(), False))

    def check_all_probabilities_present(self):
        all_probabilities_present = True
        probabilities_text = self.fault_probabilities_text.get_buffer().get_text(
            self.fault_probabilities_text.get_buffer().get_start_iter(),
            self.fault_probabilities_text.get_buffer().get_end_iter(), False)

        for line in probabilities_text.split("\n"):
            item = re.search(r"([a-zA-Z0-9_-]*)\s*:"  # name
                             r"\s*([0-9.]*),?\s*"  # mean fault probability
                             r"\[?([0-9.]*),?\s*"  # lower bound of uncertainty interval
                             r"([0-9.]*)\]?",  # upper bound of uncertainty interval
                             line)
            if item:
                if item.group(1) and item.group(2) and not (item.group(3) and item.group(4)):
                    all_probabilities_present = False

        return all_probabilities_present

    def get_probabilities(self, probabilities_type="mean"):
        probabilities_text = self.fault_probabilities_text.get_buffer().get_text(
            self.fault_probabilities_text.get_buffer().get_start_iter(),
            self.fault_probabilities_text.get_buffer().get_end_iter(), False)

        mean_probabilities = {}
        # logging.info(probabilities_text.split('\n'))
        if probabilities_type == "all":
            lower_bound = {}
            upper_bound = {}
        for line in probabilities_text.split("\n"):
            item = re.search(r"([a-zA-Z0-9_-]*)\s*:"  # name
                             r"\s*([0-9.]*),?\s*"  # mean fault probability
                             r"\[?([0-9.]*),?\s*"  # lower bound of uncertainty interval
                             r"([0-9.]*)\]?",  # upper bound of uncertainty interval
                             line)
            if item:
                if item.group(1) and item.group(2):
                    mean_probabilities[item.group(1)] = float(item.group(2))
                if probabilities_type == "all" and item.group(3) and item.group(4):
                    lower_bound[item.group(1)] = float(item.group(3))
                    upper_bound[item.group(1)] = float(item.group(4))
        if probabilities_type == "all":
            return mean_probabilities, lower_bound, upper_bound
        else:
            return mean_probabilities

    def read_costs(self):
        try:
            with open(self.filename_mode_costs, 'r') as file_ref:
                file_content = file_ref.read()
                logging.info(f"Read mode costs from {self.filename_mode_costs}")
        except FileNotFoundError:
            file_content = self.generate_mode_costs()
            logging.warning(f"File {self.filename_mode_costs} doesn't exist yet")
        finally:
            self.mode_costs_text.get_buffer().set_text(file_content, len(file_content))

    def get_costs(self):
        mode_costs = {}
        costs_text = self.mode_costs_text.get_buffer().get_text(
            self.mode_costs_text.get_buffer().get_start_iter(),
            self.mode_costs_text.get_buffer().get_end_iter(), False)
        for line in costs_text.split("\n"):
            item = re.search(r"([a-zA-Z0-9_-]*)\s*:"  # name
                             r"\s*([0-9.]*),?\s*",  # cost
                             line)
            if item:
                if item.group(1) and item.group(2):
                    mode_costs[item.group(1)] = item.group(2)
        return mode_costs

    def generate_mode_costs(self):
        string_list = [mode + ": 100.0" for mode in get_root_node_names(self.graph)]
        logging.info(f"Generated mode costs template: {', '.join(string_list)}")
        return ",\n".join(string_list)

    def write_costs(self, button):
        with open(self.filename_mode_costs, 'w') as file_ref:
            file_ref.write(self.mode_costs_text.get_buffer().get_text(
                self.mode_costs_text.get_buffer().get_start_iter(),
                self.mode_costs_text.get_buffer().get_end_iter(), False))

    def get_report_initial(self):
        # Clear textview
        self.report_text.get_buffer().delete(
            self.report_text.get_buffer().get_start_iter(),
            self.report_text.get_buffer().get_end_iter())

        message = "Run Analyze Graph, Check Isolation, and Check Recovery to generate the report"
        end_iter = self.report_text.get_buffer().get_end_iter()
        self.report_text.get_buffer().insert_markup(end_iter, message, -1)

    def get_report(self):
        # Clear textview
        self.report_text.get_buffer().delete(
            self.report_text.get_buffer().get_start_iter(),
            self.report_text.get_buffer().get_end_iter())

        message = "<b><big>Weakness Report</big></b>\n\n"
        if self.check_isolability_done and self.check_recoverability_done:
            message += f"Isolation info\n"
            if int(self.number_of_faults_entry.get_text()) > 1:
                component_text = "fault combinations"
            else:
                component_text = "components"
            percentage = to_precision(100 * (len(self.isolable) /
                                             (len(self.isolable) + len(self.non_isolable))),
                                      3,
                                      notation='std')
            message += f"\t {len(self.isolable)} {component_text} ({percentage}%) can be isolated\n"
            message += f"\t {len(self.non_isolable)} {component_text} cannot be isolated\n\n"

            fault_number = int(self.number_of_faults_entry.get_text())
            percentage = to_precision(100 * (len(self.recoverable) / len(self.component_lists)),
                                      3,
                                      notation='std')
            message += "Recovery info\n"
            message += f"\t {len(self.recoverable)} modes ({percentage}%) are "
            message += f"{fault_number}-fault-tolerant\n"
            message += f"\t {len(self.non_recoverable)} modes are not {fault_number}-fault-tolerant"
            message += "\n\n"

            if not self.non_isolable and not self.non_recoverable:
                message += f"The graph {self.filename.split('/')[-1]} shows no weaknesses.\n"
            else:
                message += f"The graph {self.filename.split('/')[-1]} shows these weaknesses:\n"
                for components in self.missing_components:
                    if len(components) == 1:
                        component_text = f"A component fault in {components[0]}"
                    else:
                        component_text = f"The fault combination {components}"
                    message += f"\t{component_text} is not isolable because the components "
                    message += f"{', '.join(self.missing_components[components])} "
                    plural = True if len(self.missing_components[components]) > 1 else False
                    message += f"{'are' if plural else 'is'} not independently accessible\n"
                message += "\n"
                for mode in self.non_recoverable:
                    for fault_number in range(1, fault_number + 1):
                        filtered_combinations = filter(lambda x: len(x) == fault_number,
                                                       self.single_string_components[mode])
                        # A filter object is like a generator so we can only iterate over it once
                        list_comb = list(filtered_combinations)
                        if list_comb:
                            message += f"\tMode {get_node_name(self.graph, mode)} is not "
                            message += f"{fault_number}-fault tolerant for "
                            if fault_number == 1:
                                message += f"{'a ' if len(list_comb) == 1 else ''}fault"
                                message += f"{'s' if len(list_comb) > 1 else ''} in "
                                message += f"{', '.join([', '.join(item) for item in list_comb])}\n"
                                logging.debug(f"Mode {get_node_name(self.graph, mode)} is not "
                                              f"{fault_number}-fault tolerant for "
                                              f"{'a ' if len(list_comb) == 1 else ''}fault"
                                              f"{'s' if len(list_comb) > 1 else ''} in "
                                              f"{', '.join([', '.join(itm) for itm in list_comb])}")
                            else:
                                message += f"the fault combination"
                                message += f"{'s' if len(list_comb) > 1 else ''} "
                                message += f"{', '.join([repr(item) for item in list_comb])}\n"
                                logging.debug(f"Mode {get_node_name(self.graph, mode)} is not "
                                              f"{fault_number}-fault tolerant for the fault "
                                              f"combination{'s' if len(list_comb) > 1 else ''} "
                                              f"{', '.join([repr(item) for item in list_comb])}")
                message += "\n"
            if self.isolable or self.recoverable:
                message += "\nThe following components and modes show no weaknesses:\n"
                for components in self.isolable:
                    if len(components) == 1:
                        component_text = f"Component {components[0]}"
                    else:
                        component_text = f"The fault combination {components}"
                    message += f"\t{component_text} is isolable\n"
                for mode in self.recoverable:
                    message += f"\tMode {get_node_name(self.graph, mode)} is " \
                               f"{self.number_of_faults_entry.get_text()}-fault tolerant\n"
                message += "\n"
        else:
            message += "Run Check Isolation and Check Recovery to include an assessment on the " \
                       "isolability of the components and recoverability of the modes.\n"

        if self.analysis_done:
            message += f"Assuming the component fault probabilities defined in " \
                       f"‘{self.filename_fault_probs.split('/')[-1]}’, the modes have these " \
                       f"fault probabilities:\n"

            fault_probs = {mode: get_fault_probability(self.graph, mode,
                                                       self.get_probabilities(
                                                           probabilities_type="mean"))
                           for mode in find_root_nodes(self.graph)}
            fault_probs_sorted = dict(sorted(fault_probs.items(),
                                             key=lambda item: item[1],
                                             reverse=True))
            for mode in fault_probs_sorted:
                message += f"\tThe fault probability for mode {get_node_name(self.graph, mode)} " \
                           f"is {to_precision(100 * fault_probs_sorted[mode], 3)} %\n"
            message += "\n"

        if self.run_isolation_done:
            message += f"Cost for the isolation of the components:\n"
            for component, cost in sorted(self.isolation_cost.items(),
                                          key=lambda item: item[1],
                                          reverse=True):
                if cost < float('inf'):
                    message += f"\tThe cost for isolating {component} is {to_precision(cost, 4)}\n"
            for component, cost in self.isolation_cost.items():
                if cost == float('inf'):
                    message += f"\t{component} is not isolable. No cost can be calculated\n"
        else:
            message += f"Execute 'Export PRISM' and 'Run PRISM' to get the isolation cost.\n"
        message += "\n"

        # Execution time log
        if self.analysis_time:
            message += f"Analyzing the graph took " \
                       f"{to_precision(self.analysis_time, 3, notation='std')} seconds.\n"
        if self.check_isolability_time:
            message += f"Checking isolability took " \
                       f"{to_precision(self.check_isolability_time, 3, notation='std')} seconds.\n"
        if self.mcts_isolation_build_time:
            message += f"Building MCTS isolation took " \
                       f"{to_precision(self.mcts_isolation_build_time, 3, notation='std')} " \
                       f"seconds.\n"
        if self.prism_isolation_time:
            message += f"Checking isolation cost took " \
                       f"{to_precision(self.prism_isolation_time, 3, notation='std')} seconds.\n"
        if self.check_recoverability_time:
            message += f"Checking recoverability took " \
                       f"{to_precision(self.check_recoverability_time, 3, notation='std')} " \
                       f"seconds.\n"

        message += f"\nThis report was generated on " \
                   f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.\n"

        end_iter = self.report_text.get_buffer().get_end_iter()
        self.report_text.get_buffer().insert_markup(end_iter, message, -1)

    def write_report(self, button):
        with open(self.filename_report, 'w') as file_ref:
            file_ref.write(self.report_text.get_buffer().get_text(
                self.report_text.get_buffer().get_start_iter(),
                self.report_text.get_buffer().get_end_iter(), False))

    def initialize_liststore(self, all_equipment):
        # Creating the ListStore model
        self.equipment_liststore = Gtk.ListStore(str, str)
        self.update_enter_state(all_equipment)

    def update_enter_state(self, all_equipment):
        self.equipment_liststore.clear()
        for equipment in all_equipment:
            self.equipment_liststore.append([equipment, "suspicious"])

    def initialize_treelist(self, states_liststore, change_callback):
        # Creating the treeview and adding the columns
        treeview = Gtk.TreeView(model=self.equipment_liststore)
        for i, column_title in enumerate(["Equipment"]):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(column_title, renderer, text=i)
            treeview.append_column(column)

        cellrenderercombo = Gtk.CellRendererCombo(model=states_liststore)
        cellrenderercombo.set_property("editable", True)
        cellrenderercombo.set_property("has-entry", False)
        cellrenderercombo.set_property('sensitive', True)
        cellrenderercombo.set_property('mode', Gtk.CellRendererMode.EDITABLE)
        cellrenderercombo.set_property('height', 25)
        cellrenderercombo.set_property("model", states_liststore)
        cellrenderercombo.set_property("text_column", 0)
        cellrenderercombo.connect("changed", change_callback)
        column = Gtk.TreeViewColumn("State", cellrenderercombo)
        treeview.append_column(column)
        column.add_attribute(cellrenderercombo, "text", 1)

        # setting up the layout, putting the treeview in a scrollwindow, and the buttons in a row
        scrollable_treelist = Gtk.ScrolledWindow()
        scrollable_treelist.set_vexpand(True)
        scrollable_treelist.add(treeview)
        return scrollable_treelist

    def on_combo_changed(self, cellrenderercombo, treepath, treeiter):
        self.equipment_liststore[treepath][1] = self.states_liststore[treeiter][0]

    def export_action(self, widget):
        equipment_state = [self.equipment_liststore[state][1]
                           for state in range(len(self.all_equipment))]
        for i in range(len(equipment_state)):
            if equipment_state[i] == "available":
                equipment_state[i] = 0
            elif equipment_state[i] == "suspicious":
                equipment_state[i] = 1
        with open(self.filename_initial_state, 'w') as file_ref:
            file_ref.write(str(equipment_state))

    def get_initial_state(self):
        initial_state = {component: self.equipment_liststore[index][1] for index, component in
                         enumerate(self.all_equipment)}
        return initial_state

    def build_isolation_per_state(self, button):
        self.prune_graph_with_initial_state(button)
        self.feed_input(f'\n')

    def prune_graph_with_initial_state(self, button):
        self.feed_input(f'python3 src/mcts.py '
                        f'--modecosts {self.filename_mode_costs} '
                        f'--equipfailprobs {self.filename_fault_probs} '
                        f'--successorstokeep {self.children_to_keep_entry.get_text()} '
                        f'--simulationsize {self.simulations_per_node_entry.get_text()} '
                        f'--initialstatefile {self.filename_initial_state} '
                        f'{self.filename}\n')

        self.feed_input(f'\n')

    def visualize_isolation_per_state(self, button):
        graph_filename = self.base_directory + "temp/mcts_graph.dot"
        self.open_file(graph_filename, self.page6)
        self.page6.zoom_to_fit()
        self.notebook.set_current_page(5)

    def get_sensitivity_initial(self):
        # Clear textview
        self.sensitivity_text.get_buffer().delete(
            self.sensitivity_text.get_buffer().get_start_iter(),
            self.sensitivity_text.get_buffer().get_end_iter())

        message = "Run Analyze Graph to retrieve the sensitivity analysis"
        end_iter = self.sensitivity_text.get_buffer().get_end_iter()
        self.sensitivity_text.get_buffer().insert_markup(end_iter, message, -1)

    def get_sensitivity(self):
        # Clear textview
        self.sensitivity_text.get_buffer().delete(
            self.sensitivity_text.get_buffer().get_start_iter(),
            self.sensitivity_text.get_buffer().get_end_iter())

        message = get_sensitivity_analysis(self.graph,
                                           self.get_probabilities(probabilities_type="mean"),
                                           self.get_costs())
        message += "\n\n\n"
        if self.check_all_probabilities_present():
            equipment_fault_probabilities, \
                equipment_fault_probabilities_lower_bound, \
                equipment_fault_probabilities_upper_bound = \
                self.get_probabilities(probabilities_type="all")
            message += get_uncertainty_propagation(self.graph,
                                                   equipment_fault_probabilities,
                                                   equipment_fault_probabilities_lower_bound,
                                                   equipment_fault_probabilities_upper_bound,
                                                   self.get_costs())
        else:
            message += "Append an uncertainty interval to every fault probability to analyze " \
                       "fault propagation."

        end_iter = self.sensitivity_text.get_buffer().get_end_iter()
        self.sensitivity_text.get_buffer().insert_markup(end_iter, message, -1)

    def write_sensitivity(self, button):
        with open(self.filename_sensitivity, 'w') as file_ref:
            file_ref.write(self.sensitivity_text.get_buffer().get_text(
                self.sensitivity_text.get_buffer().get_start_iter(),
                self.sensitivity_text.get_buffer().get_end_iter(), False))


def main():
    logging.basicConfig(format="[%(levelname)s] %(funcName)s: %(message)s")
    logging.getLogger().setLevel(logging.INFO)

    window = MainWindow()
    window.set_default_size(1500, 900)
    window.connect('delete-event', Gtk.main_quit)
    window.set_icon_name("pmc-fdir")
    window.show_all()

    Gtk.main()


if __name__ == '__main__':
    main()
