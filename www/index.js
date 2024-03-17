
$(document).ready(async function () {
    var data = await fetchData();
    var jsonData = data[0];
    var nameMap = data[1];
    var selectedRun = Object.keys(jsonData)[0];
    $(`#table-select-runs1 tr[data-name=${selectedRun}]`).addClass("row-selected");
    var selectedRun2 = -1;
    if (Object.keys(jsonData).length == 2) {
        selectedRun2 =  Object.keys(jsonData)[1]
        handleAccordion("collapse-two", false);
    }
    var getTestRunResult = getTestRun(selectedRun, selectedRun2, jsonData);
    var jsonArray = getTestRunResult[0]
    var compareRunInformation = getTestRunResult[1]
    var currentArray = jsonArray;
    var currentTestName = -1;
    buildRunTables(jsonData, nameMap, "", selectedRun, selectedRun2);
    buildFilter(jsonArray);
    currentArray = filterTable($("#search-input").val(), jsonArray);
    buildTable(currentArray, currentTestName);
    showCorrectElement(currentTestName, selectedRun2);
    
    $(document).on("click", ".button-toggle", function() {
        $(`#div-${this.id}`).toggleClass("visually-hidden");
    });

    $(document).on("click", ".link-collapse", function() {
        var element = document.getElementById(`${this.id}`);
        var pElement = element.querySelectorAll("p")[0];
        var arrowElement = pElement.querySelectorAll("i")[0];
        if (arrowElement.classList.contains("up")) {
            arrowElement.classList.remove("up");
            arrowElement.classList.add("down");
        } else {
            arrowElement.classList.remove("down");
            arrowElement.classList.add("up");   
        }
    });

    $(document).on("click", ".form-check-input", function() {
        currentArray = filterTable($("#search-input").val(), jsonArray);
        buildTable(currentArray, currentTestName);
        updateFilter($("#search-input").val(), jsonArray, currentArray, document.getElementById("accordion-filter").querySelectorAll("input"));
    });

    $(".button-toggle-filter").on("click", function() {
        var buttonId = this.id;
        var value = $(this).attr("value")
        var divElem = document.getElementById(`container-filter-${value}`);
        var checkNodes = divElem.querySelectorAll("input");
        checkNodes.forEach(function(check) {
            if (buttonId.includes("uncheck")) {
                check.checked = false;
            }
            else {
                check.checked = true;
            }
        });
        currentArray = filterTable($("#search-input").val(), jsonArray);
        buildTable(currentArray, currentTestName);
        updateFilter($("#search-input").val(), jsonArray, currentArray, document.getElementById("accordion-filter").querySelectorAll("input"));
    });

    $("#button-expand-all").on("click", function() {
        var divNodes = document.querySelectorAll(`a.link-collapse`);
        divNodes.forEach(function(div) {
            var element = document.getElementById(`${div.id}`);
            if (element.classList.contains('collapsed')) {
                element.click();
            }
        });
    });

    $("#button-collapse-all").on("click", function() {
        var divNodes = document.querySelectorAll(`a.link-collapse`);
        divNodes.forEach(function(div) {
            var element = document.getElementById(`${div.id}`);
            if (!element.classList.contains('collapsed')) {
                element.click();
            }
        });
    });

    $("#button-matching").on("click", function() {
        var preNodes = document.querySelectorAll(`pre.normalText`);
        preNodes.forEach(function(label) {
            label.classList.toggle("visually-hidden");
        });
        preNodes = document.querySelectorAll(`pre.redText`);
        preNodes.forEach(function(label) {
            label.classList.toggle("visually-hidden");
        });
    });

    $("#search-input").on("keyup", function(){
        var value = $(this).val();
        currentArray = filterTable(value, jsonArray);
        buildTable(currentArray, currentTestName);
        updateFilter(value, jsonArray, currentArray, document.getElementById("accordion-filter").querySelectorAll("input"));
    });

    $("#search-input-run").on("keyup", function(){
        var value = $(this).val();
        buildRunTables(jsonData, nameMap, value, selectedRun, selectedRun2);
    });

    $("#button-overview").on("click", function() {
        if (selectedRun2 == -1) {
            $("#button-overview").addClass("active");
            $("#button-details").removeClass("active");
            $("#container-test-details").addClass("visually-hidden");
            $("#container-test-overview").removeClass("visually-hidden");
        } else {
            $("#button-overview").addClass("active");
            $("#button-details").removeClass("active");
            $("#container-test-details-1").addClass("visually-hidden");
            $("#container-test-overview-1").removeClass("visually-hidden");
            $("#container-test-details-2").addClass("visually-hidden");
            $("#container-test-overview-2").removeClass("visually-hidden");
        }
    });

    $("#button-details").on("click", function() {
        if (selectedRun2 == -1) {
            $("#button-overview").removeClass("active");
            $("#button-details").addClass("active");
            $("#container-test-details").removeClass("visually-hidden");
            $("#container-test-overview").addClass("visually-hidden");
        } else {
            $("#button-overview").removeClass("active");
            $("#button-details").addClass("active");
            $("#container-test-details-1").removeClass("visually-hidden");
            $("#container-test-overview-1").addClass("visually-hidden");
            $("#container-test-details-2").removeClass("visually-hidden");
            $("#container-test-overview-2").addClass("visually-hidden");
        }
    });

    $("#table-select-tests").on("click", "tr", function() {
        if (this.id != "head") {
            handleAccordion("collapse-one", true);
            handleAccordion("collapse-three", false);
            var testName = $(this).data("name");
            if (testName != currentTestName) {
                $("#table-select-tests tr").removeClass("row-selected");
                $(this).addClass("row-selected");
                buildTestInformation(testName, jsonArray, selectedRun, selectedRun2);
            }
            currentTestName = testName;
            showCorrectElement(currentTestName, selectedRun2)
            goBackToOverview();
        }
    });

    $("#table-select-runs1").on("click", "tr", function() {
        handleAccordion("collapse-two", false);
        var runName = $(this).data("name");
        $(`#table-select-runs1 tr[data-name=${selectedRun}]`).removeClass("row-selected");
        $(`#table-select-runs1 tr[data-name=${runName}]`).addClass("row-selected");
        selectedRun = runName;
        getTestRunResult = getTestRun(selectedRun, selectedRun2, jsonData);
        jsonArray = getTestRunResult[0]
        compareRunInformation = getTestRunResult[1]
        currentArray = jsonArray;
        currentTestName = -1;
        buildFilter(jsonArray);
        currentArray = filterTable($("#search-input").val(), jsonArray);
        buildTable(currentArray, currentTestName);
        showCorrectElement(currentTestName, selectedRun2);
        updateRunSelectionText(selectedRun, selectedRun2, compareRunInformation);
    });

    $("#table-select-runs2").on("click", "tr", function() {
        handleAccordion("collapse-two", false);
        $(`#table-select-runs2 tr[data-name=${selectedRun2}]`).removeClass("row-selected");
        var runName = $(this).data("name");
        if (runName == selectedRun2){
            selectedRun2 = -1;
        } else {
            selectedRun2 = runName;
            $(`#table-select-runs2 tr[data-name=${runName}]`).addClass("row-selected");
        }
        getTestRunResult = getTestRun(selectedRun, selectedRun2, jsonData);
        jsonArray = getTestRunResult[0]
        compareRunInformation = getTestRunResult[1]
        currentArray = jsonArray;
        currentTestName = -1;
        buildFilter(jsonArray);
        currentArray = filterTable($("#search-input").val(),jsonArray);
        buildTable(currentArray, currentTestName);
        showCorrectElement(currentTestName, selectedRun2);
        updateRunSelectionText(selectedRun, selectedRun2, compareRunInformation);
    });

});

function goBackToOverview(){
    var buttonOverview = document.getElementById("button-overview");
    var buttonExpand = document.getElementById("button-expand-all");
    buttonOverview.click();
    buttonExpand.click();
}

function updateRunSelectionText(selectedRun, selectedRun2, compareRunInformation){

    function generateInfoArrow(label1, label2, count){
        return `<p class="text-center fs-5 m-0 p-0" data-bs-toggle="tooltip" data-bs-title="David Nig"><label class="text-primary">${label1}</label> &larr; <label class="text-info">prev. ${label2}</label> : ${count}</p>`;
    }

    function generateAdded(countDict){
        result = "";
        for (let key in countDict) {
            if (countDict[key] != 0){
                if (key.startsWith("P")) {
                    label = '<label class="tests-passed">';
                } else if (key.startsWith("F")) {
                    label = '<label class="tests-failed">';
                } else if (key.startsWith("I")) {
                    label = '<label class="tests-passedFailed">';
                } else {
                    label = "<label>";
                }
                result += `${label}${countDict[key]}</label> `;
            }
        }
        return result;
    }

    var paragraphInfo = document.getElementById("run-selection-information");
    var paragraph = document.getElementById("run-selection-text");
    paragraph.innerHTML = "";
    paragraphInfo.innerHTML = "";
    if (selectedRun2 == -1) {
        paragraph.innerHTML = `Show test results for <label class="text-primary">${selectedRun}</label>`;
    } else {
        paragraph.innerHTML = `Compare <label class="text-primary">${selectedRun}</label> with <label class="text-info">${selectedRun2}</label>`;
        for (let key in compareRunInformation) {
            if (compareRunInformation[key] == 0) {
                continue;
            } else {
                label1 = "";
                label2 = "";
                if (key.endsWith("P")) {
                    label1 = "Passed";
                } else if (key.endsWith("F")) {
                    label1 = "Failed";
                } else if (key.endsWith("I")) {
                    label1 = "Intended";
                } else if (key.endsWith("N")) {
                    label1 = "Not tested";
                }
                if (key.startsWith("p")) {
                    label2 = "Passed";
                } else if (key.startsWith("f")) {
                    label2 = "Failed";
                } else if (key.startsWith("i")) {
                    label2 = "Intended";
                } else if (key.startsWith("n")) {
                    label2 = "Not tested";
                }
                if (label1 != "" && label2 != "") {
                    paragraphInfo.innerHTML += generateInfoArrow(label1, label2, compareRunInformation[key]);
                } else if (key.startsWith("added")) {
                    result = generateAdded(compareRunInformation[key])
                    if (result != "") {
                        paragraphInfo.innerHTML += `<p class="text-center fs-5 m-0 p-0"><label class="text-primary">Added</label>: ${result}</p>`;
                    }
                } else if (key.startsWith("deleted") && compareRunInformation[key] > 0) {
                    paragraphInfo.innerHTML += `<p class="text-center fs-5 m-0 p-0"><label class="text-primary">Deleted</label>: ${compareRunInformation[key]}</p>`;
                }
            }
        }
    }
    information = {
        "deleted": 0,
        "unchanged": 0
    };
}

function isArrayEqual(array1, array2){
    if (array1.length != array2.length) {
        return false;
    }
    if (array1.length == 0) {
        return true;
    }
    array1.forEach(function(object) {
        if (!array2.includes(object)){
            return false;
        }
    });
    return true;
}

function updateFilter(value, jsonArray, currentArray, nodes){
    nodes.forEach(function(node) {
        // Invert checked and see if it changes the table
        node.checked = !node.checked;
        if (isArrayEqual(filterTable(value, jsonArray), currentArray)) {
            node.disabled = true;
        } else {
            node.disabled = false;
        }
        node.checked = !node.checked;
    });
}

function handleAccordion(itemId, collapse) {
    var item = document.getElementById(itemId);
    var bsCollapse = new bootstrap.Collapse(item, {
      toggle: false
    });
    if (collapse) {
        bsCollapse.hide();
    }
    else {
        bsCollapse.show();
    }
}

async function fetchData() {
    var jsonData = {};
    var runs = [];
    var resultsPath = window.location.pathname.replace(/www\/.*/, "results/");
    var nameMap = await fetch(window.location.pathname.replace(/www\/.*/, "name_map.json")).then(response => response.json());
    let data = await fetch(resultsPath).then(response => response.text());
    let fileFetchPromises = $(data).find("a").map(function() {
        var file = $(this).attr("href");
        runs.push(file);
        return fetch(`/results/${file}`).then(response => response.json());
    }).get();

    let fileDataArray = await Promise.all(fileFetchPromises);
    fileDataArray.forEach((fileData, index) => {
        var name = runs[index].replace(".json", "");
        jsonData[name] = fileData;
    });

    return [jsonData, nameMap]
}

function getTestRun(run1, run2, jsonData) {
    var result = {};
    information = {};
    if (run1 == -1 || run2 == -1) {
        if (run1 != -1) {
            result = jsonData[run1];
        } else if (run1 != -1) {
            result = jsonData[run2];
        } else {
            return;
        }
    } else {
        compareResult = compare(jsonData[run1], jsonData[run2])
        result = compareResult[0]
        information = compareResult[1]
    }
    resultArray = convertObjectToArray(result);
    if (result.hasOwnProperty('info')) {
        resultArray.splice(resultArray.length - 1, 1);
    }
    return [resultArray, information];
}

function convertObjectToArray(jsonData) {
    var jsonArray = Object.keys(jsonData).map(function (key) {
        return jsonData[key];
    });
    return jsonArray;
}

function buildRunTables(jsonData, nameMap, filter, selectedRun, selectedRun2){
    var tableBodies = document.getElementsByClassName("table-body-runs");
    tableBodies[0].innerHTML = "";
    tableBodies[1].innerHTML = "";
    const keys = Object.keys(jsonData);
    for (var i in keys) {
        var info = jsonData[keys[i]].info;

        if (!keys[i].toLowerCase().includes(filter.toLowerCase())){
            continue;
        }

        function createRow() {
            var row = document.createElement("tr");
            row.setAttribute("data-name", keys[i]);
            row.setAttribute("id", keys[i] + "-" + Math.random().toString(36).slice(2, 11));
            var cell = document.createElement("td");
            var divRow = document.createElement("div");
            divRow.classList.add("row");
            var name = document.createElement("div");
            name.classList.add("col");
            if (keys[i] in nameMap) {
                name.innerHTML = nameMap[keys[i]];
            } else {
                name.innerHTML = keys[i];
            }
            divRow.appendChild(name);
            var count = document.createElement("div");
            count.classList.add("col-md-auto");
            count.innerHTML += `${info.tests}-<label class="tests-passed">${info.passed}</label>`;
            count.innerHTML += `-<label class="tests-passedFailed">${info.passedFailed}</label>`;
            count.innerHTML += `-<label class="tests-failed">${info.failed}</label>`;
            count.innerHTML += `-<label class="tests-notTested">${info.notTested}</label>`;
            divRow.appendChild(count);
            cell.appendChild(divRow)
            row.appendChild(cell);
            return row;
        }
        tableBodies[0].appendChild(createRow());
        tableBodies[1].appendChild(createRow());
    }
    $(`#table-select-runs1 tr[data-name=${selectedRun}]`).addClass("row-selected");
    $(`#table-select-runs2 tr[data-name=${selectedRun2}]`).addClass("row-selected");
}

function buildTable(jsonArray, currentTestName){
    var tableCountContainer = document.getElementById("container-table-test-count");
    tableCountContainer.innerHTML = `Tests found: ${jsonArray.length}`
    var tableBody = document.getElementById("table-body-tests");
    tableBody.innerHTML = "";
    for (var testNumber in jsonArray) {
        var test = jsonArray[testNumber];
        var row = document.createElement("tr");
        row.setAttribute("data-name", test.name);
        row.setAttribute("id", test.name);
        if (test.name == currentTestName) {
            row.setAttribute("class", "row-selected");
        }

        var testNameCell = document.createElement("td");
        testNameCell.textContent = test.name;
        row.appendChild(testNameCell);

        var testGroupCell = document.createElement("td");
        testGroupCell.textContent = test.group;
        row.appendChild(testGroupCell);

        var testTypeCell = document.createElement("td");
        testTypeCell.textContent = test.typeName;
        row.appendChild(testTypeCell);

        var statusCell = document.createElement("td");
        statusCell.textContent = test.status;
        row.appendChild(statusCell);

        var errorTypeCell = document.createElement("td");
        errorTypeCell.textContent = test.errorType;
        row.appendChild(errorTypeCell);

        tableBody.appendChild(row);
    }
}

function buildTestInformation(testName, jsonArray, selectedRun, selectedRun2){
    var testDetails = jsonArray.find((test) => test.name === testName);
    if (selectedRun2 != -1) {
        var run1Heading = document.getElementById("heading-result1");
        var run2Heading = document.getElementById("heading-result2");
        run1Heading.innerHTML = selectedRun;
        run2Heading.innerHTML = selectedRun2;
    }
    var header = document.getElementById("test-info-header");
    var labelClass = "tests-passed";
    switch (testDetails.status) {
        case "Failed":
            labelClass = "tests-failed";
            break;
        case "Failed: Intended":
            labelClass = "tests-passedFailed";
            break;
    }
    header.innerHTML = `<p>${testDetails.name}</p><p><label class="${labelClass}">${testDetails.status}</label> ${testDetails.errorType}</p>`;

    var buttonNodes = document.querySelectorAll(`#buttons-text input`);
    buttonNodes.forEach(function(node) {
        node.checked = true;
    });

    var overviewEntries = [
        { label: "Comment", value: testDetails.comment, key: "comment", line: "True" }
    ];

    if (testDetails.typeName == "QueryEvaluationTest" || testDetails.typeName == "CSVResultFormatTest" || testDetails.typeName == "UpdateEvaluationTest") {
        if (testDetails.status != "Failed" || testDetails.errorType == "RESULTS NOT THE SAME" || testDetails.errorType == "QUERY RESULT FORMAT ERROR") {
            queryResult = [testDetails.gotHtml, testDetails.gotHtmlRed];
            expectedResult = [testDetails.expectedHtml, testDetails.expectedHtmlRed];
            queryKey = ["gotHtml", "gotHtmlRed"];
            expectedKey = ["expectedHtml", "expectedHtmlRed"];
        } else {
            queryResult = testDetails.queryLog;
            expectedResult = testDetails.resultFile;
            queryKey = "queryLog";
            expectedKey = "resultFile";
        }
        overviewEntries.push({ label: "Index File", value: testDetails.graphFile, key: "graphFile", line: "False" });
        overviewEntries.push({ label: "Query File", value: testDetails.queryFile, key: "queryFile", line: "False"  });
        overviewEntries.push({ label: "Expected Result", value: expectedResult, key: expectedKey, line: "False" });
        overviewEntries.push({ label: "Query Result", value: queryResult, key: queryKey, line: "False" });
    } else if (testDetails.typeName == "PositiveSyntaxTest11" || testDetails.typeName == "NegativeSyntaxTest11" || testDetails.typeName == "PositiveUpdateSyntaxTest11" || testDetails.typeName == "NegativeUpdateSyntaxTest11") {
        overviewEntries.push({ label: "Query File", value: testDetails.queryFile, key: "queryFile", line: "False"  });
        overviewEntries.push({ label: "Query Result", value: testDetails.queryLog, key: "gotHtml", line: "False" });
    } else if (testDetails.typeName == "ProtocolTest" || testDetails.typeName == "GraphStoreProtocolTest") {
        overviewEntries.splice(0,0);
        overviewEntries.push({ label: "Protocol", value: testDetails.protocol, key: "protocol", line: "False"  });
        overviewEntries.push({ label: "Response", value: testDetails.response, key: "response", line: "False" });
        overviewEntries.push({ label: "Protocol sent", value: testDetails.protocolSent, key: "protocolSent", line: "False"  });
        overviewEntries.push({ label: "Response Extracted", value: testDetails.responseExtracted, key: "responseExtracted", line: "False" });
    }

    if (testDetails.errorType == "INDEX BUILD ERROR") {
        overviewEntries.push({ label: "Index Build Log", value: testDetails.indexLog, key: "indexLog", line: "False"  });
    }
    if (testDetails.errorType == "SERVER ERROR") {
        overviewEntries.push({ label: "Server Status", value: testDetails.serverStatus, key: "serverStatus", line: "True" });
        overviewEntries.push({ label: "Server Log", value: testDetails.serverLog, key: "serverLog", line: "False" });
    }
    var allEntries = [
        { label: "Index File", value: testDetails.graphFile, key: "graphFile", line: "False"  },
        { label: "Index Build Log", value: testDetails.indexLog, key: "indexLog", line: "False"  },
        { label: "Query File", value: testDetails.queryFile, key: "queryFile", line: "False"  },
        { label: "Query Sent", value: testDetails.querySent, key: "querySent", line: "False"  },
        { label: "Query Log", value: testDetails.queryLog, key: "queryLog", line: "False"  },
        { label: "Server Status", value: testDetails.serverStatus, key: "serverStatus", line: "True" },
        { label: "Server Log", value: testDetails.serverLog, key: "serverLog", line: "False" },
        { label: "Expected Query Result",value: [testDetails.expectedHtml, testDetails.expectedHtmlRed], key: "expectedHtml", line: "False" },
        { label: "Query Result", value: [testDetails.gotHtml, testDetails.gotHtmlRed], key: "gotHtml", line: "False" },
        { label: "Query Filename", value: testDetails.query, key: "query", line: "True"  },
        { label: "Index Filename", value: testDetails.graph, key: "graph", line: "True" },
        { label: "Result Filename", value: testDetails.result, key: "result", line: "True"  },
        { label: "Result File", value: testDetails.resultFile, key: "resultFile", line: "False" },
        { label: "Test Type", value: testDetails.type, key: "type", line: "True" },
        { label: "Test Feature", value: testDetails.feature, key: "feature", line: "True" },
        { label: "Approval", value: testDetails.approval, key: "approval", line: "True" },
        { label: "Approved by", value: testDetails.approvedBy, key: "approvedBy", line: "True" },
        { label: "Config", value: testDetails.config, key: "configs", line: "False" }
    ];

    if (selectedRun2 == -1){
        buildHTML(overviewEntries, "container-test-overview");
        buildHTML(allEntries, "container-test-details");
    } else {
        buildHTML(overviewEntries, "container-test-overview-1");
        buildHTML(allEntries, "container-test-details-1");

        overviewEntries = replaceEntries(overviewEntries, testDetails);
        allEntries = replaceEntries(allEntries, testDetails)         
        buildHTML(overviewEntries, "container-test-overview-2");
        buildHTML(allEntries, "container-test-details-2");
    }
}

function escapeHtml(html) {
    return html.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#039;');
}

function replaceEntries(entries, testDetails){
    entries.forEach(function(entry) {
        if (Array.isArray(entry.key)) {
            entry.value = [];
            for (let keyId in entry.key) {
                entry.value.push(testDetails[entry.key[keyId] + "-run2"]);
            }
        } else {
            entry.value = testDetails[entry.key + "-run2"];
        }
    });
    return entries;
}

function buildHTML(entries, id){
    var element = document.getElementById(id);
    element.innerHTML = ""
    entries.forEach(entry => {
        if (Array.isArray(entry.value)) {
            element.innerHTML += createInfoElement(entry.label, entry.value[0], entry.value[1])
        }
        else {
            element.innerHTML += createInfoElement(entry.label, entry.value, null)
        }
    });
}

function copyObject(object){
    return JSON.parse(JSON.stringify(object));
}

function matchStatus(status, s, results){
    switch(status) {
        case "Passed":
            results[`${s}ToP`] = results[`${s}ToP`] + 1
            break;
        case "Failed: Intended":
            results[`${s}ToI`] = results[`${s}ToI`] + 1
            break;
        case "Failed":
            results[`${s}ToF`] = results[`${s}ToF`] + 1
            break;
        case "NOT TESTED":
            results[`${s}ToN`] = results[`${s}ToN`] + 1
                break;
    }
}

function compare(dict1, dict2) {
    const allKeys = new Set([...Object.keys(dict1), ...Object.keys(dict2)]);
    var result = {};
    // dict2 to dict 1 ex. pToF dict2 Passed to dict1 Failed
    var information = {
        "pToF": 0,
        "pToI": 0,
        "pToN": 0,
        "fToP": 0,
        "fToI": 0,
        "fToN": 0,
        "iToP": 0,
        "iToF": 0,
        "iToN": 0,
        "nToP": 0,
        "nToF": 0,
        "nToI": 0,
        "added": {"N": 0, "P": 0, "I": 0, "F": 0},
        "deleted": 0,
        "unchanged": 0
    };

    for (const key of allKeys) {
        if (key === "info") continue
        if (key in dict1 && key in dict2) {
            if (dict1[key]["status"] != dict2[key]["status"] || dict1[key]["errorType"] != dict2[key]["errorType"]){
                result[key] = copyObject(dict1[key]);
                for (let subKey in result[key]){
                    result[key][subKey + "-run2"] = dict2[key][subKey]
                }
            }
            if (dict1[key]["status"] != dict2[key]["status"]) {
                switch(dict2[key]["status"]) {
                    case "Passed":
                        matchStatus(dict1[key]["status"], "p", information)
                        break;
                    case "Failed: Intended":
                        matchStatus(dict1[key]["status"], "i", information)
                        break;
                    case "Failed":
                        matchStatus(dict1[key]["status"], "f", information)
                        break;
                    case "NOT TESTED":
                        matchStatus(dict1[key]["status"], "n", information)
                            break;
                }
            } else {
                information["unchanged"] = information["unchanged"] + 1
            }
        } else if (key in dict1) {
            switch(dict1[key]["status"]) {
                case "Passed":
                    information["added"]["P"] = information["added"]["P"] + 1
                    break;
                case "Failed: Intended":
                    information["added"]["I"]  = information["added"]["I"]  + 1
                    break;
                case "Failed":
                    information["added"]["F"]  = information["added"]["F"]  + 1
                    break;
                case "NOT TESTED":
                    information["added"]["N"]  = information["added"]["N"] + 1
                    break;
            }
            result[key] = copyObject(dict1[key]);
            for (let subKey in result[key]){
                result[key][subKey + "-run2"] = "Test not part of run!"
            }
        } else {
            information["deleted"] = information["deleted"] + 1
            result[key] = copyObject(dict2[key])
            for (let subKey in result[key]){
                result[key][subKey + "-run2"] = result[key][subKey]
                result[key][subKey] = "Test not part of run!"
            }
            result[key]["name"] = result[key]["name" + "-run2"]
            result[key]["group"] = result[key]["group" + "-run2"]
            result[key]["typeName"] = result[key]["typeName" + "-run2"]
        }
    }
    return [result, information];
}

function showCorrectElement(currentTestName, selectedRun2){
    $("#nothing").addClass("visually-hidden");
    $("#buttons").addClass("visually-hidden");
    $("#toggles").addClass("visually-hidden");
    $("#compare").addClass("visually-hidden");
    $("#single").addClass("visually-hidden");
    $("#test-info-header").addClass("visually-hidden");
    if (currentTestName == -1) {
        $("#nothing").removeClass("visually-hidden");
    } else {
        $("#test-info-header").removeClass("visually-hidden");
        $("#buttons").removeClass("visually-hidden");
        $("#toggles").removeClass("visually-hidden");
        if (selectedRun2 == -1) {
            $("#single").removeClass("visually-hidden");
        } else {
            $("#compare").removeClass("visually-hidden");
        }
    }
}

function createInfoElement(heading, text, text2){
    var className = ""
    if (text2 != null){
        className = "normalText"
    }
    var id = Math.random().toString(36).slice(2, 11);
    var html = `<div class="row container-info justify-content-center">`;
    html += `<div class="col-auto align-self-center">`
    html += `<a id="a-${id}" class="link-collapse" data-bs-toggle="collapse" href="#c-${id}" role="button" aria-expanded="true" aria-controls="c-${id}">`;
    html += `<p class="text-center"><strong>${heading} </strong><i class="arrow up"></i></p></a>`;
    html += `<div class="collapse show" id="c-${id}"><div class="card card-body">`;
    html += `<pre class="${className}">${text}</pre>`
    if (text2 != null){
        html += `<pre class="redText visually-hidden">${text2}</pre>`
    }
    html += `</div></div></div></div>`
    return html;
}

function addIfNotPresent(array, item) {
    if (!array.includes(item)) {
        array.push(item);
    }
    return array;
}

function buildFilter(jsonArray){
    var status = document.getElementById("container-filter-status");
    var error = document.getElementById("container-filter-error");
    var type = document.getElementById("container-filter-type");
    var group = document.getElementById("container-filter-group");
    status.innerHTML = "";
    error.innerHTML = "";
    type.innerHTML = "";
    group.innerHTML = "";
    var statusItems = []
    var errorTypeItems = []
    var testTypeItems = []
    var testGroupItems = []
    for (let testId in jsonArray) {
        statusItems = addIfNotPresent(statusItems, jsonArray[testId].status);
        errorTypeItems = addIfNotPresent(errorTypeItems, jsonArray[testId].errorType);
        testTypeItems = addIfNotPresent(testTypeItems, jsonArray[testId].typeName);
        testGroupItems = addIfNotPresent(testGroupItems, jsonArray[testId].group);
    }
    status.innerHTML = createChekboxes(statusItems);
    error.innerHTML = createChekboxes(errorTypeItems);
    type.innerHTML = createChekboxes(testTypeItems);
    group.innerHTML = createChekboxes(testGroupItems);
}

function createChekboxes(items){
    var html = "";
    for (let itemId in items) {
        html += `<div class="form-check form-check-inline">`;
        html += `<input class="form-check-input" type="checkbox" id="filter-${items[itemId].replace(/\s+/g, '')}" value="${items[itemId]}" checked>`;
        html += `<label class="form-check-label" for="filter-${items[itemId].replace(/\s+/g, '')}">${items[itemId]}</label></div>`;
    } 
    return html
}

function getCheckedValues(containerId){
    var inputNodes = document.querySelectorAll(`#${containerId} input`);
    var values = [];
    inputNodes.forEach(function(node) {
        if (node.checked) {
            values.push(node.value);
        }
    });
    return values;
}

function filterTable(value, jsonArray){
    var filteredArray = [];
    var statusFilter = getCheckedValues("container-filter-status");
    var errorFilter = getCheckedValues("container-filter-error");
    var typeFilter = getCheckedValues("container-filter-type");
    var groupFilter = getCheckedValues("container-filter-group");
    jsonArray.forEach(function(test) {
        if (!statusFilter.includes(test.status)){
            return;
        }
        if (!errorFilter.includes(test.errorType)){
            return;
        }
        if (!typeFilter.includes(test.typeName)){
            return;
        }
        if (!groupFilter.includes(test.group)){
            return;
        }
        filteredArray.push(test);
    });
    return searchTable(value, filteredArray);
}

function searchTable(value, currentArray) {
    // Keyword search, match if all keywords are found within a item of currentArray
    var searchedArray = [];
    var keywords = value.toLowerCase().split(' ');

    currentArray.forEach(function(test) {
        // Check that every keyword matches at least one property of 'test'
        var matchesAllKeywords = keywords.every(function(keyword) {
            return test.name.toLowerCase().includes(keyword) ||
                   test.status.toLowerCase().includes(keyword) ||
                   test.errorType.toLowerCase().includes(keyword) ||
                   test.typeName.toLowerCase().includes(keyword) ||
                   test.group.toLowerCase() == keyword;
        });
        if (matchesAllKeywords) {
            searchedArray.push(test);
        }
    });

    return searchedArray;
}