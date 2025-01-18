document.addEventListener("DOMContentLoaded", function () {
  const qrInput = document.getElementById("qr-input");
  const fileNameDisplay = document.getElementById("file-name");

  qrInput.addEventListener("change", function () {
      if (qrInput.files.length > 0) {
          // Display the selected file name
          fileNameDisplay.textContent = qrInput.files[0].name;
          fileNameDisplay.style.color="green";
          fileNameDisplay.style.fontSize='large';
      } else {
          fileNameDisplay.textContent = " No file selected";
      }
  });
});
