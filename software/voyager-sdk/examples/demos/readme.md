# Axelera AI demos
In this folder, you will find demos that we have created for conferences and to help you get started.

Inside the [demo_specific_readmes](/examples/demos/demo_specific_readmes), you will find information about each demo:
- [Fruit demo](/examples/demos/demo_specific_readmes/fruit_demo.md)
- [8k demo](/examples/demos/demo_specific_readmes/8k_demo.md)

To generate a desktop icon and a runscript, you can use the [install.py](/examples/demos/install.py) script. Use `./install.py -h` to view available demos to install. This script automatically looks for all demos available inside the demos folder. You may need to right click the desktop icon and select _allow launching_.

Some demos use environment variables. For more general information about environment variables, run `inference.py` with `AXELERA_HELP=1` and see lots of help. Note, the environment variables are subject to change and are for advanced usage to override defaults. They are not intended for general use.
