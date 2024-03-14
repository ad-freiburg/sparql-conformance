import json
import sys
import os 

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
            match old_run_test["status"]:
                case "Passed":
                    match_status(new_run_test["status"], new_run_test, "p", results)
                case "Failed":
                    match_status(new_run_test["status"], new_run_test, "f", results)
                case "NOT TESTED":
                    match_status(new_run_test["status"], new_run_test, "n", results)
                case "Failed: Intended":
                    match_status(new_run_test["status"], new_run_test, "i", results)

    return results

def main():
    msg = ""
    status = 0
    args = sys.argv[1:]
    workflow = {"master": ""}
    with open("../test-web/workflow.json", "r") as file:
        workflow = json.load(file)
    old_run = workflow["master"]

    if old_run != "":
        with open("../test-web/results/" + old_run + ".json", "r") as file:
            f1 = json.load(file)
        with open("./results/" + args[0] + ".json", "r") as file:
            f2 = json.load(file)
        results = compare_dicts(f1, f2)
        for key in results.keys():
            if len(results[key]) > 0:
                print("--------")
                print(key)
                print(len(results[key]))
                if key.startswith("p") and key != "p":
                    status = 1
    
        if status != 0:
            msg = "New run contains test that previously 'Passed' and now don't."
            print(msg)
        else:
            workflow["master"] = args[0]
            with open("workflow.json", "w") as file:
                json.dump(workflow, file, indent=4)
        link = "Link to compare runs: https://sirdnarch.github.io/test-web/index-" + args[0] + "-" + old_run + ".html"
        print(link)
        os.system("cp ../test-web/index.html ../test-web/index-" + args[0] + "-" + old_run + ".html")
    else:
        workflow["master"] = args[0]
        with open("../test-web/workflow.json", "w") as file:
            json.dump(workflow, file, indent=4)
        print("New run")
        print("Link to look at run: https://sirdnarch.github.io/test-web/index.html")
    os.system(f'echo "status={status}" >> $GITHUB_ENV')
    os.system(f'echo "msg={msg}" >> $GITHUB_ENV')
    os.system(f'echo "link={link}" >> $GITHUB_ENV')

if __name__ == "__main__":
    main()