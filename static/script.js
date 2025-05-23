document.addEventListener("DOMContentLoaded", function () {
  const qrInput = document.getElementById("qr-input");
  const fileNameDisplay = document.getElementById("file-name");

  qrInput.addEventListener("change", function () {
    if (qrInput.files.length > 0) {
      // Display the selected file name
      fileNameDisplay.textContent = qrInput.files[0].name;
      fileNameDisplay.classList.add("text-green-500"); // Tailwind green text color
    } else {
      fileNameDisplay.textContent = "Upload Barcode Image";
      fileNameDisplay.classList.remove("text-green-500");
    }
  });
});
