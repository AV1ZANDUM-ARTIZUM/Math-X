const form = document.querySelector('#proxy-form');
const input = document.querySelector('#url');
const statusBox = document.querySelector('#status');
const result = document.querySelector('#result');

function setStatus(message, error = false) {
  statusBox.hidden = false;
  statusBox.textContent = message;
  statusBox.classList.toggle('error', error);
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const target = input.value.trim();
  if (!target) return;

  try {
    const parsed = new URL(target);
    if (!['http:', 'https:'].includes(parsed.protocol)) throw new Error('Use an http:// or https:// URL.');
  } catch (err) {
    setStatus(err.message || 'Enter a valid URL.', true);
    result.hidden = true;
    return;
  }

  setStatus('Fetching…');
  result.hidden = true;

  try {
    const response = await fetch(`/proxy?url=${encodeURIComponent(target)}`);
    const type = response.headers.get('content-type') || '';
    if (!response.ok) {
      let message = `Proxy returned HTTP ${response.status}.`;
      try {
        const body = await response.json();
        if (body.error) message = body.error;
      } catch (_) {}
      throw new Error(message);
    }

    if (type.includes('text/html')) {
      const html = await response.text();
      result.srcdoc = html;
      result.hidden = false;
      setStatus('Loaded HTML response.');
    } else {
      const text = await response.text();
      result.srcdoc = `<pre style="white-space:pre-wrap;padding:20px;font:14px monospace">${escapeHtml(text)}</pre>`;
      result.hidden = false;
      setStatus(`Loaded ${type || 'response'}.`);
    }
  } catch (err) {
    setStatus(err.message || 'The proxy request failed.', true);
  }
});

document.querySelectorAll('.example').forEach(button => {
  button.addEventListener('click', () => {
    input.value = button.dataset.url;
    form.requestSubmit();
  });
});

function escapeHtml(value) {
  return value.replace(/[&<>"']/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[char]));
}
