// static/js/main.js
document.addEventListener('DOMContentLoaded', function () {
  const applyForm = document.querySelector('#apply-form');
  if (applyForm) {
    applyForm.addEventListener('submit', function () {
      // Simple UX hint — will show the flash message from server after redirect
      // Keep minimal here so form posts normally.
      console.log('Submitting application...');
    });
  }
});
