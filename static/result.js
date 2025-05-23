// Result page functionality
document.addEventListener("DOMContentLoaded", function () {
  // Toast notification functionality
  const toast = document.getElementById("toast");
  const toastMessage = document.getElementById("toast-message");

  // Add animation to nutrition cards
  const nutritionCards = document.querySelectorAll(".nutrition-card");
  nutritionCards.forEach((card, index) => {
    card.style.opacity = "0";
    card.style.transform = "translateY(20px)";
    setTimeout(() => {
      card.style.transition = "all 0.5s ease";
      card.style.opacity = "1";
      card.style.transform = "translateY(0)";
    }, index * 100);
  });

  // Update sugar content meter and daily value
  const sugarContentElement = document.querySelector(".sugar-content-value");
  if (sugarContentElement) {
    const sugarText = sugarContentElement.textContent;
    const sugarValue = parseFloat(sugarText.match(/\d+(\.\d+)?/)?.[0] || 0);
    const maxSugar = 50; // Maximum daily recommended sugar intake in grams
    const percentage = (sugarValue / maxSugar) * 100;

    // Update sugar meter
    const sugarMeter = document.getElementById("sugar-level-indicator");
    if (sugarMeter) {
      sugarMeter.style.width = `${Math.min(percentage, 100)}%`;
    }

    // Update daily value percentage
    const dailyValueElement = document.getElementById("daily-value-percent");
    if (dailyValueElement) {
      dailyValueElement.textContent = `${Math.round(
        percentage
      )}% of daily value`;
    }
  }
  // Update serving size circular progress
  const servingSizeElement = document.querySelector(".serving-size-value");
  if (servingSizeElement) {
    const servingText = servingSizeElement.textContent;
    // Extract numeric value and unit from serving text (e.g., "100g" -> value: 100, unit: "g")
    const matches = servingText.match(/(\d+(?:\.\d+)?)\s*([a-zA-Z]+)/);
    if (matches) {
      const servingValue = parseFloat(matches[1]);
      const servingUnit = matches[2];

      // Set reference values based on common serving sizes
      let maxServing;
      switch (servingUnit.toLowerCase()) {
        case "g":
        case "grams":
          maxServing = 100; // 100g reference
          break;
        case "ml":
        case "milliliters":
          maxServing = 240; // Common serving size for beverages
          break;
        default:
          maxServing = 100;
      }

      const servingPercentage = Math.min(
        (servingValue / maxServing) * 100,
        100
      );

      // Update the progress circle
      const progressCircle = document.querySelector(
        ".circular-progress .progress"
      );
      if (progressCircle) {
        const circumference = 2 * Math.PI * 36; // r=36 from the SVG
        const offset =
          circumference - (servingPercentage / 100) * circumference;
        progressCircle.style.strokeDasharray = `${circumference} ${circumference}`;
        progressCircle.style.strokeDashoffset = offset;

        // Change color based on serving size percentage
        if (servingPercentage < 33) {
          progressCircle.style.stroke = "#4CAF50"; // Green for small servings
        } else if (servingPercentage < 66) {
          progressCircle.style.stroke = "#FFC107"; // Yellow for medium servings
        } else {
          progressCircle.style.stroke = "#FF4646"; // Red for large servings
        }
      }

      // Update label with percentage
      const servingSizeLabel = document.querySelector(".serving-size-label");
      if (servingSizeLabel) {
        servingSizeLabel.innerHTML = `Serving Size: ${servingText}<br><span class="text-sm text-gray-400">${Math.round(
          servingPercentage
        )}% of reference serving</span>`;
      }
    }
  }

  window.showToast = function (message, duration = 3000) {
    toastMessage.textContent = message;
    toast.style.display = "block";
    setTimeout(() => {
      toast.style.display = "none";
    }, duration);
  };

  // Extract sugar content value for the meter
  const sugarContent = document.querySelector(".sugar-content-value");
  if (sugarContent) {
    const sugarValue = parseFloat(sugarContent.textContent);
    const maxSugar = 50; // Maximum daily recommended sugar intake in grams
    const percentage = (sugarValue / maxSugar) * 100;

    // Update sugar meter
    const sugarMeter = document.querySelector(".sugar-level");
    if (sugarMeter) {
      sugarMeter.style.width = `${Math.min(percentage, 100)}%`;
    }
  }

  // Save to History button functionality
  const saveButton = document.querySelector('button[title="Save to History"]');
  if (saveButton) {
    saveButton.addEventListener("click", function () {
      showToast("Result saved to history successfully!");
    });
  }

  // Share Results button functionality
  const shareButton = document.querySelector('button[title="Share Results"]');
  if (shareButton) {
    shareButton.addEventListener("click", function () {
      const productName = document
        .querySelector("h3.text-2xl")
        .textContent.trim();
      const shareData = {
        title: "FoodScan Result",
        text: `Check out ${productName}'s sugar content analysis!`,
        url: window.location.href,
      };

      if (navigator.share) {
        navigator
          .share(shareData)
          .then(() => showToast("Shared successfully!"))
          .catch(() => showToast("Error sharing result"));
      } else {
        showToast("Sharing not supported in this browser");
      }
    });
  }

  // Scan Another button functionality
  const scanButton = document.querySelector('button[title="Scan Another"]');
  if (scanButton) {
    scanButton.addEventListener("click", function () {
      window.location.href = "UI.html";
    });
  }

  // Initialize Chart.js for the comparison chart
  const chartContainer = document.getElementById("comparison-chart");
  if (chartContainer) {
    const ctx = chartContainer.getContext("2d");
    const sugarValue =
      parseFloat(document.querySelector(".sugar-content-value")?.textContent) ||
      0;

    new Chart(ctx, {
      type: "bar",
      data: {
        labels: ["Your Product", "Average", "Lowest", "Highest"],
        datasets: [
          {
            label: "Sugar Content (g)",
            data: [sugarValue, 15, 5, 25],
            backgroundColor: [
              "rgba(255, 70, 70, 1)", // Primary color
              "rgba(255, 255, 255, 0.2)",
              "rgba(255, 255, 255, 0.2)",
              "rgba(255, 255, 255, 0.2)",
            ],
            borderColor: [
              "rgba(255, 70, 70, 1)",
              "rgba(255, 255, 255, 0.2)",
              "rgba(255, 255, 255, 0.2)",
              "rgba(255, 255, 255, 0.2)",
            ],
            borderWidth: 1,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: true,
            grid: {
              color: "rgba(255, 255, 255, 0.1)",
            },
            ticks: {
              color: "rgba(255, 255, 255, 0.7)",
            },
          },
          x: {
            grid: {
              display: false,
            },
            ticks: {
              color: "rgba(255, 255, 255, 0.7)",
            },
          },
        },
        plugins: {
          legend: {
            labels: {
              color: "rgba(255, 255, 255, 0.7)",
            },
          },
        },
      },
    });
  }
});
