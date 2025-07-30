# Overview

pbi_pyadomd is a fork of the original [pyadomd](https://pypi.org/project/pyadomd/) library, designed to provide a typed Python interface for communicating with SQL Server Analysis Services (SSAS) instances. This library allows developers to execute DAX and XML queries against SSAS in a more structured and type-safe manner.

For more information, see the [docs](https://douglassimonsen.github.io/pbi_pyadomd/)

# Installation

```shell
python -m pip install pbi_pyadomd
```
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

# Running the Documentation Server

```shell
python -m pip install .[docs]
mkdocs serve -f docs/mkdocs.yml
```

## Deploy docs to Github Pages

```shell
mkdocs  gh-deploy --clean -f docs/mkdocs.yml
```