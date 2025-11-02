Code reference
==============

.. toctree::
   :maxdepth: 3

Main interfaces
---------------

.. mermaid::

   flowchart TD
       A["bh.Models<br/>Registry of models"]
       B["bh.Models.new(...)<br/>create new model"]
       C["bh.Models.list()<br/>list all models"]
       D["env = bh.Environment()<br/>create Environment instance"]
       E["bh.compute(env, ...)<br/>run with default model"]

       B --> A
       A --> C
       D --> E
       A --> E

File structure
--------------

    +------------------+-------------------------------------------------+
    | Source file      | Description                                     |
    +==================+=================================================+
    | `main.py`        | Top level module file                           |
    +------------------+-------------------------------------------------+
    | `models.py`      | Model registry for BellhopSimulator variants    |
    +------------------+-------------------------------------------------+
    | `bellhop.py`     | Class definition of bellhop(3d).exe interface   |
    +------------------+-------------------------------------------------+
    | `constants.py`   | Strings and mappings mainly for option parsing  |
    +------------------+-------------------------------------------------+
    | `readers.py`     | Functions for reading Bellhop input text files  |
    +------------------+-------------------------------------------------+
    | `environment.py` | Environment class definition                    |
    +------------------+-------------------------------------------------+
    | `plot.py`        | Plotting functions using Bokeh                  |
    +------------------+-------------------------------------------------+
    | `plotutils.py`   | Internal interface to Bokeh                     |
    +------------------+-------------------------------------------------+
    | `pyplot.py`      | Plotting functions using Matplotlib             |
    +------------------+-------------------------------------------------+

