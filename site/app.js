const examples = {
  shell: ['omztty shell', 'A familiar zsh. Thoughtful defaults. Ready when you are.'],
  ai: ['omztty ai context', 'Share a small, explicit context. Keep command execution in your hands.'],
  dots: ['omztty dot --help', 'See what will change before applying your dotfiles.']
};
for (const button of document.querySelectorAll('[data-demo]')) {
  button.addEventListener('click', () => {
    const selected = examples[button.dataset.demo];
    if (!selected) return;
    document.querySelector('#demo-command').textContent = selected[0];
    document.querySelector('#demo-description').textContent = selected[1];
    for (const item of document.querySelectorAll('[data-demo]')) item.setAttribute('aria-pressed', String(item === button));
  });
}
for (const button of document.querySelectorAll('[data-copy]')) {
  button.addEventListener('click', async () => {
    const code = document.getElementById(button.dataset.copy);
    const status = document.querySelector('#copy-status');
    if (!code) return;
    try {
      await navigator.clipboard.writeText(code.innerText);
      button.textContent = 'Copied ✓';
      status.textContent = 'Installation commands copied.';
      setTimeout(() => {button.textContent = 'Copy ⧉';}, 2000);
    } catch {
      const range = document.createRange(); range.selectNodeContents(code);
      const selection = window.getSelection(); selection.removeAllRanges(); selection.addRange(range);
      status.textContent = 'Commands selected. Copy them using your browser.';
    }
  });
}
