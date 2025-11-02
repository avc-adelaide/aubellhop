Code reference
==============

.. toctree::
   :maxdepth: 3

Main interfaces
---------------

.. mermaid::

   flowchart TD
       A["bh.models<br/>Registry of models"]
       B["bh.models.new(...)<br/>create new model"]
       C["bh.models.list()<br/>list all models"]
       D["env = bh.Environment()<br/>create Environment instance"]
       E["bh.compute(env, ...)<br/>run with default model"]

       B --> A
       A --> C
       D --> E
       A --> E

.. mermaid::

   classDiagram
       class Models {
           +new(name, ...)
           +list()
       }

       class Environment {
           +__init__()
       }

       class Bellhop {
           +compute(env, task, model=None)
       }

       Models <|-- Bellhop : uses
       Environment <.. Bellhop : input


.. code-block:: text

     import bellhop as bh

   ┌──────────────────────────────────────────────────────────────┐
   │ bh.models                                                    │
   │  • Registry of BellhopSimulator instances                    │
   │                                                              │
   │ bh.models.new(name="...")                                    │
   │    → create new model                                        │
   │                                                              │
   │ bh.models.list()                                             │
   │    → list all models                                         │
   └──────────────────────────────────────────────────────────────┘

   ┌──────────────────────────────────────────────────────────────┐
   │ env = bh.Environment(...)                                    │
   │    → create new Environment instance                         │
   └──────────────────────────────────────────────────────────────┘

   ┌──────────────────────────────────────────────────────────────┐
   │ bh.compute(env, task=["..."])                                │
   │    → run Bellhop computations using the *auto* model         │
   │                                                              │
   │ bh.compute(env, task=["..."], model=["..."])                 │
   │    → run Bellhop computations using the *specified* model    │
   └──────────────────────────────────────────────────────────────┘

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

