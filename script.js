fetch('RESULTS.json')
  .then(response => response.json())
  .then(jsonData => {
    const entries = Object.entries(jsonData);
    let passedCount = 0;
    let failedCount = 0;

    const container = document.createElement('div');
    container.classList.add('data-container');

    entries.forEach(([key, entry]) => {
      if (entry.status === "Passed") {
        passedCount++;
      } else if (entry.status === "Failed") {
        failedCount++;
      }

      const itemElement = document.createElement('div');
      itemElement.classList.add('item');
      
      // Add a CSS class based on the status
      if (entry.status === "Passed") {
        itemElement.classList.add('status-passed');
      } else if (entry.status === "Failed") {
        itemElement.classList.add('status-failed');
      }
      itemElement.innerHTML = `
        <strong>${entry.name}</strong> - Status: <span class="status">${entry.status}</span>
        <div class="item-details">
          <p><strong>Test:</strong> <a href="${entry.test}" target="_blank">${entry.test}</a></p>
          <p><strong>Type:</strong> ${entry.type}</p>
          <p><strong>Feature:</strong> ${entry.feature}</p>
          <p><strong>Error Type:</strong> ${entry.errorType}</p>
          <p><strong>Error Message:</strong> ${entry.errorMessage}</p>
          <p><strong>Expected:</strong> <pre>${entry.expected}</pre></p>
          <p><strong>Got:</strong> <pre>${entry.got}</pre></p>
          <p><strong>Index Log:</strong> <pre>${entry.indexLog}</pre></p>
          <p><strong>Server Log:</strong> <pre>${entry.serverLog}</pre></p>
          <p><strong>Server Status:</strong> <pre>${entry.serverStatus}</pre></p>
          <p><strong>Query Log:</strong> <pre>${entry.queryLog}</pre></p>
        </div>
      `;
      // Toggle item details on click
      itemElement.addEventListener('click', () => {
        const itemDetails = itemElement.querySelector('.item-details');
        itemDetails.style.display = itemDetails.style.display === 'block' ? 'none' : 'block';
      });
      
      container.appendChild(itemElement);
    });
    const passedCountElement = document.getElementById('passedCount');
    const failedCountElement = document.getElementById('failedCount');
    passedCountElement.textContent = passedCount;
    failedCountElement.textContent = failedCount;

    const outputContainer = document.getElementById('output-container');
    outputContainer.appendChild(container);
  })
  .catch(error => {
    console.error("Error loading JSON file:", error);
  });
