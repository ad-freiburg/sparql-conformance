$(document).ready(async function () {
    var jsonData = await fetch("RESULTS.json").then(response => response.json());
    var selectedRun = Object.keys(jsonData)[0];
    var selectedRun2 = -1;
    var jsonArray = getTestRun(selectedRun, selectedRun2, jsonData);
    var currentArray = jsonArray;
    var currentTestName = -1;
    buildTable(currentArray, currentTestName);
    buildRunTable(jsonData);

    $("#"+selectedRun).addClass("row-selected");
    $("#result-wrapper-general").hide();
    $("#result-wrapper-server").hide();
    $("#result-wrapper-index").hide();
    $("#result-wrapper-query").hide();

    $("#test-table").on("click", "th", function(){
        var column = $(this).data("column");
        var order = $(this).data("order");
        if(order == "desc"){
            $(this).data("order", "asc");
            currentArray = currentArray.sort((a,b) => a[column] > b[column] ? 1 : -1);
        }else{
            $(this).data("order", "desc")
            currentArray = currentArray.sort((a,b) => a[column] < b[column] ? 1 : -1);
        }
        buildTable(currentArray, currentTestName);
    });

    $("#test-table").on("click", "tr", function() {
        var testName = $(this).data("name");
        if (testName != currentTestName) {
            $("#test-table tr").removeClass("row-selected");
            $(this).addClass("row-selected");
            buildTestInformation(testName, jsonArray, selectedRun, selectedRun2);
        }
        currentTestName = testName;
    });

    $("#select-run-table").on("click", "tr", async function() {
        var runName = $(this).data("name");
        if (runName == selectedRun) {
            $(this).removeClass("row-selected");
            selectedRun = selectedRun2;
            selectedRun2 = -1
        } else if (runName == selectedRun2) {
            $(this).removeClass("row-selected");
            selectedRun2 = -1;
        } else if (selectedRun == -1) {
            selectedRun = runName;
            $(this).addClass("row-selected");
        } else if (selectedRun2 == -1) {
            selectedRun2 = runName;
            $(this).addClass("row-selected");
        } else {
            return;
        }
        $("button").removeClass("button-pressed");
        $("#result-wrapper-general").hide();
        $("#result-wrapper-server").hide();
        $("#result-wrapper-index").hide();
        $("#result-wrapper-query").hide();
        jsonArray = getTestRun(selectedRun, selectedRun2, jsonData);
        currentArray = jsonArray
        currentTestName = -1
        buildTable(currentArray, currentTestName);
    });
    
    $("button").on("click", function() {
        $("button").removeClass("button-pressed");
        $(this).addClass("button-pressed");
        $("#result-wrapper-general").hide();
        $("#result-wrapper-server").hide();
        $("#result-wrapper-index").hide();
        $("#result-wrapper-query").hide();
        buttonId = $(this).attr("id");
        switch (buttonId) {
            case "general":
                $("#result-wrapper-general").show();
                break;
            case "server":
                $("#result-wrapper-server").show();
                break;
            case "index":
                $("#result-wrapper-index").show();
                break;
            case "query":
                $("#result-wrapper-query").show();
                break;
            default:
                break;
        }
    });
    
    $("#search-input").on("keyup", function(){
        var value = $(this).val();
        var mode = $("#search-mode").val();
        currentArray = searchTable(value, mode, jsonArray);
        buildTable(currentArray, currentTestName);
    });
});

function getTestRun(run1, run2, jsonData) {
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

function searchTable(value, mode, jsonArray){
    var newArray = [];

    for (var i = 0; i < jsonArray.length; i++){
        value = value.toLowerCase();
        var search;
        switch (mode) {
            case "name":
                search = jsonArray[i].name.toLowerCase();
                break;
            case "errorType":
                search = jsonArray[i].errorType.toLowerCase();
                break;
            case "typeName":
                search = jsonArray[i].typeName.toLowerCase();
                break;
            case "status":
                search = jsonArray[i].status.toLowerCase();
                break;
            default:
                search = "name"; 
        }
        if (search.includes(value)){
            newArray.push(jsonArray[i]);
        }
    }
    return newArray;
}

function buildRunTable(jsonData){
    var tableBody = document.getElementById("table-body-runs");
    const keys = Object.keys(jsonData);
    for (var i in keys) {
        var info = jsonData[keys[i]].info;
        var row = document.createElement("tr");
        row.setAttribute("data-name", keys[i]);
        row.setAttribute("id", keys[i]);
        var testNameCell = document.createElement("td");
        testNameCell.textContent = keys[i];
        row.appendChild(testNameCell);
        var testTestsCell = document.createElement("td");
        testTestsCell.textContent = info.tests;
        row.appendChild(testTestsCell);
        var testPassedCell = document.createElement("td");
        testPassedCell.textContent = info.passed;
        row.appendChild(testPassedCell);
        var testPassedFailedCell = document.createElement("td");
        testPassedFailedCell.textContent = info.passedFailed;
        row.appendChild(testPassedFailedCell);
        var testFailedCell = document.createElement("td");
        testFailedCell.textContent = info.failed;
        row.appendChild(testFailedCell);
        var testNotTestedCell = document.createElement("td");
        testNotTestedCell.textContent = info.notTested;
        row.appendChild(testNotTestedCell);

        tableBody.appendChild(row);
    }
}

function buildTable(jsonArray, currentTestName){
    var tableBody = document.getElementById("table-body");
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
    var testDetails = jsonArray.find((test) => test.name === testName);
    if (typeof testDetails === "undefined")
        return;
    var resultGeneral = document.getElementById("result-wrapper-general");
    var resultIndex = document.getElementById("result-wrapper-index");
    var resultResults = document.getElementById("result-wrapper-server");
    var resultQuery = document.getElementById("result-wrapper-query");

    var generalEntries = [
        { label: "Test Name", value: testDetails.name, key: "name" },
        { label: "Test Status", value: testDetails.status, key: "status" },
        { label: "Error Type", value: testDetails.errorType, key: "errorType" },
    ];
    if (testDetails.errorType == "RESULTS NOT THE SAME" || testDetails.errorType == "Known, intended bevaviour that does not comply with SPARQL standard") {
        generalEntries.push({ label: "Expected Query Result", value: testDetails.expectedHtml, key: "expectedHtml" });
        generalEntries.push({ label: "Query Result", value: testDetails.gotHtml, key: "gotHtml" });
    }
    if (testDetails.errorType == "QUERY EXCEPTION") {
        generalEntries.push({ label: "Query File", value: testDetails.queryFile, key: "queryFile" });
        generalEntries.push({ label: "Query Log", value: testDetails.queryLog, key: "queryLog"  });
    }
    //{ label: "Test Type", value: testDetails.Type, key: "Type" },
    //{ label: "Test Feature", value: testDetails.Feature, key: "Feature" },
    const indexEntries = [
        { label: "Index Filename", value: testDetails.graph, key: "graph" },
        { label: "Index File", value: testDetails.graphFile, key: "graphFile" },
        { label: "Index Build Log", value: testDetails.indexLog, key: "indexLog" }
    ];

    const resultsEntries = [
        { label: "Expected Query Result", value: testDetails.expectedHtml, key: "expectedHtml" },
        { label: "Query Result", value: testDetails.gotHtml, key: "gotHtml" },
        { label: "Expected result after comparing", value: testDetails.expectedDif, key: "expectedDif" },
        { label: "Query result after comparing", value: testDetails.resultDif, key: "resultDif" }
    ];
    const queryEntries = [
        { label: "Query Filename", value: testDetails.query, key: "query"  },
        { label: "Query File", value: testDetails.queryFile, key: "queryFile"  },
        { label: "Result Filename", value: testDetails.result, key: "result"  },
        { label: "Result File", value: testDetails.resultFile.replace(/</g, "&lt;").replace(/>/g, "&gt;"), key: "resultFile" },
        { label: "Query Sent", value: testDetails.querySent, key: "querySent"  },
        { label: "Query Log", value: testDetails.queryLog, key: "queryLog"  },
    ];

    resultGeneral.innerHTML = generateHTML(testDetails, generalEntries, selectedRun, selectedRun2);
    resultIndex.innerHTML = generateHTML(testDetails, indexEntries, selectedRun, selectedRun2);
    resultResults.innerHTML = generateHTML(testDetails, resultsEntries, selectedRun, selectedRun2);
    resultQuery.innerHTML = generateHTML(testDetails, queryEntries, selectedRun, selectedRun2);
}

function generateHTML(testDetails, entries, selectedRun, selectedRun2) {
    if (selectedRun2 == -1) {
        return generateEntry(testDetails, entries, false);
    }
    var html = "<table><thead><th>" + selectedRun + "</th><th>" + selectedRun2 + "</thead>";
    html += "<td>" + generateEntry(testDetails, entries, false) + "</td>";
    html += "<td>" + generateEntry(testDetails, entries, true) + "</td>";
    return html += '</table>';
}

function generateEntry(testDetails, entries, secondRun) {
    var html = '<div class="topic-wrapper">';
    entries.forEach(entry => {
        html += `<p class="heading"><strong>${entry.label}:</strong></p>`
        if (secondRun && testDetails.hasOwnProperty(`${entry.key}-run2`)) {
            html += `<div class="results-wrapper" id="${entry.key}"><pre>${testDetails[`${entry.key}-run2`]}</pre></div>`;
        } else {
        html += `<div class="results-wrapper" id="${entry.key}"><pre>${entry.value}</pre></div>`;
        }
    });
    return html += '</div>';
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