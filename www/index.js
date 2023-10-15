fetch("RESULTS.json")
.then(response => response.json())
.then(jsonData => {

    var jsonArray = Object.keys(jsonData).map(function (key) {
        return jsonData[key];
    });
    var currentArray = jsonArray
    var currentTestName = -1
    $("#result-wrapper-general").hide()
    $("#result-wrapper-server").hide()
    $("#result-wrapper-index").hide()
    $("#result-wrapper-query").hide()
    buildTable(currentArray)
    $("table").on("click", "th", function(){
		var column = $(this).data("column")
		var order = $(this).data("order")
		if(order == "desc"){
			$(this).data("order", "asc")
			currentArray = currentArray.sort((a,b) => a[column] > b[column] ? 1 : -1)

		}else{
			$(this).data("order", "desc")
			currentArray = currentArray.sort((a,b) => a[column] < b[column] ? 1 : -1)

		}
		buildTable(currentArray)
	})

    $("table").on("click", "tr", function() {
        var testName = $(this).data("name")
        if (typeof testName === "undefined")
            return
        if (testName != currentTestName) {
            $("tr").removeClass("row-selected")
            $(this).addClass("row-selected")
            buildTestInformation(testName)
        }
        currentTestName= testName
	})

    $("button").on("click", function() {
        $("button").removeClass("button-pressed");
        $(this).addClass("button-pressed")
        $("#result-wrapper-general").hide()
        $("#result-wrapper-server").hide()
        $("#result-wrapper-index").hide()
        $("#result-wrapper-query").hide()
        buttonId = $(this).attr("id")
        switch (buttonId) {
            case "general":
                $("#result-wrapper-general").show()
                break;
            case "server":
                $("#result-wrapper-server").show()
                break;
            case "index":
                $("#result-wrapper-index").show()
                break;
            case "query":
                $("#result-wrapper-query").show()
                break;
            default:
                break;
        }
	})


    $("#search-input").on("keyup", function(){
        var value = $(this).val()
        var mode = $("#search-mode").val()
        searchTable(value, mode)
        buildTable(currentArray)
	})
    function searchTable(value, mode){
        var newArray = []

        for (var i = 0; i < jsonArray.length; i++){
            value = value.toLowerCase()
            var search
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
                newArray.push(jsonArray[i])
            }
        }
        currentArray = newArray
    }
    
    function buildTable(jsonArray){
        var tableBody = document.getElementById("table-body");
        tableBody.innerHTML = ""
        for (var testNumber in jsonArray) {
            var test = jsonArray[testNumber]
            var row = document.createElement("tr");
            row.setAttribute("data-name", test.name);
            row.setAttribute("id", test.name);
            if (test.name == currentTestName) {
                row.setAttribute("class", "row-selected")
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
    function buildTestInformation(testName){
        var entry = jsonArray.find((test) => test.name === testName)
        if (typeof entry === "undefined")
            return
        var resultGeneral = document.getElementById("result-wrapper-general")
        var resultIndex = document.getElementById("result-wrapper-index")
        var resultResults = document.getElementById("result-wrapper-server")
        var resultQuery = document.getElementById("result-wrapper-query")


        resultGeneral.innerHTML = `
        <div class="topic-wrapper">
            <p class="heading"><strong>Test Name:</strong></p>
            <div class="results-wrapper"><pre>${entry.name}</pre></div>
            <p class="heading"><strong>Test Status:</strong></p>
            <div class="results-wrapper"><pre>${entry.status}</pre></div>
            <p class="heading"><strong>Test:</strong></p>
            <div class="results-wrapper"><pre>${entry.test}</pre></div>
            <p class="heading"><strong>Test Type:</strong></p>
            <div class="results-wrapper"><pre>${entry.Type}</pre></div>
            <p class="heading"><strong>Test Feature:</strong></p>
            <div class="results-wrapper"><pre>${entry.Feature}</pre></div>
            <p class="heading"><strong>Error Type:</strong></p>
            <div class="results-wrapper"><pre>${entry.errorType}</pre></div>
            <p class="heading"><strong>Test Feature:</strong></p>
            <div class="results-wrapper"><pre>${entry.Feature}</pre></div>
        </div>
        `;
        resultIndex.innerHTML = `
        <div class="topic-wrapper">
            <p class="heading"><strong>Index Filename:</strong></p>
            <div class="results-wrapper"><pre>${entry.graph}</pre></div>
            <p class="heading"><strong>Index File:</strong></p>
            <div class="results-wrapper"><pre>${entry.graphFile}</pre></div>
            <p class="heading"><strong>Index Build Log:</strong></p>
            <div class="results-wrapper"><pre>${entry.indexLog}</pre></div>
        </div>
        `;
        resultResults.innerHTML = `
        <div class="topic-wrapper">
            <p class="heading"><strong>Expected Query Result:</strong></p>
            <div class="results-wrapper"><pre>${entry.expected}</pre></div>
            <p class="heading"><strong>Query Result:</strong></p>
            <div class="results-wrapper"><pre>${entry.got}</pre></div>
            <p class="heading"><strong><b>Difference</b></strong></p>
            <p class="heading"><strong>Expected result after comparing:</strong></p>
            <div class="results-wrapper"><pre>${entry.expectedDif}</pre></div>
            <p class="heading"><strong>Query result after comparing:</strong></p>
            <div class="results-wrapper"><pre>${entry.resultDif}</pre></div>
        </div>
        `;
        resultQuery.innerHTML = `
        <div class="topic-wrapper">
            <p class="heading"><strong>Query Filename:</strong></p>
            <div class="results-wrapper"><pre>${entry.query}</pre></div>
            <p class="heading"><strong>Query File:</strong></p>
            <div class="results-wrapper"><pre>${entry.queryFile}</pre></div>
            <p class="heading"><strong>Result Filename:</strong></p>
            <div class="results-wrapper"><pre>${entry.result}</pre></div>
            <p class="heading"><strong>Result File:</strong></p>
            <div class="results-wrapper"><pre>${entry.resultFile}</pre></div>
            <p class="heading"><strong>Query Sent:</strong></p>
            <div class="results-wrapper"><pre>${entry.querySent}</pre></div>
            <p class="heading"><strong>Query Log:</strong></p>
            <div class="results-wrapper"><pre>${entry.queryLog}</pre></div>
            <p class="heading"><strong>Test Feature:</strong></p>
            <div class="results-wrapper"><pre>${entry.Feature}</pre></div>
        </div>
        `;
    }
})
.catch(error => {
    console.error("Error fetching data:", error);
});
 