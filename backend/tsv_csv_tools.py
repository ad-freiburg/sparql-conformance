from backend.util import escape, is_number
from io import StringIO
import csv
from backend.models import FAILED, PASSED, INTENDED, RESULTS_NOT_THE_SAME, INTENDED_MSG


def write_csv_file(file_path: str, csv_rows: list):
    with open(file_path, "w", newline="") as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerows(csv_rows)


def row_to_string(row: list, separator: str) -> str:
    """
    Converts a row (list of values) to a string representation separated by a specified delimiter.

    Parameters:
        row (list): The row to be converted to a string.
        separator (str): The separator used to separate the values in the row "," or "\t"

    Returns:
        str: A string representation of the row.
    """
    result = ""
    index = 0
    row_length = len(row) - 1
    for element in row:
        if index == row_length:
            delimiter = ""
        else:
            delimiter = separator
        element = str(element)
        if separator in element:
            element = "\"" + element + "\""
        result += element + delimiter
        index += 1
    return result


def generate_highlighted_string_sv(
        array: list,
        remaining: list,
        mark_red: list,
        result_type: str) -> str:
    """
    Generates a string representation of an array, with specific rows highlighted.

    Parameters:
        array (list): The array to be converted to a string.
        remaining (list): The rows to be highlighted.
        result_type (str): The type of result (csv or tsv) to determine the separator.

    Returns:
        str: A string representation of the array with highlighted rows.
    """
    separator = "," if result_type == "csv" else "\t"

    result_string = ""
    for row in array:
        if row in remaining:
            if row in mark_red:
                result_string += '<label class="red">'
            else:
                result_string += '<label class="yellow">'
            result_string += escape(row_to_string(row, separator))
            result_string += '</label>\n'
        else:
            result_string += escape(row_to_string(row, separator)) + "\n"
    return result_string


def compare_values(
        value1: str,
        value2: str,
        use_config: bool,
        alias: dict,
        map_bnodes: dict) -> bool:
    """
    Compares two values for equality accounting for numeric differences and aliases.

    Parameters:
        value1 (str): The first value to compare.
        value2 (str): The second value to compare.
        use_config (bool): Flag to use configuration for additional comparison logic.
        alias (dict): Dictionary with aliases for datatypes ex. int = integer .
        map_bnodes (dict): Dictionary mapping the used bnodes.

    Returns:
        bool: True if the values are considered equal.
    """
    if value1 is None or value2 is None:
        return False
    # Blank nodes
    if len(value1) > 1 and len(
            value2) > 1 and value1[0] == "_" and value2[0] == "_":
        if value1 not in map_bnodes and value2 not in map_bnodes:
            map_bnodes[value1] = value2
            map_bnodes[value2] = value1
            return True
        if map_bnodes.get(value1) == value2 and map_bnodes.get(
                value2) == value1:
            return True
        return False
    # In most cases the values are in the same representation
    if value1 == value2:
        return True
    # Handle exceptions ex. 30000 == 3E4
    if is_number(value1) and is_number(value2):
        if float(value1) == float(value2):
            return True
    else:  # Handle exceptions integer = int
        if value1 in alias and alias[value1] == value2 and use_config:
            return True
    return False


def compare_rows(
        row1: list,
        row2: list,
        use_config: bool,
        alias: dict,
        map_bnodes: dict) -> bool:
    """
    Compares two rows for equality.

    Parameters:
        row1 (list): The first row to compare.
        row2 (list): The second row to compare.
        use_config (bool): Flag to use configuration for additional comparison logic.
        alias (dict): Dictionary with aliases for datatypes ex. int = integer .
        map_bnodes (dict): Dictionary mapping the used bnodes.

    Returns:
        bool: True if the rows are considered equal otherwise False
    """
    if len(row1) != len(row2):
        return False

    for element1, element2 in zip(row1, row2):
        if not compare_values(
                element1.split("^")[0],
                element2.split("^")[0],
                use_config,
                alias,
                map_bnodes):
            return False
    return True


def compare_array(
        expected_result: list,
        result: list,
        result_copy: list,
        expected_result_copy: list,
        use_config: bool,
        alias: dict,
        map_bnodes: dict):
    """
    Compares two arrays and removes equal rows from both arrays.

    Parameters:
        expected_result (list): The expected result array.
        result (list): The actual result array.
        result_copy (list): A copy of the actual result array for modification.
        expected_result_copy (list): A copy of the expected result array for modification.
        use_config (bool): Flag to use configuration for additional comparison logic.
        alias (dict): Dictionary with aliases for datatypes ex. int = integer .
        map_bnodes (dict): Dictionary mapping the used bnodes.
    """
    for row1 in result:
        equal = False
        row2_delete = None
        for row2 in expected_result:
            if compare_rows(row1, row2, use_config, alias, map_bnodes):
                equal = True
                row2_delete = row2
                break
        if equal:
            result_copy.remove(row1)
            expected_result_copy.remove(row2_delete)


def convert_csv_tsv_to_array(input_string: str, input_type: str):
    """
    Converts a CSV/TSV string to an array of rows.

    Parameters:
        input_string (str): The CSV/TSV formatted string.
        input_type (str): The type of the input ('csv' or 'tsv').

    Returns:
        An array representation of the input string.
    """
    rows = []
    delimiter = "," if input_type == "csv" else "\t"
    with StringIO(input_string) as io:
        reader = csv.reader(io, delimiter=delimiter)
        for row in reader:
            rows.append(row)
    return rows


def compare_sv(
        expected_string: str,
        query_result: str,
        result_format: str,
        alias: dict):
    """
    Compares CSV/TSV formatted query result with the expected output.

    Parameters:
        expected_string (str): Expected CSV/TSV formatted string.
        query_result (str): Actual CSV/TSV formatted string from the query.
        output_format (str): Format of the output ('csv' or 'tsv').
        alias (dict): Dictionary with aliases for datatypes ex. int = integer .

    Returns:
        tuple(int, str, str, str, str, str): A tuple of test status and error message and expected html, query html, expected red, query red
    """
    map_bnodes = {}
    status = FAILED
    error_type = RESULTS_NOT_THE_SAME

    expected_array = convert_csv_tsv_to_array(expected_string, result_format)
    actual_array = convert_csv_tsv_to_array(query_result, result_format)
    actual_array_copy = actual_array.copy()
    expected_array_copy = expected_array.copy()
    actual_array_mark_red = []
    expected_array_mark_red = []

    compare_array(
        expected_array,
        actual_array,
        actual_array_copy,
        expected_array_copy,
        False,
        alias,
        map_bnodes)

    if len(actual_array_copy) == 0 and len(expected_array_copy) == 0:
        status = PASSED
        error_type = ""
    else:
        actual_array_mark_red = actual_array_copy.copy()
        expected_array_mark_red = expected_array_copy.copy()
        compare_array(
            expected_array_copy,
            actual_array_copy,
            actual_array_mark_red,
            expected_array_mark_red,
            True,
            alias,
            map_bnodes)
        if len(actual_array_mark_red) == 0 and len(
                expected_array_mark_red) == 0:
            status = INTENDED
            error_type = INTENDED_MSG

    expected_html = generate_highlighted_string_sv(
        expected_array,
        expected_array_copy,
        expected_array_mark_red,
        result_format)
    actual_html = generate_highlighted_string_sv(
        actual_array, actual_array_copy, actual_array_mark_red, result_format)
    expected_html_red = generate_highlighted_string_sv(
        expected_array_copy,
        expected_array_copy,
        expected_array_mark_red,
        result_format)
    actual_html_red = generate_highlighted_string_sv(
        actual_array_copy, actual_array_copy, actual_array_mark_red, result_format)

    return status, error_type, expected_html, actual_html, expected_html_red, actual_html_red
