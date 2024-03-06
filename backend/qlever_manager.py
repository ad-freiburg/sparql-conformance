import os
import time
import requests
import subprocess
from backend.rdf_tools import write_ttl_file, delete_ttl_file, rdf_xml_to_turtle

def index(command_index: str, graph_path: str) -> tuple:
    """
    Executes a command to index a graph file using the QLever IndexBuilderMain binary.

    Parameters:
        command_index (str): Command to be executed
        graph_path (str): The path to the graph file to be indexed.

    Returns:
        tuple (bool, string): Returns the status as a bool and the error message or the index build log
    """
    remove = False
    if graph_path.endswith(".rdf"):
        remove = True
        graph_path_new = graph_path.replace(".rdf", ".ttl")
        write_ttl_file(graph_path_new, rdf_xml_to_turtle(graph_path))
        graph_path = graph_path_new
    status = False
    try:
        cmd = f"{command_index}{graph_path}"
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()
        if process.returncode != 0:
            return status, f"Indexing error: {error.decode('utf-8')} \n \n {output.decode('utf-8')}"
        index_log = output.decode("utf-8")
        if "Index build completed" in index_log:
            status = True
        if remove:
            delete_ttl_file(graph_path)
        return status, index_log
    except Exception as e:
        return status, f"Exception executing index command: {str(e)}"

def remove_index(command_remove_index: str) -> tuple:
    """
    Removes index and related files for the TestSuite.

    Parameters:
        command_remove_index (str): Command to be executed

    Returns:
        tuple (bool, string): Returns the status as a bool and the error message
    """
    try:
        subprocess.check_call(command_remove_index, shell=True)
        return True, ""
    except subprocess.CalledProcessError as e:
        return False, f"Error removing index files: {e}"

def start_server(command_start_server: str, server_address, port) -> tuple:
    """
    Starts the SPARQL server and waits for it to be ready.

    Parameters:
        command_start_server (str): Command to be executed

    Returns:
        tuple (bool, str): A tuple containing the HTTP status code and a message indicating the server startup status.
    """
    try:
        cmd = command_start_server
        subprocess.Popen(cmd, shell=True)
        return wait_for_server_startup(server_address, port)
    except Exception as e:
        return (500, f"Exception executing server command: {str(e)}")

def wait_for_server_startup(server_address, port):
    """
    Waits for the SPARQL server to start up.

    This method makes repeated attempts to send a test query to the server. If the server
    responds successfully within the maximum number of retries, it is considered operational.

    Returns:
        tuple: A tuple containing the HTTP status code and a message indicating the server status.
    """
    max_retries = 8
    retry_interval = 0.25
    url = server_address + ":" + port
    headers = {"Content-type": "application/sparql-query"}
    test_query = "SELECT ?s ?p ?o { ?s ?p ?o } LIMIT 1"

    for i in range(max_retries):
        try:
            response = requests.post(url, headers=headers, data=test_query)
            if response.status_code == 200:
                return (200, "Server ready!")
        except requests.exceptions.RequestException as e:
            pass
        time.sleep(retry_interval)

    return (500, "Server failed to start within expected time")

def stop_server(command_stop_server: str) -> str:
    """
    Stops the SPARQL server.

    Parameters:
        command_start_server (str): Command to be executed

    Returns:
        str: Returns empty string if passed and an error message if the command failed.
    """
    try:
        subprocess.check_call(command_stop_server, shell=True)
    except subprocess.CalledProcessError as e:
        print(f"Error stopping server: {e}")

def query(query, type, result_format, server_address, port) -> tuple:
    """
    Executes a SPARQL query against the server and retrieves the results.

    Parameters:
        query (str): The SPARQL query to be executed.
        type (str): Query or Update
        result_format (str): Type of the result.
        server_address (str): Server address of the SPARQL server.
        port (str): Port of the SPARQL server.

    Returns:
        tuple (int, str): A tuple containing the HTTP status code and the query result.
    """
    accept = "application/sparql-results+json"
    if result_format == "csv":
        accept = "text/csv"
    elif result_format == "tsv":
        accept = "text/tab-separated-values"
    elif result_format == "srx":
        accept = "application/sparql-results+xml"
    elif result_format == "ttl":
        accept = "text/turtle"

    if type == "rq":
        content_type = "application/sparql-query; charset=utf-8"
    else:
        content_type = "application/sparql-update; charset=utf-8"


    url = server_address + ":" + port
    headers = {"Accept": accept, "Content-type": content_type}
    try:
        response = requests.post(url, headers=headers, data=query.encode("utf-8"))
        return (response.status_code, response.content.decode("utf-8"))
    except requests.exceptions.RequestException as e:
        return (500, f"Query execution error: {str(e)}")