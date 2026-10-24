(() => {
  const input = document.getElementById('file-input');
  const zone = document.getElementById('drop-zone');
  const label = document.getElementById('file-label');
  const help = document.getElementById('file-help');
  if (!input || !zone) return;
  const showFile = file => {
    if (!file) return;
    label.textContent = file.name;
    help.textContent = `${(file.size / 1024).toFixed(1)} KB · Ready to upload`;
    zone.classList.add('has-file');
  };
  input.addEventListener('change', () => showFile(input.files[0]));
  ['dragenter', 'dragover'].forEach(eventName => zone.addEventListener(eventName, event => {
    event.preventDefault(); zone.classList.add('dragging');
  }));
  ['dragleave', 'drop'].forEach(eventName => zone.addEventListener(eventName, event => {
    event.preventDefault(); zone.classList.remove('dragging');
  }));
  zone.addEventListener('drop', event => {
    const files = event.dataTransfer.files;
    if (files.length) { input.files = files; showFile(files[0]); }
  });
})();
