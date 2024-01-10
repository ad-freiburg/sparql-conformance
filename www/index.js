
$(document).ready(async function () {
    var jsonData = await fetchData();
    console.log(jsonData)
    var selectedRun = Object.keys(jsonData)[0];
    $(`#table-select-runs1 tr[data-name=${selectedRun}]`).addClass("row-selected");
    var selectedRun2 = -1;
    var jsonArray = getTestRun(selectedRun, selectedRun2, jsonData);
    var currentArray = jsonArray;
    var currentTestName = -1;
    buildRunTables(jsonData);
    buildTable(currentArray, currentTestName);
    showCorrectElement(currentTestName, selectedRun2)

    $(document).on('click', '.button-toggle', function() {
        $(`#div-${this.id}`).toggleClass("visually-hidden");
    });

    $("#button-overview").on("click", function() {
        if (selectedRun2 == -1) {
            $("#container-test-details").addClass("visually-hidden");
            $("#container-test-overview").removeClass("visually-hidden");
        } else {
            $("#container-test-details-1").addClass("visually-hidden");
            $("#container-test-overview-1").removeClass("visually-hidden");
            $("#container-test-details-2").addClass("visually-hidden");
            $("#container-test-overview-2").removeClass("visually-hidden");
        }
    });

    $("#button-details").on("click", function() {
        if (selectedRun2 == -1) {
            $("#container-test-details").removeClass("visually-hidden");
            $("#container-test-overview").addClass("visually-hidden");
        } else {
            $("#container-test-details-1").removeClass("visually-hidden");
            $("#container-test-overview-1").addClass("visually-hidden");
            $("#container-test-details-2").removeClass("visually-hidden");
            $("#container-test-overview-2").addClass("visually-hidden");
        }
    });

    $("#table-select-tests").on("click", "tr", function() {
        var testName = $(this).data("name");
        if (testName != currentTestName) {
            $("#table-select-tests tr").removeClass("row-selected");
            $(this).addClass("row-selected");
            buildTestInformation(testName, jsonArray, selectedRun, selectedRun2);
        }
        currentTestName = testName;
        showCorrectElement(currentTestName, selectedRun2)
    });

    $("#table-select-runs1").on("click", "tr", function() {
        var runName = $(this).data("name");
        $(`#table-select-runs1 tr[data-name=${selectedRun}]`).removeClass("row-selected");
        $(`#table-select-runs1 tr[data-name=${runName}]`).addClass("row-selected");
        selectedRun = runName;
        jsonArray = getTestRun(selectedRun, selectedRun2, jsonData);
        currentArray = jsonArray;
        currentTestName = -1;
        buildTable(currentArray, currentTestName);
        showCorrectElement(currentTestName, selectedRun2)
    });

    $("#table-select-runs2").on("click", "tr", function() {
        $(`#table-select-runs2 tr[data-name=${selectedRun2}]`).removeClass("row-selected");
        var runName = $(this).data("name");
        if (runName == selectedRun2){
            selectedRun2 = -1;
        } else {
            selectedRun2 = runName;
            $(`#table-select-runs2 tr[data-name=${runName}]`).addClass("row-selected");
        }
        jsonArray = getTestRun(selectedRun, selectedRun2, jsonData);
        currentArray = jsonArray;
        currentTestName = -1;
        buildTable(currentArray, currentTestName);
        showCorrectElement(currentTestName, selectedRun2)
    });

});
async function fetchData() {
    var jsonData = {};
    var runs = [];
    var resultsPath = window.location.pathname.replace(/www\/.*/, "results/");

    let data = await fetch(resultsPath).then(response => response.text());

    let fileFetchPromises = $(data).find("a").map(function() {
        var file = $(this).attr("href");
        runs.push(file);
        return fetch(`/results/${file}`).then(response => response.json());
    }).get();

    let fileDataArray = await Promise.all(fileFetchPromises);
    fileDataArray.forEach((fileData, index) => {
        var name = runs[index].replace(".json", "");
        jsonData[name] = fileData[name];
    });

    return jsonData;
}

function getTestRun(run1, run2, jsonData) {
    console.log(run1)
    console.log(run2)
    console.log(jsonData)
    var result = {};
    if (run1 == -1 || run2 == -1) {
        if (run1 != -1) {
            result = jsonData[run1];
        } else if (run1 != -1) {
            result = jsonData[run2];
        } else {
            return;
        }
    } else {
        result = compare(jsonData[run1], jsonData[run2])
    }
    resultArray = convertObjectToArray(result);
    if (result.hasOwnProperty('info')) {
        resultArray.splice(resultArray.length - 1, 1);
    }
    return resultArray;
}

function convertObjectToArray(jsonData) {
    var jsonArray = Object.keys(jsonData).map(function (key) {
        return jsonData[key];
    });
    return jsonArray;
}

function buildRunTables(jsonData){
    var tableBodies = document.getElementsByClassName("table-body-runs");
    const keys = Object.keys(jsonData);
    for (var i in keys) {
        var info = jsonData[keys[i]].info;

        function createRow() {
            var row = document.createElement("tr");
            row.setAttribute("data-name", keys[i]);
            row.setAttribute("id", keys[i] + "-" + Math.random().toString(36).slice(2, 11));
            var cell = document.createElement("td");
            var divRow = document.createElement("div");
            divRow.classList.add("row");
            var name = document.createElement("div");
            name.classList.add("col");
            name.innerHTML = keys[i];
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
}

function buildTable(jsonArray, currentTestName){
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
    var overviewEntries = [
        { label: "Test Name", value: testDetails.name, key: "name", line: "True" },
        { label: "Test Status", value: testDetails.status, key: "status", line: "True" },
        { label: "Error Type", value: testDetails.errorType, key: "errorType", line: "False" },
    ];
    if (testDetails.errorType == "RESULTS NOT THE SAME" || testDetails.errorType == "Known, intended bevaviour that does not comply with SPARQL standard") {
        overviewEntries.push({ label: "Expected Query Result", value: testDetails.expectedHtml, key: "expectedHtml", line: "False" });
        overviewEntries.push({ label: "Query Result", value: testDetails.gotHtml, key: "gotHtml", line: "False" });
    }
    if (testDetails.errorType == "QUERY EXCEPTION") {
        overviewEntries.push({ label: "Query File", value: testDetails.queryFile, key: "queryFile", line: "False" });
        overviewEntries.push({ label: "Query Log", value: testDetails.queryLog, key: "queryLog", line: "False"  });
    }

    var allEntries = [
        { label: "Test Type", value: testDetails.Type, key: "Type", line: "True" },
        { label: "Test Feature", value: testDetails.Feature, key: "Feature", line: "True" },
        { label: "Query Filename", value: testDetails.query, key: "query", line: "True"  },
        { label: "Index Filename", value: testDetails.graph, key: "graph", line: "True" },
        { label: "Index File", value: testDetails.graphFile, key: "graphFile", line: "False"  },
        { label: "Index Build Log", value: testDetails.indexLog, key: "indexLog", line: "False"  },
        { label: "Query File", value: testDetails.queryFile, key: "queryFile", line: "False"  },
        { label: "Query Sent", value: testDetails.querySent, key: "querySent", line: "False"  },
        { label: "Query Log", value: testDetails.queryLog, key: "queryLog", line: "False"  },
        { label: "Result Filename", value: testDetails.result, key: "result", line: "True"  },
        { label: "Result File", value: testDetails.resultFile.replace(/</g, "&lt;").replace(/>/g, "&gt;"), key: "resultFile", line: "False" },
        { label: "Expected Query Result", value: testDetails.expectedHtml, key: "expectedHtml", line: "False" },
        { label: "Query Result", value: testDetails.gotHtml, key: "gotHtml", line: "False" }
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

function replaceEntries(entries, testDetails){
    entries.forEach(function(entry) {
        entry.value = testDetails[entry.key + "-run2"];
    });
    return entries;
}

function buildHTML(entries, id){
    var element = document.getElementById(id);
    element.innerHTML = ""
    entries.forEach(entry => {
        if (entry.line == "True"){
            element.innerHTML += createSingleLineElement(entry.label, entry.value)
        } else {
            element.innerHTML += createElement(entry.label, entry.value)
        }
    });
}

function compare(dict1, dict2) {
    let result = {};
    for (let key in dict1) {
        if (key === "info") continue
        if (dict1[key]["status"] != dict2[key]["status"] || dict1[key]["errorType"] != dict2[key]["errorType"]){
            result[key] = dict1[key]
            for (let subKey in dict2[key]){
                result[key][subKey + "-run2"] = dict2[key][subKey]
            }
        }
    }
    return result;
}

function showCorrectElement(currentTestName, selectedRun2){
    $("#nothing").addClass("visually-hidden");
    $("#button-changeInfo").addClass("visually-hidden");
    $("#compare").addClass("visually-hidden");
    $("#single").addClass("visually-hidden");
    if (currentTestName == -1) {
        $("#nothing").removeClass("visually-hidden");
    } else {
        $("#button-changeInfo").removeClass("visually-hidden");
        if (selectedRun2 == -1) {
            $("#single").removeClass("visually-hidden");
        } else {
            $("#compare").removeClass("visually-hidden");
        }
    }
}

function createSingleLineElement(heading, text){
    var html = '<div class="row container-info">';
        html += `<div class="col heading"><strong>${heading}:</strong></div>`
        html += `<div class="col results-wrapper""><pre>${text}</pre></div>`;
    return html += '</div>';
}

function createElement(heading, text){
    var id = Math.random().toString(36).slice(2, 11);
    var html = `<div class="row container-info">`;
        html += `<div class="col heading"><strong>${heading}:</strong></div>`;
        html += `<div class="col button"><div class="button-show" class="btn-group" role="group" aria-label="Basic example">`;
        html += `<button id="${id}" type="button" class="button-toggle btn btn-primary">Show/Hide</button></div></div>`;
        html += `<div class="row"><div id="div-${id}" class="col results-wrapper visually-hidden"><pre>${text}</pre></div></div>`;
    return html;
}