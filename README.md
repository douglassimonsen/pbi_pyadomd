# Dev Instructions


## Set Up

```shell
python -m venv venv
venv\Scripts\activate
python -m pip install .
```


# Building package

```shell
python -m build .
```

# Sphinx

```shell
python -m pip install .[docs]
sphinx-autobuild docs/source docs/build/html
# http://127.0.0.1:8000
```