"""Golden tests for the CSV/TSV results comparator."""

from sparql_conformance.test_object import ErrorMessage, Status
from sparql_conformance.tsv_csv_tools import compare_sv

XSD = "http://www.w3.org/2001/XMLSchema#"


def test_identical_csv_passes():
    doc = "s,p\na,b\nc,d\n"
    status, error, *_ = compare_sv(doc, doc, "csv", [])
    assert status == Status.PASSED
    assert error == ""


def test_identical_tsv_passes():
    doc = "?s\t?p\n<http://e.org/a>\t<http://e.org/b>\n"
    status, *_ = compare_sv(doc, doc, "tsv", [])
    assert status == Status.PASSED


def test_row_order_is_ignored():
    a = "s\nx\ny\n"
    b = "s\ny\nx\n"
    status, *_ = compare_sv(a, b, "csv", [])
    assert status == Status.PASSED


def test_column_order_is_normalized():
    a = "s,p\na,b\n"
    b = "p,s\nb,a\n"
    status, *_ = compare_sv(a, b, "csv", [])
    assert status == Status.PASSED


def test_different_values_fail():
    a = "s\nx\n"
    b = "s\nz\n"
    status, error, *_ = compare_sv(a, b, "csv", [])
    assert status == Status.FAILED
    assert error == ErrorMessage.RESULTS_NOT_THE_SAME


def test_missing_row_fails():
    a = "s\nx\ny\n"
    b = "s\nx\n"
    status, *_ = compare_sv(a, b, "csv", [])
    assert status == Status.FAILED
