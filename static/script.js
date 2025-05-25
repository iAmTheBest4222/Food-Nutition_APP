document.addEventListener("DOMContentLoaded", function () {
  const qrForm = document.getElementById("qr-form");
  const qrInput = document.getElementById("qr-input");
  const fileNameDisplay = document.getElementById("file-name");
  const errorDisplay = document.getElementById("error-display");

  function showError(message) {
    console.error("Error:", message);
    errorDisplay.textContent = message;
    errorDisplay.classList.remove("hidden");
    setTimeout(() => {
      errorDisplay.classList.add("hidden");
    }, 5000);
  }

  function validateFile(file) {
    console.log("Validating file:", file.name, file.type, file.size);

    // Check file type
    if (!file.type.startsWith("image/")) {
      showError("Please select an image file");
      return false;
    }

    // Check file size (16MB max)
    if (file.size > 16 * 1024 * 1024) {
      showError("File size must be less than 16MB");
      return false;
    }

    return true;
  }

  function handleQRUpload(file) {
    console.log("Uploading file:", file.name);
    const formData = new FormData();
    formData.append("img_file", file);

    fetch("/", {
      method: "POST",
      body: formData,
      headers: {
        'X-Requested-With': 'XMLHttpRequest'
      }
    })
      .then((response) => {
        console.log("Response status:", response.status);
        return response.json();
      })
      .then((data) => {
        console.log("Response data:", data);
        if (data.status === "success") {
          if (data.redirect_url) {
            // Redirect to the result page
            window.location.href = data.redirect_url;
          }
        } else {
          showError(data.error || "No QR code found in image");
        }
      })
      .catch((error) => {
        console.error("Upload error:", error);
        showError("Error uploading or processing file");
      });
  }

  qrInput.addEventListener("change", function (e) {
    console.log("File input change event");

    if (qrInput.files.length > 0) {
      const file = qrInput.files[0];
      console.log("File selected:", file.name);

      if (!validateFile(file)) {
        qrInput.value = "";
        fileNameDisplay.textContent = "Upload Barcode Image";
        return;
      }

      // Update UI
      fileNameDisplay.textContent = file.name;
      fileNameDisplay.classList.add("text-green-500");

      // Process file
      handleQRUpload(file);
    } else {
      fileNameDisplay.textContent = "Upload Barcode Image";
      fileNameDisplay.classList.remove("text-green-500");
    }
  });

  // Allow form submission
  qrForm.addEventListener("submit", function (e) {
    if (qrInput.files.length === 0) {
      e.preventDefault();
      showError("Please select a file first");
    }
  });
});
