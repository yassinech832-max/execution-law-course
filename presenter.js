'use strict';
const presenterVideo = document.getElementById('presenter-video');
document.querySelectorAll('[data-seek]').forEach(button => {
  button.addEventListener('click', () => {
    const seek = () => {presenterVideo.currentTime = Number(button.dataset.seek); presenterVideo.focus();};
    if (presenterVideo.readyState >= 1) seek();
    else presenterVideo.addEventListener('loadedmetadata', seek, {once: true});
  });
});
