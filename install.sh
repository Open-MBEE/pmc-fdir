#!/bin/bash

# Install required software
sudo apt update
sudo apt install git python3 python3-venv python3-pip openjdk-17-jdk xdot
sudo apt install libgirepository1.0-dev gcc libcairo2-dev pkg-config python3-dev gir1.2-gtk-3.0 libgraphviz-dev
python3 -m venv python3-venv
source python3-venv/bin/activate
pip install wheel
pip install pycairo PyGObject
pip install xdot regex networkx numpy pandas tqdm pygraphviz dtcontrol
pip install git+https://github.com/BebeSparkelSparkel/to-precision@0.0.0

# Download and install PRISM model checker
wget https://www.prismmodelchecker.org/dl/prism-4.7-linux64.tar.gz#download-box
mkdir prism
tar -zxf prism-4.7-linux64.tar.gz --strip-components=1 -C prism
cd prism
./install.sh
cd -

# Icons
ICONPATH="${HOME}/.local/share/icons/hicolor/"
ICONPATH16=${ICONPATH}16x16/apps
mkdir -p "$ICONPATH16" && cp icons/16x16/pmc-fdir.png "$ICONPATH16"
ICONPATH32=${ICONPATH}32x32/apps
mkdir -p "$ICONPATH32" && cp icons/32x32/pmc-fdir.png "$ICONPATH32"
ICONPATH48=${ICONPATH}48x48/apps
mkdir -p "$ICONPATH48" && cp icons/48x48/pmc-fdir.png "$ICONPATH48"
ICONPATH64=${ICONPATH}64x64/apps
mkdir -p "$ICONPATH64" && cp icons/64x64/pmc-fdir.png "$ICONPATH64"
ICONPATH96=${ICONPATH}96x96/apps
mkdir -p "$ICONPATH96" && cp icons/96x96/pmc-fdir.png "$ICONPATH96"
ICONPATH128=${ICONPATH}128x128/apps
mkdir -p "$ICONPATH128" && cp icons/128x128/pmc-fdir.png "$ICONPATH128"
ICONPATH256=${ICONPATH}256x256/apps
mkdir -p "$ICONPATH256" && cp icons/256x256/pmc-fdir.png "$ICONPATH256"
ICONPATHSVG=${ICONPATH}scalable/apps
mkdir -p "$ICONPATHSVG" && cp icons/pmc-fdir.svg "$ICONPATHSVG"
echo "Moved icons to ${ICONPATH}"

# Launcher shortcut
LAUNCHERPATH="${HOME}/.local/share/applications/"
mkdir -p "$LAUNCHERPATH"
SCRIPT=$(realpath "$0")
SCRIPTPATH=$(dirname "$SCRIPT")
cat >${LAUNCHERPATH}pmc-fdir.desktop  <<EOL
[Desktop Entry]
Encoding=UTF-8
Name=PMC FDIR
Comment=Probabilistic Model Checking for FDIR
Exec=${SCRIPTPATH}/launch.sh
Icon=pmc-fdir
Terminal=true
Type=Application
EOL
chmod +x ${LAUNCHERPATH}pmc-fdir.desktop
echo "Created launcher shortcut in ${LAUNCHERPATH}"
