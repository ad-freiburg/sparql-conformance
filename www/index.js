$(document).ready(async function () {
    var jsonData = await fetch("RESULTS.json").then(response => response.json());
    var selectedRun = Object.keys(jsonData)[0];
    var selectedRun2 = -1;
    var jsonArray = await getTestRun(selectedRun, selectedRun2, jsonData);
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
            buildTestInformation(testName, jsonArray);
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
        jsonArray = await getTestRun(selectedRun, selectedRun2, jsonData);
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
        searchTable(value, mode);
        buildTable(currentArray, currentTestName);
    });
});

async function fetchJSON(url) {
    try {
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error('Response error');
      }
      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error fetching data:', error);
      throw error;
    }
}

async function getTestRun(run1, run2, jsonData) {
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
        result = await fetch("/compare=" + run1 + "+" + run2).then(response => response.json());
    }
    return convertObjectToArray(result);
}

function convertObjectToArray(jsonData) {
    var jsonArray = Object.keys(jsonData).map(function (key) {
        return jsonData[key];
    });
    return jsonArray;
}

function searchTable(value, mode){
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
    currentArray = newArray;
}

function buildRunTable(jsonData){
    var tableBody = document.getElementById("table-body-runs");
    const keys = Object.keys(jsonData);
    for (var i in keys) {
        var row = document.createElement("tr");
        row.setAttribute("data-name", keys[i]);
        row.setAttribute("id", keys[i]);
        var testNameCell = document.createElement("td");
        testNameCell.textContent = keys[i];
        row.appendChild(testNameCell);

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

function buildTestInformation(testName, jsonArray){
    var entry = jsonArray.find((test) => test.name === testName);
    if (typeof entry === "undefined")
        return;
    var resultGeneral = document.getElementById("result-wrapper-general");
    var resultIndex = document.getElementById("result-wrapper-index");
    var resultResults = document.getElementById("result-wrapper-server");
    var resultQuery = document.getElementById("result-wrapper-query");

    const generalEntries = [
        { label: "Test Name", value: entry.name, key: "name" },
        { label: "Test Status", value: entry.status, key: "status" },
        { label: "Test", value: entry.test, key: "test" },
        { label: "Test Type", value: entry.Type, key: "Type" },
        { label: "Test Feature", value: entry.Feature, key: "Feature" },
        { label: "Error Type", value: entry.errorType, key: "errorType" },
        { label: "Another Test Feature", value: entry.Feature, key: "Feature" }
    ];

    const indexEntries = [
        { label: "Index Filename", value: entry.graph, key: "graph" },
        { label: "Index File", value: entry.graphFile, key: "graphFile" },
        { label: "Index Build Log", value: entry.indexLog, key: "indexLog" }
    ];

    const resultsEntries = [
        { label: "Expected Query Result", value: entry.expected, key: "expected" },
        { label: "Query Result", value: entry.got, key: "got" },
        { label: "Expected result after comparing", value: entry.expectedDif, key: "expectedDif" },
        { label: "Query result after comparing", value: entry.resultDif, key: "resultDif" }
    ];

    const queryEntries = [
        { label: "Query Filename", value: entry.query, key: "query"  },
        { label: "Query File", value: entry.queryFile, key: "queryFile"  },
        { label: "Result Filename", value: entry.result, key: "result"  },
        { label: "Result File", value: entry.resultFile, key: "resultFile" },
        { label: "Query Sent", value: entry.querySent, key: "querySent"  },
        { label: "Query Log", value: entry.queryLog, key: "queryLog"  },
        { label: "Test Feature", value: entry.Feature, key: "Feature"  }
    ];

    resultGeneral.innerHTML = generateHTML(generalEntries);
    resultIndex.innerHTML = generateHTML(indexEntries);
    resultResults.innerHTML = generateHTML(resultsEntries);
    resultQuery.innerHTML = generateHTML(queryEntries);
    for (const k in entry) {
        if (entry.hasOwnProperty(k)) {
            if (k.includes("-")) {
                const parts = k.split("-");
                var div = document.getElementById(parts[0]);
                if (div != null) {
                    div.innerHTML += `<pre class="format-difference">${entry[k]}</pre>`
                }
            }
        }
    }
}

function generateHTML(entries) {
    var html = '<div class="topic-wrapper">';
    entries.forEach(entry => {
        if (entry.value != "") {
            html += `
            <p class="heading"><strong>${entry.label}:</strong></p>
            <div class="results-wrapper" id="${entry.key}"><pre>${entry.value}</pre></div>
        `;
        }
    });
    return html += '</div>';
}