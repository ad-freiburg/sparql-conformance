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
        <strong>${entry.name}</strong> - Status: <span class="status">${entry.status}</span>
        <div class="item-details">
        <p><strong>Test:</strong> <a href="${entry.test}" target="_blank">${entry.test}</a></p>
        <p><strong>Type:</strong> ${entry.type}</p>
        <p><strong>Feature:</strong> ${entry.feature}</p>
        <p><strong>Error Type:</strong> ${entry.errorType}</p>
        <p><strong>Error Message:</strong> ${entry.errorMessage}</p>
        </div>
        `;
        resultIndex.innerHTML = `
        <div class="item-details">
            <p><strong>Index Filename:</strong> <pre>${entry.graph}</pre></p>
            <p><strong>Index File:</strong> <pre>${entry.graphFile}</pre></p>
            <p><strong>Index Log:</strong> <pre>${entry.indexLog}</pre></p>
        </div>
        `;
        resultResults.innerHTML = `
        <div class="item-details">
        <p><strong>Expected:</strong> <pre>${entry.expected}</pre></p>
        <p><strong>Got:</strong> <pre>${entry.got}</pre></p>
        <p><strong>Difference</strong></p>
        <p><strong>Expected:</strong> <pre>${entry.expectedDif}</pre></p>
        <p><strong>Got:</strong> <pre>${entry.resultDif}</pre></p>
        </div>
        `;
        resultQuery.innerHTML = `
        <div class="item-details">
        <p><strong>Query Filename:</strong> <pre>${entry.query}</pre></p>
        <p><strong>Query File:</strong> <pre>${entry.queryFile}</pre></p>
        <p><strong>Result Filename:</strong> <pre>${entry.result}</pre></p>
        <p><strong>Result File:</strong> <pre>${entry.resultFile}</pre></p>
        <p><strong>Query Sent:</strong> <pre>${entry.querySent}</pre></p>
        <p><strong>Query Log:</strong> <pre>${entry.queryLog}</pre></p>
        </div>
        `;
    }
})
.catch(error => {
    console.error("Error fetching data:", error);
});
 