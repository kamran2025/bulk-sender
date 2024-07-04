
document.getElementById('uploadForm').addEventListener('submit', function (event) {
  event.preventDefault();

  const formData = new FormData();
  const fileInput = document.getElementById('file');
  const messageInput = document.getElementById('message').value;
  let messageStatus = document.getElementById('status');
  messageStatus.firstElementChild.classList.remove('d-none');
  messageStatus.firstElementChild.classList.add('d-flex');

  formData.append('file', fileInput.files[0]);
  formData.append('message', messageInput);

  fetch('/upload', {
    method: 'POST',
    body: formData,
  })
    .then(response => response.text())
    .then(data => {
      messageStatus.firstElementChild.classList.remove('d-flex');
      messageStatus.firstElementChild.classList.add('d-none');
      messageStatus.innerText = data;
    })
    .catch(error => {
      console.error('Error:', error);
      document.getElementById('status').innerText = 'Failed to send messages.';
    });
});
