from backend.models import Config
import os
from backend.json_tools import write_json_file, read_json_file
from backend.util import path_exists


def create_config(
        server_address: str,
        port: str,
        path_to_testsuite: str,
        path_to_binaries: str,
        host: str,
        graphstore: str,
        newpath: str) -> bool:
    """
    Create the config file.
    """
    path_to_server_main = os.path.join(path_to_binaries, "ServerMain")
    path_to_index_builder = os.path.join(path_to_binaries, "IndexBuilderMain")
    if not path_exists(path_to_testsuite) or not path_exists(path_to_binaries) or not path_exists(
            path_to_server_main) or not path_exists(path_to_index_builder):
        return False
    directories = [
        directory for directory in os.listdir(path_to_testsuite) if os.path.isdir(
            os.path.join(
                path_to_testsuite,
                directory)) and os.path.isfile(
            os.path.join(
                path_to_testsuite,
                directory,
                "manifest.ttl"))]
    config = {
        "HOST": host,
        "GRAPHSTORE": graphstore,
        "NEWPATH": newpath,
        "command_index": f"{path_to_index_builder} -s TestSuite.settings.json -i TestSuite ",
        "command_start_server": f"{path_to_server_main} -i TestSuite -j 8 -p {port} > TestSuite.server-log.txt",
        "command_stop_server": f"pkill -f '{path_to_server_main} -i [^ ]*TestSuite'",
        "command_remove_index": "rm -f TestSuite.index.* TestSuite.vocabulary.* TestSuite.prefixes TestSuite.meta-data.json TestSuite.index-log.txt",
        "server_address": server_address,
        "port": port,
        "path_to_testsuite": path_to_testsuite,
        "path_to_binaries": path_to_binaries,
        "queries": [
            "Query.rq",
            "Syntax.rq",
            "Update.rq",
            "Format.rq",
            "Protocol.rq",
            "Service.rq",
            "GraphStoreProtocol.rq"],
        "directories": directories,
        "alias": {
            "http://www.w3.org/2001/XMLSchema#integer": "http://www.w3.org/2001/XMLSchema#int",
            "http://www.w3.org/2001/XMLSchema#double": "http://www.w3.org/2001/XMLSchema#decimal",
            "http://www.w3.org/2001/XMLSchema#float": "http://www.w3.org/2001/XMLSchema#decimal",
            "http://www.w3.org/2001/XMLSchema#int": "http://www.w3.org/2001/XMLSchema#integer",
            "http://www.w3.org/2001/XMLSchema#decimal": "http://www.w3.org/2001/XMLSchema#double",
            "http://www.w3.org/2001/XMLSchema#decimal": "http://www.w3.org/2001/XMLSchema#float",
            "http://www.w3.org/2001/XMLSchema#string": None},
        "number_types": [
            "http://www.w3.org/2001/XMLSchema#integer",
            "http://www.w3.org/2001/XMLSchema#double",
            "http://www.w3.org/2001/XMLSchema#decimal",
            "http://www.w3.org/2001/XMLSchema#float",
            "http://www.w3.org/2001/XMLSchema#int",
            "http://www.w3.org/2001/XMLSchema#decimal"]}
    write_json_file("config.json", config)
    return True


def initialize_config() -> Config:
    """
    Initialize config file.
    """
    path_to_config = "./config.json"

    if not os.path.exists(path_to_config):
        print(f"Can not find {path_to_config}")
        print("Use 'python3 testsuite.py config ...' to create config!")
        return None

    with open(path_to_config, "r") as file:
        config_json = read_json_file(file)
        config = Config(config_json)
        return config
