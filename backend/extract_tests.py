from backend.models import Config
from backend.tsv_csv_tools import write_csv_file
import backend.qlever_manager as qlever
import backend.util as util
import os
import csv

def extract_tests(config: Config):
    """
    Extracts tests from a set of directories and compiles results into a CSV file.

    Parameters:
        output_csv_path: Path to the output CSV file.
    """
    csv_rows = {}
    for query in config.queries:
        csv_rows[query] = []

    for path in config.directories:
        print("Extracting tests from: " + path)
        qlever.remove_index(config.command_remove_index)
        index = qlever.index(config.command_index, os.path.join(config.path_to_test_suite, path, "manifest.ttl"))
        if not index[0]:
            print(index[1])
            continue
        server = qlever.start_server(config.command_start_server, config.server_address, config.port)
        if not server[0]:
            print(index[1])
            continue
        for query in config.queries:
            query_result = qlever.query(util.read_file("./queries/" + query), "rq", "csv", config.server_address, config.port)
            if query_result[0] == 200:
                csv_content = query_result[1]

                csv_reader = csv.reader(csv_content.splitlines())
                next(csv_reader)
                for row in csv_reader:
                    row.append(path)
                    csv_rows[query].append(row)
            else:
                print(query_result[1])
        qlever.stop_server(config.command_stop_server)
        qlever.remove_index(config.command_remove_index)
    
    os.makedirs("./tests/", exist_ok=True)
    for query in csv_rows:
        write_csv_file("./tests/"+query.replace(".rq", ".csv"), csv_rows[query])