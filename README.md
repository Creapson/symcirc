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
- Small signal models
- more test cases / complete the current tests
- better icons for the node creation image buttons

