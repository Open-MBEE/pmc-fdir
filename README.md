# pmc-fdir
Probabilistic Model Checking for FDIR

![gui screenshot](gui_screenshot.png)

This app can analyze the functional decomposition of graphs in DOT format and provides the following outputs:
  * Are all components isolable for n faults?
  * Are all modes n-fault-tolerant?
  * Create a strategy for isolation with Monte Carlo tree search
  * Visualize the decision tree of the isolation strategy from arbitrary initial states
  * Convert the isolation problem to a Markov decision process in PRISM format
  * Generate code and decision trees for the isolation problem
  * Generate code and decision trees for the recovery problem
  * Weakness report and sensitivity analysis

## Getting started
Clone the repository, navigate to its root and execute the install script:
```
git clone https://github.com/Open-MBEE/pmc-fdir.git
cd pmc-fdir
./install.sh
```

## Use the GUI
The app should be found in the application launcher. Alternatively, run it by executing this command from the project's root:
```
./launch.sh
```

After startup, click `Import Graph` and navigate to one of the example DOT files in the folder `benchmarks`. 

Click `Analyze Graph` to start the analysis workflow.

## Convert your system to a graph
Learn about the graph semantics that our tool understands in our paper [Model Checking for Proving and Improving Fault Tolerance of Satellites](joniskiesbye.de/files/Model_Checking_for_Proving_and_Improving_Fault_Tolerance_of_Satellites_Accepted_Paper.pdf) [(DOI 10.1109/AERO55745.2023.10115801)](https://ieeexplore.ieee.org/document/10115801) and translate your system into a graph.
A helpful tool for this task is [Qt Visual Graph Editor](https://arsmasiuk.github.io/qvge/) which comes with an option to export DOT files.

## Requirements
The code was developed and tested on Ubuntu but any Linux distribution supporting Python 3.9 and Gtk3 should suffice.
Note that model checking problems tend to become RAM-intensive with increasing complexity. While 8GB of RAM should suffice to run the app, 32GB or more and a large swapfile are helpful when dealing with complex systems.

## Contact
If you have comments, found a bug, or have a suggestion for improvement, feel free to open an issue, submit a pull request (follow pep8 with a max line width of 100 columns) or contact us via mail: j.kiesbye@tum.de

## Credits
The authors of this tool are Kush Grover and Jonis Kiesbye,
the software is released under Apache-2.0 License.

The most notable external projects we are using in this app are:

* [PRISM](https://www.prismmodelchecker.org/)
* [dtControl](https://dtcontrol.model.in.tum.de/)
* [NetworkX](https://networkx.org/)
* [xdot](https://github.com/jrfonseca/xdot.py)
* [to-precision](https://bitbucket.org/william_rusnack/to-precision/src/master/)

All external packages are listed in `install.sh`
