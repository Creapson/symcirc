# Symcirc
Symbolic Circuit analyser

# How to install/build
- install enviroment
```python
python -m pip install poetry
python -m poetry install
```

- build .exe 
```python
python -m pip install pyinstaller
python -m pip pyinstaller -F main.py
```

# How to run tests 
Make sure you run this command from the root directory
```python
python -m poetry run python -m unittest discover -s tests
python -m poetry run python -m unittest discover -s tests
```

# What needs work?
- Theme editor/selector
    - add more settings
- addition of multiple levels of small signal model complexities
- more test cases / complete the current tests
- better icons for the node creation image buttons
- addition of LTspice parser
- sparse tableau implementation
- block approximation implementation
- transfer function numerator / denumerator approximation
- poles / zeros calcultion (numeric + symbolic)
- poles / zeros output (plot, numeric, symbolic)
- Jupyter Notebook export
- node editor zoom solution
- transfer function output (numeric, symbolic)
- system of equations output (numeric, symbolic)
- node settings in seperate window
- addition of fonts
- font resolution fix
