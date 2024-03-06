import json

def match_status(status, new_run_test, s, results):
    match status:
        case "Passed":
            results[f"{s}-p"].append(new_run_test)
        case "Failed":
            results[f"{s}-f"].append(new_run_test)
        case "NOT TESTED":
            results[f"{s}-n"].append(new_run_test)
        case "Failed: Intended":
            results[f"{s}-i"].append(new_run_test)

def compare_dicts(old_run, new_run):
    all_test = set(old_run.keys()) | set(new_run.keys())
    results = {
        "p-f": [],
        "p-i": [],
        "p-n": [],
        "f-p": [],
        "f-i": [],
        "f-n": [],
        "i-p": [],
        "i-f": [],
        "i-n": [],
        "n-p": [],
        "n-f": [],
        "n-i": [],
        "n": [],
        "p": [],
        "i": [],
        "f": [],
        "added-n": [],
        "added-p": [],
        "added-i": [],
        "added-f": [],
        "deleted": []
    }
    for test in all_test:
        if test == "info":
            continue
        old_run_test = old_run.get(test)
        new_run_test = new_run.get(test)
        if new_run_test is None:
            results["deleted"].append(old_run_test)
            continue
        if old_run_test is None:
            match new_run_test["status"]:
                case "Passed":
                    results["added-p"].append(new_run_test)
                case "Failed":
                    results["added-f"].append(new_run_test)
                case "NOT TESTED":
                    results["added-n"].append(new_run_test)
                case "Failed: Intended":
                    results["added-i"].append(new_run_test)
            continue
        print(old_run_test.keys())
        if old_run_test["status"] == new_run_test["status"]:
            match new_run_test["status"]:
                case "Passed":
                    results["p"].append(new_run_test)
                case "Failed":
                    results["f"].append(new_run_test)
                case "NOT TESTED":
                    results["n"].append(new_run_test)
                case "Failed: Intended":
                    results["i"].append(new_run_test)
        else:
            match new_run_test["status"]:
                case "Passed":
                    match_status(old_run_test["status"], new_run_test, "p", results)
                case "Failed":
                    match_status(old_run_test["status"], new_run_test, "f", results)
                case "NOT TESTED":
                    match_status(old_run_test["status"], new_run_test, "n", results)
                case "Failed: Intended":
                    match_status(old_run_test["status"], new_run_test, "i", results)

    return results


def main():
    with open('r1.json', 'r') as file:
        f1 = json.load(file)
    with open('r2.json', 'r') as file:
        f2 = json.load(file)
    results = compare_dicts(f1, f2)
    for key in results.keys():
        print("--------")
        print(key)
        print(len(results[key]))


if __name__ == "__main__":
    main()