import os
from typing import Dict, Any, Tuple, List, Optional


class Config:
    """Configuration class for SPARQL test suite execution."""

    def __init__(self,
                 image: str,
                 system: str,
                 port: str,
                 graph_store: Optional[str],
                 testsuite_dir: str,
                 type_alias: List[Tuple[str, str]],
                 binaries_directory: str,
                 exclude: List[str],
                 include: List[str] = None,
                 server_binary: str = "qlever-server",
                 index_binary: str = "qlever-index",
                 run_id: str = "qlever-sparql-conformance",
                 access_token: str = "abc",
                 ):
        self.server_address = 'localhost'
        self.run_id = run_id
        self.access_token = access_token
        self.image = image
        self.system = system
        self.port = port
        self.GRAPHSTORE = graph_store
        self.alias = type_alias
        self.path_to_test_suite = os.path.abspath(testsuite_dir)
        self.path_to_binaries = os.path.abspath(binaries_directory)
        self.server_binary = server_binary
        self.index_binary = index_binary
        self.exclude = exclude
        self.include = include
        self.number_types = [
            "http://www.w3.org/2001/XMLSchema#integer",
            "http://www.w3.org/2001/XMLSchema#double",
            "http://www.w3.org/2001/XMLSchema#decimal",
            "http://www.w3.org/2001/XMLSchema#float",
            "http://www.w3.org/2001/XMLSchema#int",
            "http://www.w3.org/2001/XMLSchema#decimal"
        ]

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary format."""
        return self.__dict__
