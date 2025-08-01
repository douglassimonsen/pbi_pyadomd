# Overview

Pbi_pyadomd is a fork of the original [pyadomd](https://pypi.org/project/pyadomd/) library, designed to provide a typed Python interface for communicating with SQL Server Analysis Services (SSAS) instances. This library allows developers to execute DAX and XML queries against SSAS in a more structured and type-safe manner. It also includes the ability to stream results from long-running queries, such as those used in SSAS Trace subscriptions.

# Installation

```shell
python -m pip install pbi_pyadomd
```

# Examples


!!! info "Reading Data from an SSAS Table"

    Note: in this version of pyadomd, executing a DAX returns a reader object rather than a cursor object. This is intended to provide a more consistent interface with the underlying C# Adomd library.

    ```python
    from pbi_pyadomd import Connection

    conn_str = "Provider=MSOLAP;Data Source=localhost:51358;Initial Catalog=<db_UUID>;"
    with Connection(conn_str) as conn:
        reader = conn.execute_dax("EVALUATE <table_name>")
        for row in reader.fetch_many():
            print(row)
    ```

!!! info "Streaming Results"

    Note: when reading a query without a definite end, such as a SSAS Trace subscription, you can use the `fetch_stream` method to continuously read results as they become available. If you use the standard `fetch_many` method, it will block until the query completes, which may not occur.

    Both the Reader and Connection with statements automatically close their underlying resources when they go out of scope, so you do not need to explicitly close them.

    ```python
    from pbi_pyadomd import Connection

    conn_str = "Provider=MSOLAP;Data Source=localhost:51358;Initial Catalog=<db_UUID>;"
    xml_command = """
    <Subscribe xmlns="http://schemas.microsoft.com/analysisservices/2003/engine">
    <Object>
        <TraceID>{{trace_name}}</TraceID>
    </Object>
    <SubscriptionId xmlns="http://schemas.microsoft.com/analysisservices/2018/engine/800">{{subscription_name}}</SubscriptionId>
    </Subscribe>
    """
    with Connection(conn_str) as conn:
        with conn.execute_xml(xml_command) as reader:
            for row in reader.fetch_stream():
                print(row)

                # this break clause is a non-functional example to illustrate how you might stop reading
                if row.val == "EndOfStream":
                    break
    ```

!!! info "Executing Non Queries"

    There are certain operations that do not return a result set, such as creating or altering database objects. You can execute these using the `execute_non_query` method.

    ```python
    from pbi_pyadomd import Connection

    conn_str = "Provider=MSOLAP;Data Source=localhost:51358;Initial Catalog=<db_UUID>;"
    with Connection(conn_str) as conn:
        result = conn.execute_non_query("CREATE TABLE <table_name> (id INT, name NVARCHAR(100))")
        print(result)  # prints "None"
    ```
